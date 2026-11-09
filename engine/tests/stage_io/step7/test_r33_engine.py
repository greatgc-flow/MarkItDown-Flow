"""R33 provenance, real/fake LibreOffice and distribution collision regressions."""
from hashlib import sha256
import builtins
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


def docx_bytes(folder, *, image=None):
    from docx import Document
    path = folder / 'seed.docx'
    doc = Document()
    doc.add_heading('R33 legacy document', level=1)
    doc.add_paragraph('Legacy conversion keeps this sentence.')
    if image:
        import io
        doc.add_picture(io.BytesIO(image))
    doc.save(path)
    return path.read_bytes()


def fake_soffice(folder, *, hang=False, broken=False, image=None):
    folder.mkdir()
    (folder / 'seed.docx').write_bytes(docx_bytes(folder, image=image))
    script = folder / 'fake.py'
    script.write_text('''import json, os, pathlib, subprocess, sys, time, urllib.parse
args = sys.argv[1:]
root = pathlib.Path(__file__).parent
if '--version' in args:
    print('LibreOffice 25.2.7.2 fake'); sys.exit(0)
(root / 'args.json').write_text(json.dumps(args))
profile = next(a.split('=', 1)[1] for a in args if a.startswith('-env:UserInstallation='))
profile = pathlib.Path(urllib.parse.unquote(urllib.parse.urlparse(profile).path).lstrip('/') if os.name == 'nt' else urllib.parse.unquote(urllib.parse.urlparse(profile).path))
(root / 'profile.xml').write_bytes((profile / 'user/registrymodifications.xcu').read_bytes())
(root / 'env.json').write_text(json.dumps(sorted(os.environ)))
if %r:
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
    (root / 'child.pid').write_text(str(child.pid))
    time.sleep(120)
out = pathlib.Path(args[args.index('--outdir')+1])
target = out / ('source.' + args[args.index('--convert-to')+1])
target.write_bytes(b'broken' if %r else (root / 'seed.docx').read_bytes())
''' % (hang, broken), encoding='utf-8')
    if os.name == 'nt':
        exe = folder / 'soffice.cmd'
        exe.write_text('@echo off\n"' + sys.executable + '" "' + str(script) + '" %*\n')
    else:
        exe = folder / 'soffice'
        exe.write_text('#!/bin/sh\nexec "' + sys.executable + '" "' + str(script) + '" "$@"\n')
        exe.chmod(0o755)
    return exe


@pytest.mark.req('REQ-CNV-07', 'REQ-GEN-02')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('state', ['missing', 'invalid_override', 'ok', 'malformed', 'timeout'])
def test_T_CLI_85_libreoffice_version_diagnostics(tmp_path, monkeypatch, capsys, state):
    from mdflow import cli, preconvert
    exe = fake_soffice(tmp_path / 'tool')
    monkeypatch.delenv('SOFFICE_PATH', raising=False)
    if state == 'missing':
        monkeypatch.setenv('PATH', str(tmp_path / 'empty'))
    elif state == 'invalid_override':
        monkeypatch.setenv('SOFFICE_PATH', str(tmp_path / 'absent'))
        monkeypatch.setenv('PATH', str(exe.parent))
    else:
        monkeypatch.setenv('SOFFICE_PATH', str(exe))
    if state in {'malformed', 'timeout'}:
        def probe(args, **kwargs):
            assert kwargs['timeout_s'] == 5
            if state == 'timeout':
                raise TimeoutError('injected deadline')
            return 'not a LibreOffice version'
        monkeypatch.setattr(preconvert, '_execute', probe)
    assert cli.main(['version']) == 0
    captured = capsys.readouterr()
    assert captured.err == ''
    value = json.loads(captured.out)
    assert value['libreoffice'] == ('25.2.7.2' if state == 'ok' else 'unavailable')
    assert value['libreoffice_status'] == ('ok' if state == 'ok' else 'not_found' if state == 'missing' else 'unusable')
    assert value['libreoffice_source'] == (None if state == 'missing' else 'SOFFICE_PATH')
    assert not (exe.parent / 'args.json').exists(), 'version must never convert a document'


@pytest.mark.req('REQ-CNV-07', 'REQ-ASM-03')
@pytest.mark.cov('S5', 'FM0')
@pytest.mark.fx('FX-36')
def test_T_CNV_91_fake_soffice_opt_in_provenance_cleanup(tmp_path, monkeypatch):
    from mdflow import cli, orchestrate, preconvert
    exe = fake_soffice(tmp_path / 'tool')
    monkeypatch.setenv('SOFFICE_PATH', str(exe))
    monkeypatch.setenv('MDFLOW_API_KEY', 'r33-private-value')
    source = tmp_path / 'original.rtf'
    source.write_bytes(b'{\\rtf1 legacy}')
    opts = dict(out=tmp_path / 'out', cache=tmp_path / 'cache')
    off = orchestrate.run([source], opts)
    assert off['exit'] == 2 and off['files'][0]['label'] == 'L'
    assert not (exe.parent / 'args.json').exists()
    result = orchestrate.run([source], dict(opts, preconvert_legacy=True))
    assert result['exit'] == 0
    entry = result['files'][0]
    assert (entry['path'], entry['format'], entry['sha256']) == ('original.rtf', 'rtf', sha256(source.read_bytes()).hexdigest())
    assert (entry['label'], entry['action']) == ('T', 'convert_only')
    warning = next(i for i in entry['issues'] if i['code'] == 'W_PRECONVERTED')
    assert (warning['tool'], warning['version']) == ('LibreOffice', '25.2.7.2')
    text = (opts['out'] / 'original.rtf.md').read_text(encoding='utf-8')
    assert 'Legacy conversion keeps this sentence.' in text
    assert 'fidelity: "DERIVED"' in text
    assert 'original_sha256: "' + entry['sha256'] + '"' in text
    assert 'derived_sha256: "' + sha256((exe.parent / 'seed.docx').read_bytes()).hexdigest() + '"' in text
    args = json.loads((exe.parent / 'args.json').read_text())
    assert '--headless' in args and '--norestore' in args
    assert 'MDFLOW_API_KEY' not in json.loads((exe.parent / 'env.json').read_text())
    profile_text = (exe.parent / 'profile.xml').read_text()
    assert 'DisableMacrosExecution' in profile_text and 'BlockUntrustedRefererLinks' in profile_text
    profile = next(a for a in args if a.startswith('-env:UserInstallation='))
    assert profile.startswith('-env:UserInstallation=file:')
    work = Path(args[args.index('--outdir') + 1]).parent
    assert not work.exists(), 'derived bytes/profile must be removed before later stages use the snapshot'
    assert cli._classification(source, preconvert_legacy=True)['classification']['label'] == 'T'
    assert cli._parser().parse_args(['plan', str(source), '--preconvert-legacy']).preconvert_legacy is True
    assert preconvert.TARGETS == {'doc': 'docx', 'ppt': 'pptx', 'rtf': 'docx', 'hwp': 'docx'}


@pytest.mark.req('REQ-CNV-07', 'REQ-PLN-01', 'REQ-APR-01', 'REQ-ASM-03')
@pytest.mark.cov('S10', 'FM0')
@pytest.mark.fx('FX-35', 'FX-36')
@pytest.mark.cells('K12:S4', 'K12:S6', 'K12:S7', 'K12:S9', 'K12:S11', 'K12:S12')
@pytest.mark.parametrize('fmt', ['doc', 'ppt', 'rtf', 'hwp'])
def test_T_CNV_94_enabled_legacy_media_reaches_stages(tmp_path, monkeypatch, gen, fmt, capsys):
    from mdflow import orchestrate, preconvert, sniff_io
    exe = fake_soffice(tmp_path / 'tool', image=gen.png_noise(200, 180))
    monkeypatch.setenv('SOFFICE_PATH', str(exe))
    source = tmp_path / ('legacy.' + fmt)
    source.write_bytes(b'HWP Document File V3.00' if fmt == 'hwp' else b'{\\rtf1 legacy}')
    if fmt in {'doc', 'ppt'}:
        # Actual CFB legacy fixtures are covered elsewhere; direct prepare below
        # verifies each declared filter against a controlled soffice process.
        source.write_bytes(gen.cfb_legacy(fmt))
    if fmt == 'ppt':
        # Supply a real PPTX as the fake tool's derived bytes for this filter.
        import io
        from pptx import Presentation
        from pptx.util import Inches
        deck = Presentation()
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.shapes.add_picture(io.BytesIO(gen.png_noise(200, 180)), Inches(1), Inches(1))
        deck.save(exe.parent / 'seed.docx')
    provider = gen.ScriptedProvider(egress=True)
    opts = dict(out=tmp_path / 'out', cache=tmp_path / 'cache', preconvert_legacy=True, progress='jsonl',
                _plan_only=True)
    plans = []
    opts['_on_plan'] = plans.append
    denied = orchestrate.run([source], opts, provider=provider)
    assert denied['exit'] == 3 and provider.calls == []
    approved = plans[0]['approved']
    assert approved['file']['sha256'] == sha256(source.read_bytes()).hexdigest()
    assert approved['preconversion']['fidelity'] == 'DERIVED'
    assert approved['preconversion']['derived_sha256'] == sha256((exe.parent / 'seed.docx').read_bytes()).hexdigest()
    result = orchestrate.run([source], dict(opts, _plan_only=False, yes_hashes=[plans[0]['plan_hash']]), provider=provider)
    entry = result['files'][0]
    assert result['exit'] == 0 and len(provider.calls) == 1
    assert entry['units']['transcribed'] == 1 and entry['placements'] == 1
    assert entry['requests']['sent'] == 1 and entry['outputs'] == [source.name + '.md']
    assert len(list((opts['cache'] / 'units').rglob('*.json'))) == 1
    warm = orchestrate.run([source], dict(opts, _plan_only=False), provider=provider)
    assert warm['exit'] == 0 and len(provider.calls) == 1
    assert warm['files'][0]['units']['cached'] == 1
    text = (opts['out'] / (source.name + '.md')).read_text(encoding='utf-8')
    assert 'text for ' in text and 'fidelity: "DERIVED"' in text
    assert list((opts['out'] / 'media').iterdir())
    events = [json.loads(line) for line in capsys.readouterr().err.splitlines()]
    assert {'select', 'convert', 'render', 'lookup', 'approve', 'transcribe', 'assemble', 'write'} <= {
        ev['stage'] for ev in events if ev['ev'] == 'stage'}


@pytest.mark.req('REQ-CNV-07', 'REQ-GEN-09')
@pytest.mark.cov('S5', 'FM7')
@pytest.mark.fx('FX-36')
@pytest.mark.parametrize('failure', ['missing', 'broken', 'timeout'])
def test_T_CNV_92_preconvert_failure_and_tree_cleanup(tmp_path, monkeypatch, failure):
    from mdflow import orchestrate
    exe = tmp_path / 'absent'
    if failure != 'missing':
        exe = fake_soffice(tmp_path / 'tool', hang=failure == 'timeout', broken=failure == 'broken')
    monkeypatch.setenv('SOFFICE_PATH', str(exe))
    source = tmp_path / 'legacy.rtf'
    source.write_bytes(b'{\\rtf1 legacy}')
    sibling = tmp_path / 'ok.txt'
    sibling.write_text('Surviving sibling.')
    result = orchestrate.run([source, sibling], dict(out=tmp_path / 'out', cache=tmp_path / 'cache',
        preconvert_legacy=True, preconvert_timeout_s=1))
    assert result['exit'] == 2
    assert 'E_PRECONVERT' in [i['code'] for i in result['files'][0]['issues']]
    assert result['files'][0]['outputs'] == [] and result['files'][1]['outputs'] == ['ok.txt.md']
    if failure != 'missing':
        args = json.loads((exe.parent / 'args.json').read_text())
        assert not Path(args[args.index('--outdir') + 1]).parent.exists()
    if failure == 'timeout':
        pid = int((exe.parent / 'child.pid').read_text())
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel.OpenProcess(0x1000, False, pid)
            if handle:
                code = ctypes.c_uint32()
                assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                kernel.CloseHandle(handle)
                assert code.value != 259, 'soffice descendant survived timeout'
            else:
                assert ctypes.get_last_error() == 87, 'process query failed for a reason other than absence'
        else:
            # A killed child can briefly remain a zombie until reaped by init.
            state = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
            assert not state or state.startswith('Z'), 'soffice descendant survived timeout'


def local_soffice():
    explicit = os.environ.get('SOFFICE_PATH')
    windows = Path('C:/Program Files/LibreOffice/program/soffice.com')
    return explicit or (str(windows) if windows.is_file() else shutil.which('soffice'))


@pytest.mark.integration
@pytest.mark.req('REQ-CNV-07', 'REQ-ASM-03')
@pytest.mark.cov('S5', 'FM0')
@pytest.mark.fx('FX-35', 'FX-36')
@pytest.mark.parametrize('extension', ['doc', 'rtf'])
def test_T_CNV_93_real_libreoffice_generated_legacy(tmp_path, monkeypatch, extension):
    from mdflow import orchestrate, preconvert, runtime_temp
    soffice = local_soffice()
    if not soffice:
        pytest.skip('LibreOffice soffice absent')
    monkeypatch.setenv('SOFFICE_PATH', soffice)
    docx_bytes(tmp_path)
    legacy = tmp_path / 'legacy'
    legacy.mkdir()
    with runtime_temp.run_directory() as generation:
        output = preconvert._execute([soffice, '-env:UserInstallation=' + (generation / 'profile').as_uri(),
            '--headless', '--convert-to', extension, '--outdir', str(legacy), str(tmp_path / 'seed.docx')],
            cwd=generation, timeout_s=60, output=generation / 'generation.log')
    path = legacy / ('seed.' + extension)
    assert path.is_file(), output
    result = orchestrate.run([path], dict(out=tmp_path / 'out', cache=tmp_path / 'cache', preconvert_legacy=True))
    assert result['exit'] == 0, result['files']
    text = (tmp_path / 'out' / (path.name + '.md')).read_text(encoding='utf-8')
    assert 'Legacy conversion keeps this sentence.' in text and 'fidelity: "DERIVED"' in text
    assert 'original_sha256: "' + sha256(path.read_bytes()).hexdigest() + '"' in text
    assert 'derived_sha256: "' in text


@pytest.mark.req('REQ-GEN-12')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.parametrize('entry', ['version', 'selftest', 'classify', 'plan', 'run', 'classification', 'orchestrate', 'core', 'convert', 'triage'])
def test_T_CLI_83_distribution_collision_before_any_core_import(tmp_path, monkeypatch, capsys, entry):
    from mdflow import cli, convert, orchestrate, sniff_io, triage
    source = tmp_path / 'source.txt'
    source.write_text('Hello collision.')
    sn = sniff_io.sniff(source, logical=source.name)
    if entry == 'convert':
        warmed = convert.convert_source(source.read_bytes(), sniff=sn, action='convert_only',
                                        run_temp=tmp_path, cache_dir=tmp_path / 'cache')
        assert warmed['body'] == 'Hello collision.' and not warmed['issues']
    dist = tmp_path / 'markitdown-99.0.dist-info'
    dist.mkdir()
    (dist / 'METADATA').write_text('Metadata-Version: 2.1\nName: markitdown\nVersion: 99.0\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    original_import = builtins.__import__
    imports = []
    def check(name, *args, **kwargs):
        if name == 'markitdown' or name.startswith('markitdown.'):
            imports.append(name)
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', check)
    if entry in {'version', 'selftest', 'classify', 'plan', 'run'}:
        args = [entry]
        if entry in {'classify', 'plan', 'run'}:
            args += [str(source)]
        if entry == 'run':
            args += ['-o', str(tmp_path / 'out')]
        assert cli.main(args) == 1
        assert json.loads(capsys.readouterr().err)['error']['code'] == 'E_CORE_CONFLICT'
    else:
        calls = {
            'classification': lambda: cli._classification(source),
            'orchestrate': lambda: orchestrate.run([source], dict(out=tmp_path / 'out')),
            'core': lambda: convert.core_convert(b'hello', '.txt'),
            'convert': lambda: convert.convert_source(source.read_bytes(), sniff=sn, action='convert_only',
                                                      run_temp=tmp_path, cache_dir=tmp_path / 'cache'),
            'triage': lambda: triage.run_triage(source, sn),
        }
        with pytest.raises(RuntimeError, match='E_CORE_CONFLICT'):
            calls[entry]()
    assert imports == []
