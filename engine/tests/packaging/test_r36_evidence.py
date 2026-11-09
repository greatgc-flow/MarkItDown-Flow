"""R36 receipt generation and reduced peer responsibilities (offline)."""
from copy import deepcopy
import hashlib
import json
import sys

import pytest

from _support import REPO, load_py, load_workflows, jobs, step_text, transitive_needs

COMMIT = 'a' * 40


def candidate_receipts(root, trace, *, soffice=False):
    docs = root / 'docs/renewal'
    docs.mkdir(parents=True)
    tests = root / 'engine/tests'
    tests.mkdir(parents=True)
    (tests / 'test_example.py').write_text(
        'def test_PT_17(): pass\ndef test_CT_01(): pass\n'
        '@pytest.mark.release\ndef test_PT_02(): pass\n'
        '@pytest.mark.release\ndef test_PT_04(): pass\n')
    if soffice:
        (tests / 'test_soffice.py').write_text(
            '@pytest.mark.soffice\ndef test_T_CNV_93(): pass\n')
    weights = [5, 7, 9, 6, 8, 7, 8, 6, 5, 6, 5, 5, 5, 4, 4, 2, 1]
    selectors = {4: 'CT-01', 13: 'PT-02', 15: 'PT-04'}
    if soffice:
        selectors[2] = 'T-CNV-93`, `CT-01'
    (docs / '90_ACCEPTANCE.md').write_text('\n'.join(
        f'| G-{i:02d} example | {w} | `{selectors.get(i, "PT-17")}` | pytest example | all pass |'
        for i, w in enumerate(weights, 1)))
    (docs / '30_TESTPLAN.md').write_text('## 4. Test catalog\n' + '\n'.join(
        f'| {tid} | REQ-PKG-17 | A |' for tid in ('PT-17', 'CT-01', 'PT-02', 'PT-04', *(['T-CNV-93'] if soffice else []))) + '\n## 5. End\n')
    executions = root / 'executions'
    executions.mkdir()
    rows = trace.discover_tests(root)
    names = ['junit-reference.xml', 'junit-contract-min.xml', 'junit-contract-max.xml']
    names += [f'junit-{phase}-{runner}-py{py}.xml'
              for phase in ('engine', 'release') for runner in ('windows-2022', 'ubuntu-24.04', 'macos-26')
              for py in ('3.10', '3.14')]
    if soffice:
        base = next(r for r in rows if r['tid'] == 'T-CNV-93')
        rows = [r for r in rows if r is not base] + [
            dict(base, nodeid=base['nodeid'] + f'[{extension}]') for extension in ('doc', 'rtf')]
        names.append('junit-legacy-libreoffice-ubuntu-24.04-py3.14.xml')
    for name in names:
        selected = [dict(r, selected=(r['tid'] == 'T-CNV-93' if 'legacy-libreoffice' in name
                                     else r['tid'] != 'T-CNV-93')) for r in rows]
        trace.write_collection(trace.collection_path(executions, name), rows, COMMIT, root=root)
        trace.write_execution_registry(executions, name, selected, COMMIT)
        (executions / name).write_text('<testsuite>' + ''.join(
            '<testcase><properties><property name="nodeid" value="' + r['nodeid'] + '"/>'
            '<property name="tid" value="' + r['tid'] + '"/></properties></testcase>' for r in selected if r['selected']) + '</testsuite>')
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


@pytest.mark.req('REQ-PKG-08', 'REQ-PKG-17', 'REQ-PKG-22')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('mutation', ['none', 'missing', 'skipped', 'failed', 'stale', 'omit_parameter', 'missing_collection'])
def test_PT_33_soffice_gate_requires_dedicated_complete_ci_receipt(tmp_path, mutation):
    sys.path.insert(0, str(REPO / 'tools'))
    tool = load_py(REPO / 'tools/release_evidence.py', 'soffice_evidence')
    import trace
    executions = candidate_receipts(tmp_path, trace, soffice=True)
    filename = 'junit-legacy-libreoffice-ubuntu-24.04-py3.14.xml'
    record = tool.generate_oracles(tmp_path, executions, COMMIT, {})
    sources = {s['path'] for s in record['G-02']['sources']}
    assert {filename, trace.execution_registry_path(executions, filename).name,
            trace.collection_path(executions, filename).name} <= sources
    assert record['G-02']['result'] == 'PASS'
    if mutation == 'none':
        return
    path = executions / filename
    if mutation == 'missing':
        path.unlink()
    elif mutation in {'skipped', 'failed'}:
        path.write_text(path.read_text().replace('</testcase>',
            '<skipped/></testcase>' if mutation == 'skipped' else '<failure/></testcase>', 1))
    elif mutation == 'stale':
        registry = trace.execution_registry_path(executions, filename)
        registry.write_text(registry.read_text().replace(COMMIT, 'b' * 40))
    elif mutation == 'missing_collection':
        trace.collection_path(executions, filename).unlink()
    else:
        registry = trace.execution_registry_path(executions, filename)
        data = json.loads(registry.read_text())
        data['tests'] = [r for r in data['tests'] if not r['nodeid'].endswith('[rtf]')]
        registry.write_text(json.dumps(data))
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        tree.getroot().remove(tree.getroot()[-1])
        tree.write(path)
    with pytest.raises(ValueError):
        tool.generate_oracles(tmp_path, executions, COMMIT, {})


@pytest.mark.req('REQ-PKG-08', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_PT_34_soffice_ci_executes_installed_wheel_and_rejects_skips(test_registry, tmp_path):
    import subprocess
    ci = jobs(load_workflows()['.github/workflows/ci.yml'])
    assert '-m "not release and not soffice"' in step_text(ci['pytest'])
    job = ci['legacy-libreoffice']
    assert job['runs-on'] == 'ubuntu-24.04'
    assert not job.get('continue-on-error', False) and not job.get('strategy')
    assert job['env']['MDFLOW_TEST_INSTALLED'] == '1'
    assert 'candidate' in transitive_needs(ci, 'legacy-libreoffice')
    assert 'legacy-libreoffice' in transitive_needs(ci, 'trace')
    steps = job['steps']
    assert any(s.get('with', {}).get('python-version') == '3.14' for s in steps)
    text = step_text(job)
    assert 'apt-get install' in text and 'libreoffice-writer-nogui' in text and 'libreoffice-impress-nogui' in text
    assert 'packaged_check.py install-current' in text and '-m soffice' in text
    assert 'junit-legacy-libreoffice-ubuntu-24.04-py3.14.xml' in text
    upload = next(s for s in steps if 'actions/upload-artifact@' in s.get('uses', ''))
    assert upload['if'] == '${{ always() }}'
    assert upload['with']['name'] == 'legacy-libreoffice'
    assert any(s.get('with', {}).get('name') == 'legacy-libreoffice' for s in ci['trace']['steps'])
    real = [r for r in test_registry if r['tid'] == 'T-CNV-93']
    assert real and all('soffice' in r['markers'] for r in real)
    # Execute the workflow's JUnit check against both a pass and a skip.
    check = next(s['run'] for s in steps if s.get('name') == 'Require zero skipped LibreOffice tests')
    path = tmp_path / 'build/trace/junit-legacy-libreoffice-ubuntu-24.04-py3.14.xml'
    path.parent.mkdir(parents=True)
    import shlex
    args = shlex.split(check)
    assert args[:2] == ['python', '-c']
    for child, expected in [('', 0), ('<skipped/>', 1), ('<failure/>', 1), ('<error/>', 1)]:
        path.write_text('<testsuite><testcase>' + child + '</testcase></testsuite>')
        result = subprocess.run([sys.executable, *args[1:]], cwd=tmp_path, capture_output=True)
        assert result.returncode == expected, result.stderr
    path.write_text('<testsuite/>')
    assert subprocess.run([sys.executable, *args[1:]], cwd=tmp_path, capture_output=True).returncode == 1


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


@pytest.mark.req("REQ-PKG-04")
@pytest.mark.cov("S0", "FM10")
def test_PT_35_install_report_accepts_legacy_pip_archive_hash_form():
    """pip < 23 writes archive_info.hash ('sha256=<hex>') without the hashes{} dict (py3.10 CI cells)."""
    module = load_py(REPO / "tools/release_evidence.py", "legacy_hash")
    digest = "a" * 64
    assert module.archive_sha256({"archive_info": {"hash": f"sha256={digest}"}}) == digest
    assert module.archive_sha256({"archive_info": {"hashes": {"sha256": digest}}}) == digest
    assert module.archive_sha256({"archive_info": {"hash": "md5=abc"}}) == ""
    assert module.archive_sha256({}) == ""


@pytest.mark.req("REQ-PKG-04")
@pytest.mark.cov("S0", "FM10")
def test_PT_36_placeholder_scan_excludes_only_pkg04_machine_fields():
    sys.path.insert(0, str(REPO / "tools"))
    module = load_py(REPO / "tools/release_evidence.py", "placeholder_scope")
    download = {"url": "https://files.pythonhosted.org/core.whl",
                "archive_info": {"hashes": {"sha256": "a" * 64}}}
    record = dict(
        reviewer="cx/cx.effort/gpt-6.1-sol", date="2026-11-10", commit=COMMIT,
        evidence=["artifact license review notes"], verdict="PASS",
        package="markitdown-gc", version="0.3.7",
        source="https://pypi.org/pypi/markitdown-gc/0.3.7/json",
        checks={"artifact_licenses": "PASS"},
        artifacts=[dict(filename="core.whl", url=download["url"], sha256="a" * 64,
                        size=123, packagetype="bdist_wheel", yanked=False)],
        install_reports=[dict(target=target, commit=COMMIT, exit=0, report={"install": [
            {"metadata": {"name": "markitdown-gc", "version": "0.3.7"}, "download_info": download},
            {"metadata": {"name": "pypdfium2", "version": "4.30.0"}, "download_info": download},
        ]}) for target in module.TARGETS],
    )
    filename = "pkg04_core_artifacts.json"
    assert module.validate_extra(filename, record, COMMIT, root=REPO) == []
    metadata = record["install_reports"][0]["report"]["install"][1]["metadata"]
    for field, text in (("description", "<!-- TODO: third-party documentation -->"),
                        ("license", "Copyright <YEAR>, <COPYRIGHT HOLDER>")):
        metadata[field] = text
        assert module.validate_extra(filename, record, COMMIT, root=REPO) == []
        del metadata[field]
    record["artifacts"][0]["filename"] = "TODO.whl"
    assert module.validate_extra(filename, record, COMMIT, root=REPO) == []
    for text in ("TODO", "<REVIEW NOTES>"):
        peer_placeholder = dict(record, evidence=[text])
        assert "unfilled evidence placeholders" in module.validate_extra(
            filename, peer_placeholder, COMMIT, root=REPO)
    # The same field names in other files remain subject to the placeholder scan.
    for other in set(module.EXTRA_FILES) - {filename}:
        assert "unfilled evidence placeholders" in module.validate_extra(
            other, record, COMMIT, root=REPO)
