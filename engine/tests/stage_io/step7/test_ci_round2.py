"""Cross-platform regressions from real CI round two."""
import pytest


@pytest.mark.req('REQ-PLN-07', 'REQ-RPT-01', 'REQ-GEN-06')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-02')
@pytest.mark.parametrize('command', ['plan', 'run'])
def test_T_CLI_84_native_core_diagnostics_cannot_corrupt_protocol(tmp_path, gen, cli_probe, command):
    source = tmp_path / 'scan.pdf'
    source.write_bytes(gen.pdf_scan(1))
    # Inject fd-level output at the actual Core import boundary. Python stream
    # redirection alone does not catch this (the ONNX Runtime failure in CI).
    prelude = '''
import importlib.abc, os, sys
class NoisyCoreImport(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'markitdown':
            os.write(1, b'native stdout diagnostic\\n')
            os.write(2, b'native stderr diagnostic\\n')
        return None
sys.meta_path.insert(0, NoisyCoreImport())
'''
    args = [command, str(source)]
    if command == 'run':
        args += ['-o', str(tmp_path / 'out'), '--progress', 'jsonl']
    result = cli_probe.run(*args, prelude=prelude, expected=0)
    assert len(cli_probe.objects(result.stdout)) == 1
    if command == 'plan':
        assert result.stderr == ''
    else:
        assert cli_probe.events(result)
    assert 'native stdout diagnostic' not in result.stdout
    assert 'native stderr diagnostic' not in result.stderr


@pytest.mark.req('REQ-GEN-02')
@pytest.mark.cov('S0', 'FM12')
@pytest.mark.fx('FX-24', 'FX-27')
def test_T_GEN_57_hwp_fixture_payloads_are_codec_independent(step7_data, repo_root, monkeypatch):
    # No host compressor or Pillow encoder may participate in these fixtures.
    import zlib
    from PIL import Image
    def forbidden(*args, **kwargs):
        raise AssertionError('host codec invoked')
    monkeypatch.setattr(zlib, 'compressobj', forbidden)
    monkeypatch.setattr(Image.Image, 'save', forbidden)
    original = (repo_root / 'engine/tests/fixtures/FX-24.hwp').read_bytes()
    assert step7_data.hwp5_bytes() == original
    encrypted = step7_data.hwp5_bytes(encrypted=True)
    assert len(encrypted) == len(original)
    changes = [(a, b) for a, b in zip(original, encrypted) if a != b]
    assert changes == [(1, 3)], 'only the FileHeader encryption property changes'
