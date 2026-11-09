"""M3: adversarial schema/pixel boundaries and independent published-unit oracles."""
from collections import Counter
from copy import deepcopy
import io
import json
import re

import pytest

from mdflow import render, triage


@pytest.mark.req('REQ-CLS-01', 'REQ-GEN-07')
@pytest.mark.cov('S3', 'FM9')
@pytest.mark.fx('FX-24', 'FX-28', 'FX-60')
@pytest.mark.parametrize('bad', [[], {}, None, 7, 'future_payload'])
def test_T_CLS_90_m3_hwp_payload_kind_is_total_and_siblings_continue(
        flow, repo_root, mock_provider, monkeypatch, bad):
    source = flow.put('a.hwp', (repo_root / 'engine/tests/fixtures/FX-24.hwp').read_bytes())
    flow.put('b.txt', b'Independent sibling text')
    raw = json.loads((repo_root / 'engine/tests/golden/FX-24/triage.json').read_text(encoding='utf-8'))
    raw['media'][0]['payload_kind'] = bad
    before = deepcopy(raw)
    original = triage.run_triage

    def inspect(path, sniff):
        return dict(report=deepcopy(raw), issues=[]) if sniff['format'] == 'hwp' else original(path, sniff)

    monkeypatch.setattr(triage, 'run_triage', inspect)
    provider = mock_provider(egress=False)
    result = flow.run(provider=provider)
    first, sibling = result['files']
    assert result['exit'] == 0 and provider.calls == []
    assert (first['need'], first['action'], first['units']['total']) == ('UNKNOWN', 'convert_only', 0)
    assert {i['code'] for i in first['issues']} == {'W_TRIAGE_UNKNOWN_VALUE'}
    assert first['outputs'] == ['a.hwp.md'] and sibling['outputs'] == ['b.txt.md']
    assert (flow.out / sibling['outputs'][0]).is_file() and source.is_file()
    assert raw == before


@pytest.mark.req('REQ-RND-04')
@pytest.mark.cov('S6', 'FM3')
@pytest.mark.fx('FX-60')
@pytest.mark.parametrize('dpi', [200, 300])
@pytest.mark.parametrize('rotation', [0, 90])
def test_T_RND_90_m3_fractional_pdf_allocation_is_bounded_before_render(dpi, rotation, monkeypatch):
    import pypdfium2 as pdfium
    calls = []
    original = pdfium.PdfPage.render

    def tracked(page, *args, **kwargs):
        calls.append(page.get_size())
        return original(page, *args, **kwargs)

    monkeypatch.setattr(pdfium.PdfPage, 'render', tracked)
    with pdfium.PdfDocument.new() as document:
        for pixels in (72.1, 71.8):
            page = document.new_page(pixels * 72 / dpi, height=71.8 * 72 / dpi)
            page.set_rotation(rotation)
            page.close()
        with pytest.raises(render._Failure, match='pixel_bound'):
            render._render_pdf_page(document, {'page': 1}, dpi, 72 * 72)
        assert calls == [], 'the over-limit decoder must not be called'
        payload = render._render_pdf_page(document, {'page': 2}, dpi, 72 * 72)
        from PIL import Image
        with Image.open(io.BytesIO(payload)) as image:
            assert image.size == (72, 72)
        assert len(calls) == 1


def published_units(text):
    """Independent output grammar: IDs, pending reasons, and paired OCR delimiters."""
    done = Counter(re.findall(r'^<!-- mdflow:ocr unit="([^"]+)" key="[0-9a-f]{16}" ', text, re.M))
    pending = Counter(re.findall(r'^<!-- mdflow:pending unit="([^"]+)" reason="([^"]+)" -->$', text, re.M))
    assert sum(done.values()) == text.count('<!-- /mdflow:ocr -->')
    return done, pending


@pytest.mark.req('REQ-ASM-01', 'REQ-ASM-04', 'REQ-ASM-06', 'REQ-GEN-07')
@pytest.mark.cov('S11', 'FM0')
@pytest.mark.fx('FX-02', 'FX-03', 'FX-12', 'FX-16', 'FX-24')
@pytest.mark.parametrize('kind,expected_done,expected_pending', [
    ('scan', ['p1', 'p2', 'p3'], []),
    ('mixed', ['p2', 'p4'], []),
    ('gif', ['f1', 'f2'], []),
    ('docx', ['word/media/image1.png', 'word/media/image2.png'], []),
    ('hwp', ['BinData/BIN0001.png'], [('BinData/BIN0002.wmf', 'unsupported_media_format')]),
])
def test_T_ASM_90_m3_each_published_unit_and_pending_placement_is_independent(
        flow, gen, repo_root, step7_data, mock_provider, kind, expected_done, expected_pending):
    if kind in {'hwp', 'docx'}:
        import markitdown
        flow.core.behavior = lambda spy, index, data, ext, extract_media, media_base_dir: (
            markitdown.MarkItDown(enable_plugins=False).convert_stream(io.BytesIO(data),
                file_extension=ext, extract_media=extract_media, media_base_dir=media_base_dir).markdown)
    payload = {'scan': gen.pdf_scan, 'mixed': gen.pdf_mixed, 'gif': gen.gif_anim, 'docx': step7_data.docx_bytes}.get(kind)
    data = payload() if payload else (repo_root / 'engine/tests/fixtures/FX-24.hwp').read_bytes()
    ext = 'pdf' if kind in {'scan', 'mixed'} else kind
    flow.put('document.' + ext, data)
    provider = mock_provider(egress=False)
    first = flow.run(provider=provider)
    entry, = first['files']
    text = (flow.out / entry['outputs'][0]).read_text(encoding='utf-8')
    assert published_units(text) == (Counter(expected_done), Counter(expected_pending))
    assert entry['placements'] == len(expected_done) + len(expected_pending)
    assert entry['units']['transcribed'] == len(expected_done)
    before = flow.snapshot(flow.out)
    requests = len(provider.calls)
    second = flow.run(provider=provider)
    assert second['files'][0]['units']['cached'] == len(expected_done)
    assert len(provider.calls) == requests and flow.snapshot(flow.out) == before


@pytest.mark.req('REQ-ASM-04', 'REQ-CLS-06', 'REQ-RND-01')
@pytest.mark.cov('S11', 'FM11')
@pytest.mark.fx('FX-07')
def test_T_ASM_91_m3_capped_pdf_preserves_uninspected_anchor_without_inventing_a_unit(flow, gen, mock_provider):
    # Tiny actual pages keep all 1000 real renders inexpensive; Core's page cap is unchanged.
    flow.put('capped.pdf', gen.pdf_scan(1001, box=(8, 8)))
    provider = mock_provider(egress=False)
    result = flow.run(provider=provider, max_units=1000)
    entry, = result['files']
    text = (flow.out / entry['outputs'][0]).read_text(encoding='utf-8')
    assert result['exit'] == 0 and {i['code'] for i in entry['issues']} == {'W_TRIAGE_PARTIAL'}
    assert re.findall(r'^<!-- mdflow:page (\d+) -->$', text, re.M) == [str(n) for n in range(1, 1002)]
    assert published_units(text) == (Counter(f'p{n}' for n in range(1, 1001)), Counter())
    assert entry['placements'] == entry['units']['transcribed'] == 1000
    assert 'unit="p1001"' not in text


@pytest.mark.req('REQ-CTR-03', 'REQ-TRI-02', 'REQ-GEN-07')
@pytest.mark.cov('S2', 'FM1')
@pytest.mark.fx('FX-43', 'FX-60')
def test_T_TRI_90_m3_corrupt_inner_document_keeps_member_and_sibling_results(flow, gen, step7_data):
    # Valid Office ZIP with a truncated relationships part: Sniff admits it; real Core reports corruption.
    import zipfile
    package = step7_data.docx_bytes()
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    rel = 'word/_rels/document.xml.rels'
    members[rel] = members[rel][:len(members[rel]) // 2]
    broken = gen.make_zip(members)
    flow.put('bundle.zip', gen.make_zip({'a.docx': broken, 'b.txt': b'Valid sibling text'}))
    result = flow.run()
    files = {f['path']: f for f in result['files']}
    bad, sibling = files['bundle.zip/a.docx'], files['bundle.zip/b.txt']
    assert 'corrupt' in {i['code'] for i in bad['triage']['issues']}
    assert bad['triage']['decision'] == 'review', 'known candidate inventory survives the corrupt relationship part'
    assert bad['outputs'] == ['bundle.zip/a.docx.md'] and sibling['outputs'] == ['bundle.zip/b.txt.md']
    assert (flow.out / sibling['outputs'][0]).is_file()
    assert len(result['files']) == 3
