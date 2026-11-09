"""M4: invalid numeric identities fail locally; run progress stays invocation-scoped."""
from copy import deepcopy
import json

import pytest

from mdflow import classify, triage


@pytest.mark.req('REQ-CLS-06', 'REQ-GEN-07')
@pytest.mark.cov('S3', 'FM9')
@pytest.mark.fx('FX-02', 'FX-12', 'FX-28')
@pytest.mark.parametrize('kind,fx,prefix', [('pdf', 'FX-02', 'p'), ('gif', 'FX-12', 'f')])
@pytest.mark.parametrize('digits', [5000, 3])
def test_T_CLS_91_m4_numeric_candidate_id_refuses_without_losing_sibling(
        flow, gen, repo_root, monkeypatch, mock_provider, kind, fx, prefix, digits):
    raw = json.loads((repo_root / f'engine/tests/golden/{fx}/triage.json').read_text(encoding='utf-8'))
    reviewed = json.loads((repo_root / f'engine/tests/golden/{fx}/classification.review.json').read_text(encoding='utf-8'))
    assert classify.classify(reviewed['sniff'], raw)['action'] == 'convert_and_ocr'
    raw['candidates'][0]['id'] = prefix + '9' * digits
    before = deepcopy(raw)
    flow.put('a.' + kind, gen.pdf_scan() if kind == 'pdf' else gen.gif_anim())
    flow.put('b.txt', b'Independent sibling survives malformed candidate identity')
    flow.core.behavior = lambda spy, index, data, ext, extract_media, media_base_dir: (
        data.decode('utf-8') if ext == '.txt' else 'Retained source body')
    original = triage.run_triage
    monkeypatch.setattr(triage, 'run_triage', lambda path, sn: (
        dict(report=deepcopy(raw), issues=[]) if sn['format'] == kind else original(path, sn)))
    provider = mock_provider(egress=False)
    result = flow.run(provider=provider)
    first, sibling = result['files']
    assert result['exit'] == 0 and provider.calls == []
    assert (first['need'], first['action'], first['units']['total']) == ('UNKNOWN', 'convert_only', 0)
    assert {i['code'] for i in first['issues']} == {'W_TRIAGE_INCONSISTENT'}
    assert first['outputs'] == ['a.' + kind + '.md']
    assert sibling['outputs'] == ['b.txt.md']
    assert 'Independent sibling' in (flow.out / 'b.txt.md').read_text(encoding='utf-8')
    assert raw == before
