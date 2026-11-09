"""R36 receipt generation and reduced peer responsibilities (offline)."""
from copy import deepcopy
import hashlib
import json
import sys

import pytest

from _support import REPO, load_py

COMMIT = 'a' * 40


def candidate_receipts(root, trace):
    docs = root / 'docs/renewal'
    docs.mkdir(parents=True)
    tests = root / 'engine/tests'
    tests.mkdir(parents=True)
    (tests / 'test_example.py').write_text(
        'def test_PT_17(): pass\ndef test_CT_01(): pass\n'
        '@pytest.mark.release\ndef test_PT_02(): pass\n'
        '@pytest.mark.release\ndef test_PT_04(): pass\n')
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    selectors = {4: 'CT-01', 13: 'PT-02', 15: 'PT-04'}
    (docs / '90_ACCEPTANCE.md').write_text('\n'.join(
        f'| G-{i:02d} example | {w} | `{selectors.get(i, "PT-17")}` | pytest example | all pass |'
        for i, w in enumerate(weights, 1)))
    (docs / '30_TESTPLAN.md').write_text('## 4. Test catalog\n' + '\n'.join(
        f'| {tid} | REQ-PKG-17 | A |' for tid in ('PT-17', 'CT-01', 'PT-02', 'PT-04')) + '\n## 5. End\n')
    executions = root / 'executions'
    executions.mkdir()
    rows = trace.discover_tests(root)
    names = ['junit-reference.xml', 'junit-contract-min.xml', 'junit-contract-max.xml']
    names += [f'junit-{phase}-{runner}-py{py}.xml'
              for phase in ('engine', 'release') for runner in ('windows-2022', 'ubuntu-24.04', 'macos-26')
              for py in ('3.10', '3.14')]
    for name in names:
        trace.write_collection(trace.collection_path(executions, name), rows, COMMIT, root=root)
        trace.write_execution_registry(executions, name, [dict(r, selected=True) for r in rows], COMMIT)
        (executions / name).write_text('<testsuite>' + ''.join(
            '<testcase><properties><property name="nodeid" value="' + r['nodeid'] + '"/>'
            '<property name="tid" value="' + r['tid'] + '"/></properties></testcase>' for r in rows) + '</testsuite>')
    return executions


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_PT_29_r36_generates_oracles_and_verifies_raw_receipts(tmp_path):
    sys.path.insert(0, str(REPO / 'tools'))
    tool = load_py(REPO / 'tools/release_evidence.py', 'r36_evidence')
    import trace
    executions = candidate_receipts(tmp_path, trace)
    peer = dict(reviewer='cx/cx.effort/gpt-6.1-sol', date='2026-11-10', commit=COMMIT,
                evidence=['raw receipt review notes'], spot_checks=['G-01', 'G-04', 'G-13'])
    record = tool.generate_oracles(tmp_path, executions, COMMIT, peer)
    assert record['generator_commit'] == COMMIT
    assert {k for k in record if k.startswith('G-')} == {f'G-{i:02d}' for i in range(1, 18)}
    assert all(record[k] == v for k, v in peer.items())
    assert tool.validate_extra('oracles.json', record, COMMIT, root=tmp_path, executions=executions) == []
    for identity in ('G-01', 'G-04', 'G-13', 'G-15'):
        sources = record[identity]['sources']
        assert sources and {s['path'].split('-')[0] for s in sources} == {'junit', 'registry', 'collection'}
        assert all(s['sha256'] == hashlib.sha256((executions / s['path']).read_bytes()).hexdigest() for s in sources)
    assert any(s['path'] == 'junit-contract-max.xml' for s in record['G-04']['sources'])
    assert [s['path'] for s in record['G-13']['sources'] if s['path'].startswith('junit-')] == ['junit-reference.xml']
    for changes in ({'spot_checks': ['G-01', 'G-02']}, {'spot_checks': ['G-01'] * 3},
                    {'spot_checks': ['G-01', 'G-02', 'G-99']}, {'generator_commit': 'b' * 40}):
        assert tool.validate_extra('oracles.json', dict(record, **changes), COMMIT, root=tmp_path, executions=executions)
    for path in ('../outside.xml', 'missing.xml'):
        bad = deepcopy(record)
        bad['G-01']['sources'][0]['path'] = path
        assert tool.validate_extra('oracles.json', bad, COMMIT, root=tmp_path, executions=executions)
    # A source mutation fails even when the generated summary and peer claims still say PASS.
    receipt = executions / record['G-01']['sources'][0]['path']
    receipt.write_bytes(receipt.read_bytes() + b' ')
    assert any('hash' in p for p in tool.validate_extra('oracles.json', record, COMMIT, root=tmp_path, executions=executions))


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('mutation', ['missing', 'failed', 'stale', 'collection_hash'])
def test_PT_30_r36_generator_refuses_incomplete_or_failed_ci(tmp_path, mutation):
    sys.path.insert(0, str(REPO / 'tools'))
    tool = load_py(REPO / 'tools/release_evidence.py', 'r36_bad_receipts')
    import trace
    executions = candidate_receipts(tmp_path, trace)
    name = 'junit-engine-windows-2022-py3.10.xml'
    if mutation == 'missing':
        (executions / name).unlink()
    elif mutation == 'failed':
        path = executions / name
        path.write_text(path.read_text().replace('</testcase>', '<failure/></testcase>', 1))
    elif mutation == 'stale':
        path = trace.execution_registry_path(executions, name)
        path.write_text(path.read_text().replace(COMMIT, 'b' * 40))
    else:
        path = trace.collection_path(executions, name)
        path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        tool.generate_oracles(tmp_path, executions, COMMIT, {})


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-11', 'REQ-PKG-04', 'REQ-PKG-15')
@pytest.mark.cov('S0', 'FM10')
def test_PT_31_r36_peer_templates_only_require_authorized_reviews():
    folder = REPO / 'docs/renewal/manual-templates'
    actions = json.loads((folder / 'actions-review.json').read_text())
    assert all(set(row['checks']) == {'ownership', 'workflow_permissions'} for row in actions['actions'])
    pkg = json.loads((folder / 'pkg04_core_artifacts.json').read_text())
    assert set(pkg['checks']) == {'artifact_licenses'}
    peer = json.loads((folder / 'oracles.json').read_text())
    assert set(peer) == {'reviewer', 'date', 'commit', 'evidence', 'spot_checks'}
    listing = json.loads((folder / 'listing-review.json').read_text())
    assert set(listing['checks']) == {'identity', 'manifest_versions', 'description', 'commands',
                                     'desktop_only', 'readme_disclosures'}


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_PT_32_r36_ci_generation_precedes_release_and_keeps_endpoint_dedup(tmp_path):
    sys.path.insert(0, str(REPO / 'tools'))
    tool = load_py(REPO / 'tools/release_evidence.py', 'r36_ci_phase')
    import trace
    executions = candidate_receipts(tmp_path, trace)
    for path in executions.glob('*release-*'):
        path.unlink()
    (executions / 'junit-contract-max.xml').unlink()
    dedup = executions / 'junit-contract-max.json'
    dedup.write_text(json.dumps(dict(version='0.3.7', deduplicated_with='contract-min',
                                    reason='same exact Core distribution/version')))
    record = tool.generate_oracles(tmp_path, executions, COMMIT, {})
    assert record['G-15']['result'] == 'pending: release execution'
    assert 'pending: release execution' in record['G-15']['stdout']
    assert any(s['path'] == dedup.name for s in record['G-04']['sources'])
    # Final scoring still requires real release executions, even with a generated summary.
    (executions / 'oracles.json').write_text(json.dumps(record))
    assert next(g for g in trace.score(tmp_path, executions, tmp_path, COMMIT)['automated']
                if g['id'] == 'G-15')['result'] == 'FAIL'
    dedup.write_text(json.dumps(dict(version='0.3.6', deduplicated_with='contract-min')))
    with pytest.raises(ValueError):
        tool.generate_oracles(tmp_path, executions, COMMIT, {})
