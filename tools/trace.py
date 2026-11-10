"""Step 0 requirement registration checks; no runtime or pytest dependency."""

import argparse
import ast
import json
from pathlib import Path
import re
import fnmatch
import hashlib
import os
import subprocess
import sys
import shutil
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC_FILES = ("10_SPEC.md", "20_SHELL.md", "25_PACKAGING.md")
REQ_PATTERN = re.compile(r"REQ-[A-Z]+-[A-Za-z0-9]+")
TEST_PATTERN = re.compile(
    r"test_((?:T_(?:GEN|SNF|TRI|CLS|SEL|PLN|CNV|RND|LKP|APR|TRX|ASM|WRT|RPT|CTR|MAP|SEC|CLI|META)_\d{2}|CT_\d{2}|PT_\d{2}))(?:_|$)"
)


def requirement_registry(root: Path) -> dict[str, dict]:
    """Read definitions only, excluding deleted requirements and prose mentions."""
    definitions = {}
    for name in SPEC_FILES:
        path = root / "docs" / "renewal" / name
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^(?:- )?(REQ-[A-Z]+-[A-Za-z0-9]+)\b(.*)", line)
            if not match or re.match(r"\s*\(deleted\b", match[2], re.IGNORECASE):
                continue
            if match[1] in definitions:
                raise ValueError(f"Duplicate definition: {match[1]}")
            definitions[match[1]] = {"path": path.relative_to(root).as_posix(), "line": number}
    if not definitions:
        raise ValueError("No requirement definitions found")
    return definitions


def test_id(name: str) -> str:
    match = TEST_PATTERN.match(name)
    return match[1].replace("_", "-") if match else ""


def discover_tests(root: Path) -> list[dict]:
    """Read actual Python decorators, never treating the planned catalog as coverage.

    This is the Python registration view; discover_shell_tests supplies Jest's
    separate registration view. Execution uses the collected per-JUnit inventory.
    """
    tests = []
    for path in sorted((root / "engine" / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        def visit(node: ast.AST, inherited: dict, scope: str) -> None:
            markers = {key: list(value) for key, value in inherited.items()}
            for decorator in getattr(node, "decorator_list", []):
                if isinstance(decorator, ast.Attribute) and ast.unparse(decorator) in {
                        'pytest.mark.release', 'pytest.mark.soffice'}:
                    markers[decorator.attr] = [[]]
                if not isinstance(decorator, ast.Call):
                    continue
                name = ast.unparse(decorator.func)
                if not name.startswith("pytest.mark."):
                    continue
                key = name.removeprefix("pytest.mark.")
                if key in {"req", "cov", "fx", "plat", 'scope', 'cells'}:
                    markers.setdefault(key, []).append([ast.literal_eval(arg) for arg in decorator.args])
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    tests.append({
                        "nodeid": f"{path.relative_to(root).as_posix()}::{scope}{node.name}",
                        "tid": test_id(node.name),
                        "markers": markers,
                    })
                return
            for child in getattr(node, "body", []):
                visit(child, markers, scope + node.name + "::" if isinstance(node, ast.ClassDef) else scope)

        visit(tree, {}, "")
    return tests


def marker_values(test: dict, name: str) -> list:
    return [value for group in test["markers"].get(name, []) for value in group]


def test_classes(test: dict, classes: dict, *, include_schema=False) -> set[str]:
    """Only actual fixture consumption contributes to the execution projection.

    The compatibility registration projection may include schema equivalences;
    it is explicitly separate from execution and never a passing-test claim.
    """
    if not include_schema and 'schema' in marker_values(test, 'scope'):
        return set()
    fixtures = set(marker_values(test, 'fx'))
    stages = {cell[0] for cell in test['markers'].get('cov', []) if len(cell) == 2}
    if 'all' in fixtures and stages <= {'S0', 'S1', 'S2', 'S3', 'S13'} and stages:
        return set(MATRIX_CLASSES)
    return set().union(*(classes.get(f, set()) for f in fixtures if f != 'all'))


def extra_cells(test: dict, *, include_schema=False) -> set[tuple[str, str]]:
    """(class, stage) cells registered by `@pytest.mark.cells("K02:S7", ...)` (M2-H class sweep).

    A class sweep drives every class through the real pipeline in one parametrized test, so it reaches several
    stages per class while the one primary `cov` cell stays unique. The marker is the explicit, literal list of
    those additional cells; the sweep test asserts that its per-class table and this marker agree.
    """
    if not include_schema and 'schema' in marker_values(test, 'scope'):
        return set()
    cells = set()
    for value in marker_values(test, 'cells'):
        match = re.fullmatch(r"(K\d{2}):(S(?:[0-9]|1[0-3]))", str(value))
        if match:
            cells.add((match[1], match[2]))
    return cells


def coverage_problems(requirements: dict, tests: list[dict]) -> dict[str, list[str]]:
    registered = {value for test in tests for value in marker_values(test, "req")}
    return {
        "unknown_req": sorted(registered - requirements.keys()),
        "uncovered_req": sorted(requirements.keys() - registered),
        "untagged_tests": sorted(test["nodeid"] for test in tests if not marker_values(test, "req")),
    }


def planned_tests(root: Path) -> dict[str, set[str]]:
    text = (root / "docs/renewal/30_TESTPLAN.md").read_text(encoding="utf-8")
    catalog = text.split("## 4. Test catalog", 1)[1].split("## 5.", 1)[0]
    return {
        cells[1].strip(): set(REQ_PATTERN.findall(cells[2]))
        for line in catalog.splitlines()
        if line.startswith("| ")
        and len(cells := line.split("|")) > 3
        and re.fullmatch(r"(?:T-[A-Z]+-\d{2}|CT-\d{2}|PT-\d{2}|JT-\d{2}|JT-SHL-19-01)", cells[1].strip())
    }


def registration_problems(root: Path, tests: list[dict]) -> list[str]:
    problems = []
    seen = {}
    planned = planned_tests(root)
    manifest = (root / "docs/renewal/30_TESTPLAN.md").read_text(encoding="utf-8")
    manifest = manifest.split("## 3. Fixture manifest", 1)[1].split("## 4.", 1)[0]
    # A manifest row can declare several IDs in its first cell (FX-09 / FX-10,
    # FX-21 / FX-22, etc.). References in recipe cells are not declarations.
    fixtures = {identity for line in manifest.splitlines() if line.startswith("| ")
                for identity in re.findall(r"\bFX-\d{2}\b", line.split("|")[1])}
    for test in tests:
        tid = test["tid"]
        if not tid or tid in seen:
            problems.append(f"Invalid or duplicate test ID: {test['nodeid']}")
        seen[tid] = test["nodeid"]
        reqs = set(marker_values(test, "req"))
        if tid not in planned or not planned[tid] <= reqs:
            problems.append(f"Planned registrations missing: {tid}")
        cov = test["markers"].get("cov", [])
        if len(cov) != 1 or len(cov[0]) != 2 or not re.fullmatch(r"S(?:[0-9]|1[0-3])", str(cov[0][0])) or not re.fullmatch(r"FM(?:[0-9]|1[0-2])", str(cov[0][1])):
            problems.append(f"Invalid primary coverage cell: {tid}")
        for fixture in marker_values(test, "fx"):
            if fixture != "all" and fixture not in fixtures:
                problems.append(f"Unknown fixture: {tid}: {fixture}")
        plats = marker_values(test, "plat")
        if plats and (len(plats) != 1 or plats[0] not in {"posix", "windows"}):
            problems.append(f"Invalid platform: {tid}")
        for cell in marker_values(test, "cells"):
            if not re.fullmatch(r"K(?:0[1-9]|1[0-9]|20):S(?:[0-9]|1[0-3])", str(cell)):
                problems.append(f"Invalid class cell: {tid}: {cell}")
    requirements = requirement_registry(root)
    planned_reqs = set().union(*planned.values())
    for req in sorted(requirements.keys() ^ planned_reqs):
        problems.append(f"Plan/spec requirement mismatch: {req}")
    return problems


def golden_problems(root: Path) -> list[str]:
    """Verify GOLDEN.lock hashes and installed Core provenance in step 1."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("mdflow_golden_verify", root / "tools/golden.py")
    golden = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(golden)
        golden.verify(root)
    except (AssertionError, OSError, ValueError, KeyError, TypeError, ImportError) as error:
        return [str(error)]
    return []


MATRIX_STAGES = [f"S{n}" for n in range(14)]
MATRIX_FMS = [f"FM{n}" for n in range(13)]
MATRIX_CLASSES = [f"K{n:02d}" for n in range(1, 21)]
REPORT_ONLY = {"K13", "K15", "K16", "K17", "K19"}  # K12 reaches execution with R33 enabled
FLOOR_STAGE_FM = {("S3", f"FM{n}") for n in (0, 1, 2, 3, 4, 10, 11, 12)} | {
    ("S1", "FM1"), ("S1", "FM2"), ("S1", "FM3"), ("S1", "FM9"), ("S2", "FM1"), ("S2", "FM10"),
    ("S6", "FM1"), ("S6", "FM3"), ("S7", "FM1"), ("S7", "FM5"), ("S9", "FM8"), ("S10", "FM6"),
    ("S10", "FM7"), ("S12", "FM5"), ("S12", "FM9"), ("S0", "FM7"), ("S0", "FM10"), ("S0", "FM12")}
FLOOR_CLASS_STAGE = {(k, s) for k in MATRIX_CLASSES for s in ("S3", "S13")} | {
    (k, "S11") for k in MATRIX_CLASSES if k not in REPORT_ONLY}


def fixture_classes(root: Path) -> dict[str, set[str]]:
    """FX id -> file classes from the manifest table (`-` and `all` rows have no class)."""
    text = (root / "docs/renewal/30_TESTPLAN.md").read_text(encoding="utf-8")
    manifest = text.split("## 3. Fixture manifest", 1)[1].split("## 4.", 1)[0]
    classes = {}
    for line in manifest.splitlines():
        cells = line.split("|")
        if line.startswith("| ") and len(cells) > 3:
            for identity in re.findall(r"\bFX-\d{2}\b", cells[1]):
                classes[identity] = set(re.findall(r"K\d{2}", cells[2]))
    return classes


def matrix_problems(root: Path, tests: list[dict]) -> list[str]:
    """Both generated grids (stage x failure mode, class x stage): covered or reasoned N/A.

    Coverage is derived from the markers only: a test covers its single `cov` cell, and the class x stage
    cell of every class of its `fx` ids (`fx("all")` expands only at S0-S3 and S13). `engine/tests/matrix.toml` supplies
    applicability only; floor cells can never be declared N/A, and an N/A that is also covered is a stale declaration.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10
        import tomli as tomllib
    path = root / "engine/tests/matrix.toml"
    if not path.is_file():
        return [f"missing applicability manifest: {path.relative_to(root).as_posix()}"]
    declared = tomllib.loads(path.read_text(encoding="utf-8"))
    problems = []
    classes_of = fixture_classes(root)
    covered_fm, covered_class = set(), set()
    for test in tests:
        cov = test["markers"].get("cov", [])
        if len(cov) != 1 or len(cov[0]) != 2:
            continue
        stage, mode = cov[0]
        covered_fm.add((stage, mode))
        klasses = test_classes(test, classes_of, include_schema=True)
        covered_class |= {(k, stage) for k in klasses} | extra_cells(test, include_schema=True)
    na_fm, na_class = {}, {}

    def reason_owner(entry, label):
        if not str(entry.get("reason", "")).strip():
            problems.append(f"{label}: N/A without a reason")
        return str(entry.get("owner", ""))

    for entry in declared.get("stage_fm", []):
        owner = reason_owner(entry, f"stage_fm {entry.get('stages')}x{entry.get('fms')}")
        match = re.fullmatch(r"(S\d+):(FM\d+)", owner)
        if not match or (match[1], match[2]) not in covered_fm:
            problems.append(f"stage_fm owner is not a covered cell: {owner!r} for {entry.get('stages')}x{entry.get('fms')}")
        for stage in entry.get("stages", []):
            for mode in entry.get("fms", []):
                if stage not in MATRIX_STAGES or mode not in MATRIX_FMS:
                    problems.append(f"unknown stage/FM in manifest: {stage}:{mode}")
                elif (stage, mode) in na_fm:
                    problems.append(f"cell declared twice: {stage}:{mode}")
                na_fm[(stage, mode)] = owner
    for entry in declared.get("class_stage", []):
        owner = reason_owner(entry, f"class_stage {entry.get('classes')}x{entry.get('stages')}")
        for klass in entry.get("classes", []):
            for stage in entry.get("stages", []):
                if klass not in MATRIX_CLASSES or stage not in MATRIX_STAGES:
                    problems.append(f"unknown class/stage in manifest: {klass}:{stage}")
                    continue
                if (klass, stage) in na_class:
                    problems.append(f"cell declared twice: {klass}:{stage}")
                na_class[(klass, stage)] = owner
                target = (klass, owner) if re.fullmatch(r"S\d+", owner) else \
                    tuple(reversed(owner.split(":"))) if re.fullmatch(r"S\d+:K\d{2}", owner) else None
                if target is None or target not in covered_class:
                    problems.append(f"class_stage owner is not a covered cell: {owner!r} for {klass}:{stage}")
    for stage in MATRIX_STAGES:
        for mode in MATRIX_FMS:
            cell = (stage, mode)
            if cell in FLOOR_STAGE_FM and cell not in covered_fm:
                problems.append(f"floor cell not covered: {stage}:{mode}")
            if cell in FLOOR_STAGE_FM and cell in na_fm:
                problems.append(f"floor cell declared N/A: {stage}:{mode}")
            if cell not in covered_fm and cell not in na_fm:
                problems.append(f"stage x failure-mode cell neither covered nor N/A: {stage}:{mode}")
            if cell in covered_fm and cell in na_fm:
                problems.append(f"stage x failure-mode cell both covered and declared N/A: {stage}:{mode}")
    for klass in MATRIX_CLASSES:
        for stage in MATRIX_STAGES:
            cell = (klass, stage)
            if cell in FLOOR_CLASS_STAGE and cell not in covered_class:
                problems.append(f"floor class cell not covered: {klass}:{stage}")
            if cell in FLOOR_CLASS_STAGE and cell in na_class:
                problems.append(f"floor class cell declared N/A: {klass}:{stage}")
            if cell not in covered_class and cell not in na_class:
                problems.append(f"class x stage cell neither covered nor N/A: {klass}:{stage}")
            if cell in covered_class and cell in na_class:
                problems.append(f"class x stage cell both covered and declared N/A: {klass}:{stage}")
    return problems


def write_registry(root: Path, requirements: dict, tests: list[dict]) -> None:
    path = root / "build/trace/registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"v": 1, "requirements": requirements, "tests": tests}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def execution_registry_path(evidence: Path, junit_name: str) -> Path:
    """Each JUnit owns its collection inventory; matrix downloads cannot overwrite it."""
    stem = junit_name.removeprefix('junit-').removesuffix('.xml')
    return evidence / f'registry-{stem}.json'


def collection_path(evidence: Path, junit_name: str) -> Path:
    stem = junit_name.removeprefix('junit-').removesuffix('.xml')
    return evidence / f'collection-{stem}.json'


def suite_digest(root: Path) -> str:
    """Bind collection to the candidate's tests, parameter builders and config."""
    digest = hashlib.sha256()
    paths = sorted((root / 'engine/tests').rglob('*.py'))
    config = root / 'engine/pyproject.toml'
    if config.is_file():
        paths.append(config)
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode('utf-8') + b'\0')
        # Git checkouts may use CRLF on Windows; evidence is consumed on Linux.
        # Normalize text line endings while retaining every source/config byte
        # that can change the collected tests.
        digest.update(path.read_bytes().replace(b'\r\n', b'\n') + b'\0')
    return digest.hexdigest()


def write_collection(path: Path, tests: list[dict], commit: str, *, root: Path = ROOT) -> None:
    """Called by a separate, fixed full-root collection (or explicit synthetic tests)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(v=1, scope='engine/tests', commit=commit,
        suite_sha256=suite_digest(root), tests=tests), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def shell_suite_digest(root: Path) -> str:
    digest = hashlib.sha256()
    paths = [p for folder in ('src', 'test') for p in (root / 'shell' / folder).rglob('*')
             if p.is_file() and p.suffix in {'.ts', '.js', '.json'}]
    paths += [p for p in (root / 'shell').glob('*') if p.is_file() and p.suffix in {'.ts', '.js', '.json'}]
    paths += [root / 'tools/trace.py']
    paths += [root / 'docs/renewal' / name for name in ('10_SPEC.md', '20_SHELL.md', '30_TESTPLAN.md')]
    for path in sorted(p for p in paths if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b'\0')
        digest.update(path.read_bytes().replace(b'\r\n', b'\n') + b'\0')
    return digest.hexdigest()


def write_shell_collection(path: Path, tests: list[dict], commit: str, *, root: Path = ROOT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(v=1, scope='shell/test', commit=commit,
        suite_sha256=shell_suite_digest(root), tests=tests), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Seal the independently collected universe, never regenerate it from JUnit.
    junit = 'junit-' + path.name.removeprefix('collection-').removesuffix('.json') + '.xml'
    write_execution_registry(path.parent, junit, tests, commit)


def collect_shell(destination: Path, commit: str, *, root: Path = ROOT) -> None:
    scratch = destination.parent / ('jest-collection-' + uuid.uuid4().hex)
    scratch.mkdir(parents=True)
    environment = dict(os.environ)
    for name in ('JEST_JUNIT_OUTPUT_NAME', 'JEST_JUNIT_OUTPUT_DIR', 'NODE_OPTIONS'):
        environment.pop(name, None)
    try:
        raw = scratch / 'expanded.json'
        done = subprocess.run(['node', str(root / 'shell/node_modules/jest/bin/jest.js'),
            '--runInBand', '--collectTests', '--json', '--outputFile=' + str(raw.resolve())], cwd=root / 'shell', env=environment,
            capture_output=True, text=True, encoding='utf-8', timeout=120)
        if done.returncode:
            raise ValueError('independent Jest collection failed: ' + done.stdout[-1000:] + done.stderr[-3000:])
        collected = json.loads(raw.read_text(encoding='utf-8'))
        records = []
        for suite in collected['testResults']:
            source = Path(suite['name']).relative_to(root).as_posix()
            tests = []
            for case in suite['assertionResults']:
                title = case['title']
                tid = (re.match(r'(JT-(?:\d{2}|SHL-19-01))\b', title) or [''])[0]
                if not tid or case.get('invocations') != 0 or case.get('wouldRun') is not True:
                    raise ValueError('unregistered/skipped/executed Jest collection case')
                tests.append(dict(tid=tid, nodeid=source + '::' + title, markers={}, selected=True))
            records.append(dict(source=source, tests=tests))
        expected_files = {p.relative_to(root).as_posix() for p in (root / 'shell/test').glob('*.test.ts')}
        if {r['source'] for r in records} != expected_files:
            raise ValueError('Jest collection omitted a source file')
        tests = sorted((t for r in records for t in r['tests']), key=lambda t: t['nodeid'])
        if not tests or len({t['nodeid'] for t in tests}) != len(tests) or not all(t['selected'] for t in tests):
            raise ValueError('empty, skipped or duplicate Jest collection identity')
        write_shell_collection(destination, tests, commit, root=root)
    finally:
        shutil.rmtree(scratch)


def collect_complete(destination: Path, commit: str, *, root: Path = ROOT) -> None:
    """Collect the entire suite independently of the caller's files/nodeids/-k/-m.

    Do not inherit pytest selection/plugin environment. This subprocess does not
    execute tests, create a JUnit, or recurse into another collection subprocess.
    """
    environment = dict(os.environ)
    for name in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'MDFLOW_CI_TARGET'):
        environment.pop(name, None)
    environment['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    environment['GITHUB_SHA'] = commit
    done = subprocess.run([sys.executable, '-B', '-I', '-m', 'pytest', 'engine/tests',
        '--collect-only', '-q', '-p', 'no:cacheprovider',
        '-o', 'addopts=--import-mode=importlib --strict-markers',
        '--mdflow-collection-output=' + str(destination.resolve())],
        cwd=root, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=120)
    if done.returncode:
        raise ValueError('independent full collection failed: ' + done.stdout[-3000:] + done.stderr[-1000:])


def write_execution_registry(evidence: Path, junit_name: str, tests: list[dict], commit: str) -> None:
    evidence.mkdir(parents=True, exist_ok=True)
    canonical = collection_path(evidence, junit_name).read_bytes()
    execution_registry_path(evidence, junit_name).write_text(
        json.dumps(dict(v=3, commit=commit, tests=tests,
            collection_sha256=hashlib.sha256(canonical).hexdigest()), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def execution_receipt(evidence: Path, junit_name: str, expected_commit: str, *, root: Path = ROOT) -> tuple[list[dict], dict]:
    """Read a candidate-bound collected inventory and exact, nonduplicated JUnit identities.

    Missing parameters are found against a separate complete collection, even
    when restricted execution omitted them from both its registry and JUnit.
    """
    manifest = json.loads(execution_registry_path(evidence, junit_name).read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or manifest.get('v') != 3 or not expected_commit or manifest.get('commit') != expected_commit:
        raise ValueError('collection registry version/commit differs')
    canonical_bytes = collection_path(evidence, junit_name).read_bytes()
    if manifest.get('collection_sha256') != hashlib.sha256(canonical_bytes).hexdigest():
        raise ValueError('independent collection digest differs')
    canonical = json.loads(canonical_bytes)
    shell = junit_name.startswith('junit-shell-')
    scope = 'shell/test' if shell else 'engine/tests'
    digest = shell_suite_digest(root) if shell else suite_digest(root)
    if (not isinstance(canonical, dict) or canonical.get('v') != 1 or canonical.get('scope') != scope
            or canonical.get('commit') != expected_commit or canonical.get('suite_sha256') != digest):
        raise ValueError('independent collection source/commit differs')
    complete = canonical.get('tests')
    if not isinstance(complete, list) or not complete or any(
            not isinstance(t, dict) or not isinstance(t.get('nodeid'), str) or not isinstance(t.get('tid'), str)
            for t in complete):
        raise ValueError('malformed independent collection')
    universe = {t['nodeid']: t for t in complete}
    if len(universe) != len(complete):
        raise ValueError('duplicate independent collection identity')
    tests = manifest['tests']
    if not isinstance(tests, list) or not tests:
        raise ValueError('empty collection registry')
    if any(not isinstance(row, dict) or not isinstance(row.get('nodeid'), str) or
           not isinstance(row.get('tid'), str) for row in tests):
        raise ValueError('malformed collection identity')
    ids = [row['nodeid'] for row in tests]
    if len(ids) != len(set(ids)) or any(not isinstance(row.get('selected'), bool) for row in tests):
        raise ValueError('duplicate or malformed collection identity')
    if any(t['nodeid'] not in universe or t['tid'] != universe[t['nodeid']]['tid'] or
           t.get('markers', {}) != universe[t['nodeid']].get('markers', {}) for t in tests):
        raise ValueError('execution identity differs from independent collection')
    selected = {row['nodeid']: row['tid'] for row in tests if row['selected']}
    actual = {}
    for case in ET.parse(evidence / junit_name).iter('testcase'):
        props = {p.get('name'): p.get('value', '') for p in case.findall('./properties/property')}
        if shell:
            source = (case.get('file') or case.get('classname', '')).replace('\\', '/')
            source = 'shell/' + source[source.rfind('test/'):] if 'test/' in source else source
            title = case.get('name', '')
            nodeid = source + '::' + title
            tid = (re.match(r'(JT-(?:\d{2}|SHL-19-01))\b', title) or [''])[0]
        else:
            nodeid, tid = props.get('nodeid'), props.get('tid')
        if not nodeid or nodeid in actual or selected.get(nodeid) != tid:
            raise ValueError('missing, duplicate, unexpected or mistagged JUnit identity')
        actual[nodeid] = not any(case.find(k) is not None for k in ('failure', 'error', 'skipped'))
    if not actual or set(actual) != set(selected):
        raise ValueError('JUnit differs from selected collection inventory')
    selection = {t['nodeid']: t['selected'] for t in tests}
    return [dict(t, selected=selection.get(t['nodeid'], False)) for t in complete], actual


def rows_passed(rows: list[dict], receipt: tuple[list[dict], dict]) -> bool:
    """Every collected parameter of each required source callable must pass."""
    tests, actual = receipt
    for row in rows:
        base = row['nodeid']
        expected = [t for t in tests if t['tid'] == row['tid'] and (
            t['nodeid'] == base or t['nodeid'].startswith(base + '['))]
        if not expected or not all(t['selected'] and actual.get(t['nodeid']) is True for t in expected):
            return False
    return bool(rows)


def shell_rows_passed(rows: list[dict], receipt: tuple[list[dict], dict]) -> bool:
    tests, actual = receipt
    for row in rows:
        source, raw = row['nodeid'].split('::', 1)
        description = raw.split(' ', 1)[1]
        pattern = re.escape(description)
        pattern = re.sub(r'%[sdifjpo#]', '.+?', pattern)
        expected = [t for t in tests if t['tid'] == row['tid'] and t['nodeid'].startswith(source + '::')
                    and re.fullmatch(pattern, t['nodeid'].split(': ', 1)[-1])]
        if not expected or not all(t['selected'] and actual.get(t['nodeid']) is True for t in expected):
            return False
    return bool(rows)


def discover_shell_tests(root: Path) -> list[dict]:
    """Read real req() registrations; JUnit, separately, proves execution."""
    records = []
    for path in sorted((root / "shell/test").glob("*.test.ts")):
        source = path.read_text(encoding="utf-8")
        bindings = {m[1]: REQ_PATTERN.findall(m[2]) for m in re.finditer(
            r"(?:const|let)\s+(\w+)\s*=\s*req\(([^;]+)\);", source)}
        platform_blocks = []
        for name, platform, operator in (('POSIX', 'posix', '!=='), ('WINDOWS', 'windows', '===')):
            if re.search(rf"const\s+{name}\s*=\s*process\.platform\s*{operator}\s*['\"]win32['\"]", source):
                platform_blocks.extend((m.start(), m.end(), platform) for m in re.finditer(
                    rf'^if \({name}\) \{{[\s\S]*?^\}}', source, re.M))
        pattern = r"\b(?:it|test)(?:\.each\([\s\S]*?\))?\s*\(\s*(\w+)\(\s*(?P<quote>['\"`])(?P<title>JT-(?:\\.|(?!(?P=quote))[\s\S])*?)(?P=quote)"
        for match in re.finditer(pattern, source):
            title = re.sub(r"\\(['\"`\\])", r'\1', match['title'])
            tid = title.split()[0]
            markers = {"req": [bindings.get(match[1], [])]}
            platform = next((p for start, end, p in platform_blocks if start <= match.start() < end), None)
            if platform:
                markers['plat'] = [[platform]]
            records.append({"tid": tid, "nodeid": f"{path.relative_to(root).as_posix()}::{title}",
                            "markers": markers})
    return records


MANUAL_FILES = {"MAN-01": "R15_cleanroom.yml", "MAN-02": "R16_readme_review.yml",
                "MAN-03": "shell_i18n_review.yml", "MAN-04": "release_rehearsal.yml"}
DEFERRED = 'deferred: post-release (R35)'


def peer_identity(value) -> bool:
    """R35: identify the peer, profile and model, rather than a generic sign-off."""
    return isinstance(value, str) and bool(re.fullmatch(r'[\w.-]+/[\w.-]+/[\w.:-]+', value))


def attest(root: Path, identity: str, folder: Path, expected_commit: str) -> list[str]:
    """Validate supplied named reviews; never synthesize a human sign-off."""
    path = folder / MANUAL_FILES[identity]
    if not path.is_file():
        return [f"missing named manual sign-off: {path}"]
    try:
        source = path.read_text(encoding="utf-8")
        try:
            data = json.loads(source)
        except ValueError:
            import yaml  # separately pinned release tool, not an engine dependency
            data = yaml.safe_load(source)
        errors = []
        if identity != 'MAN-04' and not peer_identity(data.get('reviewer')):
            errors.append(f'{identity}: reviewer must name peer/profile/model')
        for key in ("id", "reviewer", "date", "commit", "inputs", "checks", "evidence", "verdict"):
            if not data.get(key):
                errors.append(f"{identity}: missing {key}")
        if data.get("id") != identity or data.get("verdict") != "PASS":
            errors.append(f"{identity}: wrong identity/verdict")
        if not expected_commit or data.get("commit") != expected_commit:
            errors.append(f"{identity}: review must bind the candidate commit")
        for item in data.get("checks") or []:
            result = item.get("result", item.get("status")) if isinstance(item, dict) else item
            if result != "PASS":
                errors.append(f"{identity}: check did not pass")
        if identity == "MAN-01" and (not isinstance(data.get('implementer'), str) or
                not data['implementer'].strip() or
                data['implementer'].split('/')[0].casefold() == str(data.get('reviewer')).split('/')[0].casefold()):
            errors.append("MAN-01: independent named implementer/reviewer required")
        if identity == "MAN-04":
            from release_evidence import validate_rehearsal
            manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
            errors += validate_rehearsal(data, minimum_version=manifest['minAppVersion'])
            if errors:
                errors.append('MAN-04 failed post-release: REQ-PKG-20 rollback required')
        return errors
    except (OSError, ValueError, TypeError, AttributeError, ImportError) as error:
        return [f"{identity}: {error}"]


def report(root: Path, destination: Path) -> dict:
    """Generate both matrices from registrations and reasoned applicability."""
    tests = discover_tests(root)
    classes = fixture_classes(root)
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    na = tomllib.loads((root / "engine/tests/matrix.toml").read_text(encoding="utf-8"))
    fm, ks, execution = {}, {}, {}
    for test in tests:
        values = test["markers"].get("cov", [])
        if len(values) != 1 or len(values[0]) != 2:
            continue
        stage, failure = values[0]
        fm.setdefault(f"{stage}:{failure}", []).append(test["nodeid"])
        covered = test_classes(test, classes, include_schema=True)
        for klass in covered:
            ks.setdefault(f"{klass}:{stage}", []).append(test["nodeid"])
        for klass in test_classes(test, classes):
            execution.setdefault(f'{klass}:{stage}', []).append(test['nodeid'])
        for klass, extra_stage in sorted(extra_cells(test, include_schema=True)):
            ks.setdefault(f"{klass}:{extra_stage}", []).append(test["nodeid"])
        for klass, extra_stage in sorted(extra_cells(test)):
            execution.setdefault(f'{klass}:{extra_stage}', []).append(test['nodeid'])
    def grid(keys, covered, kind, axes):
        result = {}
        for key in keys:
            if key in covered:
                result[key] = {"status": "registered", "assertions": covered[key]}
                continue
            a, b = key.split(":")
            entry = next((e for e in na.get(kind, []) if a in e.get(axes[0], []) and b in e.get(axes[1], [])), None)
            result[key] = {"status": "N/A", "reason": entry.get("reason"), "owner": entry.get("owner")} if entry else {"status": "missing"}
        return result
    result = {"stage_failure": grid((f"{s}:{f}" for s in MATRIX_STAGES for f in MATRIX_FMS), fm, "stage_fm", ("stages", "fms")),
              "class_stage": grid((f"{k}:{s}" for k in MATRIX_CLASSES for s in MATRIX_STAGES), ks, "class_stage", ("classes", "stages")),
              'class_execution_registrations': execution,
              'common_schema_assertions': [t['nodeid'] for t in tests if 'schema' in marker_values(t, 'scope')],
              "automated": {"registration_only": True, 'class_stage_includes_schema_equivalences': True,
                            'execution_requires_junit': True, "problems": matrix_problems(root, tests)},
              "manual": {k: {"status": "requires named review", "file": v} for k, v in MANUAL_FILES.items()}}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def required_executions(evidence: Path, expected_commit: str) -> list[str]:
    """Release prerequisite receipts: real installed endpoints and all nine smokes."""
    problems = []
    source_rows = discover_tests(ROOT)
    for runner in ('windows-2022', 'ubuntu-24.04', 'macos-26'):
        for py in ('3.10', '3.14'):
            path = evidence / f'junit-engine-{runner}-py{py}.xml'
            try:
                platform = 'windows' if runner.startswith('windows') else 'posix'
                expected = [r for r in source_rows if not {'release', 'soffice'}.intersection(r['markers']) and (
                    not marker_values(r, 'plat') or platform in marker_values(r, 'plat'))]
                receipt = execution_receipt(evidence, path.name, expected_commit)
                if not rows_passed(expected, receipt) or not all(receipt[1].values()):
                    raise ValueError('missing, failed, skipped or deselected engine parameter')
                runtime = json.loads((evidence / f'runtime-{runner}-py{py}.json').read_text(encoding='utf-8'))
                if runtime.get('commit') != expected_commit or runtime.get('installed') is not True:
                    raise ValueError('installed import/commit receipt differs')
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
                problems.append(f'{runner}/py{py}: {error}')
        for py in ('3.11', '3.12', '3.13'):
            try:
                smoke = json.loads((evidence / f'smoke-{runner}-py{py}.json').read_text(encoding='utf-8'))
                if smoke.get('commit') != expected_commit or smoke.get('exit') != 0:
                    raise ValueError('missing successful candidate-bound smoke')
            except (OSError, ValueError) as error:
                problems.append(f'{runner}/py{py}: {error}')
    return problems


def oracle_receipts(root: Path, evidence: Path, expected_commit: str, *, defer_release=False) -> list[dict]:
    """Evaluate gate selectors against candidate CI receipts; retain each source name."""
    registry = discover_tests(root) + discover_shell_tests(root)
    planned = planned_tests(root)
    receipts = {}
    sources = set()
    def engine_passed(filename, rows, *, shell=False):
        sources.add(filename)
        if filename not in receipts:
            try:
                receipts[filename] = execution_receipt(evidence, filename, expected_commit, root=root)
            except (OSError, ValueError, KeyError, TypeError, ET.ParseError):
                receipts[filename] = None
        checker = shell_rows_passed if shell else rows_passed
        return receipts[filename] is not None and checker(rows, receipts[filename])

    def passed(tid):
        rows = [t for t in registry if t["tid"] == tid]
        if not rows:
            return False
        if any('soffice' in row['markers'] for row in rows):
            return engine_passed('junit-legacy-libreoffice-ubuntu-24.04-py3.14.xml', rows)
        if tid == 'PT-02':
            # R27's hash reproduction is scoped to its single reference target.
            return engine_passed('junit-reference.xml', rows)
        shell = tid.startswith("JT-")
        deferred = defer_release and any('release' in row['markers'] for row in rows)
        for runner in ("windows-2022", "ubuntu-24.04", "macos-26"):
            for py in ([None] if shell else ["3.10", "3.14"]):
                # A platform-restricted test is required only on the matching OS.
                platform = "windows" if runner.startswith("windows") else "posix"
                expected = [r for r in rows if not marker_values(r, "plat") or platform in marker_values(r, "plat")]
                if not expected:
                    continue
                filename = f"junit-shell-{runner}.xml" if shell else f"junit-engine-{runner}-py{py}.xml"
                release = f'junit-release-{runner}-py{py}.xml'
                if deferred:
                    # CI collection inventories retain the release tests as deselected.
                    # Validate their raw inventories without claiming they executed.
                    engine_passed(filename, [])
                    if receipts[filename] is None:
                        return False
                    continue
                if not shell:
                    if not engine_passed(release if any('release' in row['markers'] for row in rows) else filename, expected):
                        return False
                    continue
                if not engine_passed(filename, expected, shell=True):
                    return False
        return None if deferred else True
    gates = []
    text = (root / "docs/renewal/90_ACCEPTANCE.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 5 or not re.match(r"G-\d{2}\b", cells[1]):
            continue
        identity = cells[1].split()[0]
        patterns = re.findall(r"`([^`]+)`", cells[3])
        selectors = []
        for pattern in patterns:
            match = re.fullmatch(r"(.+-)(\d+)\.\.(?:[A-Z]+-)*(\d+)", pattern)
            selectors.extend([f"{match[1]}{n:02d}" for n in range(int(match[2]), int(match[3]) + 1)] if match else [pattern])
        tids = {tid for tid in planned if any(fnmatch.fnmatchcase(tid, p) for p in selectors)}
        sources.clear()
        outcomes = [passed(t) for t in sorted(tids)]
        if identity == 'G-04':
            contracts = [r for r in registry if r['tid'] in tids and r['tid'].startswith('CT-')]
            if contracts:
                outcomes.append(engine_passed('junit-contract-min.xml', contracts))
                if (evidence / 'junit-contract-max.xml').is_file():
                    outcomes.append(engine_passed('junit-contract-max.xml', contracts))
                else:
                    sources.add('junit-contract-max.json')
                    try:
                        dedup = json.loads((evidence / 'junit-contract-max.json').read_text(encoding='utf-8'))
                        outcomes.append(dedup.get('version') == '0.3.7' and dedup.get('deduplicated_with') == 'contract-min')
                    except (OSError, ValueError, AttributeError):
                        outcomes.append(False)
        result = ('FAIL' if not tids or False in outcomes else
                  'pending: release execution' if None in outcomes else 'PASS')
        gates.append(dict(id=identity, weight=int(cells[2]), result=result,
                          tests=sorted(tids), sources=sorted(sources), command=cells[4].strip(),
                          expected=line.rsplit('|', 2)[-2].strip()))
    return gates


def score(root: Path, evidence: Path, reviews: Path, expected_commit: str) -> dict:
    """Score complete per-cell executions plus separate command-oracle evidence."""
    try:
        oracles = json.loads((evidence / "oracles.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        oracles = {}
    gates = oracle_receipts(root, evidence, expected_commit)
    for gate in gates:
        identity = gate['id']
        oracle = oracles.get(identity, {})
        good = gate['result'] == 'PASS' and oracle.get("exit") == 0 and oracle.get("commit") == expected_commit
        # R36 summaries describe receipt evaluation; release parameters are checked above.
        good &= bool(oracle.get("command")) and isinstance(oracle.get("stdout"), str) and bool(expected_commit)
        gate['result'] = 'PASS' if good else 'FAIL'
        for field in ('sources', 'command', 'expected'):
            del gate[field]
    manual = []
    for identity, weight in zip(MANUAL_FILES, (3, 2, 1, 1)):
        deferred = identity == 'MAN-04' and not (reviews / MANUAL_FILES[identity]).exists()
        problems = [] if deferred else attest(root, identity, reviews, expected_commit)
        manual.append(dict(id=identity, weight=weight, problems=problems,
                           status=DEFERRED if deferred else 'FAIL' if problems else 'PASS'))
    if len(gates) != 17 or sum(g["weight"] for g in gates) != 93:
        raise ValueError("acceptance table must define all 17 automated gates with total weight 93")
    automated_total = sum(g["weight"] for g in gates if g["result"] == "PASS")
    manual_total = sum(g['weight'] for g in manual if g['status'] == 'PASS')
    post_release = [dict(id='MAN-04', status=manual[-1]['status']),
                    dict(id='REQ-PKG-19', status='pending: post-release'),
                    dict(id='REQ-PKG-21', status='pending: post-release')]
    wording = DEFERRED if manual[-1]['status'] == DEFERRED else manual[-1]['status'] + ' (post-release)'
    return {"score": f"SCORE {automated_total + manual_total}/100 (automated {automated_total}/93, manual {manual_total}/7); MAN-04 {wording}",
            "automated": gates, "manual": manual, 'post_release': post_release}


def publication_problems(result: dict) -> list[str]:
    """Shared gate/publisher policy: 93 automated + six peer points; explicit MAN-04 state."""
    problems = []
    gates = result.get('automated', result.get('gates', []))
    weights = (5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1)
    if (len(gates) != 17 or {g.get('id') for g in gates} != {f'G-{i:02d}' for i in range(1, 18)} or
            any(g.get('result') != 'PASS' or g.get('weight') != weights[int(g['id'][2:]) - 1] for g in gates)):
        problems.append('pre-publication requires automated 93/93')
    manual = result.get('manual', [])
    if len(manual) != 4 or {g.get('id') for g in manual} != set(MANUAL_FILES):
        return problems + ['all four manual states must be explicitly recorded']
    for identity, weight in zip(MANUAL_FILES, (3, 2, 1, 1)):
        row = next(g for g in manual if g['id'] == identity)
        allowed = {'PASS', DEFERRED} if identity == 'MAN-04' else {'PASS'}
        if row.get('weight') != weight or row.get('status') not in allowed or row.get('problems') != []:
            problems.append(f'{identity}: invalid publication state')
    state = next(g['status'] for g in manual if g['id'] == 'MAN-04')
    expected = ('SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 ' + DEFERRED if state == DEFERRED else
                'SCORE 100/100 (automated 93/93, manual 7/7); MAN-04 PASS (post-release)')
    if result.get('score') != expected:
        problems.append('score disagrees with explicit R35 states')
    if result.get('post_release') != [dict(id='MAN-04', status=state),
            dict(id='REQ-PKG-19', status='pending: post-release'), dict(id='REQ-PKG-21', status='pending: post-release')]:
        problems.append('post-release validators must be explicitly recorded')
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    collect = commands.add_parser('collect-shell', help='independent expanded Jest registration inventory')
    collect.add_argument('--output', type=Path, required=True)
    collect.add_argument('--commit', default=os.environ.get('GITHUB_SHA', ''))
    rep = commands.add_parser("report", help="generate registration matrices; manual reviews remain separate")
    rep.add_argument("--output", type=Path, default=ROOT / "build/trace/matrices.json")
    sc = commands.add_parser("score", description="Report automated and manual acceptance results separately; missing evidence fails.")
    sc.add_argument("--evidence", type=Path, default=ROOT / "build/trace")
    sc.add_argument("--attest-dir", type=Path, default=ROOT / "attest")
    sc.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    sc.add_argument('--post-release', action='store_true', help='require MAN-04 PASS for 100/100')
    att = commands.add_parser("attest", help="validate an independently supplied named manual sign-off")
    att.add_argument("identity", choices=MANUAL_FILES)
    att.add_argument("--attest-dir", type=Path, default=ROOT / "attest")
    att.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args(argv)
    if args.command == 'collect-shell':
        collect_shell(args.output, args.commit)
        print('Independent expanded Jest inventory written: ' + str(args.output))
        return 0
    if args.command == "report":
        return int(bool(report(ROOT, args.output)["automated"]["problems"]))
    if args.command == "attest":
        errors = attest(ROOT, args.identity, args.attest_dir, args.commit)
        print("\n".join(errors) if errors else "Named manual record valid; claims require independent verification.")
        return int(bool(errors))
    if args.command == "score":
        result = score(ROOT, args.evidence, args.attest_dir, args.commit)
        args.evidence.mkdir(parents=True, exist_ok=True)
        (args.evidence / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["score"])
        return int(bool(publication_problems(result)) or
                   (args.post_release and result['manual'][-1]['status'] != 'PASS'))
    try:
        requirements = requirement_registry(ROOT)
        tests = discover_tests(ROOT)
        shell = discover_shell_tests(ROOT)
        problems = coverage_problems(requirements, tests + shell)
        problems["registration_errors"] = registration_problems(ROOT, tests)
        shell_ids = {t["tid"] for t in shell}
        for tid, reqs in planned_tests(ROOT).items():
            if tid.startswith("JT-") and tid not in shell_ids:
                problems["registration_errors"].append(f"Missing executable Jest registration: {tid}")
            for record in (t for t in shell if t["tid"] == tid):
                if not reqs <= set(marker_values(record, "req")):
                    problems["registration_errors"].append(f"Missing planned Jest requirements: {record['nodeid']}")
        problems["matrix_errors"] = matrix_problems(ROOT, tests)
        write_registry(ROOT, requirements, tests)
    except (OSError, ValueError, SyntaxError, IndexError) as error:
        print(f"trace check failed: {error}")
        return 1
    print(" ".join(f"{key}={len(values)}" for key, values in problems.items()))
    for key, values in problems.items():
        for value in values:
            print(f"{key}: {value}")
    print("Registration and applicability checked; executed automated results and named manual reviews are separate gates.")
    return int(any(problems.values()))


if __name__ == "__main__":
    raise SystemExit(main())
