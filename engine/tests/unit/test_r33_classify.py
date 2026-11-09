"""Policy oracles derive from R33, never from production classification."""
import pytest


@pytest.mark.req('REQ-CLS-08')
@pytest.mark.cov('S3', 'FM0')
@pytest.mark.fx('FX-30', 'FX-31', 'FX-32', 'FX-33')
@pytest.mark.parametrize('fmt,warning', [(f, False) for f in ('csv', 'tsv', 'json')] +
    [(f, True) for f in ('md', 'markdown', 'html', 'htm', 'xml', 'epub')])
def test_T_CLS_93_r33_text_groups(core_api, core_fx, fmt, warning):
    sn = core_fx.sniff('FX-30', format=fmt)
    result = core_api.classify.classify(sn, core_fx.report('FX-30'))
    assert (result['route'], result['need'], result['label'], result['action']) == ('NATIVE', 'NONE', 'T', 'convert_only')
    assert [i['code'] for i in result['issues']] == (['W_MEDIA_NOT_INSPECTED'] if warning else [])
