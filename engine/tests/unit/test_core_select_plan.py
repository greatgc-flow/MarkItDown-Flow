"""Step 3: selection, immutable approval identity, and budget equations."""
from copy import deepcopy
from hashlib import sha256

import pytest


@pytest.mark.req("REQ-SEL-01")
@pytest.mark.cov("S4", "FM11")
@pytest.mark.fx("FX-19")
def test_T_SEL_01_min_priority_marks_low_units(core_api, core_data):
    classification = core_data.Cases(".").classification(low=True)
    selected = core_api.select.select(classification, core_data.options(min_priority="normal"))
    assert not selected["oversize"]
    assert [u["status"] for u in selected["units"]] == ["skipped_low_priority"] * 2
    assert all(u["raster_sha256"] is None and u["mime"] is None and u["bytes"] is None for u in selected["units"])
    default = core_api.select.select(classification, core_data.options())
    assert [u["status"] for u in default["units"]] == ["eligible"] * 2


@pytest.mark.req("REQ-SEL-02")
@pytest.mark.cov("S4", "FM3")
@pytest.mark.fx("FX-02")
def test_T_SEL_02_oversize_all_or_none_with_strict_boundary(core_api, core_data):
    c = core_data.Cases(".").classification(ids=("p1", "p2", "p3", "p4", "p5"))
    for maximum, oversized in ((2, True), (5, False)):
        selected = core_api.select.select(c, core_data.options(max_units=maximum))
        assert selected["oversize"] is oversized
        assert len(selected["units"]) == 5
        assert all(u["status"] == ("oversize" if oversized else "eligible") for u in selected["units"])


@pytest.mark.req("REQ-SEL-01")
@pytest.mark.cov("S4", "FM0")
@pytest.mark.fx("FX-02")
def test_T_SEL_03_numeric_page_order_member_codepoint_order(core_api, core_data, core_fx):
    c = core_api.classify.classify(core_fx.sniff("FX-02", pages=12), core_fx.report("FX-02", suffix="-12p"))
    c["candidates_unique"].reverse()
    result = core_api.select.select(c, core_data.options())
    assert [u["source_id"] for u in result["units"]] == [f"p{n}" for n in range(1, 13)]
    assert [u["page"] for u in result["units"]] == list(range(1, 13))
    members = ("word/media/image2.png", "word/media/image10.png", "word/media/A.png")
    c["candidates_unique"] = [dict(id=n, kind="image", page=None, priority="normal", priority_core="high", refs=1) for n in members]
    hashes = {n: core_data.digest(n.encode()) for n in members}
    result = core_api.select.select(c, core_data.options(media_hashes=hashes))
    assert [u["source_id"] for u in result["units"]] == sorted(members)


@pytest.mark.req("REQ-SEL-01", "REQ-MAP-08")
@pytest.mark.cov("S4", "FM12")
@pytest.mark.fx("FX-17")
def test_T_SEL_04_refs_informational_and_equal_members_merge(core_api, core_fx, core_data):
    report = core_fx.report("FX-17")
    classification = core_api.classify.classify(core_fx.sniff("FX-17", format="docx"), report)
    identity = classification["candidates_unique"][0]["id"]
    result = core_api.select.select(classification, core_data.options(media_hashes={identity: "a" * 64}))
    assert len(result["units"]) == 1 and result["units"][0]["kind"] == "media"
    changed = deepcopy(classification)
    changed["candidates_unique"][0]["refs"] = 999
    assert core_api.select.select(changed, core_data.options(media_hashes={identity: "a" * 64})) == result
    other = "word/media/zz.png"
    changed["candidates_unique"].append(dict(changed["candidates_unique"][0], id=other))
    merged = core_api.select.select(changed, core_data.options(media_hashes={identity: "a" * 64, other: "a" * 64}))
    assert len(merged["units"]) == 1
    assert merged["units"][0]["source_id"] == min(identity, other)
    assert merged["units"][0]["also"] == [max(identity, other)]


@pytest.mark.req("REQ-PLN-01")
@pytest.mark.cov("S8", "FM0")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
@pytest.mark.parametrize("fmt,frames", (("pdf", None), ("png", 1), ("tiff", 3), ("docx", None)))
def test_T_PLN_01_exact_schema_and_all_equations(core_build_plan, core_data, fmt, frames):
    units = [core_data.unit("p2"), core_data.unit("p4"), core_data.unit("p5", status="render_failed")]
    opts = core_data.options()
    opts["file"]["format"] = fmt
    result = core_build_plan(units, hits=("p2",), opts=opts, frames_total=frames)
    assert set(result) == {"v", "approved", "status", "plan_hash"} and result["v"] == 1
    a, s = result["approved"], result["status"]
    assert set(a) == {"file", "classification", "provider", "provider_fingerprint", "prompt_version", "dpi", "units",
                      "units_total", "keys_unique", "max_requests", "est_max_cost", "cost_known", "approve_threshold",
                      "threshold_exceeded", "sensitive_hits", "oversize"}
    assert set(s) == {"units", "requests_to_send", "uninspected_pages", "frames_total"}
    assert set(a["file"]) == {"path", "sha256", "bytes", "format"}
    assert set(a["classification"]) == {"route", "need", "label", "action", "decision", "coverage_state"}
    assert set(a["provider"]) == {"name", "model", "egress", "cost_hint", "max_batch", "retries", "destination", "proxy", "command_env_names"}
    assert set(s["units"]) == {"eligible", "cached", "skipped_low_priority", "oversize", "render_failed", "unsupported_media_format"}
    assert a["units_total"] == len(a["units"]) == 3 == sum(s["units"].values())
    assert a["keys_unique"] == 2 and a["max_requests"] == a["keys_unique"] * (1 + a["provider"]["retries"])
    assert s["requests_to_send"] == 1 <= a["keys_unique"]
    assert s["units"]["cached"] == 1 and s["units"]["render_failed"] == 1
    assert a["units"][0]["status"] == "eligible"
    assert s["frames_total"] == frames
    assert result["plan_hash"] == sha256(core_data.canonical(a)).hexdigest()


@pytest.mark.req("REQ-PLN-02")
@pytest.mark.cov("S8", "FM12")
@pytest.mark.fx("FX-60")
@pytest.mark.scope("schema")
def test_T_PLN_02_approved_hash_and_cache_independence(core_api, core_data):
    options = core_data.options()
    options['file'].update(path='sample.docx', format='docx')
    units = [dict(core_data.unit('word/media/a.png', media=True), kind='media', page=None, also=[],
                  media_file='media/aaaaaaaaaaaa.png')]
    inputs = dict(selected=dict(units=units, oversize=False), rendered=dict(frames_total=None, uninspected_pages=0),
                  lookup={}, provider=core_data.provider(), options=options)
    def build(value):
        return core_api.plan.plan(value['selected'], value['rendered'], value['lookup'], value['provider'], value['options'])
    baseline = build(inputs)
    def field(value, path):
        for key in path: value = value[key]
        return value
    # Each row changes actual input, executes production Plan, and checks the
    # corresponding approved field plus an independent canonical digest.
    mutations = [
        (('options','file','path'), 'other.docx', ('file','path')),
        (('options','file','sha256'), 'b'*64, ('file','sha256')),
        (('options','file','bytes'), 777, ('file','bytes')),
        (('options','file','format'), 'hwpx', ('file','format')),
        (('options','dpi'), 300, ('dpi',)),
        (('options','proxy'), 'http://localhost:9000', ('provider','proxy')),
        (('options','prompt_version'), 'p2', ('prompt_version',)),
        (('options','approve_threshold'), 0, ('approve_threshold',)),
        (('options','sensitive'), ['*.docx'], ('sensitive_hits',)),
        (('provider','name'), 'command', ('provider','name')),
        (('provider','model'), 'other-model', ('provider','model')),
        (('provider','destination'), 'https://other.example/v1/chat/completions', ('provider','destination')),
        (('provider','egress'), False, ('provider','egress')),
        (('provider','cost_hint'), '0.10', ('provider','cost_hint')),
        (('provider','max_batch'), 2, ('provider','max_batch')),
        (('provider','retries'), 0, ('provider','retries')),
        (('provider','command_env_names'), ['PUBLIC_NAME'], ('provider','command_env_names')),
        (('selected','units',0,'source_id'), 'word/media/b.png', ('units',0,'source_id')),
        (('selected','units',0,'also'), ['word/media/c.png'], ('units',0,'also')),
        (('selected','units',0,'media_file'), 'media/bbbbbbbbbbbb.png', ('units',0,'media_file')),
        (('selected','units',0,'raster_sha256'), 'c'*64, ('units',0,'raster_sha256')),
        (('selected','units',0,'mime'), 'image/jpeg', ('units',0,'mime')),
        (('selected','units',0,'bytes'), 99, ('units',0,'bytes')),
    ]
    for path, replacement, expected_path in mutations:
        changed = deepcopy(inputs)
        field(changed, path[:-1])[path[-1]] = replacement
        result = build(changed)
        assert field(result['approved'], expected_path) == replacement, path
        assert result['approved'] != baseline['approved'] and result['plan_hash'] != baseline['plan_hash'], path
        assert result['plan_hash'] == core_data.digest(core_data.canonical(result['approved'])), path
    for signature in [
        ('PROTECTED','UNKNOWN','P','report_only','not_run','not_run'),
        ('UNSUPPORTED','UNKNOWN','X','report_only','not_run','not_run'),
        ('NATIVE','NONE','T','convert_only','no_candidates','complete'),
        ('NATIVE','UNKNOWN','U','convert_only','unknown','partial'),
        ('NATIVE','PARTIAL','M','convert_and_ocr','review','complete'),
    ]:
        changed = deepcopy(inputs)
        expected = dict(zip(('route','need','label','action','decision','coverage_state'), signature))
        changed['options']['classification'] = expected
        if expected['action'] != 'convert_and_ocr': changed['selected']['units'] = []
        else: changed['selected']['units'][0].update(priority='low', priority_core='low')
        result = build(changed)
        assert result['approved']['classification'] == expected
        assert result['plan_hash'] != baseline['plan_hash']
    page = deepcopy(inputs)
    page['options']['file'].update(path='sample.pdf', format='pdf')
    page['selected']['units'] = [core_data.unit('p1')]
    page_base = build(page)
    page['selected']['units'][0] = core_data.unit('p2', dpi=300)
    page_changed = build(page)
    assert page_changed['approved']['units'][0]['page'] == 2
    assert page_changed['approved']['units'][0]['dpi'] == 300
    assert page_changed['plan_hash'] != page_base['plan_hash']
    for status in ('render_failed','oversize','skipped_low_priority','unsupported_media_format'):
        changed = deepcopy(inputs)
        changed['selected']['units'][0]['status'] = status
        changed['selected']['oversize'] = status == 'oversize'
        result = build(changed)
        assert result['approved']['units'][0]['status'] == status
        assert result['plan_hash'] != baseline['plan_hash'] and result['approved']['keys_unique'] == 0
    more = deepcopy(inputs)
    more['selected']['units'].append(dict(units[0], source_id='word/media/b.png', raster_sha256='d'*64))
    doubled = build(more)
    assert doubled['approved']['units_total'] == doubled['approved']['keys_unique'] == 2
    assert doubled['plan_hash'] != baseline['plan_hash']
    for changed in (dict(deepcopy(inputs), lookup={'word/media/a.png':'hit'}),
                    dict(deepcopy(inputs), rendered=dict(frames_total=None, uninspected_pages=7))):
        result = build(changed)
        assert result['approved'] == baseline['approved'] and result['plan_hash'] == baseline['plan_hash']
        assert result['status'] != baseline['status']
    other_file = deepcopy(inputs)
    other_file['options']['other_files'] = [{'path':'unrelated.pdf','status':'failed'}]
    assert build(other_file) == baseline


@pytest.mark.req("REQ-PLN-03")
@pytest.mark.cov("S8", "FM11")
@pytest.mark.fx("FX-19")
def test_T_PLN_03_preserves_skipped_low_counts(core_build_plan, core_data):
    result = core_build_plan([core_data.unit(status="skipped_low_priority")])
    assert result["status"]["units"]["skipped_low_priority"] == 1
    assert result["approved"]["units"][0]["status"] == "skipped_low_priority"
    assert result["approved"]["keys_unique"] == result["status"]["requests_to_send"] == 0


@pytest.mark.req("REQ-PLN-04")
@pytest.mark.cov("S8", "FM3")
@pytest.mark.fx("FX-02")
def test_T_PLN_04_oversize_is_hashed_and_has_zero_work(core_build_plan, core_data):
    result = core_build_plan([core_data.unit(status="oversize")], oversize=True)
    assert result["approved"]["oversize"] is True
    assert result["approved"]["keys_unique"] == result["approved"]["max_requests"] == result["status"]["requests_to_send"] == 0
    assert result["status"]["units"]["oversize"] == 1


@pytest.mark.req("REQ-PLN-05")
@pytest.mark.cov("S8", "FM12")
@pytest.mark.fx("FX-17", "FX-61")
def test_T_PLN_05_unique_keys_budget_and_threshold_boundary(core_build_plan, core_data):
    units = [core_data.unit("p2", raster="a" * 64), core_data.unit("p4", raster="a" * 64)]
    for threshold, exceeded in ((0, True), (1, False)):
        a = core_build_plan(units, opts=core_data.options(approve_threshold=threshold))["approved"]
        assert a["units_total"] == 2 and a["keys_unique"] == 1
        assert a["max_requests"] == 3 and a["threshold_exceeded"] is exceeded


@pytest.mark.req("REQ-PLN-06")
@pytest.mark.cov("S8", "FM9")
@pytest.mark.fx("FX-51")
def test_T_PLN_06_sensitive_globs_are_casefolded_path_only(core_build_plan, core_data, monkeypatch):
    opts = core_data.options(sensitive=["*/HR/*", "*.PDF", "not-matched*"])
    opts["file"]["path"] = "docs/hr/x.pdf"
    def forbidden(*args, **kwargs):
        raise AssertionError("Plan must not read document content")
    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", forbidden)
        patch.setattr("io.open", forbidden)
        result = core_build_plan(opts=opts)
    assert result["approved"]["sensitive_hits"] == ["*/HR/*", "*.PDF"]


@pytest.mark.req("REQ-PLN-07")
@pytest.mark.cov("S8", "FM0")
@pytest.mark.fx("FX-02")
def test_T_PLN_07_none_provider_offline_plan(core_build_plan, core_data):
    p = core_data.provider(name="none", model="none", egress=False, destination=None, retries=0, cost_hint=None)
    result = core_build_plan(p=p)
    assert result["approved"]["provider"]["egress"] is False
    assert result["approved"]["provider"]["destination"] is None
    assert result["plan_hash"] == core_data.digest(core_data.canonical(result["approved"]))


@pytest.mark.req("REQ-PLN-08")
@pytest.mark.cov("S8", "FM0")
@pytest.mark.fx("FX-03")
def test_T_PLN_08_exact_decimal_cost_or_null(core_build_plan, core_data):
    a = core_build_plan()["approved"]
    assert a["est_max_cost"] == "0.024000" and a["cost_known"] is True
    a = core_build_plan(p=core_data.provider(cost_hint=None))["approved"]
    assert a["est_max_cost"] is None and a["cost_known"] is False
    a = core_build_plan(p=core_data.provider(cost_hint="0.000001"))["approved"]
    assert a["est_max_cost"] == "0.000006"


@pytest.mark.req("REQ-PLN-05")
@pytest.mark.cov("S8", "FM3")
@pytest.mark.fx("FX-02", "FX-61")
def test_T_PLN_09_requests_count_distinct_misses_only(core_build_plan, core_data):
    units = [core_data.unit("p1", raster="a" * 64), core_data.unit("p2", raster="a" * 64), core_data.unit("p3", raster="b" * 64)]
    result = core_build_plan(units, hits=("p1", "p2"))
    assert result["approved"]["keys_unique"] == 2
    assert result["status"]["requests_to_send"] == 1
    assert result["status"]["units"]["cached"] == 2


@pytest.mark.req("REQ-PLN-02")
@pytest.mark.cov("S8", "FM10")
@pytest.mark.fx("FX-63")
def test_T_PLN_10_command_fingerprint_binds_template_env_names_destination(core_build_plan, core_data):
    p = core_data.provider(name="command", destination='command:["python","ocr.py","{input}"]', command_env_names=["TOKEN_A"])
    baseline = core_build_plan(p=p)
    for changes in (dict(command_env_names=["TOKEN_B"]), dict(model="other-model"),
                    dict(destination='command:["python","other.py","{input}"]'), dict(egress=False)):
        changed = core_build_plan(p=dict(p, **changes))
        assert changed["plan_hash"] != baseline["plan_hash"]
        assert changed["approved"]["provider_fingerprint"] != baseline["approved"]["provider_fingerprint"]


@pytest.mark.req("REQ-MAP-07")
@pytest.mark.cov("S8", "FM12")
@pytest.mark.fx("FX-02")
def test_T_MAP_07_equal_keys_across_files_share_one_ledger(core_api, core_data, core_build_plan, tmp_path):
    u = core_data.unit(raster="a" * 64)
    key = core_api.ledger.make_key(u, core_data.provider(), "p1")
    store = core_api.ledger.Ledger(tmp_path)
    assert store.write(core_data.entry(u)) == []
    for logical in ("a.pdf", "b.pdf"):
        opts = core_data.options()
        opts["file"]["path"] = logical
        assert store.lookup(key)["hit"] is True
        assert core_build_plan([u], hits=(u["source_id"],), opts=opts)["status"]["requests_to_send"] == 0
    assert len(list((tmp_path / "units").rglob("*.json"))) == 1


@pytest.mark.req("REQ-MAP-08")
@pytest.mark.cov("S3", "FM12")
@pytest.mark.fx("FX-17")
def test_T_MAP_08_references_do_not_multiply_unit_but_links_do(core_api, core_fx, core_data):
    report = core_fx.report("FX-17")
    c = core_api.classify.classify(core_fx.sniff("FX-17", format="docx"), report)
    assert len(c["candidates_unique"]) == 1 and c["candidates_unique"][0]["refs"] == 2
    identity = c["candidates_unique"][0]["id"]
    units = core_api.select.select(c, core_data.options(media_hashes={identity: "0123456789ab" + "0" * 52}))["units"]
    assert len(units) == 1
    units[0].update(raster_sha256="a" * 64, mime="image/png", bytes=100, media_file="media/0123456789ab.png")
    body = "![one](media/0123456789ab.png)\ntext\n![two](media/0123456789ab.png)"
    output, placements = core_api.assemble.assemble(body, units, {}, core_data.assembly_meta(format="docx"))
    assert placements == {identity: 2}
    assert output.count("<!-- mdflow:pending ") == 2
