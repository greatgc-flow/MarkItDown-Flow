"""M2 boundary regressions: real stage composition and owned resources."""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from mdflow import classify, convert, ledger, render, select, sniff_io, transcribe, write
from mdflow.providers.command import CommandProvider


@pytest.mark.req('REQ-GEN-09', 'REQ-SEC-04')
@pytest.mark.cov('S10', 'FM7')
@pytest.mark.fx('FX-63')
def test_T_TRX_80_m2_inherited_stdout_cannot_block_timeout_or_leave_reader(tmp_path):
    provider = CommandProvider(command='unused', egress=False, model='test', timeout_s=.15)
    code = "import subprocess,sys; subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(1.2)'])"
    start = time.monotonic()
    try:
        value = provider._capture([sys.executable, '-B', '-c', code], start)
        elapsed = time.monotonic() - start
        assert value['error']['code'] == 'E_PROVIDER_TIMEOUT'
        assert elapsed < .8, f'timeout cleanup blocked for {elapsed:.2f}s'
        assert not any(t.name == 'mdflow-command-output' for t in threading.enumerate())
    finally:
        # The trusted command's deliberately short-lived descendant owns no engine
        # scratch. Let it exit even if the deadline assertion fails.
        time.sleep(max(0, 1.4 - (time.monotonic() - start)))


@pytest.mark.req('REQ-RND-05', 'REQ-WRT-02')
@pytest.mark.cov('S6', 'FM5')
@pytest.mark.fx('FX-09', 'FX-65')
def test_T_RND_80_m2_render_setup_failure_is_per_unit_and_sibling_continues(flow, gen, monkeypatch):
    flow.put('a.png', gen.png_noise())
    flow.put('b.txt', b'Sibling remains available')
    original = Path.mkdir
    def denied(path, *args, **kwargs):
        if path.name == '1' and kwargs.get('exist_ok') is True:
            raise PermissionError('injected Render setup failure')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'mkdir', denied)
    value = flow.run()
    first, sibling = value['files']
    assert value['exit'] == 2
    assert {i['code'] for i in first['issues']} == {'E_RENDER_FAIL'}
    assert first['units']['pending'] == 1 and first['outputs'] == ['a.png.md']
    assert 'reason="render_failed"' in (flow.out / first['outputs'][0]).read_text(encoding='utf-8')
    assert sibling['outputs'] == ['b.txt.md']


@pytest.mark.req('REQ-MAP-05', 'REQ-RND-03', 'REQ-TRX-01', 'REQ-ASM-06')
@pytest.mark.cov('S6', 'FM4')
@pytest.mark.fx('FX-24')
@pytest.mark.parametrize('reverse', [False, True])
def test_T_RND_81_m2_hwp_equal_payloads_keep_stored_refusal_through_pipeline(flow, gen, repo_root, monkeypatch, mock_provider, reverse):
    from mdflow import triage
    source = flow.put('document.hwp', (repo_root / 'engine/tests/fixtures/FX-24.hwp').read_bytes())
    raw = json.loads((repo_root / 'engine/tests/golden/FX-24/triage.json').read_text(encoding='utf-8'))
    png = gen.png_noise()
    digest = gen.sha256(png)
    sample, candidate = raw['media'][0], raw['candidates'][0]
    raw['media'] = [dict(deepcopy(sample), id='BinData/B.png', payload_kind='parser_image_payload', payload_sha256=digest),
                    dict(deepcopy(sample), id='BinData/A.png', payload_kind='stored_ole_stream', payload_sha256=digest)]
    raw['candidates'] = [dict(deepcopy(candidate), id=m['id']) for m in raw['media']]
    if reverse:
        raw['media'].reverse()
        raw['candidates'].reverse()
    monkeypatch.setattr(triage, 'run_triage', lambda *a: dict(report=deepcopy(raw), issues=[]))
    def extracted(spy, index, data, ext, extract_media, media_base_dir):
        assert data == source.read_bytes() and ext == '.hwp'
        target = Path(extract_media) / (digest[:12] + '.png')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(png)
        # The stored stream has no supported extracted body link; its unit must
        # still receive one explicit unmapped pending placement.
        return f'![parser](media/{target.name})\nStored stream retained as evidence.'
    flow.core.behavior = extracted
    def no_zip(*a, **k): pytest.fail('HWP5 must not use ZIP fallback')
    monkeypatch.setattr(sniff_io, 'read_member_bytes', no_zip)
    plans = []
    provider = mock_provider(egress=False)
    value = flow.run(provider=provider, _on_plan=plans.append)
    f, = value['files']
    assert f['units'] == dict(total=2, eligible=1, cached=0, transcribed=1, pending=1, failed=0)
    assert len(provider.calls) == 1 and provider.calls[0]['unit']['source_id'] == 'BinData/B.png'
    assert provider.calls[0]['raster'] == png
    assert {i['code'] for i in f['issues']} >= {'W_MEDIA_FORMAT'}
    output = (flow.out / f['outputs'][0]).read_text(encoding='utf-8')
    assert 'unit="BinData/A.png" reason="unsupported_media_format"' in output
    assert 'unit="BinData/B.png" key=' in output
    assert f['placements'] == 2, 'one policy-specific placement per source occurrence'


@pytest.mark.req('REQ-MAP-05', 'REQ-CNV-03', 'REQ-RND-03')
@pytest.mark.cov('S6', 'FM0')
@pytest.mark.fx('FX-24')
def test_T_RND_82_m2_real_hwp_extraction_renders_parser_payload_only(flow, repo_root, mock_provider, monkeypatch):
    import markitdown
    source = flow.put('actual.hwp', (repo_root / 'engine/tests/fixtures/FX-24.hwp').read_bytes())
    def real_core(spy, index, data, ext, extract_media, media_base_dir):
        return markitdown.MarkItDown(enable_plugins=False).convert_stream(io.BytesIO(data),
            file_extension=ext, extract_media=extract_media, media_base_dir=media_base_dir).markdown
    flow.core.behavior = real_core
    monkeypatch.setattr(sniff_io, 'read_member_bytes', lambda *a, **k: pytest.fail('HWP ZIP fallback'))
    provider = mock_provider(egress=False)
    value = flow.run([source], provider=provider)
    f, = value['files']
    assert f['units'] == dict(total=2, eligible=1, cached=0, transcribed=1, pending=1, failed=0)
    assert len(provider.calls) == 1 and provider.calls[0]['unit']['source_id'] == 'BinData/BIN0001.png'
    assert provider.calls[0]['raster'].startswith(b'\x89PNG')
    text = (flow.out / f['outputs'][0]).read_text(encoding='utf-8')
    assert 'unit="BinData/BIN0002.wmf" reason="unsupported_media_format"' in text
    assert f['placements'] == 2


@pytest.mark.req('REQ-CLS-05', 'REQ-RND-03', 'REQ-ASM-06')
@pytest.mark.cov('S6', 'FM4')
@pytest.mark.fx('FX-23', 'FX-60')
def test_T_RND_83_m2_core_unsupported_media_cannot_become_eligible_by_decodable_bytes(flow, gen, mock_provider):
    import zipfile
    png = gen.png_noise(200, 200)
    source = flow.put('wrapped.hwpx', gen.hwpx_like({'image.wmz': png}))
    def extract(spy, index, data, ext, extract_media, media_base_dir):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            name = next(n for n in archive.namelist() if n.endswith('.wmz'))
            payload = archive.read(name)
        target = Path(extract_media) / (gen.sha256(payload)[:12] + '.wmz')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return f'![wrapped](media/{target.name})'
    flow.core.behavior = extract
    provider = mock_provider(egress=False)
    result = flow.run([source], provider=provider)
    f, = result['files']
    assert 'unsupported_media' in {i['code'] for i in f['triage']['issues']}
    assert provider.calls == [] and f['requests']['sent'] == 0
    assert f['units']['pending'] == 1 and f['placements'] == 1
    assert 'W_MEDIA_FORMAT' in {i['code'] for i in f['issues']}
    assert 'reason="unsupported_media_format"' in (flow.out / f['outputs'][0]).read_text(encoding='utf-8')


@pytest.mark.req('REQ-LKP-03', 'REQ-GEN-05')
@pytest.mark.cov('S7', 'FM12')
@pytest.mark.fx('FX-09')
def test_T_LKP_80_m2_ledger_reuses_atomic_writer_and_hash_identity(tmp_path, gen, monkeypatch):
    from mdflow import hashing
    job = gen.make_job(tmp_path, 'image', gen.png_noise())
    entry = dict(v=1, key=job['key'], key_id=job['key_id'], status='ok', text='result', error=None,
                 created=gen.NOW.isoformat(timespec='seconds'))
    calls = []
    original = write.atomic_write
    def tracked(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(write, 'atomic_write', tracked)
    assert ledger.Ledger(tmp_path / 'cache').write(entry) == []
    assert len(calls) == 1 and calls[0][1]['dir_mode'] == 0o700
    assert ledger.key_id is hashing.key_id


@pytest.mark.req('REQ-CNV-03', 'REQ-RPT-03')
@pytest.mark.cov('S5', 'FM4')
@pytest.mark.fx('FX-11', 'FX-12')
@pytest.mark.parametrize('fmt', ['gif', 'tiff'])
def test_T_CNV_80_m2_real_core_unsupported_raster_has_clean_empty_base(gen, tmp_path, fmt):
    data = gen.gif_anim() if fmt == 'gif' else gen.tiff_frames()
    result = convert.convert_source(data, sniff=gen.fake_sniff('frames.' + fmt, data, fmt=fmt),
        action='convert_and_ocr', run_temp=tmp_path)
    assert result == dict(body='', pages=None, media={}, issues=[])
