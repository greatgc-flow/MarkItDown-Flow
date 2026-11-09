"""M4 operational recipes and explicit external evidence obligations."""
import re

import pytest

from _support import REPO


@pytest.mark.req('REQ-PKG-05', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_95_m4_all_bootstrap_engine_probes_are_isolated_and_evidence_is_explicit():
    for relative in ('engine/BOOTSTRAP.md', 'docs/renewal/25_PACKAGING.md'):
        lines = (REPO / relative).read_text(encoding='utf-8').splitlines()
        recipes = [line for line in lines if re.search(r'-m mdflow (?:version|selftest)', line)]
        assert recipes and all('-I -m mdflow' in line for line in recipes), relative
    acceptance = (REPO / 'docs/renewal/90_ACCEPTANCE.md').read_text(encoding='utf-8')
    assert re.search(r'^## \d+\. External evidence pending$', acceptance, re.M)
    for item in ('MAN-01', 'MAN-02', 'MAN-03', 'MAN-04', 'junit-reference.xml', 'smoke-', 'junit-release-'):
        assert item in acceptance
    for relative in ('docs/renewal/25_PACKAGING.md', 'docs/renewal/30_TESTPLAN.md',
                     'docs/renewal/90_ACCEPTANCE.md'):
        assert 'SYNC-AFTER-DRAFT-3' not in (REPO / relative).read_text(encoding='utf-8')


@pytest.mark.req('REQ-PKG-06')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('field,value,enabled', [
    ('python', '3.14garbage', False), ('python', '3.14.0rc1', True),
    ('mdflow', '2.0.0???', False), ('mdflow', '2.0.0.dev0', True),
    ('markitdown-gc', '0.3.7???', False), ('markitdown-gc', '0.3.7rc1', True),
    ('pypdfium2', '5.15.1???', False), ('pypdfium2', ' 5.15.1', False),
    ('pypdfium2', '5.15.1rc1', True), ('pypdfium2', '5.15.1.post1', True),
    ('pillow', '13.0.0???', False), ('pillow', '13.0.0+local', True),
    ('mdflow', '2.0', True), ('mdflow', '2.0rc1', True),
    ('mdflow', '2.0.0', True), ('mdflow', '2.0.0rc1', True), ('mdflow', '2.1', False),
    ('mdflow', '2.1.0.0', False), ('mdflow', '2.0.0.1', True),
    ('markitdown-gc', '0.4', False), ('python', '3.15', False),
    ('pillow', '14.0', False), ('pypdfium2', '6.0', False),
])
def test_T_GEN_96_m4_package_version_oracle_checks_full_syntax(field, value, enabled):
    from _support import load_py
    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'm4_gate')
    base = dict(mdflow='2.0.0', **{'markitdown-gc': '0.3.7'}, python='3.14.10', platform='test',
                protocol=1, triage_schema=1, pypdfium2='5.15.1', pillow='13.0.0')
    assert (release.gate(dict(base, **{field: value})) == []) is enabled


@pytest.mark.req('REQ-PKG-09', 'REQ-PKG-01')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_97_m4_recorded_argv_label_includes_the_actual_isolated_prefix(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from _support import load_py
    recorder = load_py(REPO / 'tools/record_protocol.py', 'm4_recorder')
    subject = recorder.Recorder(tmp_path / 'out', tmp_path / 'work')
    saved = []
    monkeypatch.setattr(recorder.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=0, stdout=b'{}', stderr=b''))
    monkeypatch.setattr(subject, 'save', lambda name, data, **kw: saved.append(kw))
    subject.record('version', ['version'], expect=0, stdout='version.json')
    assert saved[0]['argv'] == ['python', '-I', '-m', 'mdflow', 'version']
