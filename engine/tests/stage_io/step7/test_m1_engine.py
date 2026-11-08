"""M1 regressions: observable stage boundaries, never a fabricated release pass."""

from copy import deepcopy
from datetime import datetime
import gc
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import time
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
import weakref
import zipfile

import pytest

from mdflow import assemble, classify, cli, convert, ledger, orchestrate, plan, providers
from mdflow import render, report, select, sniff_io, transcribe, write


def codes(value):
    return {i['code'] for f in value['files'] for i in f['issues']} | {
        i['code'] for i in value.get('issues', [])}


def golden(repo_root, fx='FX-03'):
    folder = repo_root / 'engine/tests/golden' / fx
    return (json.loads((folder / 'classification.review.json').read_text(encoding='utf-8'))['sniff'],
            json.loads((folder / 'triage.json').read_text(encoding='utf-8')))


@pytest.mark.req('REQ-SNF-01', 'REQ-SNF-01b', 'REQ-GEN-07')
@pytest.mark.cov('S0', 'FM5')
@pytest.mark.fx('FX-51', 'FX-53')
def test_T_SNF_50_m1_v06_discovery_failures_roots_and_exclusions(flow, gen, monkeypatch):
    source = flow.put('visible.txt', gen.txt_utf8())
    hidden = flow.put('.hidden.txt', b'hidden')
    excluded = flow.out
    excluded.mkdir()
    (excluded / 'old.txt').write_bytes(b'old')
    assert sniff_io.discover([hidden])['files'] == []
    assert sniff_io.discover([excluded], exclude=[excluded])['files'] == []
    link = flow.inputs / 'linked'
    gen.make_dir_link(link, excluded)
    assert sniff_io.discover([link])['files'] == []
    real_listdir, visited = os.listdir, []
    def listing(path):
        visited.append(os.path.realpath(path))
        return real_listdir(path)
    monkeypatch.setattr(os, 'listdir', listing)
    sniff_io.discover([flow.inputs, flow.inputs])
    assert visited.count(os.path.realpath(flow.inputs)) == 1
    def denied(path):
        if os.path.realpath(path) == os.path.realpath(flow.inputs):
            raise PermissionError('injected unreadable input directory')
        return real_listdir(path)
    monkeypatch.setattr(os, 'listdir', denied)
    result = flow.run([flow.inputs])
    assert result['exit'] == 2 and 'E_SNIFF_IO' in codes(result)
    assert len(result['files']) == 1 and result['files'][0]['outputs'] == []
    assert source.exists()


@pytest.mark.req('REQ-SNF-06', 'REQ-PLN-02', 'REQ-TRI-05')
@pytest.mark.cov('S1', 'FM12')
@pytest.mark.fx('FX-28')
def test_T_SNF_51_m1_v07_source_replacement_cannot_use_old_identity(flow, gen, monkeypatch):
    source = flow.put('note.txt', gen.txt_utf8())
    original = sniff_io.sniff
    def replaced(path, **kwargs):
        value = original(path, **kwargs)
        if Path(path) == source:
            source.write_bytes(b'different document after Sniff')
        return value
    monkeypatch.setattr(sniff_io, 'sniff', replaced)
    result = flow.run([source])
    assert result['exit'] == 2 and 'E_SNIFF_IO' in codes(result)
    assert flow.core.calls == [] and result['files'][0]['outputs'] == []
    assert not list(flow.cache.rglob('*.md'))


@pytest.mark.req('REQ-SNF-09', 'REQ-CNV-01')
@pytest.mark.cov('S5', 'FM3')
@pytest.mark.fx('FX-54', 'FX-16')
def test_T_CNV_50_m1_v08_member_overrun_stops_convert(flow, gen, step7_data, monkeypatch):
    source = flow.put('document.docx', step7_data.docx_bytes())
    def bomb(*args, **kwargs):
        raise sniff_io.ZipReadError('actual size exceeds declared size', code='E_ZIP_BOMB')
    monkeypatch.setattr(sniff_io, 'read_member_bytes', bomb)
    result = flow.run([source])
    assert result['exit'] == 2 and 'E_ZIP_BOMB' in codes(result)
    assert flow.core.calls == [] and result['files'][0]['outputs'] == []


@pytest.mark.req('REQ-SNF-09', 'REQ-RND-03')
@pytest.mark.cov('S6', 'FM3')
@pytest.mark.fx('FX-16')
def test_T_RND_50_m1_v08_configured_media_bound(gen, tmp_path):
    blob = gen.png_noise(100, 100)
    data = gen.docx_like({'large.png': blob})
    result = render.render_units(data, sniff=gen.fake_sniff('x.docx', data, fmt='docx'),
        units=[gen.media_unit('word/media/large.png')], run_temp=tmp_path,
        max_bytes=len(blob) - 1, total_remaining=len(blob) - 1)
    assert result['rasters'] == {}
    assert 'E_ZIP_BOMB' in {i['code'] for i in result['issues']}


@pytest.mark.req('REQ-CTR-02', 'REQ-GEN-07')
@pytest.mark.cov('S1', 'FM3')
@pytest.mark.fx('FX-50', 'FX-16')
def test_T_CTR_50_m1_v08_nested_office_budget_preserves_discovery(gen):
    office = gen.docx_like({'a.png': gen.png_noise(seed=88)})
    package = gen.make_zip({'first.txt': b'first', 'nested.docx': office}, method=0)
    cap = len(office) + 6
    result = sniff_io.expand_container(package, logical='a.zip', zip_total_bytes=cap)
    assert 'E_ZIP_TOTAL' in {i['code'] for i in result['issues']}
    assert {m['logical'] for m in result['members']} == {'a.zip/first.txt', 'a.zip/nested.docx'}


@pytest.mark.req('REQ-WRT-01', 'REQ-SEC-05')
@pytest.mark.cov('S12', 'FM9')
@pytest.mark.fx('FX-28', 'FX-51')
@pytest.mark.parametrize('edited', [False, True])
def test_T_WRT_50_m1_v09_skipped_writes_check_containment(flow, gen, monkeypatch, edited):
    source = flow.put('nested/note.txt', gen.txt_utf8())
    first = flow.run([flow.inputs])
    assert first['exit'] == 0
    output = flow.out / 'nested/note.txt.md'
    body = output.read_bytes() + (b'\nUser edit' if edited else b'')
    outside = flow.inputs.parent / 'outside'
    outside.mkdir()
    secret = outside / output.name
    secret.write_bytes(body)
    output.unlink()
    output.parent.rmdir()
    gen.make_dir_link(output.parent, outside)
    real_read, reads = Path.read_text, []
    def tracked(path, *args, **kwargs):
        if path == output:
            reads.append(path)
        return real_read(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', tracked)
    second = flow.run([flow.inputs])
    assert second['exit'] == 2 and 'E_OUTPUT_IO' in codes(second)
    assert reads == [] and secret.read_bytes() == body


def office_extract(spy, index, raw, ext, extract_media, media_base_dir):
    links = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in archive.namelist():
            if name.startswith('word/media/'):
                data = archive.read(name)
                import hashlib
                target = Path(extract_media) / (hashlib.sha256(data).hexdigest()[:12] + Path(name).suffix)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                links.append(f'![image](media/{target.name})')
    return '\n'.join(links)


@pytest.mark.req('REQ-CNV-03', 'REQ-GEN-05', 'REQ-GEN-06')
@pytest.mark.cov('S12', 'FM0')
@pytest.mark.fx('FX-16')
def test_T_WRT_51_m1_v10_restore_media_without_rewriting_markdown(flow, step7_data):
    source = flow.put('document.docx', step7_data.docx_bytes())
    flow.core.behavior = office_extract
    first = flow.run([source])
    assert first['exit'] == 0
    md = flow.out / 'document.docx.md'
    stamp = md.stat().st_mtime_ns
    picture = next((flow.out / 'media').iterdir())
    expected = picture.read_bytes()
    picture.unlink()
    second = flow.run([source])
    assert second['exit'] == 0 and picture.read_bytes() == expected
    assert md.stat().st_mtime_ns == stamp


@pytest.mark.req('REQ-LKP-04', 'REQ-ASM-10')
@pytest.mark.cov('S7', 'FM9')
@pytest.mark.fx('FX-66')
@pytest.mark.parametrize('created', [None, '', 'bad', '2026-11-09T00:00:00', 7])
def test_T_LKP_50_m1_v11_missing_or_invalid_provenance_is_cache_miss(flow, gen, mock_provider, created):
    source = flow.put('photo.png', gen.png_noise())
    first = flow.run([source], provider=mock_provider(egress=False))
    assert first['exit'] == 0
    record = next(flow.cache.glob('units/**/*.json'))
    entry = json.loads(record.read_text(encoding='utf-8'))
    if created is None:
        del entry['created']
    else:
        entry['created'] = created
    record.write_text(json.dumps(entry), encoding='utf-8')
    provider = mock_provider(egress=False)
    second = flow.run([source], provider=provider)
    assert second['exit'] == 0 and 'W_CACHE_CORRUPT' in codes(second)
    assert len(provider.calls) == 1 and second['files'][0]['units']['transcribed'] == 1


@pytest.mark.req('REQ-RPT-01', 'REQ-SEC-02')
@pytest.mark.cov('S13', 'FM3')
@pytest.mark.fx('FX-71')
def test_T_RPT_50_m1_v12_nested_progress_budget():
    event = dict(v=1, ev='file_end', ts='2026-11-09T00:00:00+00:00', file='가' * 14000,
                 outputs=['가' * 14000 + '.md'] * 3, units={'total': 0})
    original, sink = deepcopy(event), io.StringIO()
    report.emit_progress(event, sink)
    assert len(sink.getvalue().encode('utf-8')) <= 65536
    decoded = json.loads(sink.getvalue())
    assert decoded['ev'] == 'file_end' and decoded['units'] == {'total': 0}
    assert event == original


@pytest.mark.req('REQ-RPT-01', 'REQ-RPT-03', 'REQ-GEN-10')
@pytest.mark.cov('S13', 'FM5')
@pytest.mark.fx('FX-28', 'FX-65')
@pytest.mark.parametrize('empty', [False, True])
def test_T_RPT_51_m1_v13_report_copy_failure_terminal_agreement(tmp_path, gen, cli_probe, empty):
    root = tmp_path / 'input'
    root.mkdir()
    if not empty:
        (root / 'note.txt').write_bytes(gen.txt_utf8())
    target = tmp_path / 'report.json'
    prelude = f'''
from mdflow import write
from pathlib import Path
_real_write = write.atomic_write
def denied(path, *args, **kwargs):
    if Path(path) == Path({str(target)!r}):
        raise PermissionError('injected report copy failure')
    return _real_write(path, *args, **kwargs)
write.atomic_write = denied
'''
    proc = cli_probe.run('run', root, '-o', tmp_path / 'out', '--cache', tmp_path / 'cache',
                         '--report', target, '--progress', 'jsonl', prelude=prelude)
    value, = cli_probe.objects(proc.stdout)
    events = cli_probe.events(proc)
    assert proc.returncode == value['exit'] == events[-1]['exit'] == 2
    assert 'E_OUTPUT_IO' in codes(value)
    assert any(e.get('code') == 'E_OUTPUT_IO' for e in events)
    assert len([e for e in events if e['ev'] == 'run_end']) == 1


@pytest.mark.req('REQ-SEC-04', 'REQ-TRX-03')
@pytest.mark.cov('S10', 'FM3')
@pytest.mark.fx('FX-63')
def test_T_TRX_50_m1_v14_command_output_is_bounded_while_child_runs(tmp_path, gen):
    script = tmp_path / 'noisy.py'
    script.write_text("import os,sys,time\nwhile True:\n os.write(1,b'x'*65536)\n time.sleep(.002)\n", encoding='utf-8')
    provider = providers.build_provider('command', model='bounded', command=gen.command_template(script, '{input}'),
        command_egress=False, trust_command=True, env={'MDFLOW_TIMEOUT_S': '3'})
    unit = gen.page_unit('p1', gen.png_noise())
    started = time.monotonic()
    result = provider.transcribe(unit, gen.png_noise(), transcribe.load_prompt('p1'))
    assert result['error']['code'] == 'E_PROVIDER_OUTPUT'
    assert time.monotonic() - started < 2.5


@pytest.mark.req('REQ-GEN-09', 'REQ-TRX-03')
@pytest.mark.cov('S10', 'FM6')
@pytest.mark.fx('FX-62', 'FX-67')
def test_T_TRX_51_m1_v15_slow_drip_obeys_request_deadline(gen, monkeypatch):
    from mdflow.providers.openai_compat import OpenAICompatProvider
    clock = [0.0]
    class Drip:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, count):
            clock[0] += .4
            return b'x' if clock[0] < 3 else b''
        read1 = read
    provider = OpenAICompatProvider(api_key='dummy', base_url='https://example.invalid/v1', model='m', timeout_s=1)
    monkeypatch.setattr(provider._opener, 'open', lambda *args, **kwargs: Drip())
    monkeypatch.setattr(time, 'monotonic', lambda: clock[0])
    result = provider.transcribe(gen.page_unit('p1', b'png'), b'png', transcribe.load_prompt('p1'))
    assert result['error']['code'] == 'E_PROVIDER_TIMEOUT'
    assert clock[0] <= 1.5


@pytest.mark.req('REQ-RPT-03', 'REQ-PLN-08')
@pytest.mark.cov('S0', 'FM1')
@pytest.mark.fx('FX-28')
@pytest.mark.parametrize('extra', [['--prov', 'none'], ['--command', 'unused'], ['--command-env', 'NAME']])
def test_T_CLI_50_m1_v16_exact_flags_and_provider_scope(tmp_path, gen, cli_probe, extra):
    source = tmp_path / 'note.txt'
    source.write_bytes(gen.txt_utf8())
    proc = cli_probe.run('run', source, '-o', tmp_path / 'out', *extra)
    assert proc.returncode == 1 and 'E_USAGE' in proc.stderr and proc.stdout == ''
    assert not (tmp_path / 'out').exists()


@pytest.mark.req('REQ-PLN-08')
@pytest.mark.cov('S8', 'FM0')
@pytest.mark.fx('FX-09')
def test_T_PLN_50_m1_v16_none_cost_override_is_explicit():
    assert providers.build_provider('none', cost_hint='1.25').meta['cost_hint'] == '1.25'


@pytest.mark.req('REQ-TRX-03', 'REQ-GEN-10', 'REQ-SEC-02')
@pytest.mark.cov('S10', 'FM6')
@pytest.mark.fx('FX-61', 'FX-66')
def test_T_TRX_52_m1_v17_unknown_codes_and_redaction_before_storage(tmp_path, gen, mock_provider, monkeypatch):
    provider = mock_provider(egress=False)
    secret = 'redact-before-cap-secret'
    monkeypatch.setenv('M1_SECRET_TOKEN', secret)
    replies = iter([
        dict(status='failed', error={'code': 'E_INVENTED', 'message': 'bad code'}),
        dict(status='failed', error={'code': 'E_PROVIDER_HTTP', 'message': 'x' * 495 + secret}),
        dict(status='ok', text='sibling succeeds')])
    provider.transcribe = lambda *args: next(replies)
    jobs = [gen.make_job(tmp_path, f'p{n}', gen.png_noise(seed=n)) for n in (1, 2, 3)]
    published = []
    value = transcribe.run_transcribe(jobs, provider, prompt=transcribe.load_prompt('p1'), force=False,
        max_requests=3, consent=None, tools=gen.TOOLS, now=gen.NOW, publish=published.append,
        postprocess=assemble.postprocess_text)
    assert published[0]['error']['code'] == 'E_PROVIDER_OUTPUT'
    assert published[1]['error']['message'] == 'x' * 495 + '***'
    assert published[2]['text'] == 'sibling succeeds' and value['ok'] == 1


@pytest.mark.req('REQ-SEC-01', 'REQ-SEC-02')
@pytest.mark.cov('S0', 'FM9')
@pytest.mark.fx('FX-62')
def test_T_SEC_50_m1_v18_proxy_credentials_never_enter_plan():
    with pytest.raises(providers.ProviderConfigError) as error:
        providers.build_provider('openai-compatible', model='m',
            env={'MDFLOW_API_KEY': 'dummy', 'MDFLOW_PROXY': 'http://user:secret@localhost:9'})
    assert 'secret' not in str(error.value)


@pytest.mark.req('REQ-MAP-05', 'REQ-RND-03')
@pytest.mark.cov('S6', 'FM4')
@pytest.mark.fx('FX-24')
@pytest.mark.parametrize('stored', [True, False])
def test_T_RND_51_m1_v19_hwp_stored_or_missing_media_never_zip_opened(tmp_path, gen, monkeypatch, stored):
    media = tmp_path / 'media'
    media.mkdir()
    (media / '123456789abc.png').write_bytes(gen.png_noise())
    unit = gen.media_unit('BinData/BIN0001.png', media_file='media/123456789abc.png' if stored else None)
    unit['payload_kind'] = 'stored_ole_stream' if stored else 'parser_image_payload'
    def forbidden(*args, **kwargs):
        pytest.fail('HWP5 must never be ZIP-opened')
    monkeypatch.setattr(sniff_io, 'read_member_bytes', forbidden)
    value = render.render_units(gen.hwp5_min(), sniff=gen.fake_sniff('x.hwp', fmt='hwp'),
        units=[unit], run_temp=tmp_path)
    assert value['units'][0]['status'] == 'unsupported_media_format' and value['rasters'] == {}
    assert [i['code'] for i in value['issues']] == ['W_MEDIA_FORMAT']


@pytest.mark.req('REQ-MAP-03', 'REQ-SEL-01', 'REQ-GEN-07')
@pytest.mark.cov('S4', 'FM12')
@pytest.mark.fx('FX-17')
def test_T_SEL_50_m1_v20_full_digest_not_prefix_identity(repo_root):
    sn, raw = golden(repo_root, 'FX-17')
    c = classify.classify(sn, raw)
    first = c['candidates_unique'][0]
    c['candidates_unique'] = [dict(first, id='word/media/a.png'), dict(first, id='word/media/b.png')]
    hashes = {'word/media/a.png': 'a' * 12 + '0' * 52, 'word/media/b.png': 'a' * 12 + '1' * 52}
    value = select.select(c, {'file': {'format': 'docx'}, 'media_hashes': hashes})
    assert len(value['units']) == 2 and all(not u['also'] for u in value['units'])


@pytest.mark.req('REQ-SNF-04', 'REQ-SNF-05', 'REQ-SNF-07')
@pytest.mark.cov('S1', 'FM2')
@pytest.mark.fx('FX-01', 'FX-27')
def test_T_SNF_52_m1_v21_literal_encrypt_and_broken_hwp_header(tmp_path, gen, monkeypatch):
    source = tmp_path / 'literal.pdf'
    source.write_bytes(gen.make_pdf([{'text': 'Ordinary /Encrypt literal in a content stream'}]))
    sn = sniff_io.sniff(source, logical=source.name)
    assert sn['route'] == 'NATIVE' and 'pdf_encrypt_trailer' not in sn['reasons']
    hwp = tmp_path / 'broken.hwp'
    hwp.write_bytes(gen.hwp5_min())
    def broken(*args, **kwargs):
        raise sniff_io._CfbError('broken FileHeader stream')
    monkeypatch.setattr(sniff_io._Cfb, 'read_head', broken)
    result = sniff_io.sniff(hwp, logical=hwp.name)
    assert 'E_CORRUPT' in {i['code'] for i in result['issues']}


@pytest.mark.req('REQ-CLS-01', 'REQ-CLS-06')
@pytest.mark.cov('S3', 'FM9')
@pytest.mark.fx('FX-60', 'FX-24')
@pytest.mark.parametrize('field,value', [('media', 7), ('media', [None]), ('rasters', [None]), ('pages', [None])])
def test_T_CLS_50_m1_v22_nested_required_fields_fallback(repo_root, field, value):
    sn, raw = golden(repo_root, 'FX-24')
    raw[field] = value
    actual = classify.classify(sn, raw)
    assert (actual['need'], actual['action'], actual['candidates_unique']) == ('UNKNOWN', 'convert_only', [])
    assert 'W_TRIAGE_UNKNOWN_VALUE' in {i['code'] for i in actual['issues']}


@pytest.mark.req('REQ-CLS-01', 'REQ-CLS-06')
@pytest.mark.cov('S3', 'FM10')
@pytest.mark.fx('FX-30', 'FX-60')
def test_T_CLS_51_m1_v22_g2b_encrypted_follows_declared_row(repo_root):
    sn, raw = golden(repo_root, 'FX-30')
    raw['issues'].append({'code': 'encrypted', 'detail': 'known code outside G1'})
    actual = classify.classify(sn, raw)
    assert (actual['route'], actual['action']) == ('NATIVE', 'convert_only')


@pytest.mark.req('REQ-PLN-02', 'REQ-PLN-04')
@pytest.mark.cov('S8', 'FM10')
@pytest.mark.fx('FX-60')
def test_T_PLN_51_m1_v23_normative_snapshot_and_oversize_location(repo_root):
    spec = (repo_root / 'docs/renewal/10_SPEC.md').read_text(encoding='utf-8')
    rule = next(line for line in spec.splitlines() if line.startswith('- REQ-PLN-04 '))
    assert 'approved.oversize' in rule and 'status.oversize' not in rule
    assert 'prepared snapshot' in spec and 'DRAFT-3.3' in spec


@pytest.mark.req('REQ-APR-07', 'REQ-ASM-06')
@pytest.mark.cov('S10', 'FM8')
@pytest.mark.fx('FX-09', 'FX-65')
def test_T_TRX_53_m1_v24_changed_raster_denied_at_real_send_boundary(flow, gen, mock_provider, monkeypatch):
    source = flow.put('image.png', gen.png_noise())
    original = orchestrate._Pipeline.stage
    def tamper(pipeline, file, name, function, *args, **kwargs):
        if name == 'transcribe':
            jobs = args[0]
            Path(jobs[0]['raster_path']).write_bytes(b'replaced after approval')
        return original(pipeline, file, name, function, *args, **kwargs)
    monkeypatch.setattr(orchestrate._Pipeline, 'stage', tamper)
    provider = mock_provider(egress=False)
    value = flow.run([source], provider=provider)
    assert value['exit'] == 3 and provider.calls == []
    assert 'E_APPROVAL_DENIED' in codes(value) and not list(flow.cache.glob('units/**/*.json'))
    text = (flow.out / 'image.png.md').read_text(encoding='utf-8')
    assert 'reason="approval_denied"' in text


@pytest.mark.req('REQ-RND-05')
@pytest.mark.cov('S6', 'FM0')
@pytest.mark.fx('FX-02')
def test_T_RND_52_m1_v25_previous_raster_released_before_next_render(tmp_path, gen, monkeypatch):
    class Raster(bytearray): pass
    previous = []
    def raster(*args):
        gc.collect()
        assert not previous or previous[-1]() is None, 'previous raster still retained'
        value = Raster(b'pixels')
        previous.append(weakref.ref(value))
        return value
    monkeypatch.setattr(render, '_render_pdf_page', raster)
    data = gen.pdf_scan(3)
    result = render.render_units(data, sniff=gen.fake_sniff('x.pdf', data, fmt='pdf'),
        units=[gen.pre_render_unit(f'p{n}', n) for n in (1, 2, 3)], run_temp=tmp_path)
    assert all(u['status'] == 'eligible' for u in result['units'])
    assert len(result['rasters']) == 3 and all(ref() is None for ref in previous)


@pytest.mark.req('REQ-RND-06')
@pytest.mark.cov('S6', 'FM3')
@pytest.mark.fx('FX-08')
def test_T_RND_53_m1_v26_pixel_bound_precedes_expensive_decode(tmp_path, gen, monkeypatch):
    import pypdfium2
    from PIL import Image
    calls = []
    real_render = pypdfium2.PdfPage.render
    def decoded(self, *args, **kwargs):
        calls.append('pdf')
        return real_render(self, *args, **kwargs)
    monkeypatch.setattr(pypdfium2.PdfPage, 'render', decoded)
    data = gen.pdf_scan(1)
    bad = render.render_units(data, sniff=gen.fake_sniff('x.pdf', data, fmt='pdf'),
        units=[gen.pre_render_unit('p1', 1)], run_temp=tmp_path / 'bad', max_pixels=1)
    assert bad['units'][0]['status'] == 'render_failed' and calls == []
    good = render.render_units(data, sniff=gen.fake_sniff('x.pdf', data, fmt='pdf'),
        units=[gen.pre_render_unit('p1', 1)], run_temp=tmp_path / 'good')
    assert good['units'][0]['status'] == 'eligible' and calls == ['pdf']
    from PIL import ImageFile
    image_calls, real_load = [], ImageFile.ImageFile.load
    def loaded(image, *args, **kwargs):
        image_calls.append(image.size)
        return real_load(image, *args, **kwargs)
    monkeypatch.setattr(ImageFile.ImageFile, 'load', loaded)
    raster = gen.bmp_noise()
    refused = render.render_units(raster, sniff=gen.fake_sniff('x.bmp', raster, fmt='bmp'),
        units=[gen.pre_render_unit('image', 1, dpi=0)], run_temp=tmp_path / 'image-bad', max_pixels=1)
    assert refused['units'][0]['status'] == 'render_failed' and image_calls == []
    allowed = render.render_units(raster, sniff=gen.fake_sniff('x.bmp', raster, fmt='bmp'),
        units=[gen.pre_render_unit('image', 1, dpi=0)], run_temp=tmp_path / 'image-good')
    assert allowed['units'][0]['status'] == 'eligible' and image_calls


@pytest.mark.req('REQ-RND-03')
@pytest.mark.cov('S6', 'FM11')
@pytest.mark.fx('FX-11', 'FX-16')
def test_T_RND_54_m1_v27_animated_media_pixels_are_frame_zero(tmp_path, gen):
    from PIL import Image
    data = gen.gif_anim(2)
    archive = gen.docx_like({'anim.gif': data})
    value = render.render_units(archive, sniff=gen.fake_sniff('x.docx', archive, fmt='docx'),
        units=[gen.media_unit('word/media/anim.gif')], run_temp=tmp_path)
    actual = Image.open(value['rasters']['word/media/anim.gif']).convert('RGB').tobytes()
    with Image.open(io.BytesIO(data)) as image:
        frame0 = image.convert('RGB').tobytes()
        image.seek(1)
        frame1 = image.convert('RGB').tobytes()
    assert actual == frame0 and actual != frame1


@pytest.mark.req('REQ-SNF-01b', 'REQ-ASM-02')
@pytest.mark.cov('S12', 'FM12')
@pytest.mark.fx('FX-52')
def test_T_WRT_52_m1_v28_collision_is_propagated_through_pipeline(flow, gen):
    a = flow.put('one/same.txt', gen.txt_utf8())
    b = flow.put('two/same.txt', b'distinct second source')
    value = flow.run([a, b])
    assert value['exit'] == 2 and len(value['files']) == 2
    assert value['files'][1]['action'] == 'report_only'
    assert 'E_OUTPUT_COLLISION' in codes(value)
    assert len(flow.core.calls) == 1 and flow.core.calls[0]['data'] == a.read_bytes()
    assert len(list(flow.out.rglob('*.md'))) == 1


@pytest.mark.req('REQ-LKP-05')
@pytest.mark.cov('S7', 'FM5')
@pytest.mark.fx('FX-09', 'FX-65')
def test_T_LKP_51_m1_v29_cache_failure_keeps_output_and_sibling(flow, gen, mock_provider, monkeypatch):
    sources = [flow.put(f'{n}.png', gen.png_noise(seed=n)) for n in (1, 2)]
    original = os.replace
    def denied(src, dst, *args):
        if 'units' in Path(dst).parts:
            raise PermissionError('cache publication denied')
        return original(src, dst, *args)
    monkeypatch.setattr(os, 'replace', denied)
    provider = mock_provider(egress=False)
    value = flow.run(sources, provider=provider)
    assert value['exit'] == 2 and len(provider.calls) == 2
    for f in value['files']:
        assert any(i['code'] == 'E_CACHE_IO' for i in f['issues'])
        assert f['units']['transcribed'] == 1 and f['outputs']
        text = (flow.out / f['outputs'][0]).read_text(encoding='utf-8')
        assert 'text for image' in text and '<!-- /mdflow:ocr -->' in text


@pytest.mark.req('REQ-PLN-02')
@pytest.mark.cov('S8', 'FM12')
@pytest.mark.fx('FX-09')
def test_T_PLN_52_m1_v30_real_input_mutations_change_plan(flow, gen, mock_provider):
    source = flow.put('image.png', gen.png_noise())
    def get(**flags):
        results = []
        value = flow.run([source], provider=mock_provider(egress=False), _plan_only=True,
                         _on_plan=results.append, **flags)
        assert value['exit'] == (2 if flags.get('max_units') == 0 else 0)
        return results[0]
    baseline = get()
    for change in ({'dpi': 300}, {'approve_threshold': 0}, {'sensitive': ['*.png']}, {'prompt_version': 'p1', 'max_units': 0}):
        other = get(**change)
        assert other['approved'] != baseline['approved'] and other['plan_hash'] != baseline['plan_hash']
    assert get()['approved'] == baseline['approved']


@pytest.mark.req('REQ-CLS-01', 'REQ-CLS-05')
@pytest.mark.cov('S3', 'FM1')
@pytest.mark.fx('FX-60')
@pytest.mark.parametrize('mutation,expected', [('decision', 'W_TRIAGE_UNKNOWN_VALUE'),
    ('priority', 'W_TRIAGE_UNKNOWN_VALUE'), ('page', 'W_TRIAGE_INCONSISTENT')])
def test_T_CLS_52_m1_v33_mutations_have_exact_fallback(repo_root, mutation, expected):
    sn, raw = golden(repo_root)
    if mutation == 'decision': raw['decision'] = 'future'
    elif mutation == 'priority': raw['candidates'][0]['priority'] = 'medium'
    else: raw['candidates'][0]['page'] = 999
    value = classify.classify(sn, raw)
    assert tuple(value[k] for k in ('route', 'need', 'label', 'action')) == ('NATIVE', 'UNKNOWN', 'U', 'convert_only')
    assert value['candidates_unique'] == [] and {i['code'] for i in value['issues']} == {expected}


@pytest.mark.req('REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-60')
def test_T_META_50_m1_v01_applicable_nominal_and_report_cells_not_na(repo_root):
    matrix = tomllib.loads((repo_root / 'engine/tests/matrix.toml').read_text(encoding='utf-8'))
    na = {(s, f) for e in matrix['stage_fm'] for s in e['stages'] for f in e['fms']}
    required = {('S10', 'FM0'), ('S12', 'FM0'), ('S13', 'FM1'), ('S13', 'FM3'),
                ('S13', 'FM6'), ('S13', 'FM8'), ('S13', 'FM11'), ('S8', 'FM4')}
    assert not na & required


@pytest.mark.req('REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-60')
def test_T_META_51_m1_v04_common_schema_is_not_class_execution(trace_module):
    synthetic = {'markers': {'fx': [['all']], 'scope': [['schema']]}}
    assert trace_module.test_classes(synthetic, {}) == set()
    actual = {'markers': {'fx': [['FX-02']]}}
    assert trace_module.test_classes(actual, {'FX-02': {'K02'}}) == {'K02'}


@pytest.mark.req('REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-60')
def test_T_META_52_m1_v05_applicability_comments_describe_registration(repo_root):
    text = (repo_root / 'engine/tests/matrix.toml').read_text(encoding='utf-8').split('version =', 1)[0]
    assert 'still a stub' not in text and 'by a passing test' not in text
    assert 'registration' in text.lower()


@pytest.mark.req('REQ-GEN-03')
@pytest.mark.cov('S0', 'FM10')
@pytest.mark.fx('FX-60')
def test_T_GEN_50_m1_v31_runtime_support_evidence_is_not_source_lint(repo_root):
    spec = (repo_root / 'docs/renewal/10_SPEC.md').read_text(encoding='utf-8')
    assert 'Runtime support requires executed CI evidence' in spec
    assert 'source syntax checks alone do not establish runtime compatibility' in spec


@pytest.mark.req('REQ-PKG-02')
@pytest.mark.cov('S0', 'FM9')
@pytest.mark.fx('FX-72')
def test_T_GEN_51_m1_v32_hash_oracle_checks_dependency_closure(repo_root):
    text = (repo_root / 'engine/tests/packaging/test_pt_release.py').read_text(encoding='utf-8')
    assert 'def assert_full_lock_rejects_dependency_mutations(' in text
    assert 'assert_full_lock_rejects_dependency_mutations(release_bundle' in text


@pytest.mark.req('REQ-CNV-04', 'REQ-GEN-06')
@pytest.mark.cov('S5', 'FM12')
@pytest.mark.fx('FX-28')
def test_T_CNV_51_m1_v37_base_cache_reuse_is_intentional(flow, gen):
    source = flow.put('note.txt', gen.txt_utf8())
    first = flow.run([source])
    before = flow.snapshot(flow.cache), flow.snapshot(flow.out), len(flow.core.calls)
    second = flow.run([source])
    assert first['exit'] == second['exit'] == 0
    assert (flow.snapshot(flow.cache), flow.snapshot(flow.out), len(flow.core.calls)) == before


@pytest.mark.req('REQ-CLS-01', 'REQ-SEL-01', 'REQ-TRX-01')
@pytest.mark.cov('S4', 'FM2')
@pytest.mark.fx('FX-03', 'FX-60')
def test_T_CLS_53_m1_v38_core_encrypted_cannot_produce_executable_units(repo_root):
    sn, raw = golden(repo_root)
    raw['issues'].append({'code': 'encrypted', 'detail': 'found after Sniff'})
    actual = classify.classify(sn, raw)
    assert actual['route'] == 'PROTECTED' and actual['action'] == 'report_only'
    assert select.select(actual, {'file': {'format': 'pdf'}})['units'] == []


@pytest.mark.req('REQ-PLN-05', 'REQ-TRX-01')
@pytest.mark.cov('S10', 'FM12')
@pytest.mark.fx('FX-61')
def test_T_TRX_55_m1_v37_attempt_accounting_never_patches_provider_methods(gen):
    class Provider:
        meta = gen.ScriptedProvider().meta
        requests_sent = 0
        @property
        def _post_once(self):
            return self.send
        def send(self):
            self.requests_sent += 1
        def transcribe(self, *args):
            for _ in range(3): self._post_once()
            return dict(status='ok', text='three attempts', error=None, duration_ms=0)
    provider = Provider()
    measured = orchestrate._MeasuredProvider(provider)
    assert measured.transcribe({}, b'', None)['text'] == 'three attempts'
    assert measured.calls == provider.requests_sent == 3


@pytest.mark.req('REQ-CNV-01', 'REQ-WRT-02')
@pytest.mark.cov('S5', 'FM5')
@pytest.mark.fx('FX-16', 'FX-65')
def test_T_CNV_52_m1_v02_conversion_temp_io_error_is_per_source(flow, step7_data):
    source = flow.put('a.docx', step7_data.docx_bytes())
    sibling = flow.put('b.txt', b'Own sibling text')
    def convert_behavior(spy, index, data, ext, *args):
        if ext == '.docx': raise PermissionError('injected media temp failure')
        return 'Own sibling text'
    flow.core.behavior = convert_behavior
    value = flow.run([source, sibling])
    assert value['exit'] == 2 and 'E_CONVERT_FAIL' in codes(value)
    assert value['files'][0]['outputs'] and value['files'][1]['outputs'] == ['b.txt.md']
    assert 'Own sibling text' in (flow.out / 'b.txt.md').read_text(encoding='utf-8')


@pytest.mark.req('REQ-CNV-04', 'REQ-GEN-05', 'REQ-GEN-09')
@pytest.mark.cov('S5', 'FM7')
@pytest.mark.fx('FX-28', 'FX-65')
def test_T_CNV_53_m1_v02_interrupted_base_cache_retries_without_reading_temp(flow, gen, monkeypatch):
    source = flow.put('note.txt', gen.txt_utf8())
    original = os.replace
    def interrupted(src, dst):
        if 'base' in Path(dst).parts:
            raise gen.SimulatedCrash('interrupted base-cache publication')
        return original(src, dst)
    with monkeypatch.context() as patch:
        patch.setattr(os, 'replace', interrupted)
        with pytest.raises(gen.SimulatedCrash): flow.run([source])
    assert not list(flow.out.glob('*.md')) and not list(flow.cache.glob('base/*.md'))
    strays = list(flow.cache.rglob('*.tmp-*'))
    assert strays and len(flow.core.calls) == 1
    value = flow.run([source])
    assert value['exit'] == 0 and len(flow.core.calls) == 2
    assert (flow.out / 'note.txt.md').exists()


@pytest.mark.req('REQ-APR-07', 'REQ-TRX-03')
@pytest.mark.cov('S10', 'FM5')
@pytest.mark.fx('FX-63', 'FX-65')
def test_T_TRX_54_m1_v03_unreadable_raster_denied_and_sibling_continues(tmp_path, gen, mock_provider):
    first = gen.make_job(tmp_path, 'p1', gen.png_noise(seed=1))
    second = gen.make_job(tmp_path, 'p2', gen.png_noise(seed=2))
    Path(first['raster_path']).unlink()
    provider = mock_provider(egress=False)
    result = transcribe.run_transcribe([first, second], provider, prompt=transcribe.load_prompt('p1'),
        force=False, max_requests=2, consent=None, tools=gen.TOOLS, now=gen.NOW,
        publish=lambda value: None, postprocess=assemble.postprocess_text)
    assert result['denied'] == [first['key_id']] and result['ok'] == 1
    assert [call['unit']['source_id'] for call in provider.calls] == ['p2']


@pytest.mark.req('REQ-TRX-03')
@pytest.mark.cov('S10', 'FM4')
@pytest.mark.fx('FX-63')
def test_T_TRX_56_m1_v03_mime_refusal_before_provider(tmp_path, gen, mock_provider):
    provider = mock_provider(egress=False, accepts=['image/png'])
    job = gen.make_job(tmp_path, 'image', gen.jpeg_noise(), mime='image/jpeg')
    result = transcribe.run_transcribe([job], provider, prompt=transcribe.load_prompt('p1'), force=False,
        max_requests=1, consent=None, tools=gen.TOOLS, now=gen.NOW,
        publish=lambda value: None, postprocess=assemble.postprocess_text)
    assert provider.calls == [] and result['sent'] == 0 and result['failed'] == 1
    assert result['entries'][job['key_id']]['error']['code'] == 'E_PROVIDER_CONFIG'


@pytest.mark.req('REQ-TRX-01', 'REQ-TRX-02')
@pytest.mark.cov('S10', 'FM0')
@pytest.mark.fx('FX-09')
def test_T_TRX_57_m1_v01_nominal_result_is_durably_published(flow, gen, mock_provider):
    source = flow.put('photo.png', gen.png_noise())
    provider = mock_provider(egress=False)
    value = flow.run([source], provider=provider)
    assert value['exit'] == 0 and len(provider.calls) == 1
    record, = list(flow.cache.glob('units/**/*.json'))
    entry = json.loads(record.read_text(encoding='utf-8'))
    assert entry['status'] == 'ok' and entry['text'] == 'text for image' and entry['error'] is None
    assert entry['key_id'] == ledger.key_id(entry['key']) and entry['created'] == gen.NOW.isoformat(timespec='seconds')
    assert entry['text'] in (flow.out / 'photo.png.md').read_text(encoding='utf-8')


@pytest.mark.req('REQ-LKP-04', 'REQ-ASM-01', 'REQ-ASM-10')
@pytest.mark.cov('S11', 'FM1')
@pytest.mark.fx('FX-09', 'FX-66')
def test_T_ASM_50_m1_v03_invalid_cache_never_reaches_assembly(flow, gen, mock_provider, monkeypatch):
    source = flow.put('photo.png', gen.png_noise())
    assert flow.run([source], provider=mock_provider(egress=False))['exit'] == 0
    target, = list(flow.cache.glob('units/**/*.json'))
    entry = json.loads(target.read_text(encoding='utf-8'))
    del entry['created']
    target.write_text(json.dumps(entry), encoding='utf-8')
    original, observed = assemble.assemble, []
    def checked(body, units, entries, meta):
        for result in entries.values():
            assert datetime.fromisoformat(result['created']).tzinfo is not None
        observed.append(True)
        return original(body, units, entries, meta)
    monkeypatch.setattr(assemble, 'assemble', checked)
    value = flow.run([source], provider=mock_provider(egress=False))
    assert value['exit'] == 0 and observed == [True] and 'W_CACHE_CORRUPT' in codes(value)


@pytest.mark.req('REQ-PLN-01', 'REQ-APR-01')
@pytest.mark.cov('S8', 'FM4')
@pytest.mark.fx('FX-35', 'FX-39')
def test_T_PLN_53_m1_v01_report_only_sources_have_zero_work_plans(flow, gen):
    sources = [flow.put('legacy.doc', gen.cfb_legacy()), flow.put('unknown.blob', b'unknown bytes')]
    plans = []
    value = flow.run(sources, _plan_only=True, _on_plan=plans.append)
    assert value['exit'] == 2 and len(plans) == 2
    for p in plans:
        assert p['approved']['classification']['action'] == 'report_only'
        assert p['approved']['units'] == [] and p['approved']['keys_unique'] == p['status']['requests_to_send'] == 0
    assert flow.core.calls == [] and not flow.out.exists()


@pytest.mark.req('REQ-RPT-02', 'REQ-RPT-03')
@pytest.mark.cov('S13', 'FM1')
@pytest.mark.fx('FX-09', 'FX-61')
def test_T_RPT_52_m1_v01_internal_provider_failure_has_consistent_report(flow, gen, mock_provider):
    source = flow.put('photo.png', gen.png_noise())
    provider = mock_provider(egress=False)
    provider.script = [('raise', RuntimeError('internal provider failure'))]
    value = flow.run([source], provider=provider)
    f, = value['files']
    assert value['exit'] == 4 and codes(value) == {'E_PROVIDER_CONFIG'}
    assert f['units'] == dict(total=1, eligible=1, cached=0, transcribed=0, pending=0, failed=1)
    assert f['requests'] == dict(to_send=1, sent=1, ok=0, failed=1)


@pytest.mark.req('REQ-TRI-01', 'REQ-SEL-01', 'REQ-APR-01')
@pytest.mark.cov('S2', 'FM2')
@pytest.mark.fx('FX-09', 'FX-60')
def test_T_TRI_50_m1_v03_core_discovered_protection_has_no_work(flow, gen, mock_provider, monkeypatch):
    from mdflow import triage
    source = flow.put('image.png', gen.png_noise())
    original = triage.run_triage
    def encrypted(path, sn):
        outcome = original(path, sn)
        outcome['report']['issues'].append({'code': 'encrypted', 'detail': 'Core found protection'})
        return outcome
    monkeypatch.setattr(triage, 'run_triage', encrypted)
    def forbidden(*args, **kwargs): pytest.fail('report_only cannot render or look up a Key')
    monkeypatch.setattr(render, 'render_units', forbidden)
    monkeypatch.setattr(ledger.Ledger, 'lookup', forbidden)
    provider = mock_provider(egress=True)
    value = flow.run([source], provider=provider)
    f, = value['files']
    assert value['exit'] == 2 and f['route'] == 'PROTECTED' and f['action'] == 'report_only'
    assert f['units']['total'] == 0 and f['requests']['sent'] == 0 and f['outputs'] == []
    assert f['triage']['issues'][-1]['code'] == 'encrypted' and f['consent'] is None
    assert flow.core.calls == [] and provider.calls == []


@pytest.mark.req('REQ-PLN-01', 'REQ-APR-01')
@pytest.mark.cov('S8', 'FM2')
@pytest.mark.fx('FX-27')
def test_T_PLN_54_m1_v01_protected_source_metadata_plan_has_zero_work(flow, gen):
    source = flow.put('locked.hwp', gen.hwp5_min(encrypted=True))
    plans = []
    value = flow.run([source], _plan_only=True, _on_plan=plans.append)
    assert value['exit'] == 2 and len(plans) == 1
    p = plans[0]
    assert p['approved']['classification']['route'] == 'PROTECTED'
    assert p['approved']['units'] == [] and p['approved']['keys_unique'] == p['approved']['max_requests'] == 0
    assert p['status']['requests_to_send'] == 0 and not flow.out.exists()


@pytest.mark.req('REQ-SNF-01')
@pytest.mark.cov('S1', 'FM0')
@pytest.mark.fx('FX-51')
def test_T_SNF_53_m1_v06_dot_root_is_not_a_hidden_entry(flow, monkeypatch):
    flow.put('note.txt', b'Own source')
    monkeypatch.chdir(flow.inputs)
    result = sniff_io.discover([Path('.')])
    assert [f['logical'] for f in result['files']] == ['note.txt']
    assert result['skipped'] == []


@pytest.mark.req('REQ-SEL-01', 'REQ-CLS-06')
@pytest.mark.cov('S4', 'FM4')
@pytest.mark.fx('FX-30', 'FX-60')
def test_T_SEL_51_m1_v22_convert_only_does_not_schedule_ocr(repo_root):
    sn, raw = golden(repo_root, 'FX-30')
    raw['decision'] = 'unknown'
    raw['coverage']['state'] = 'none'
    raw['candidates'] = [dict(id='uninspected/media.png', kind='image', page=None,
                              priority='high', reasons=['embedded_image'])]
    c = classify.classify(sn, raw)
    assert c['action'] == 'convert_only' and c['candidates_unique'], 'real G2b decision row retains evidence'
    assert select.select(c, {'file': {'format': sn['format']}})['units'] == []


@pytest.mark.req('REQ-MAP-03', 'REQ-GEN-07')
@pytest.mark.cov('S5', 'FM12')
@pytest.mark.fx('FX-17')
def test_T_CNV_54_m1_v20_short_filename_collision_fails_before_conversion(flow, step7_data, mock_provider, monkeypatch):
    source = flow.put('document.docx', step7_data.docx_bytes())
    with zipfile.ZipFile(source) as archive:
        images = [archive.read(n) for n in archive.namelist() if n.startswith('word/media/')]
    assert len(images) == 2 and images[0] != images[1]
    original = orchestrate.sha256
    class Digest:
        def __init__(self, value): self.value = value
        def hexdigest(self): return self.value
    def forced(data):
        for index, payload in enumerate(images):
            if data == payload: return Digest('a' * 12 + str(index) * 52)
        return original(data)
    monkeypatch.setattr(orchestrate, 'sha256', forced)
    provider = mock_provider(egress=False)
    value = flow.run([source], provider=provider)
    assert value['exit'] == 2 and 'E_OUTPUT_COLLISION' in codes(value)
    assert flow.core.calls == [] and provider.calls == [] and value['files'][0]['outputs'] == []


@pytest.mark.req('REQ-GEN-07', 'REQ-WRT-02', 'REQ-RPT-03')
@pytest.mark.cov('S0', 'FM5')
@pytest.mark.fx('FX-51', 'FX-65')
def test_T_GEN_53_m1_v02_empty_run_temp_failure_is_not_success(flow, monkeypatch):
    def denied(*args, **kwargs): raise PermissionError('injected run temp failure')
    monkeypatch.setattr(orchestrate.tempfile, 'TemporaryDirectory', denied)
    value = flow.run()
    assert value['exit'] == 2 and value['files'] == []
    assert codes(value) == {'E_OUTPUT_IO'}


@pytest.mark.req('REQ-SNF-08', 'REQ-CTR-02')
@pytest.mark.cov('S1', 'FM3')
@pytest.mark.fx('FX-45', 'FX-46')
@pytest.mark.parametrize('case', ['zero_depth', 'nested_bomb'])
def test_T_CTR_51_m1_v08_root_and_nested_package_bounds(gen, case):
    data = gen.make_zip({'a.txt': b'a'}) if case == 'zero_depth' else gen.make_zip({'bomb.docx': gen.zip_bomb('c')})
    result = sniff_io.expand_container(data, logical='root.zip', zip_depth=0 if case == 'zero_depth' else 3)
    expected = 'E_ZIP_DEPTH' if case == 'zero_depth' else 'E_ZIP_BOMB'
    assert expected in {i['code'] for i in result['issues']}


@pytest.mark.req('REQ-SNF-06', 'REQ-CTR-03')
@pytest.mark.cov('S1', 'FM12')
@pytest.mark.fx('FX-43')
def test_T_SNF_54_m1_v07_container_replacement_cannot_change_inventory(flow, gen, monkeypatch):
    source = flow.put('bundle.zip', gen.make_zip({'old.txt': b'old'}))
    original = sniff_io.sniff
    def replaced(path, **kwargs):
        sn = original(path, **kwargs)
        if Path(path) == source:
            source.write_bytes(gen.make_zip({'new.txt': b'new'}))
        return sn
    monkeypatch.setattr(sniff_io, 'sniff', replaced)
    value = flow.run([source])
    assert value['exit'] == 2 and codes(value) == {'E_SNIFF_IO'}
    assert [f['path'] for f in value['files']] == ['bundle.zip']
    assert flow.core.calls == [] and value['files'][0]['outputs'] == []
