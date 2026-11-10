"""M6: optional diagnostics stay within the version gate's latency budget."""
import json
import os
import sys
import time

import pytest

TOOL_SLEEP_S = 30  # a stalled optional tool; every probe deadline is far shorter
# Child prelude: wrap Core's contained executor (used by both optional-tool probes) and record each
# probe's deadline, outcome and own monotonic duration, so T-CLI-87 does not depend on host load.
PROBE_RECORDER = '''
import json as _json, time as _time
from mdflow import core_guard as _guard
with _guard.quiet_output():
    from markitdown import _libreoffice as _lo
_real_execute = _lo._execute
def _recorded_execute(args, **kwargs):
    started, outcome = _time.monotonic(), 'ok'
    try:
        return _real_execute(args, **kwargs)
    except BaseException as error:
        outcome = type(error).__name__
        raise
    finally:
        with open(PROBES_LOG, 'a', encoding='utf-8') as log:
            log.write(_json.dumps(dict(tool='exiftool' if '-ver' in args else 'libreoffice',
                                       timeout_s=kwargs.get('timeout_s'), elapsed=_time.monotonic() - started,
                                       outcome=outcome)) + '\\n')
_lo._execute = _recorded_execute
'''


@pytest.fixture(autouse=True)
def reset_optional_probes():
    from mdflow import cli

    cli.reset_optional_tool_probes()
    try:
        yield
    finally:
        cli.reset_optional_tool_probes()


@pytest.mark.req('REQ-GEN-02', 'REQ-CNV-06', 'REQ-CNV-07')
@pytest.mark.cov('S0', 'FM7')
@pytest.mark.parametrize('slow', ['exiftool', 'libreoffice', 'both'])
def test_T_CLI_87_slow_optional_tools_cannot_exhaust_version_gate(tmp_path, monkeypatch, cli_command, slow):
    from markitdown import _libreoffice as lo

    script = tmp_path / 'slow.py'
    script.write_text(f'import time; time.sleep({TOOL_SLEEP_S})\n', encoding='utf-8')
    tool = tmp_path / ('slow.cmd' if os.name == 'nt' else 'slow')
    if os.name == 'nt':
        tool.write_text('@echo off\nif "%1"=="-ver" (type nul > "' + str(tmp_path / 'exiftool.started') +
                        '") else (type nul > "' + str(tmp_path / 'libreoffice.started') + '")\n"' +
                        sys.executable + '" "' + str(script) + '" %*\n')
    else:
        tool.write_text('#!/bin/sh\nif [ "$1" = "-ver" ]; then : > "' + str(tmp_path / 'exiftool.started') +
                        '"; else : > "' + str(tmp_path / 'libreoffice.started') + '"; fi\nexec "' +
                        sys.executable + '" "' + str(script) + '" "$@"\n')
        tool.chmod(0o755)
    environment = dict(
        EXIFTOOL_PATH=str(tool if slow in {'exiftool', 'both'} else tmp_path / 'absent-exif'),
        SOFFICE_PATH=str(tool if slow in {'libreoffice', 'both'} else tmp_path / 'absent-lo'),
        PATH=str(tmp_path), M1_WINDOWS_TEST_TEMP=os.environ.get('M1_WINDOWS_TEST_TEMP', ''))
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    # The property is measured inside the engine, not as whole-process wall time (interpreter start and
    # imports vary on a loaded host; the 3 s SPEC 10.1 figure is a healthy-machine target, see 30_TESTPLAN):
    # the child records every optional-tool probe's own deadline, outcome and monotonic duration.
    probes = tmp_path / 'probes.jsonl'
    prelude = PROBE_RECORDER.replace('PROBES_LOG', repr(str(probes)))
    # Core intentionally strips tool overrides from its contained child's env.
    # Restore test values before the temp bridge and any mdflow import, too.
    # Core contains the whole test child and its descendants even on a red timeout. The outer deadline
    # stays far below the stalled tool's 30 s sleep, so completing at all proves no probe waited for a tool.
    started = time.monotonic()
    text = lo._execute(cli_command('version', environment=environment, prelude=prelude), cwd=tmp_path,
                       timeout_s=TOOL_SLEEP_S / 2, output=tmp_path / 'capture.log')
    elapsed = time.monotonic() - started
    from mdflow import exiftool
    records = [json.loads(line) for line in probes.read_text(encoding='utf-8').splitlines()] if probes.exists() else []
    expected = [name for name in ('exiftool', 'libreoffice') if slow in {name, 'both'}]
    assert [r['tool'] for r in records] == expected, records
    for record in records:
        # Each stalled tool was killed at its own deadline: it ran at least that long, the probe failed,
        # and the probe ended long before the tool's own sleep would have.
        assert record['timeout_s'] == exiftool.VERSION_TIMEOUT_S == 0.5, record
        assert record['outcome'] != 'ok', record
        assert record['timeout_s'] * 0.9 <= record['elapsed'] < TOOL_SLEEP_S / 3, record
    print(f'T-CLI-87 {slow}: whole version child {elapsed:.3f}s (healthy-machine target < 3 s, not asserted)')
    value = json.loads(text)
    assert value['mdflow'] == '2.0.0' and value['python'] and value['markitdown-gc']
    assert value['protocol'] == value['triage_schema'] == 1
    assert value['exiftool'] == value['libreoffice'] == 'unavailable'
    assert value['exiftool_status'] == value['libreoffice_status'] == 'unusable'
    assert value['exiftool_source'] == 'EXIFTOOL_PATH'
    assert value['libreoffice_source'] == 'SOFFICE_PATH'
    for name in ('exiftool', 'libreoffice'):
        assert (tmp_path / (name + '.started')).exists() == (slow in {name, 'both'})


@pytest.mark.req('REQ-GEN-02', 'REQ-CNV-06', 'REQ-CNV-07')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('state', ['ok', 'timeout', 'malformed'])
def test_T_CLI_88_optional_probes_are_short_and_cached(tmp_path, monkeypatch, capsys, state):
    from mdflow import cli, exiftool
    from markitdown import _libreoffice as lo

    calls = []
    monkeypatch.setenv('EXIFTOOL_PATH', sys.executable)
    monkeypatch.setenv('SOFFICE_PATH', sys.executable)
    # A fresh environment cache key for each control, including cached failures.
    monkeypatch.setenv('PATH', str(tmp_path))
    cli.reset_optional_tool_probes()

    def execute(args, **kwargs):
        calls.append(args)
        assert 0 < kwargs['timeout_s'] <= 0.5
        if state == 'timeout':
            raise TimeoutError('optional tool deadline')
        if state == 'malformed':
            return 'garbage'
        return '13.59' if '-ver' in args else 'LibreOffice 25.2.7.2'

    monkeypatch.setattr(lo, '_execute', execute)
    try:
        for _ in range(2):
            assert cli.main(['version']) == 0
            captured = capsys.readouterr()
            assert captured.err == ''
            value = json.loads(captured.out)
            assert value['exiftool_status'] == value['libreoffice_status'] == ('ok' if state == 'ok' else 'unusable')
        assert len(calls) == 2, 'each optional tool is probed once per process/environment, even after failure'
    finally:
        cli.reset_optional_tool_probes()


@pytest.mark.req('REQ-GEN-02', 'REQ-CNV-06', 'REQ-CNV-07')
@pytest.mark.cov('S0', 'FM10')
def test_T_CLI_89_optional_diagnostic_errors_preserve_gate_fields(monkeypatch, capsys):
    from mdflow import cli

    def broken():
        raise RuntimeError('optional diagnostic failed')

    monkeypatch.setattr(cli.exiftool, 'detect', broken)
    # This tests the main command's informational boundary, independent of each resolver.
    monkeypatch.setattr(cli, '_libreoffice_versions', broken)
    assert cli.main(['version']) == 0
    captured = capsys.readouterr()
    assert captured.err == ''
    value = json.loads(captured.out)
    assert {'mdflow', 'markitdown-gc', 'pypdfium2', 'pillow', 'python', 'platform',
            'protocol', 'triage_schema'} <= value.keys()
    assert value['exiftool_status'] == value['libreoffice_status'] == 'unusable'
