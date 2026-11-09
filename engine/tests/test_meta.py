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
def test_T_META_04_matrix_cells_covered_or_reasoned_na(trace_module, repo_root, test_registry):
    problems = trace_module.matrix_problems(repo_root, test_registry)
    assert not problems, problems


@pytest.mark.req("REQ-PKG-10")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_META_05_no_stale_class_stage_na(trace_module, repo_root, test_registry):
    """M4-H: a cell asserted by a real test must not also be declared N/A (stale registry)."""
    import tomllib
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
