"""R28: class-specific Plan assertions replacing blanket schema credit."""
from copy import deepcopy
import json

import pytest


@pytest.mark.req('REQ-PLN-01', 'REQ-PLN-02', 'REQ-PLN-04')
@pytest.mark.cov('S8', 'FM0')
@pytest.mark.fx('FX-01', 'FX-03', 'FX-07', 'FX-11', 'FX-23', 'FX-24', 'FX-28', 'FX-30', 'FX-38', 'FX-42', 'FX-41')
@pytest.mark.parametrize('fx', ['FX-01', 'FX-03', 'FX-07', 'FX-11', 'FX-23', 'FX-24', 'FX-28', 'FX-30', 'FX-38', 'FX-42', 'FX-41'])
def test_T_PLN_55_r28_class_specific_plan_identity_counts_and_cache_status(core_api, core_data, core_fx, repo_root, fx):
    source = core_fx.path(fx)
    payload = source.read_bytes()
    folder = repo_root / 'engine/tests/golden' / fx
    reviewed = json.loads((folder / 'classification.review.json').read_text(encoding='utf-8'))
    classification = json.loads((folder / 'classification.json').read_text(encoding='utf-8'))
    assert {k: classification[k] for k in ('route', 'need', 'label', 'action')} == {
        k: reviewed['independent'][k] for k in ('route', 'need', 'label', 'action')}
    file = dict(path=source.name, bytes=len(payload), sha256=core_data.digest(payload), format=reviewed['sniff']['format'])
    options = core_data.options(file=file, classification=classification)
    selected = core_api.select.select(classification, options)
    # Render/Lookup are controlled inputs to this PURE stage. Each class uses
    # its actual candidate IDs; no common-schema marker supplies class credit.
    for u in selected['units']:
        if u['status'] == 'eligible':
            u.update(raster_sha256=core_data.digest(payload + u['source_id'].encode()), mime='image/png', bytes=100)
    frames = 3 if fx == 'FX-11' else None
    rendering = dict(frames_total=frames, uninspected_pages=classification.get('uninspected_pages', 0))
    before = deepcopy((selected, rendering, options))
    provider = core_data.provider()
    result = core_api.plan.plan(selected, rendering, {}, provider, options)
    approved, status = result['approved'], result['status']
    assert approved['file'] == file
    assert approved['classification'] == {k: classification[k] for k in approved['classification']}
    expected = len(selected['units'])
    eligible = sum(u['status'] == 'eligible' for u in selected['units'])
    assert approved['units_total'] == sum(status['units'].values()) == expected
    assert approved['keys_unique'] == status['requests_to_send'] == eligible
    assert approved['max_requests'] == eligible * (1 + provider['retries'])
    assert status['frames_total'] == frames
    if classification['action'] in {'report_only', 'convert_only'}:
        assert expected == eligible == 0
    if fx == 'FX-07':
        assert approved['oversize'] and status['units']['oversize'] == expected > options['max_units']
        assert status['uninspected_pages'] == 1
    hits = {u['source_id']: 'hit' for u in selected['units'] if u['status'] == 'eligible'}
    warm = core_api.plan.plan(selected, rendering, hits, provider, options)
    assert warm['approved'] == approved and warm['plan_hash'] == result['plan_hash']
    assert warm['status']['requests_to_send'] == 0 and warm['status']['units']['cached'] == eligible
    assert (selected, rendering, options) == before
