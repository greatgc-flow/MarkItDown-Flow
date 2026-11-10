"""Fable X-14: version diagnoses Core without invoking its startup gate."""
import json

import pytest


@pytest.mark.req('REQ-GEN-02', 'REQ-RPT-03')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('core', [None, '0.3.4', '0.4.0'])
def test_T_CLI_80_version_emits_complete_gate_fields_when_core_missing_or_incompatible(cli_probe, core):
    prelude = f'''
import importlib.metadata as metadata
_version = metadata.version
def installed_version(name):
    if name == 'markitdown-gc':
        value = {core!r}
        if value is None:
            raise metadata.PackageNotFoundError(name)
        return value
    return _version(name)
metadata.version = installed_version
from mdflow import core_guard
with core_guard.quiet_output():
    from markitdown import tools
tools.installation_conflict = lambda: None  # the faked metadata is missing/out of range, not a broken install

'''
    proc = cli_probe.run('version', prelude=prelude)
    assert proc.returncode == 0 and proc.stderr == '', (proc.stdout, proc.stderr)
    value = json.loads(proc.stdout)
    required = {'mdflow', 'markitdown-gc', 'pypdfium2', 'pillow', 'python', 'platform', 'protocol', 'triage_schema'}
    assert set(value) == required | {'exiftool', 'exiftool_status', 'exiftool_source',
                                    'libreoffice', 'libreoffice_status', 'libreoffice_source'}
    assert value['markitdown-gc'] == ('unavailable' if core is None else core)
    assert value['protocol'] == value['triage_schema'] == 1
    assert all(isinstance(value[k], str) and value[k] for k in required - {'protocol', 'triage_schema'})
    assert isinstance(value['exiftool'], str) and value['exiftool_status'] in {'ok', 'not_found', 'too_old', 'unusable'}
    assert not cli_probe.attempts.exists()
