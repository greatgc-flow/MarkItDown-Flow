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


@pytest.mark.req('REQ-RPT-01', 'REQ-RPT-02', 'REQ-GEN-07')
@pytest.mark.cov('S13', 'FM0')
@pytest.mark.fx('FX-09')
def test_T_RPT_91_m4_plan_and_replay_progress_have_independent_literal_counts(flow, gen, mock_provider, capsys):
    flow.put('a.png', gen.png_noise(seed=91))
    provider = mock_provider(egress=True)
    plans = []
    first = flow.run(provider=provider, progress='jsonl', _plan_only=True, _on_plan=plans.append)
    first_lines = capsys.readouterr().err.splitlines()
    assert first['exit'] == 3 and provider.calls == [] and len(plans) == 1
    second = flow.run(provider=provider, progress='jsonl', yes_hashes=[plans[0]['plan_hash']])
    second_lines = capsys.readouterr().err.splitlines()
    assert second['exit'] == 0 and len(provider.calls) == 1
    # A literal per-invocation oracle, independent of the shell's summarizer.
    for lines, units, exit_code, calls in [
        (first_lines, dict(total=1, done=0, pending=1, failed=0), 3, 0),
        (second_lines, dict(total=1, done=1, pending=0, failed=0), 0, 1),
    ]:
        assert all(len(line.encode('utf-8')) < 65536 for line in lines)
        events = [json.loads(line) for line in lines]
        starts = [e for e in events if e['ev'] == 'run_start']
        ends = [e for e in events if e['ev'] == 'file_end']
        terminal = [e for e in events if e['ev'] == 'run_end']
        assert len(starts) == len(ends) == len(terminal) == 1
        assert starts[0]['files'] == 1 and ends[0]['units'] == units
        assert terminal[0]['exit'] == exit_code and terminal[0]['provider_calls'] == calls
