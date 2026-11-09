"""M3 release receipts must cover collected parameter identities, not only TIDs."""
import json
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.req('REQ-PKG-10', 'REQ-PKG-17', 'REQ-PKG-08')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('mutation', ['omit', 'duplicate', 'wrong_parameter', 'skip', 'fail', 'stale', 'missing_registry'])
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

    for runner in ('windows-2022', 'ubuntu-24.04', 'macos-15-intel'):
        for py in ('3.10', '3.14'):
            filename = f'junit-engine-{runner}-py{py}.xml'
            receipt(filename, nodes)
            manifest = dict(v=2, commit=commit, tests=nodes)
            (evidence / filename.replace('junit-', 'registry-').replace('.xml', '.json')).write_text(json.dumps(manifest))
    score = lambda: trace_module.score(tmp_path, evidence, tmp_path / 'reviews', commit)
    assert all(g['result'] == 'PASS' for g in score()['automated']), 'complete parameter inventory is the positive control'
    filename = 'junit-engine-windows-2022-py3.10.xml'
    registry = evidence / 'registry-engine-windows-2022-py3.10.json'
    changed = list(nodes)
    if mutation == 'omit':
        changed = [n for n in nodes if not n['nodeid'].endswith('[K09]')]
    elif mutation == 'duplicate':
        changed[8] = nodes[0]
    elif mutation == 'wrong_parameter':
        changed[8] = dict(nodes[8], nodeid=base + '[K99]')
    suite = receipt(filename, changed)
    if mutation in {'skip', 'fail'}:
        ET.SubElement(list(suite)[8], 'skipped' if mutation == 'skip' else 'failure')
        ET.ElementTree(suite).write(evidence / filename)
    elif mutation == 'stale':
        registry.write_text(json.dumps(dict(v=2, commit='b' * 40, tests=nodes)))
    elif mutation == 'missing_registry':
        registry.unlink()
    assert all(g['result'] == 'FAIL' for g in score()['automated']), mutation
