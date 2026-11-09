"""M3 release receipts must cover collected parameter identities, not only TIDs."""
import json
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.req('REQ-PKG-10', 'REQ-PKG-17', 'REQ-PKG-08')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('mutation', ['omit', 'duplicate', 'wrong_parameter', 'skip', 'fail', 'stale',
    'missing_registry', 'omit_both', 'only_one', 'missing_collection', 'stale_collection',
    'changed_source', 'collection_tamper', 'duplicate_collection'])
def test_T_META_90_m3_score_requires_each_collected_parameter(trace_module, tmp_path, monkeypatch, mutation):
    commit = 'a' * 40
    base = 'engine/tests/stage_io/test_class_sweep.py::test_T_GEN_85_class_sweep'
    rows = [{'tid': 'T-GEN-85', 'nodeid': base, 'markers': {}}]
    monkeypatch.setattr(trace_module, 'discover_tests', lambda root: rows)
    monkeypatch.setattr(trace_module, 'discover_shell_tests', lambda root: [])
    monkeypatch.setattr(trace_module, 'planned_tests', lambda root: {'T-GEN-85': {'REQ-GEN-07'}})
    monkeypatch.setattr(trace_module, 'attest', lambda *a: ['synthetic control: no manual review'])
    docs = tmp_path / 'docs/renewal'
    docs.mkdir(parents=True)
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    (docs / '90_ACCEPTANCE.md').write_text('\n'.join(
        f'| G-{n:02d} | {w} | `T-GEN-85` | synthetic command | explicit control |'
        for n, w in enumerate(weights, 1)), encoding='utf-8')
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    (evidence / 'oracles.json').write_text(json.dumps({f'G-{n:02d}': dict(
        command='synthetic control', stdout='synthetic', exit=0, commit=commit) for n in range(1, 18)}))
    nodes = [dict(nodeid=f'{base}[K{n:02d}]', tid='T-GEN-85', markers={}, selected=True) for n in range(1, 21)]

    def receipt(filename, selected):
        suite = ET.Element('testsuite')
        for node in selected:
            case = ET.SubElement(suite, 'testcase', name=node['nodeid'].split('::')[-1])
            props = ET.SubElement(case, 'properties')
            for key in ('tid', 'nodeid'):
                ET.SubElement(props, 'property', name=key, value=node[key])
        ET.ElementTree(suite).write(evidence / filename, encoding='utf-8')
        return suite

    for runner in ('windows-2022', 'ubuntu-24.04', 'macos-26'):
        for py in ('3.10', '3.14'):
            filename = f'junit-engine-{runner}-py{py}.xml'
            receipt(filename, nodes)
            trace_module.write_collection(trace_module.collection_path(evidence, filename), nodes, commit, root=tmp_path)
            trace_module.write_execution_registry(evidence, filename, nodes, commit)
    score = lambda: trace_module.score(tmp_path, evidence, tmp_path / 'reviews', commit)
    assert all(g['result'] == 'PASS' for g in score()['automated']), 'complete parameter inventory is the positive control'
    filename = 'junit-engine-windows-2022-py3.10.xml'
    registry = evidence / 'registry-engine-windows-2022-py3.10.json'
    changed = list(nodes)
    if mutation == 'omit':
        changed = [n for n in nodes if not n['nodeid'].endswith('[K09]')]
    elif mutation == 'omit_both':
        changed = [n for n in nodes if not n['nodeid'].endswith('[K09]')]
        trace_module.write_execution_registry(evidence, filename, changed, commit)
    elif mutation == 'only_one':
        changed = nodes[:1]
        trace_module.write_execution_registry(evidence, filename, changed, commit)
    elif mutation == 'duplicate':
        changed[8] = nodes[0]
    elif mutation == 'wrong_parameter':
        changed[8] = dict(nodes[8], nodeid=base + '[K99]')
    suite = receipt(filename, changed)
    if mutation in {'skip', 'fail'}:
        ET.SubElement(list(suite)[8], 'skipped' if mutation == 'skip' else 'failure')
        ET.ElementTree(suite).write(evidence / filename)
    elif mutation == 'stale':
        trace_module.write_execution_registry(evidence, filename, nodes, 'b' * 40)
    elif mutation == 'missing_registry':
        registry.unlink()
    elif mutation == 'missing_collection':
        trace_module.collection_path(evidence, filename).unlink()
    elif mutation == 'stale_collection':
        trace_module.write_collection(trace_module.collection_path(evidence, filename), nodes, 'b' * 40, root=tmp_path)
        trace_module.write_execution_registry(evidence, filename, nodes, commit)
    elif mutation == 'changed_source':
        source = tmp_path / 'engine/tests/new.py'
        source.parent.mkdir(parents=True)
        source.write_text('# changed candidate test source\n')
    elif mutation == 'collection_tamper':
        path = trace_module.collection_path(evidence, filename)
        path.write_bytes(path.read_bytes() + b' ')
    elif mutation == 'duplicate_collection':
        trace_module.write_collection(trace_module.collection_path(evidence, filename), [*nodes, nodes[0]], commit, root=tmp_path)
        trace_module.write_execution_registry(evidence, filename, nodes, commit)
    assert all(g['result'] == 'FAIL' for g in score()['automated']), mutation
