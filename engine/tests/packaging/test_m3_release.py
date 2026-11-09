"""M3 release policy and documentation are independently checked against current sources."""
import sys
from types import SimpleNamespace

import pytest

from _support import REPO, load_py


@pytest.mark.req('REQ-PKG-06')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('platform', ['', '   '])
def test_T_GEN_90_m3_package_gate_requires_nonempty_platform(platform):
    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'm3_runtime_gate')
    response = dict(mdflow='2.0.0', **{'markitdown-gc': '0.3.6'}, python='3.14.0', platform=platform,
                    protocol=1, triage_schema=1, pypdfium2='5.15.1', pillow='13.0.0')
    assert release.gate(response) == ['platform']


@pytest.mark.req('REQ-PKG-02', 'REQ-PKG-03', 'REQ-GEN-01')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_91_m3_reference_core_and_normative_dependency_hook_are_current():
    builder = (REPO / 'tools/build_engine.py').read_text(encoding='utf-8')
    assert 'markitdown-gc==0.3.6' in builder and 'Core 0.3.6' in builder
    bootstrap = (REPO / 'engine/BOOTSTRAP.md').read_text(encoding='utf-8')
    packaging = (REPO / 'docs/renewal/25_PACKAGING.md').read_text(encoding='utf-8')
    assert 'Core 0.3.6' in bootstrap and 'exact Core 0.3.6' in packaging
    assert 'markitdown-gc>=0.3.5,<0.4' in builder or 'pyproject.toml' in builder
    spec = (REPO / 'docs/renewal/10_SPEC.md').read_text(encoding='utf-8')
    hook = next(line for line in spec.splitlines() if line.startswith('| GEN-01 |'))
    assert all(name in hook for name in ('markitdown-gc', 'pypdfium2', 'Pillow'))
    assert 'Status: SPEC DRAFT-3.7' in spec


@pytest.mark.req('REQ-PKG-10', 'REQ-PLN-01')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_92_m3_handoff_and_plan_catalog_match_current_ownership():
    handoff = (REPO / 'docs/renewal/HANDOFF.md').read_text(encoding='utf-8')
    assert 'M3_ENGINE_FIXES.md' in handoff and 'Core 0.3.6' in handoff
    assert 'X-14 `version` must not fail' not in handoff
    plan = (REPO / 'docs/renewal/30_TESTPLAN.md').read_text(encoding='utf-8')
    row = next(line for line in plan.splitlines() if line.startswith('| T-PLN-55 |'))
    assert 'FX-03' in row or 'FX-01,03,' in row


@pytest.mark.req('REQ-PKG-03', 'REQ-GEN-10')
@pytest.mark.cov('S2', 'FM10')
@pytest.mark.fx('all')
@pytest.mark.scope('schema')
def test_T_META_94_m3_minimum_core_can_check_the_reference_seal_without_relabelling(monkeypatch):
    golden = load_py(REPO / 'tools/golden.py', 'm3_reference_golden')
    version = golden.importlib.metadata.version
    monkeypatch.setattr(golden.importlib.metadata, 'version', lambda name: '0.3.5' if name == 'markitdown-gc' else version(name))
    assert golden.verify(REPO)['core_version'] == '0.3.6'


@pytest.mark.req('REQ-PKG-09', 'REQ-PKG-01')
@pytest.mark.cov('S0', 'FM9')
def test_T_GEN_92_m3_recorder_launch_is_isolated_from_work_directory_modules(tmp_path, monkeypatch):
    record = load_py(REPO / 'tools/record_protocol.py', 'm3_isolated_recorder')
    recorder = record.Recorder(tmp_path / 'out', tmp_path / 'work')
    launches = []
    def child(argv, **kwargs):
        launches.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout=b'{}', stderr=b'')
    monkeypatch.setattr(record.subprocess, 'run', child)
    monkeypatch.setattr(recorder, 'save', lambda *a, **k: None)
    recorder.record('version', ['version'], expect=0, stdout='version.json')
    argv, options = launches[0]
    assert argv == [sys.executable, '-I', '-m', 'mdflow', 'version']
    assert options['cwd'] == recorder.work
    assert 'PYTHONPATH' not in options['env'] and 'PYTHONHOME' not in options['env']
