"""Step 0 requirement registration checks; no runtime or pytest dependency."""

import argparse
import ast
import json
from pathlib import Path
import re
import fnmatch
import hashlib
import os
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

    This is the minimal Python registry. Jest export support belongs to the shell
    step; shell requirements therefore remain uncovered until it is implemented.
    """
    tests = []
    for path in sorted((root / "engine" / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        def visit(node: ast.AST, inherited: dict, scope: str) -> None:
            markers = {key: list(value) for key, value in inherited.items()}
            for decorator in getattr(node, "decorator_list", []):
                if isinstance(decorator, ast.Attribute) and ast.unparse(decorator) == 'pytest.mark.release':
                    markers['release'] = [[]]
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
REPORT_ONLY = {"K12", "K13", "K15", "K16", "K17", "K19"}
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
    applicability only; floor cells can never be declared N/A. An N/A that is covered is not a problem.
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
    for klass in MATRIX_CLASSES:
        for stage in MATRIX_STAGES:
            cell = (klass, stage)
            if cell in FLOOR_CLASS_STAGE and cell not in covered_class:
                problems.append(f"floor class cell not covered: {klass}:{stage}")
            if cell in FLOOR_CLASS_STAGE and cell in na_class:
                problems.append(f"floor class cell declared N/A: {klass}:{stage}")
            if cell not in covered_class and cell not in na_class:
                problems.append(f"class x stage cell neither covered nor N/A: {klass}:{stage}")
    return problems


def write_registry(root: Path, requirements: dict, tests: list[dict]) -> None:
    path = root / "build/trace/registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"v": 1, "requirements": requirements, "tests": tests}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_shell_tests(root: Path) -> list[dict]:
    """Read real req() registrations; JUnit, separately, proves execution."""
    records = []
    for path in sorted((root / "shell/test").glob("*.test.ts")):
        source = path.read_text(encoding="utf-8")
        bindings = {m[1]: REQ_PATTERN.findall(m[2]) for m in re.finditer(
            r"(?:const|let)\s+(\w+)\s*=\s*req\(([^;]+)\);", source)}
        for match in re.finditer(r"\b(?:it|test)(?:\.each\([\s\S]*?\))?\s*\(\s*(\w+)\(\s*['\"`](JT-[^'\"`]+)['\"`]", source):
            title = match[2]
            tid = title.split()[0]
            records.append({"tid": tid, "nodeid": f"{path.relative_to(root).as_posix()}::{title}",
                            "markers": {"req": [bindings.get(match[1], [])]}})
    return records


MANUAL_FILES = {"MAN-01": "R15_cleanroom.yml", "MAN-02": "R16_readme_review.yml",
                "MAN-03": "shell_i18n_review.yml", "MAN-04": "release_rehearsal.yml"}


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
        if identity == "MAN-01" and (not data.get("implementer") or data.get("implementer") == data.get("reviewer")):
            errors.append("MAN-01: independent named implementer/reviewer required")
        if identity == "MAN-04":
            from release_evidence import validate_rehearsal
            errors += validate_rehearsal(data)
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
    for runner in ('windows-2022', 'ubuntu-24.04', 'macos-15-intel'):
        for py in ('3.10', '3.14'):
            path = evidence / f'junit-engine-{runner}-py{py}.xml'
            try:
                cases = list(ET.parse(path).iter('testcase'))
                if not cases or any(c.find(k) is not None for c in cases for k in ('failure','error','skipped')):
                    raise ValueError('empty, failed or skipped engine receipt')
                runtime = json.loads((evidence / f'runtime-{runner}-py{py}.json').read_text(encoding='utf-8'))
                if runtime.get('commit') != expected_commit or runtime.get('installed') is not True:
                    raise ValueError('installed import/commit receipt differs')
            except (OSError, ValueError, ET.ParseError) as error:
                problems.append(f'{runner}/py{py}: {error}')
        for py in ('3.11', '3.12', '3.13'):
            try:
                smoke = json.loads((evidence / f'smoke-{runner}-py{py}.json').read_text(encoding='utf-8'))
                if smoke.get('commit') != expected_commit or smoke.get('exit') != 0:
                    raise ValueError('missing successful candidate-bound smoke')
            except (OSError, ValueError) as error:
                problems.append(f'{runner}/py{py}: {error}')
    return problems


def score(root: Path, evidence: Path, reviews: Path, expected_commit: str) -> dict:
    """Score only complete per-cell executions plus separate command-oracle evidence."""
    registry = discover_tests(root) + discover_shell_tests(root)
    planned = planned_tests(root)
    results = {}
    for path in evidence.glob("junit-*.xml"):
        if "py3.15" in path.name:
            continue
        for case in ET.parse(path).iter("testcase"):
            props = {p.get("name"): p.get("value", "") for p in case.findall("./properties/property")}
            tid = props.get("tid") or (re.search(r"\b(JT-(?:\d{2}|SHL-19-01))\b", case.get("name", "")) or [""])[0]
            if not tid:
                continue
            good = not any(case.find(k) is not None for k in ("failure", "error", "skipped"))
            results.setdefault((path.name, tid), []).append(good)
    try:
        oracles = json.loads((evidence / "oracles.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        oracles = {}
    def passed(tid):
        rows = [t for t in registry if t["tid"] == tid]
        if not rows:
            return False
        if tid == 'PT-02':
            # R27's hash reproduction is scoped to its single reference target.
            values = results.get(('junit-reference.xml', tid), [])
            return len(values) >= len(rows) and all(values)
        shell = tid.startswith("JT-")
        for runner in ("windows-2022", "ubuntu-24.04", "macos-15-intel"):
            for py in ([None] if shell else ["3.10", "3.14"]):
                # A platform-restricted test is required only on the matching OS.
                platform = "windows" if runner.startswith("windows") else "posix"
                expected = [r for r in rows if not marker_values(r, "plat") or platform in marker_values(r, "plat")]
                if not expected:
                    continue
                filename = f"junit-shell-{runner}.xml" if shell else f"junit-engine-{runner}-py{py}.xml"
                packaged = f"junit-pkg-{runner}-py{py}.xml"
                release = f'junit-release-{runner}-py{py}.xml'
                if any('release' in row['markers'] for row in rows):
                    values = results.get((release, tid), [])
                    if len(values) < len(expected) or not all(values):
                        return False
                    continue
                # Source-suite release-mode skips are superseded by actual packaged execution.
                values = results.get((packaged, tid), []) if tid.startswith("PT-") else []
                values = values or results.get((filename, tid), [])
                if len(values) < len(expected) or not all(values):
                    return False
        return True
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
        oracle = oracles.get(identity, {})
        good = bool(tids) and all(passed(t) for t in tids) and oracle.get("exit") == 0 and oracle.get("commit") == expected_commit
        # A command receipt must preserve its actual stdout and command, not just a PASS flag.
        good &= bool(oracle.get("command")) and isinstance(oracle.get("stdout"), str) and bool(expected_commit)
        gates.append({"id": identity, "weight": int(cells[2]), "result": "PASS" if good else "FAIL", "tests": sorted(tids)})
    manual = [{"id": identity, "weight": weight, "problems": attest(root, identity, reviews, expected_commit)}
              for identity, weight in zip(MANUAL_FILES, (3, 2, 1, 1))]
    if len(gates) != 17 or sum(g["weight"] for g in gates) != 93:
        raise ValueError("acceptance table must define all 17 automated gates with total weight 93")
    automated_total = sum(g["weight"] for g in gates if g["result"] == "PASS")
    manual_total = sum(g["weight"] for g in manual if not g["problems"])
    return {"score": f"SCORE {automated_total + manual_total}/100 (automated {automated_total}/93, manual {manual_total}/7)",
            "automated": gates, "manual": manual}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    rep = commands.add_parser("report", help="generate registration matrices; manual reviews remain separate")
    rep.add_argument("--output", type=Path, default=ROOT / "build/trace/matrices.json")
    sc = commands.add_parser("score", description="Report automated and manual acceptance results separately; missing evidence fails.")
    sc.add_argument("--evidence", type=Path, default=ROOT / "build/trace")
    sc.add_argument("--attest-dir", type=Path, default=ROOT / "attest")
    sc.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    att = commands.add_parser("attest", help="validate an independently supplied named manual sign-off")
    att.add_argument("identity", choices=MANUAL_FILES)
    att.add_argument("--attest-dir", type=Path, default=ROOT / "attest")
    att.add_argument("--commit", default=os.environ.get("GITHUB_SHA", ""))
    args = parser.parse_args(argv)
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
        return int(result["score"] != "SCORE 100/100 (automated 93/93, manual 7/7)")
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
