"""M5-O01: shell execution identities cannot be replaced by counts."""
import json
import xml.etree.ElementTree as ET

import pytest


@pytest.mark.req('REQ-PKG-10', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_98_m5_shell_inventory_preserves_quoted_titles_and_platforms(trace_module, tmp_path):
    folder = tmp_path / 'shell/test'
    folder.mkdir(parents=True)
    (folder / 'jt-17-syntax.test.ts').write_text('''const R = req('REQ-SHL-03');
const POSIX = process.platform !== 'win32';
const WINDOWS = process.platform === 'win32';
it(R('JT-17 user\\'s "quoted" setting'), () => {});
if (POSIX) {
  it(R('JT-17 POSIX child'), () => {});
}
if (WINDOWS) {
  it(R('JT-17 Windows child'), () => {});
}
''')
    rows = trace_module.discover_shell_tests(tmp_path)
    assert [r['nodeid'].split('::')[1] for r in rows] == [
        'JT-17 user\'s "quoted" setting', 'JT-17 POSIX child', 'JT-17 Windows child']
    assert [r['markers'].get('plat', []) for r in rows] == [[], [['posix']], [['windows']]]


@pytest.mark.req('REQ-PKG-10', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('mutation', ['omit', 'duplicate', 'substitute', 'skip', 'fail', 'stale',
    'source', 'collection_tamper', 'missing_collection', 'omit_both'])
def test_T_META_97_m5_shell_score_requires_complete_bound_unique_identities(trace_module, tmp_path, monkeypatch, mutation):
    commit = 'a' * 40
    base = 'shell/test/jt-17-example.test.ts'
    rows = [dict(tid='JT-17', nodeid=base + '::JT-17 ' + title, markers={}) for title in ('first', 'second')]
    monkeypatch.setattr(trace_module, 'discover_tests', lambda root: [])
    monkeypatch.setattr(trace_module, 'discover_shell_tests', lambda root: rows)
    monkeypatch.setattr(trace_module, 'planned_tests', lambda root: {'JT-17': {'REQ-SHL-03'}})
    monkeypatch.setattr(trace_module, 'attest', lambda *a: ['synthetic control; no human receipt'])
    docs = tmp_path / 'docs/renewal'
    docs.mkdir(parents=True)
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    (docs / '90_ACCEPTANCE.md').write_text('\n'.join(
        f'| G-{n:02d} | {w} | `JT-17` | synthetic command | control |' for n, w in enumerate(weights, 1)))
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    (evidence / 'oracles.json').write_text(json.dumps({f'G-{n:02d}': dict(
        command='synthetic', stdout='control', exit=0, commit=commit) for n in range(1, 18)}))
    source = tmp_path / base
    source.parent.mkdir(parents=True)
    source.write_text('// synthetic candidate source\n')
    nodes = [dict(tid='JT-17', nodeid=base + '::JT-17 REQ-SHL-03: ' + title, markers={}, selected=True)
             for title in ('first', 'second')]
    def receipt(filename, cases):
        suite = ET.Element('testsuite')
        for row in cases:
            ET.SubElement(suite, 'testcase', classname='test/jt-17-example.test.ts',
                          name=row['nodeid'].split('::')[1])
        ET.ElementTree(suite).write(evidence / filename)
        return suite
    for runner in ('windows-2022', 'ubuntu-24.04', 'macos-15-intel'):
        filename = f'junit-shell-{runner}.xml'
        receipt(filename, nodes)
        trace_module.write_shell_collection(trace_module.collection_path(evidence, filename), nodes, commit, root=tmp_path)
    score = lambda: trace_module.score(tmp_path, evidence, tmp_path / 'reviews', commit)
    assert all(g['result'] == 'PASS' for g in score()['automated'])
    filename = 'junit-shell-windows-2022.xml'
    changed = list(nodes)
    if mutation in {'omit', 'omit_both'}:
        changed.pop()
    elif mutation == 'duplicate':
        changed[1] = nodes[0]
    elif mutation == 'substitute':
        changed[1] = dict(nodes[1], nodeid=base + '::JT-17 REQ-SHL-03: invented')
    suite = receipt(filename, changed)
    if mutation in {'skip', 'fail'}:
        ET.SubElement(list(suite)[1], 'skipped' if mutation == 'skip' else 'failure')
        ET.ElementTree(suite).write(evidence / filename)
    path = trace_module.collection_path(evidence, filename)
    if mutation == 'stale':
        trace_module.write_shell_collection(path, nodes, 'b' * 40, root=tmp_path)
    elif mutation == 'source':
        source.write_text('// source changed\n')
    elif mutation == 'collection_tamper':
        path.write_text(path.read_text().replace('first', 'tampered'))
    elif mutation == 'missing_collection':
        path.unlink()
    elif mutation == 'omit_both':
        trace_module.write_shell_collection(path, changed, commit, root=tmp_path)
    assert all(g['result'] == 'FAIL' for g in score()['automated']), mutation
