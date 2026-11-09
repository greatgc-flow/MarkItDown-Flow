"""Missing Core is a typed diagnostic response, not a package-gate exception."""
import json

import pytest

from _support import REPO, load_py


@pytest.mark.req('REQ-PKG-06', 'REQ-GEN-02')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('core', ['unavailable', 'not-a-version', ''])
def test_T_GEN_87_package_gate_blocks_unavailable_core_without_raising(core):
    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'fable_handoff_pt_release')
    value = dict(mdflow='2.0.0', **{'markitdown-gc': core}, python='3.14.0', platform='test',
                 protocol=1, triage_schema=1, pypdfium2='5.15.1', pillow='13.0.0')
    assert 'Core range' in release.gate(value)


@pytest.mark.req('REQ-PKG-09', 'REQ-PKG-06')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-71')
def test_T_GEN_88_fx71_records_current_engine_with_honest_host_policy_and_replayable_variants():
    import mdflow

    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'fable_fx71_pt_release')
    record = load_py(REPO / 'tools/record_protocol.py', 'fable_fx71_recorder')
    fixtures = REPO / 'shell/test/fixtures/fx71'
    manifest = json.loads((fixtures / 'manifest.json').read_text(encoding='utf-8'))
    actual = json.loads((fixtures / 'version.json').read_text(encoding='utf-8'))
    assert actual['mdflow'] == mdflow.__version__ == '2.0.0'
    assert manifest['engine'] == actual
    assert actual['python'] == manifest['recording_host']['python']
    # Host compatibility is diagnosed, never rewritten to make a recording pass.
    # A supported-host recording remains a release prerequisite (PT-06).
    supported = (3, 10) <= release.version_tuple(actual['python'])[:2] < (3, 15)
    assert release.gate(actual) == ([] if supported else ['Python range'])
    assert record.verify(fixtures) == 0
    for variant, field, value in [('python-3.15', 'python', '3.15.2'),
                                  ('core-unavailable', 'markitdown-gc', 'unavailable')]:
        name = f'version.{variant}.json'
        assert manifest['files'][name]['kind'] == 'derived'
        assert manifest['files'][name]['derived_from'] == 'version.json'
        response = json.loads((fixtures / name).read_text(encoding='utf-8'))
        assert response == dict(actual, **{field: value})
        assert release.gate(response)


@pytest.mark.req('REQ-PKG-09', 'REQ-PKG-01')
@pytest.mark.cov('S0', 'FM10')
def test_T_GEN_89_fx71_recorder_does_not_inject_engine_sources(tmp_path):
    record = load_py(REPO / 'tools/record_protocol.py', 'fable_fx71_installed_recorder')
    recorder = record.Recorder(tmp_path / 'out', tmp_path / 'work')
    assert 'PYTHONPATH' not in recorder.env
    assert 'PYTHONHOME' not in recorder.env
