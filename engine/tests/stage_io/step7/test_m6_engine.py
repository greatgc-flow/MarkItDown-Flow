"""M6: optional diagnostics stay within the version gate's latency budget."""
import json
import os
import sys
import time

import pytest

TOOL_SLEEP_S = 30  # a stalled optional tool; every probe deadline is far shorter
# A stalled probe must end within its deadline plus this kill allowance (process-tree kill and reap).
# Two stalled probes then cost <= 2 * (0.5 + 1.0) = 3 s, inside the shell's 5 s version-gate budget.
KILL_SLACK_S = 1.0
# Child prelude: wrap Core's contained executor (used by both optional-tool probes) and record each
# probe's REQUESTED deadline, outcome and own monotonic duration, so T-CLI-87 does not depend on host
# load. DELAY_S > 0 is the negative control: Core is handed a later deadline than the one requested.
PROBE_RECORDER = '''
import json as _json, time as _time
from mdflow import core_guard as _guard
with _guard.quiet_output():
    from markitdown import _libreoffice as _lo
_real_execute = _lo._execute
def _recorded_execute(args, **kwargs):
    started, outcome = _time.monotonic(), 'ok'
    try:
        return _real_execute(args, **dict(kwargs, timeout_s=kwargs['timeout_s'] + DELAY_S))
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


def probe_problems(records, expected, deadline):
    """Every way the probe records can violate the M6 property (empty list: property holds)."""
    problems = []
    # An absent override with a folder (EXIFTOOL_PATH) is still probed as given and fails at once with
    # FileNotFoundError; only the stalled tools reach their deadline.
    stalled = [r for r in records if r['outcome'] != 'FileNotFoundError']
    if [r['tool'] for r in stalled] != expected or len({r['tool'] for r in records}) != len(records):
        problems.append(f'probed tools {records} != expected stalled {expected}')
    for r in records:
        if r['timeout_s'] != deadline or r['outcome'] == 'ok':
            problems.append(f'{r["tool"]}: deadline {r["timeout_s"]} / outcome {r["outcome"]}')
    for r in stalled:
        # Enforced: killed AT its deadline -- it ran at least that long and ended within the kill allowance.
        if r['elapsed'] < r['timeout_s'] * 0.9:
            problems.append(f'{r["tool"]}: ended before its deadline ({r["elapsed"]:.3f}s)')
        if r['elapsed'] > r['timeout_s'] + KILL_SLACK_S:
            problems.append(f'{r["tool"]}: killed late ({r["elapsed"]:.3f}s > {r["timeout_s"]} + {KILL_SLACK_S}s)')
    return problems


def run_version_child(tmp_path, monkeypatch, cli_command, slow, delay_s=0.0):
    """Run `mdflow version` in Core's contained executor with stalled optional tools; (records, stdout)."""
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
    prelude = PROBE_RECORDER.replace('PROBES_LOG', repr(str(probes))).replace('DELAY_S', repr(float(delay_s)))
    # Core intentionally strips tool overrides from its contained child's env.
    # Restore test values before the temp bridge and any mdflow import, too.
    # Core contains the whole test child and its descendants even on a red timeout. The outer deadline
    # stays far below the stalled tool's 30 s sleep, so completing at all proves no probe waited for a tool.
    started = time.monotonic()
    text = lo._execute(cli_command('version', environment=environment, prelude=prelude), cwd=tmp_path,
                       timeout_s=TOOL_SLEEP_S / 2, output=tmp_path / 'capture.log')
    elapsed = time.monotonic() - started
    records = [json.loads(line) for line in probes.read_text(encoding='utf-8').splitlines()] if probes.exists() else []
    print(f'T-CLI-87 {slow} delay={delay_s}: whole version child {elapsed:.3f}s (healthy-machine target < 3 s, '
          'not asserted); probes ' + ', '.join(f'{r["tool"]} {r["elapsed"]:.3f}s' for r in records))
    return records, text


@pytest.mark.req('REQ-GEN-02', 'REQ-CNV-06', 'REQ-CNV-07')
@pytest.mark.cov('S0', 'FM7')
@pytest.mark.parametrize('slow', ['exiftool', 'libreoffice', 'both', 'late-kill-control'])
def test_T_CLI_87_slow_optional_tools_cannot_exhaust_version_gate(tmp_path, monkeypatch, cli_command, slow):
    from mdflow import exiftool

    assert exiftool.VERSION_TIMEOUT_S == 0.5
    if slow == 'late-kill-control':
        # Negative control: the check is not vacuous. Core handed a deadline 2 s later than requested
        # must be reported as killed late (and was still killed, not left to finish its 30 s sleep).
        delay = KILL_SLACK_S + 1.0
        records, _ = run_version_child(tmp_path, monkeypatch, cli_command, 'exiftool', delay_s=delay)
        problems = probe_problems(records, ['exiftool'], exiftool.VERSION_TIMEOUT_S)
        assert len(problems) == 1 and problems[0].startswith('exiftool: killed late'), problems
        stalled = next(r for r in records if r['tool'] == 'exiftool')
        assert 0.9 * (exiftool.VERSION_TIMEOUT_S + delay) <= stalled['elapsed'] < TOOL_SLEEP_S / 3, stalled
        assert stalled['outcome'] != 'ok', stalled
        return
    records, text = run_version_child(tmp_path, monkeypatch, cli_command, slow)
    expected = [name for name in ('exiftool', 'libreoffice') if slow in {name, 'both'}]
    assert probe_problems(records, expected, exiftool.VERSION_TIMEOUT_S) == [], records
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
