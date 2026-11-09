"""M2 independent inventory, input-binding and source-equivalence oracles."""
from copy import deepcopy

import pytest


@pytest.mark.req('REQ-CLS-01')
@pytest.mark.cov('S3', 'FM9')
@pytest.mark.fx('FX-09', 'FX-24', 'FX-03', 'FX-60')
@pytest.mark.parametrize('fx,path,bad', [
    ('FX-09', ('rasters', 0, 'dpi_tag'), {}),
    ('FX-09', ('rasters', 0, 'dpi_tag'), 'bad'),
    ('FX-24', ('media', 0, 'where'), 'bad'),
    ('FX-24', ('media', 0, 'references'), [{'part': 7, 'id': []}]),
    ('FX-24', ('media', 0, 'stored_bytes'), 'bad'),
    ('FX-24', ('media', 0, 'stored_sha256'), 'not-a-digest'),
    ('FX-03', ('pages', 1, 'images', 0, 'dpi_xy'), 'bad'),
    ('FX-03', ('pages', 1, 'images', 0, 'bits'), False),
    ('FX-03', ('pages', 1, 'images', 0, 'filter'), [7]),
    ('FX-09', ('candidates', 0, 'decor'), 'bad'),
    ('FX-09', ('options', 'samples'), 1),
    ('FX-09', ('summary', 'candidates_high'), 'bad'),
    ('FX-09', ('summary', 'scope'), []),
    ('FX-09', ('coverage', 'reason'), 7),
])
def test_T_CLS_80_m2_v1_checks_all_promised_nested_types(core_api, core_fx, fx, path, bad):
    raw = core_fx.report(fx)
    fmt = 'hwp' if fx == 'FX-24' else 'png' if fx == 'FX-09' else 'pdf'
    sniff = core_fx.sniff(fx, format=fmt)
    target = raw
    for key in path[:-1]: target = target[key]
    target[path[-1]] = bad
    c = core_api.classify.classify(sniff, raw)
    assert tuple(c[k] for k in ('route', 'need', 'label', 'action')) == ('NATIVE', 'UNKNOWN', 'U', 'convert_only')
    assert c['candidates_unique'] == [] and {i['code'] for i in c['issues']} == {'W_TRIAGE_UNKNOWN_VALUE'}


@pytest.mark.req('REQ-SNF-03', 'REQ-GEN-04')
@pytest.mark.cov('S1', 'FM0')
@pytest.mark.fx('FX-60')
@pytest.mark.scope('schema')
def test_T_SNF_80_m2_io_uses_the_same_pure_format_decisions(core_api):
    from mdflow import sniff_io
    for ext in ('pdf', 'jpg', 'txt', 'docx', 'mp3', 'pages', ''):
        result = core_api.sniff_pure.detect_format(b'unrecognized', ext)
        assert (result['format'], result['route'], result['reasons']) == sniff_io._by_extension(ext)
    assert sniff_io._by_extension is core_api.sniff_pure.by_extension
    assert sniff_io._magic_format is core_api.sniff_pure.magic_format


@pytest.mark.req('REQ-PLN-02', 'REQ-PKG-10')
@pytest.mark.cov('S8', 'FM12')
@pytest.mark.fx('FX-60')
@pytest.mark.scope('schema')
def test_T_META_80_m2_v30_oracle_calls_plan_instead_of_hashing_detached_expected(repo_root):
    text = (repo_root / 'engine/tests/unit/test_core_select_plan.py').read_text(encoding='utf-8')
    body = text.split('def test_T_PLN_02_', 1)[1].split('@pytest.mark', 1)[0]
    assert 'mutated = deepcopy(baseline["approved"])' not in body
    assert 'changed["status"][field]' not in body


@pytest.mark.req('REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_81_m2_matrix_comments_match_r28_expansion(repo_root):
    text = (repo_root / 'engine/tests/matrix.toml').read_text(encoding='utf-8')
    header = text.split('version =', 1)[0]
    assert 'S0-S3/S13' in header and 'S8 T-PLN-01' not in header

