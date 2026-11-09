"""R28 trace policy: blanket common-schema markers cannot imply later class execution."""
import pytest


@pytest.mark.req('REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('stage', [f'S{i}' for i in range(14)])
def test_T_META_53_r28_all_class_credit_is_limited_and_explicit_fixtures_survive(trace_module, stage):
    record = {'markers': {'cov': [[stage, 'FM0']], 'fx': [['all']], 'scope': [['schema']]}}
    expected = set(trace_module.MATRIX_CLASSES) if stage in {'S0', 'S1', 'S2', 'S3', 'S13'} else set()
    assert trace_module.test_classes(record, {}, include_schema=True) == expected
    assert trace_module.test_classes(record, {}) == set()
    record['markers']['scope'] = []
    assert trace_module.test_classes(record, {}) == expected
    record['markers']['fx'] = [['all', 'FX-28']]
    assert trace_module.test_classes(record, {'FX-28': {'K10'}}) == (expected | {'K10'})


@pytest.mark.req('REQ-PKG-02', 'REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_54_r27_reference_score_requires_reference_execution_not_matrix_substitution(trace_module, tmp_path, monkeypatch):
    import json
    import xml.etree.ElementTree as ET

    record = {'tid': 'PT-02', 'nodeid': 'engine/tests/packaging/test_pt_release.py::test_PT_02_reference', 'markers': {'release': [[]]}}
    monkeypatch.setattr(trace_module, 'discover_tests', lambda root: [record])
    monkeypatch.setattr(trace_module, 'discover_shell_tests', lambda root: [])
    monkeypatch.setattr(trace_module, 'planned_tests', lambda root: {'PT-02': {'REQ-PKG-02'}})
    monkeypatch.setattr(trace_module, 'attest', lambda *args: ['named review absent'])
    docs = tmp_path / 'docs/renewal'
    docs.mkdir(parents=True)
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    (docs / '90_ACCEPTANCE.md').write_text('\n'.join(
        f'| G-{i:02d} | {w} | `PT-02` | reference receipt | target-specific success |'
        for i, w in enumerate(weights, 1)), encoding='utf-8')
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    commit = 'a' * 40
    (evidence / 'oracles.json').write_text(json.dumps({f'G-{i:02d}': {
        'command': 'reference test fixture', 'stdout': 'test fixture', 'exit': 0, 'commit': commit}
        for i in range(1, 18)}), encoding='utf-8')

    def execution(name, outcome=None):
        suite = ET.Element('testsuite')
        case = ET.SubElement(suite, 'testcase', name='reference-test')
        props = ET.SubElement(case, 'properties')
        ET.SubElement(props, 'property', name='tid', value='PT-02')
        ET.SubElement(props, 'property', name='nodeid', value=record['nodeid'])
        if outcome:
            ET.SubElement(case, outcome)
        ET.ElementTree(suite).write(evidence / name, encoding='utf-8')
        trace_module.write_collection(trace_module.collection_path(evidence, name), [record], commit, root=tmp_path)
        trace_module.write_execution_registry(evidence, name, [dict(record, selected=True)], commit)

    for os in ('windows-2022', 'ubuntu-24.04', 'macos-15-intel'):
        for py in ('3.10', '3.14'):
            execution(f'junit-engine-{os}-py{py}.xml')
    score = lambda: trace_module.score(tmp_path, evidence, tmp_path / 'reviews', commit)
    assert all(g['result'] == 'FAIL' for g in score()['automated'])
    execution('junit-reference.xml')
    assert all(g['result'] == 'PASS' for g in score()['automated'])
    for outcome in ('skipped', 'failure', 'error'):
        execution('junit-reference.xml', outcome)
        assert all(g['result'] == 'FAIL' for g in score()['automated'])
