"""Core admission and portable FX-71 recording/verification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

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
def test_T_GEN_89_fx71_recorder_does_not_inject_engine_sources(tmp_path, monkeypatch):
    from mdflow.providers.command import CommandProvider

    record = load_py(REPO / 'tools/record_protocol.py', 'fable_fx71_installed_recorder')
    recorder = record.Recorder(tmp_path / 'out', tmp_path / 'work')
    assert 'PYTHONPATH' not in recorder.env
    assert 'PYTHONHOME' not in recorder.env
    shim = recorder.work / 'bin' / ('python.cmd' if os.name == 'nt' else 'python')
    assert recorder.env['PATH'].split(os.pathsep)[0] == str(shim.parent)
    with monkeypatch.context() as patch:
        for name, value in recorder.env.items():
            patch.setenv(name, value)
        provider = CommandProvider(command='python ocr_echo.py {input}', egress=False, model='test')
    assert Path(json.loads(provider.meta['destination'][len('command:'):])[0]) == Path('~') / shim.relative_to(recorder.work)
    result = subprocess.run([str(shim), '-I', '-c', 'import sys; print(sys.executable)'],
                            cwd=recorder.work, env=recorder.env, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert os.path.samefile(result.stdout.decode().strip(), sys.executable)


@pytest.mark.req('REQ-PKG-09', 'REQ-SEC-02')
@pytest.mark.cov('S0', 'FM9')
@pytest.mark.fx('FX-71')
@pytest.mark.parametrize('data', [
    b'X:\\outside\\python.exe', b'X:/outside/python.exe',
    b'/Users/another/bin/python', b'/home/another/bin/python', b'/tmp/private/file',
    b'/var/folders/private/file', b'/opt/bin/python', b'/custom-root/private/file',
    json.dumps({'destination': 'command:' + json.dumps([r'Q:\elsewhere\python.exe'])}).encode(),
])
def test_T_GEN_98_fx71_leak_check_rejects_paths_beyond_known_recording_roots(tmp_path, data):
    record = load_py(REPO / 'tools/record_protocol.py', 'fx71_path_leak_recorder')
    subject = record.Recorder(tmp_path / 'out', tmp_path / 'work')
    subject.out.mkdir()
    # A valid manifest hash must never make a privacy leak pass verification.
    with pytest.raises(SystemExit, match='absolute path'):
        subject.save('leak.json', data, argv=[], exit_code=0, stream='stdout', env_names=[])
    (subject.out / 'leak.json').write_bytes(data)
    manifest = {'files': {'leak.json': dict(kind='recorded', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())}}
    (subject.out / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    assert record.verify(subject.out) == 1


@pytest.mark.req('REQ-PKG-09', 'REQ-SEC-02')
@pytest.mark.cov('S0', 'FM9')
@pytest.mark.fx('FX-71')
def test_T_GEN_99_fx71_leak_check_allows_portable_paths_and_endpoint_urls(tmp_path):
    record = load_py(REPO / 'tools/record_protocol.py', 'fx71_portable_recorder')
    subject = record.Recorder(tmp_path / 'out', tmp_path / 'work')
    subject.out.mkdir()
    subject.save('portable.json', b'{"paths":["~/bin/python","~\\\\bin\\\\python.cmd","sub/a.pdf"],'
                 b'"url":"https://api.openai.com/v1/chat/completions","text":"<!-- /mdflow:ocr -->"}',
                 argv=[], exit_code=0, stream='stdout', env_names=[])
    subject.save('korean.json', json.dumps({'path': '보고서/3분기 결산.pdf'}, ensure_ascii=False).encode(),
                 argv=[], exit_code=0, stream='stdout', env_names=[])
