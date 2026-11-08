"""Step 0 requirement registration checks; no runtime or pytest dependency."""

import argparse
import ast
import json
from pathlib import Path
import re

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
                if not isinstance(decorator, ast.Call):
                    continue
                name = ast.unparse(decorator.func)
                if not name.startswith("pytest.mark."):
                    continue
                key = name.removeprefix("pytest.mark.")
                if key in {"req", "cov", "fx", "plat"}:
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
    cell of every class of its `fx` ids (`fx("all")` = every class). `engine/tests/matrix.toml` supplies
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
        fixtures = set(marker_values(test, "fx"))
        klasses = set(MATRIX_CLASSES) if "all" in fixtures else set().union(*(classes_of.get(f, set()) for f in fixtures))
        covered_class |= {(k, stage) for k in klasses}
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_subparsers(dest="command", required=True).add_parser("check")
    parser.parse_args(argv)
    try:
        requirements = requirement_registry(ROOT)
        tests = discover_tests(ROOT)
        problems = coverage_problems(requirements, tests)
        problems["registration_errors"] = registration_problems(ROOT, tests)
        write_registry(ROOT, requirements, tests)
    except (OSError, ValueError, SyntaxError, IndexError) as error:
        print(f"trace check failed: {error}")
        return 1
    print(" ".join(f"{key}={len(values)}" for key, values in problems.items()))
    for key, values in problems.items():
        for value in values:
            print(f"{key}: {value}")
    print("Step 0 registration check only; golden, matrix, Jest and PASS-evidence gates are pending.")
    return int(any(problems.values()))


if __name__ == "__main__":
    raise SystemExit(main())
