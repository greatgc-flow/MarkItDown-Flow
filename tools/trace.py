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
    fixtures = set(re.findall(r"\| (FX-\d{2})\b", manifest))
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
    raise NotImplementedError("Golden verification requires step 1 goldens and lock")


def matrix_problems(root: Path, tests: list[dict]) -> list[str]:
    """Verify both generated coverage grids and reasoned N/A declarations."""
    raise NotImplementedError("Matrix verification requires the applicability manifest")


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
