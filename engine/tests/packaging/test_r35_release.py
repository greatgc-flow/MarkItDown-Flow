"""R35 publication, peer identities and evidence production regressions (offline)."""
from copy import deepcopy
import json
import sys

import pytest

from _support import REPO, load_py, load_yaml

COMMIT = 'a' * 40
DEFERRED = 'deferred: post-release (R35)'


@pytest.mark.req('REQ-PKG-17', 'REQ-PKG-22')
@pytest.mark.cov('S0', 'FM10')
def test_PT_25_r35_score_and_publication_require_93_plus_three_peer_reviews(trace_module, tmp_path, monkeypatch):
    trace = trace_module
    docs = tmp_path / 'docs/renewal'
    docs.mkdir(parents=True)
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    (docs / '90_ACCEPTANCE.md').write_text('\n'.join(
        f'| G-{i:02d} | {w} | `PT-17` | command | expected |' for i, w in enumerate(weights, 1)))
    rows = [dict(tid='PT-17', nodeid='test::test_PT_17', markers={})]
    monkeypatch.setattr(trace, 'discover_tests', lambda root: rows)
    monkeypatch.setattr(trace, 'discover_shell_tests', lambda root: [])
    monkeypatch.setattr(trace, 'planned_tests', lambda root: {'PT-17': set()})
    monkeypatch.setattr(trace, 'execution_receipt', lambda *a, **kw: ([], {}))
    monkeypatch.setattr(trace, 'rows_passed', lambda *a: True)
    reviews = tmp_path / 'reviews'
    reviews.mkdir()
    errors = {k: [] for k in trace.MANUAL_FILES}
    monkeypatch.setattr(trace, 'attest', lambda root, identity, *a: errors[identity])
    (tmp_path / 'oracles.json').write_text(json.dumps({f'G-{i:02d}': dict(
        command='actual command', stdout='actual output', exit=0, commit=COMMIT) for i in range(1, 18)}))
    result = trace.score(tmp_path, tmp_path, reviews, COMMIT)
    assert result['score'] == 'SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 ' + DEFERRED
    assert result['manual'][-1]['status'] == DEFERRED
    assert trace.publication_problems(result) == []
    assert {r['id'] for r in result['post_release']} == {'MAN-04', 'REQ-PKG-19', 'REQ-PKG-21'}
    # No missing, failed or substituted pre-publication gate can be hidden by a score string.
    for identity in ('MAN-01', 'MAN-02', 'MAN-03'):
        errors[identity] = ['missing peer review']
        assert trace.publication_problems(trace.score(tmp_path, tmp_path, reviews, COMMIT))
        errors[identity] = []
    for mutation in ('automated', 'manual', 'deferred'):
        bad = deepcopy(result)
        if mutation == 'automated':
            bad['automated'][0]['result'] = 'FAIL'
        elif mutation == 'manual':
            bad['manual'].pop(0)
        else:
            bad['manual'][-1]['status'] = 'PASS'
        assert trace.publication_problems(bad)
    # A supplied MAN-04 is validated; invalid evidence cannot become a deferral.
    (reviews / trace.MANUAL_FILES['MAN-04']).write_text('{}')
    errors['MAN-04'] = ['failed rehearsal']
    assert trace.publication_problems(trace.score(tmp_path, tmp_path, reviews, COMMIT))
    errors['MAN-04'] = []
    complete = trace.score(tmp_path, tmp_path, reviews, COMMIT)
    assert complete['score'] == 'SCORE 100/100 (automated 93/93, manual 7/7); MAN-04 PASS (post-release)'
    assert trace.publication_problems(complete) == []
    # Both the gate and the publisher enforce the same structured policy.
    for name in ('release_gate.py', 'publish_release.py'):
        assert 'publication_problems(' in (REPO / 'tools' / name).read_text(encoding='utf-8')


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('identity', ['MAN-01', 'MAN-02', 'MAN-03'])
def test_PT_26_r35_attest_requires_named_peer_profile_model(trace_module, tmp_path, identity):
    record = dict(id=identity, reviewer='cx/cx.effort/gpt-6.1-sol', implementer='cc.fable',
                  date='2026-11-09', commit=COMMIT, inputs=['SPEC'], checks=['PASS'],
                  evidence=['review notes'], verdict='PASS')
    path = tmp_path / trace_module.MANUAL_FILES[identity]
    path.write_text(json.dumps(record))
    assert trace_module.attest(REPO, identity, tmp_path, COMMIT) == []
    for reviewer in ('Reviewer', 'peer/model', ' /profile/model', 'peer//model', '<PEER>/<PROFILE>/<MODEL>'):
        path.write_text(json.dumps(dict(record, reviewer=reviewer)))
        assert trace_module.attest(REPO, identity, tmp_path, COMMIT), reviewer
    if identity == 'MAN-01':
        path.write_text(json.dumps(dict(record, implementer='cx/other-profile/other-model')))
        assert trace_module.attest(REPO, identity, tmp_path, COMMIT)


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-04', 'REQ-PKG-11', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_PT_27_r35_extra_evidence_has_validated_templates_and_automatic_facts(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / 'tools'))
    tool = load_py(REPO / 'tools/release_evidence.py', 'r35_release_evidence')
    from test_pt_manual_evidence import fill
    for filename in tool.EXTRA_FILES:
        template = json.loads((REPO / 'docs/renewal/manual-templates' / filename).read_text())
        assert tool.validate_extra(filename, template, COMMIT, root=REPO)
    reviews = tmp_path / 'reviews'
    reviews.mkdir()
    # Producer fills only machine facts; it preserves the peer's supplied reviews.
    for filename in tool.EXTRA_FILES:
        data = fill(json.loads((REPO / 'docs/renewal/manual-templates' / filename).read_text()))
        def bind(node):
            if isinstance(node, dict):
                return {k: COMMIT if k == 'commit' else 0 if k == 'exit' else bind(v) for k, v in node.items()}
            return [bind(v) for v in node] if isinstance(node, list) else node
        (reviews / filename).write_text(json.dumps(bind(data)))
    pins = tool.action_pins(REPO)
    seen = []
    def gh_json(endpoint):
        seen.append(endpoint)
        for action, sha in pins.items():
            if endpoint == f'repos/{action}/commits/{sha}':
                return {'sha': sha}
        raise AssertionError(endpoint)
    catalog = {'info': {'name': 'markitdown-gc', 'version': '0.3.7', 'license': 'MIT'}, 'urls': [
        {'filename': 'markitdown_gc-0.3.7-py3-none-any.whl', 'url': 'https://files.pythonhosted.org/core.whl',
         'digests': {'sha256': 'ab' * 32}, 'packagetype': 'bdist_wheel', 'size': 123, 'yanked': False}]}
    monkeypatch.setattr(tool, 'gh_json', gh_json)
    monkeypatch.setattr(tool, 'pypi_json', lambda version: deepcopy(catalog))
    executions = tmp_path / 'executions'
    executions.mkdir()
    for runner, platform in (('windows-2022', 'win32'), ('ubuntu-24.04', 'linux'), ('macos-26', 'darwin')):
        for py in ('3.10', '3.14'):
            (executions / f'runtime-{runner}-py{py}.json').write_text(json.dumps(dict(commit=COMMIT, installed=True)))
            (executions / f'install-{platform}-py{py}-compat-env.json').write_text(json.dumps({'install': [
                {'metadata': {'name': 'markitdown-gc', 'version': '0.3.7'}, 'download_info': {
                    'url': catalog['urls'][0]['url'], 'archive_info': {'hashes': {'sha256': 'ab' * 32}}}}]}))
    output = tmp_path / 'output'
    tool.produce_extras(REPO, reviews, output, COMMIT, executions=executions)
    assert len(seen) == len(pins)
    for filename in tool.EXTRA_FILES:
        record = json.loads((output / filename).read_text())
        assert tool.validate_extra(filename, record, COMMIT, root=REPO) == [], filename
        assert tool.validate_extra(filename, record, 'b' * 40, root=REPO), filename
        broken = deepcopy(record)
        if filename == 'oracles.json':
            broken['G-01']['exit'] = False  # booleans cannot stand in for command return codes
        elif filename == 'actions-review.json':
            broken['actions'][0]['sha'] = '0' * 40
        elif filename == 'pkg04_core_artifacts.json':
            broken['artifacts'][0]['sha256'] = 'bad digest'
        else:
            broken['checks']['readme_disclosures'] = 'FAIL'
        assert tool.validate_extra(filename, broken, COMMIT, root=REPO), filename
        broken = deepcopy(record)
        if filename == 'oracles.json':
            del broken['G-17']
        elif filename == 'actions-review.json':
            del broken['actions'][0]['checks']['dependencies']
        elif filename == 'pkg04_core_artifacts.json':
            broken['install_reports'].pop()
        else:
            broken['reviewer'] = 'generic reviewer'
        assert tool.validate_extra(filename, broken, COMMIT, root=REPO), filename
    generated = json.loads((output / 'pkg04_core_artifacts.json').read_text())
    assert generated['artifacts'][0]['sha256'] == 'ab' * 32
    assert generated['artifacts'][0]['url'] == catalog['urls'][0]['url']
    assert generated['reviewer'] == 'cx/cx.effort/gpt-6.1-sol'
    monkeypatch.setattr(tool, 'gh_json', lambda endpoint: {'sha': '0' * 40})
    with pytest.raises(ValueError, match='SHA'):
        tool.produce_extras(REPO, reviews, tmp_path / 'bad', COMMIT, executions=executions)


@pytest.mark.req('REQ-PKG-17', 'REQ-PKG-18', 'REQ-PKG-20', 'REQ-PKG-22')
@pytest.mark.cov('S0', 'FM10')
def test_PT_28_r35_gate_seals_deferral_publisher_enforces_it_and_rehearsal_stays_post_release(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / 'tools'))
    gate = load_py(REPO / 'tools/release_gate.py', 'r35_gate')
    publisher = load_py(REPO / 'tools/publish_release.py', 'r35_publisher')
    schema = load_py(REPO / 'tools/release_evidence.py', 'r35_schema')
    tests = load_py(REPO / 'engine/tests/packaging/test_pt_evidence.py', 'r35_evidence_tests')
    # The rollback observation belongs to the owner's real-app MAN-04, not this tooling gate.
    try:
        tests.test_PT_20_rollback_rehearsal_schema_validator(schema, tmp_path)
    except pytest.skip.Exception:
        pytest.fail('pre-publication PT-20 still requires the post-release real-app rollback record')
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    result = dict(score='SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 ' + DEFERRED,
        automated=[dict(id=f'G-{i:02d}', weight=w, result='PASS') for i, w in enumerate(weights, 1)],
        manual=[dict(id=f'MAN-{i:02d}', weight=w, problems=[], status=DEFERRED if i == 4 else 'PASS')
                for i, w in enumerate((3, 2, 1, 1), 1)],
        post_release=[dict(id='MAN-04', status=DEFERRED), dict(id='REQ-PKG-19', status='pending: post-release'),
                      dict(id='REQ-PKG-21', status='pending: post-release')])
    candidate = dict(commit=COMMIT, repo='owner/repo', tag='2.0.0')
    folder = tmp_path / 'candidate'
    folder.mkdir()
    manual = tmp_path / 'manual'
    manual.mkdir()
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    for name in schema.EXTRA_FILES:
        (manual / name).write_text('{}')
    for key, value in dict(GITHUB_REF_TYPE='tag', GITHUB_REF_NAME='2.0.0', GITHUB_SHA=COMMIT,
                           GITHUB_REPOSITORY='owner/repo', GITHUB_RUN_ID='123').items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(gate, 'verify', lambda path: deepcopy(candidate))
    monkeypatch.setattr(gate, 'versions', lambda tag: None)
    monkeypatch.setattr(gate, 'required_executions', lambda *a: [])
    monkeypatch.setattr(gate, 'validate_extra', lambda *a, **kw: [])
    monkeypatch.setattr(gate, 'score', lambda *a: deepcopy(result))
    monkeypatch.setattr(gate.subprocess, 'check_output', lambda args, **kw: COMMIT if args[1] == 'api' else
                        json.dumps(dict(tagName='1.0.8', assets=[dict(name=n) for n in ('main.js', 'manifest.json', 'styles.css')])))
    monkeypatch.setattr(sys, 'argv', ['release_gate.py', '--candidate', str(folder), '--evidence', str(evidence), '--manual', str(manual)])
    gate.main()
    sealed = json.loads((folder / 'release-candidate.json').read_text())
    assert sealed['acceptance']['manual'][-1]['status'] == DEFERRED
    assert sealed['acceptance']['post_release'] == result['post_release']
    monkeypatch.setattr(publisher, 'verify', lambda path: sealed)
    monkeypatch.setattr(publisher, 'versions', lambda tag: None)
    def reached_gh(*args, **kwargs):
        raise RuntimeError('accepted before external operations')
    monkeypatch.setattr(publisher, 'gh', reached_gh)
    monkeypatch.setattr(sys, 'argv', ['publish_release.py', '--candidate', str(folder)])
    with pytest.raises(RuntimeError, match='accepted before external operations'):
        publisher.main()
    sealed['acceptance']['manual'].pop()
    with pytest.raises(ValueError, match='acceptance must pass'):
        publisher.main()
