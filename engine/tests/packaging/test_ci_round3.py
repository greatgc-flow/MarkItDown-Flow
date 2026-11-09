"""Offline controls for the release-mode oracles that failed in CI round three."""
import json

import pytest

from _support import REPO, load_py


@pytest.mark.req('REQ-PKG-06')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-71')
@pytest.mark.parametrize('pillow', ('11.0.0', '12.3.0', '13.0.0'))
def test_T_GEN_58_version_mutations_reject_every_supported_pillow_endpoint(pillow):
    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'round3_release')
    recorder = load_py(REPO / 'tools/record_protocol.py', 'round3_recorder')
    parent = json.loads((REPO / 'shell/test/fixtures/fx71/version.json').read_text(encoding='utf-8'))
    parent['pillow'] = pillow
    assert release.gate(parent) == []
    for name in recorder.VERSION_VARIANTS:
        variant = json.loads(recorder.version_variant(name, json.dumps(parent).encode('utf-8')))
        assert bool(release.gate(variant)) == (name != 'unknown-optional-field'), name


@pytest.mark.req('REQ-PKG-05')
@pytest.mark.cov('S0', 'FM9')
def test_T_GEN_59_installer_scan_distinguishes_process_requests_from_display_text():
    release = load_py(REPO / 'engine/tests/packaging/test_pt_release.py', 'round3_release_scan')
    scan = release.installer_commands
    assert not scan((REPO / 'shell/src/process/setup.ts').read_text(encoding='utf-8'))
    assert not scan("const instructions = [`python -m pip install wheel`, `python -m venv env`];")
    assert not scan("{ command: 'python', args: ['-I', '--version'] }")
    for source in ("{ command: 'pip', args: ['install', 'wheel'] }",
                   "{ command: 'python', args: ['-m', 'pip', 'install', 'wheel'] }",
                   "{ command: 'python', args: ['-m', 'venv', 'env'] }",
                   "spawn('python', ['-m', 'pip', 'install', 'wheel'])",
                   "spawn('pip install wheel')"):
        assert scan(source), source
