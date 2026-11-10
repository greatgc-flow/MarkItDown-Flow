"""Collectable red traceability oracles; no Core import is needed."""

import pytest


@pytest.mark.req("REQ-PKG-10", "REQ-SHL-21")
@pytest.mark.cov("S0", "FM10")
def test_T_META_01_requirement_closure(trace_module, repo_root, test_registry):
    requirements = trace_module.requirement_registry(repo_root)
    # Exercise the unknown-marker oracle even before an unknown marker exists.
    invented = {"nodeid": "mutation", "markers": {"req": [["REQ-INVENTED-00"]]}}
    mutation = trace_module.coverage_problems(requirements, [invented])
    assert mutation["unknown_req"] == ["REQ-INVENTED-00"]
    assert set(mutation["uncovered_req"]) == set(requirements)
    # The same combined registry used by trace check: Python cannot register
    # the shell's assertions merely by being collected in an engine run.
    problems = trace_module.coverage_problems(requirements,
        test_registry + trace_module.discover_shell_tests(repo_root))
    assert not any(problems.values()), problems


@pytest.mark.req("REQ-PKG-10")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_META_02_marker_manifest_and_plan_closure(trace_module, repo_root, test_registry):
    problems = trace_module.registration_problems(repo_root, test_registry)
    assert not problems, problems
    planned = trace_module.planned_tests(repo_root)
    actual = {test["tid"] for test in test_registry}
    # Missing executable tests cannot be replaced by rows in the planned catalog.
    expected_python = {tid for tid in planned if not tid.startswith("JT-")}
    assert expected_python <= actual, sorted(expected_python - actual)


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_META_03_golden_integrity_and_core_provenance(trace_module, repo_root):
    problems = trace_module.golden_problems(repo_root)
    assert not problems, problems


@pytest.mark.req("REQ-PKG-10")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_META_04_matrix_cells_covered_or_reasoned_na(trace_module, repo_root, test_registry, tmp_path):
    problems = trace_module.matrix_problems(repo_root, test_registry)
    assert not problems, problems
    # Round 10: a cell both covered and declared N/A is a stale declaration and is reported, never accepted.
    (tmp_path / "docs/renewal").mkdir(parents=True)
    (tmp_path / "engine/tests").mkdir(parents=True)
    plan = (repo_root / "docs/renewal/30_TESTPLAN.md").read_bytes()
    (tmp_path / "docs/renewal/30_TESTPLAN.md").write_bytes(plan)
    matrix = (repo_root / "engine/tests/matrix.toml").read_text(encoding="utf-8")
    stale = ('\n[[stage_fm]]\nstages = ["S5"]\nfms = ["FM9"]\nreason = "stale"\nowner = "S1:FM9"\n'
             '\n[[class_stage]]\nclasses = ["K01"]\nstages = ["S12"]\nreason = "stale"\nowner = "S3"\n')
    (tmp_path / "engine/tests/matrix.toml").write_text(matrix + stale, encoding="utf-8")
    assert sorted(trace_module.matrix_problems(tmp_path, test_registry)) == [
        "class x stage cell both covered and declared N/A: K01:S12",
        "stage x failure-mode cell both covered and declared N/A: S5:FM9"]


@pytest.mark.req("REQ-PKG-10")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_META_05_no_stale_class_stage_na(trace_module, repo_root, test_registry):
    """M4-H: a cell asserted by a real test must not also be declared N/A (stale registry)."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    declared = tomllib.loads((repo_root / "engine/tests/matrix.toml").read_text(encoding="utf-8"))
    classes_of = trace_module.fixture_classes(repo_root)
    covered = set()
    for test in test_registry:
        cov = test["markers"].get("cov", [])
        if len(cov) != 1 or len(cov[0]) != 2:
            continue
        stage = cov[0][0]
        covered |= {(k, stage) for k in trace_module.test_classes(test, classes_of, include_schema=True)}
        covered |= trace_module.extra_cells(test, include_schema=True)
    stale = sorted(f"{k}:{s}" for e in declared.get("class_stage", [])
                   for k in e.get("classes", []) for s in e.get("stages", []) if (k, s) in covered)
    assert not stale, f"stale N/A declarations also covered by tests: {stale}"


@pytest.mark.req("REQ-PKG-10")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_META_06_class_stage_header_count_matches_expanded_cells(repo_root):
    """M4-H: the '(N cells)' header of the class x stage section equals the expanded declarations."""
    import re
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    text = (repo_root / "engine/tests/matrix.toml").read_text(encoding="utf-8")
    declared = tomllib.loads(text).get("class_stage", [])
    actual = sum(len(e["classes"]) * len(e["stages"]) for e in declared)
    found = re.search(r"file class x stage \((\d+) cells\)", text)
    assert found and int(found.group(1)) == actual, (found and found.group(1), actual)
