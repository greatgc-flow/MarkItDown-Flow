"""M2 release regressions; offline controls never fabricate real CI evidence."""
import importlib
import inspect
from pathlib import Path

import pytest

from _support import REPO, load_py, load_workflows, jobs, transitive_needs, step_text


@pytest.mark.req('REQ-PKG-01')
@pytest.mark.cov('S0', 'FM0')
def test_T_GEN_80_m2_installed_import_accepts_repo_local_venv_and_rejects_sources(tmp_path):
    module = importlib.import_module('_support')
    venv = REPO / 'build/test-venv'
    installed = venv / 'Lib/site-packages/mdflow/__init__.py'
    assert module.installed_import(installed, venv, REPO)
    assert not module.installed_import(REPO / 'engine/src/mdflow/__init__.py', venv, REPO)
    assert not module.installed_import(tmp_path / 'mdflow/__init__.py', venv, REPO)


@pytest.mark.req('REQ-PKG-06', 'REQ-GEN-03')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_81_m2_package_runtime_policy_rejects_experimental_and_renderer_mismatches():
    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'm2_pt_release')
    value = dict(mdflow='2.0.0', **{'markitdown-gc': '0.3.6'}, python='3.14.0', platform='test',
                 protocol=1, triage_schema=1, pypdfium2='5.15.1', pillow='13.0.0')
    assert release.gate(value) == []
    for field, bad in [('python', '3.15.0'), ('pypdfium2', '6.0.0'), ('pypdfium2', '4.30.0'),
                       ('pillow', '14.0.0'), ('pillow', '10.0.0')]:
        assert release.gate(dict(value, **{field: bad})), (field, bad)


@pytest.mark.req('REQ-PKG-17', 'REQ-PKG-13', 'REQ-PKG-08', 'REQ-GEN-03')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_82_m2_release_attests_then_verifies_then_scores_and_installed_suite_is_real():
    flows = load_workflows()
    release = jobs(flows['.github/workflows/release.yml'])
    assert 'verify-release' in release
    assert 'attest' in transitive_needs(release, 'verify-release')
    assert 'verify-release' in transitive_needs(release, 'publish')
    assert 'tools/release_gate.py' not in step_text(release['freeze'])
    verification = step_text(release['verify-release'])
    assert 'MDFLOW_RELEASE_BUNDLE' in verification and 'MDFLOW_ATTEST_DIR' in verification
    assert '-m release' in verification and 'junit-release-${{ matrix.os }}-py${{ matrix.python }}.xml' in verification
    assert 'verify-release' in transitive_needs(release, 'accept-release')
    assert 'tools/release_gate.py' in step_text(release['accept-release'])
    ci = jobs(flows['.github/workflows/ci.yml'])
    assert ci['pytest']['env']['MDFLOW_TEST_INSTALLED'] == '1'
    pt = (REPO / 'engine/tests/packaging/test_pt_release.py').read_text(encoding='utf-8')
    body = pt.split('def test_PT_17_', 1)[1]
    assert 'candidate["acceptance"]["score"]' not in body


@pytest.mark.req('REQ-PKG-08', 'REQ-GEN-03')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_83_m2_all_fixture_launchers_honor_installed_mode():
    root = (REPO / 'engine/tests/conftest.py').read_text(encoding='utf-8')
    unit = (REPO / 'engine/tests/unit/conftest.py').read_text(encoding='utf-8')
    assert 'MDFLOW_TEST_INSTALLED' in root and 'MDFLOW_TEST_INSTALLED' in unit
    assert 'assert_installed_import' in root


@pytest.mark.req('REQ-PKG-10', 'REQ-PLN-08', 'REQ-RPT-01')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_84_m2_fable_s14_s15_duplicate_provider_and_report_boundaries_removed():
    from mdflow import cli, report
    assert not hasattr(cli, '_provider_list')
    assert 'report_path' not in inspect.signature(report.publish).parameters


@pytest.mark.req('REQ-PKG-08', 'REQ-GEN-03', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_86_m2_missing_failed_or_wrong_commit_runtime_receipts_block_acceptance(tmp_path, trace_module, monkeypatch):
    import json
    import xml.etree.ElementTree as ET
    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    commit = 'a' * 40
    record = dict(nodeid='engine/tests/synthetic.py::test_T_GEN_00_receipt_control', tid='T-GEN-00', markers={})
    monkeypatch.setattr(trace_module, 'discover_tests', lambda root: [record])
    assert trace_module.required_executions(evidence, commit)
    for target in ('windows-2022', 'ubuntu-24.04', 'macos-15-intel'):
        for py in ('3.10', '3.14'):
            suite = ET.Element('testsuite')
            case = ET.SubElement(suite, 'testcase', name='explicit synthetic receipt control')
            props = ET.SubElement(case, 'properties')
            for key in ('nodeid', 'tid'):
                ET.SubElement(props, 'property', name=key, value=record[key])
            filename = f'junit-engine-{target}-py{py}.xml'
            ET.ElementTree(suite).write(evidence / filename)
            trace_module.write_execution_registry(evidence, filename, [dict(record, selected=True)], commit)
            (evidence / f'runtime-{target}-py{py}.json').write_text(json.dumps(dict(installed=True, commit=commit)))
        for py in ('3.11', '3.12', '3.13'):
            (evidence / f'smoke-{target}-py{py}.json').write_text(json.dumps(dict(exit=0, commit=commit)))
    assert trace_module.required_executions(evidence, commit) == []
    assert trace_module.required_executions(evidence, 'b' * 40)
    path = evidence / 'junit-engine-windows-2022-py3.10.xml'
    for bad in ('skipped','error','failure'):
        suite = ET.Element('testsuite')
        ET.SubElement(ET.SubElement(suite, 'testcase'), bad)
        ET.ElementTree(suite).write(path)
        assert trace_module.required_executions(evidence, commit)
