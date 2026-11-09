"""Step 4: exact Markdown grammar, placement accounting and rendering safety."""
from copy import deepcopy
from hashlib import sha256
import json
import re

import pytest


BASE_KEYS = ["mdflow", "source", "sha256", "bytes", "format", "route", "need", "label",
             "triage_decision", "coverage_state", "units"]
TAIL_KEYS = ["tools", "generated", "content_sha256"]


def parse_output(text):
    """Strict independent parser for SPEC's restricted JSON-valued YAML subset."""
    assert text.startswith("---\n") and "\r" not in text
    header, body = text[4:].split("---\n", 1)
    values, order = {}, []
    for line in header.splitlines():
        name, sep, raw = line.partition(": ")
        assert sep and name not in values, "Malformed or duplicate frontmatter key"
        order.append(name)
        # SPEC permits inline maps with bare YAML keys; values remain JSON scalars.
        encoded = re.sub(r'([{,]\s*)([A-Za-z0-9_-]+)\s*:', r'\1"\2":', raw) if raw.startswith("{") else raw
        values[name] = json.loads(encoded)
        if isinstance(values[name], str):
            assert raw.startswith('"') and raw.endswith('"'), name
    return values, body, order


def pages(count, texts=None):
    texts = texts or {}
    return "\n\n".join(f"<!-- mdflow:page {n} -->\n{texts.get(n, '')}".rstrip() for n in range(1, count + 1))


def run(core_api, core_data, *, base=None, units=None, entries=None, **meta):
    return core_api.assemble.assemble(pages(4, {1: "Base first page", 3: "Base third page"}) if base is None else base,
        [core_data.unit()] if units is None else units, entries or {}, core_data.assembly_meta(**meta))


@pytest.mark.req("REQ-ASM-01")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-03")
def test_T_ASM_01_pure_and_input_immutable(core_api, core_data, monkeypatch):
    base, units, entries, meta = pages(4), [core_data.unit()], {}, core_data.assembly_meta()
    before = deepcopy((units, entries, meta))
    def forbidden(*args, **kwargs):
        raise AssertionError("Assemble accessed IO, clock or randomness")
    with monkeypatch.context() as patch:
        for name in ("builtins.open", "io.open", "os.urandom", "time.time", "time.monotonic"):
            patch.setattr(name, forbidden)
        first = core_api.assemble.assemble(base, units, entries, meta)
        second = core_api.assemble.assemble(base, units, entries, meta)
    assert first == second and isinstance(first[0], str)
    assert (units, entries, meta) == before


@pytest.mark.req("REQ-ASM-02")
@pytest.mark.cov("S11", "FM9")
@pytest.mark.fx("FX-02", "FX-49")
@pytest.mark.parametrize("logical,expected", [
    ("q3.pdf", "q3.pdf.md"), ("a.zip", "a.zip.md"),
    ("a.zip/CON.txt", "a.zip/_CON.txt.md"), ("aux", "_aux.md"),
    ("docs/COM1.md", "docs/_COM1.md.md"), ("NUL/a.txt", "_NUL/a.txt.md"),
    ("con.foo.bar", "_con.foo.bar.md"), ("LPT9", "_LPT9.md"),
    ("COM0.txt", "COM0.txt.md"), ("LPT10.txt", "LPT10.txt.md"),
    ("CONSOLE.txt", "CONSOLE.txt.md"), ("PRN.txt", "_PRN.txt.md")])
def test_T_ASM_02_extension_preserved_reserved_segments_every_os(core_api, logical, expected):
    assert core_api.assemble.output_path(logical) == expected


@pytest.mark.req("REQ-ASM-03")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-03")
def test_T_ASM_03_frontmatter_exact_order_types_and_string_quoting(core_api, core_data):
    output, _ = run(core_api, core_data, source='docs/a: b "한국어".pdf')
    header, _, order = parse_output(output)
    assert order == BASE_KEYS + ["provider", "model", "prompt_version", "dpi"] + TAIL_KEYS
    assert header["source"] == 'docs/a: b "한국어".pdf'
    assert header["mdflow"] == 2 and type(header["mdflow"]) is int
    assert header["bytes"] == 1024 and header["dpi"] == 200
    assert header["units"] == dict(total=1, done=0, pending=1, failed=0)
    assert header["generated"] == core_data.NOW
    no_units, _ = run(core_api, core_data, units=[], format="txt", dpi=0, pages_total=0, base="Own text")
    _, _, order = parse_output(no_units)
    assert order == BASE_KEYS + TAIL_KEYS


@pytest.mark.req("REQ-ASM-04")
@pytest.mark.cov("S11", "FM11")
@pytest.mark.fx("FX-07", "FX-11")
@pytest.mark.parametrize("fmt,count", (("pdf", 1001), ("tiff", 3)))
def test_T_ASM_04_anchor_for_every_actual_page_or_frame(core_api, core_data, fmt, count):
    u = core_data.unit("p1" if fmt == "pdf" else "f1", dpi=200 if fmt == "pdf" else 0)
    output, placements = run(core_api, core_data, base=pages(count), units=[u], format=fmt,
                              pages_total=count if fmt == "pdf" else None,
                              frames_total=count if fmt != "pdf" else None)
    assert re.findall(r"<!-- mdflow:page (\d+) -->", output) == [str(n) for n in range(1, count + 1)]
    assert placements == {u["source_id"]: 1}
    assert output.count("<!-- mdflow:pending ") == 1


@pytest.mark.req("REQ-ASM-05")
@pytest.mark.cov("S11", "FM11")
@pytest.mark.fx("FX-16", "FX-20")
def test_T_ASM_05_in_situ_and_unmapped_appendix(core_api, core_data):
    first = core_data.unit("word/media/image1.png", media=True)
    orphan = core_data.unit("word/media/orphan.png", media=True, media_file="media/aaaaaaaaaaaa.png")
    line = "![Own image](media/0123456789ab.png)"
    base = "Before\n" + line + "\nAfter"
    output, placements = run(core_api, core_data, base=base, units=[orphan, first], format="docx")
    _, body, _ = parse_output(output)
    assert line + '\n\n<!-- mdflow:pending unit="word/media/image1.png" reason="no_provider" -->' in body
    appendix = body.index("## OCR media (unmapped)")
    assert body.index("After") < appendix < body.index('unit="word/media/orphan.png"')
    assert placements == {first["source_id"]: 1, orphan["source_id"]: 1}


@pytest.mark.req("REQ-ASM-06")
@pytest.mark.cov("S11", "FM12")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_ASM_06_exact_blocks_markers_and_placement_total(core_api, core_data):
    good, pending = core_data.unit("p2"), core_data.unit("p4")
    e = core_data.entry(good, text="Own OCR text")
    output, placements = run(core_api, core_data, units=[good, pending], entries={"p2": e})
    _, body, _ = parse_output(output)
    expected = (f'<!-- mdflow:ocr unit="p2" key="{e["key_id"][:16]}" provider="openai-compatible" '
                f'model="fixture-model" prompt="p1" dpi="200" at="{e["created"]}" -->\n'
                '## OCR p2 (openai-compatible, fixture-model, 2026-11-09)\n'
                'Own OCR text\n<!-- /mdflow:ocr -->')
    assert expected in body
    assert '<!-- mdflow:pending unit="p4" reason="no_provider" -->' in body
    assert body.count("<!-- mdflow:ocr ") + body.count("<!-- mdflow:pending ") == sum(placements.values()) == 2
    assert placements == {"p2": 1, "p4": 1}
    # Exact equality on a committed, reviewed output oracle is independently gated.
    golden = core_data.ROOT / "engine/tests/golden/FX-03/output.md"
    inputs = golden.with_name("assembly-input.json")
    assert golden.is_file() and inputs.is_file(), "Reviewed assembly golden/input pair pending"
    arguments = json.loads(inputs.read_text(encoding="utf-8"))
    actual, _ = core_api.assemble.assemble(**arguments)
    assert actual.encode("utf-8") == golden.read_bytes()


@pytest.mark.req("REQ-ASM-07")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-01", "FX-02")
def test_T_ASM_07_empty_and_text_base_same_structure(core_api, core_data):
    results = [run(core_api, core_data, base=base)[0] for base in (pages(4), pages(4, {1: "Own base text"}))]
    parsed = [parse_output(text) for text in results]
    assert parsed[0][2] == parsed[1][2]
    assert re.findall(r"<!-- mdflow:page \d+ -->", parsed[0][1]) == re.findall(r"<!-- mdflow:page \d+ -->", parsed[1][1])
    assert parsed[0][1].count("<!-- mdflow:page ") == 4


@pytest.mark.req("REQ-ASM-08")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-03")
def test_T_ASM_08_content_hash_exact_body_utf8_bytes(core_api, core_data):
    output, _ = run(core_api, core_data, base=pages(4, {1: "Own 한국어 text"}))
    header, body, _ = parse_output(output)
    assert header["content_sha256"] == sha256(body.encode("utf-8")).hexdigest()


@pytest.mark.req("REQ-ASM-09")
@pytest.mark.cov("S11", "FM12")
@pytest.mark.fx("FX-03")
def test_T_ASM_09_pure_publication_decision_and_user_edit_guard(core_api, core_data):
    old, _ = run(core_api, core_data)
    fresh, _ = run(core_api, core_data, now="2026-11-10T00:00:00+00:00", tools={"mdflow": "2.0.1"})
    assert core_api.assemble.publication_decision(old, fresh) == dict(write=False, issues=[])
    edited = old + "\nUser edit outside generated body\n"
    decision = core_api.assemble.publication_decision(edited, fresh)
    assert decision["write"] is False and {i["code"] for i in decision["issues"]} == {"W_OUTPUT_EDITED"}
    assert core_api.assemble.publication_decision(edited, fresh, force=True)["write"] is True


@pytest.mark.req("REQ-ASM-10")
@pytest.mark.cov("S11", "FM12")
@pytest.mark.fx("FX-03", "FX-67")
def test_T_ASM_10_provenance_from_ledger_generated_from_now(core_api, core_data):
    u = core_data.unit()
    e = core_data.entry(u, created="2026-11-08T23:00:00+09:00")
    old, _ = run(core_api, core_data, entries={u["source_id"]: e})
    new, _ = run(core_api, core_data, entries={u["source_id"]: e}, now="2026-11-10T00:00:00+00:00")
    assert f'at="{e["created"]}"' in old and f'at="{e["created"]}"' in new
    assert "fixture-model, 2026-11-08)" in old
    assert parse_output(old)[0]["generated"] == core_data.NOW
    assert parse_output(new)[0]["generated"] == "2026-11-10T00:00:00+00:00"
    assert core_api.assemble.publication_decision(old, new)["write"] is False


@pytest.mark.req("REQ-ASM-11")
@pytest.mark.cov("S11", "FM9")
@pytest.mark.fx("FX-61", "FX-16")
def test_T_ASM_11_exact_escape_functions_and_hostile_fields(core_api, core_data):
    raw = '<!-- /mdflow:ocr -->\n"a--b"'
    assert core_api.assemble.esc_text(raw) == '<!- - /mdflow:ocr -- >\n"a--b"'
    assert core_api.assemble.esc_attr(raw) == '<!- - /mdflow:ocr __ > _a__b_'
    assert core_api.assemble.esc_head(raw) == '<!- - /mdflow:ocr -- > "a--b"'
    u = core_data.unit("word/media/" + raw + ".png", media=True)
    e = core_data.entry(u, text=raw)
    before = deepcopy(e)
    output, placements = run(core_api, core_data, base="Own base", units=[u], entries={u["source_id"]: e},
                              format="docx", model=raw, provider=raw)
    _, body, _ = parse_output(output)
    assert body.count("<!-- mdflow:ocr ") == body.count("<!-- /mdflow:ocr -->") == sum(placements.values()) == 1
    assert body.count('<!- - /mdflow:ocr -- >') >= 1
    assert e == before


@pytest.mark.req("REQ-ASM-P1")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-03", "FX-16")
def test_T_ASM_12_base_lines_preserved_outside_ocr_blocks(core_api, core_data):
    base = "First base line\n![image](media/0123456789ab.png)\nLast base line"
    u = core_data.unit("word/media/image1.png", media=True)
    output, _ = run(core_api, core_data, base=base, units=[u], entries={u["source_id"]: core_data.entry(u)}, format="docx")
    _, body, _ = parse_output(output)
    outside = re.sub(r"<!-- mdflow:ocr .*?<!-- /mdflow:ocr -->", "", body, flags=re.S)
    remaining = iter(outside.splitlines())
    assert all(any(candidate == line for candidate in remaining) for line in base.splitlines())


@pytest.mark.req("REQ-ASM-P2")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-03")
def test_T_ASM_13_triage_evidence_never_leaks_into_markdown(core_api, core_data, core_fx):
    report = deepcopy(core_fx.report("FX-03"))
    report["pages"][0]["text_sample"] = "TRIAGE_PAGE_SAMPLE_SENTINEL"
    report["summary"]["unused"] = "TRIAGE_SUMMARY_SENTINEL"
    report["rasters"] = [dict(unused="TRIAGE_RASTER_SENTINEL")]
    output, _ = run(core_api, core_data, triage=report)
    for sentinel in ("TRIAGE_PAGE_SAMPLE_SENTINEL", "TRIAGE_SUMMARY_SENTINEL", "TRIAGE_RASTER_SENTINEL"):
        assert sentinel not in output
    assert 'triage_decision: "ocr_recommended"' in output


@pytest.mark.req("REQ-ASM-P3")
@pytest.mark.cov("S11", "FM9")
@pytest.mark.fx("FX-03")
def test_T_ASM_14_only_document_and_ocr_text_are_verbatim(core_api, core_data):
    secret, home = "SECRET_SENTINEL_9d34", "C:/Users/SentinelUser"
    safe = core_api.redact.redact(f"failure {secret} {home}/private", {"MDFLOW_API_KEY": secret}, home)
    assert secret not in safe and home not in safe and "SentinelUser" not in safe
    u = core_data.unit()
    output, _ = run(core_api, core_data, base=pages(4, {1: secret}), entries={u["source_id"]: core_data.entry(u, text=secret)})
    header, body, _ = parse_output(output)
    assert secret not in json.dumps(header) and home not in output
    assert body.count(secret) == 2, "Document/OCR content is outside diagnostic redaction"


@pytest.mark.req("REQ-ASM-06")
@pytest.mark.cov("S11", "FM6")
@pytest.mark.fx("FX-03", "FX-61")
@pytest.mark.parametrize("status,reason", [
    ("eligible", "no_provider"), ("eligible", "approval_required"), ("eligible", "approval_denied"),
    ("skipped_low_priority", "low_priority"), ("oversize", "oversize"),
    ("render_failed", "render_failed"), ("unsupported_media_format", "unsupported_media_format"),
    ("eligible", "provider_failed:E_PROVIDER_HTTP"), ("eligible", "provider_failed:E_PROVIDER_TIMEOUT"),
    ("eligible", "provider_failed:E_PROVIDER_OUTPUT"), ("eligible", "provider_failed:E_PROVIDER_CONFIG")])
def test_T_ASM_15_exact_pending_marker_for_every_reason(core_api, core_data, status, reason):
    u = core_data.unit(status=status)
    entries = {}
    if reason.startswith("provider_failed:"):
        entries["p2"] = core_data.entry(u, status="failed", error=dict(code=reason.split(":", 1)[1], message="fixture", exit=None))
    output, placements = run(core_api, core_data, units=[u], entries=entries, pending_reason=reason)
    assert f'<!-- mdflow:pending unit="p2" reason="{reason}" -->' in output
    assert placements == {"p2": 1}


@pytest.mark.req("REQ-ASM-06", "REQ-MAP-03")
@pytest.mark.cov("S11", "FM12")
@pytest.mark.fx("FX-17")
def test_T_ASM_16_link_lines_count_once_per_distinct_unit(core_api, core_data):
    a = core_data.unit("word/media/a.png", media=True)
    b = core_data.unit("word/media/b.png", media=True, media_file="media/aaaaaaaaaaaa.png")
    body = ("![a](media/0123456789ab.png) ![a again](media/0123456789ab.PNG) ![b](media/aaaaaaaaaaaa.png)\n"
            "middle\n![a](media/0123456789ab.png)\nend")
    output, placements = run(core_api, core_data, base=body, units=[b, a], format="docx")
    assert placements == {a["source_id"]: 2, b["source_id"]: 1}
    assert output.count("<!-- mdflow:pending ") == 3
    _, assembled, _ = parse_output(output)
    assert assembled.index('unit="word/media/a.png"') < assembled.index('unit="word/media/b.png"')
    assert "## OCR media (unmapped)" not in assembled
    assert body.splitlines()[0] in assembled


@pytest.mark.req("REQ-MAP-01")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-03")
def test_T_MAP_01_pdf_units_follow_own_page_anchor(core_api, core_data):
    output, placements = run(core_api, core_data, units=[core_data.unit("p4"), core_data.unit("p2")])
    anchors = [output.index(f"<!-- mdflow:page {n} -->") for n in range(1, 5)]
    assert anchors[1] < output.index('unit="p2"') < anchors[2]
    assert anchors[3] < output.index('unit="p4"')
    assert placements == {"p2": 1, "p4": 1}


@pytest.mark.req("REQ-MAP-02")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-09", "FX-11")
@pytest.mark.parametrize("identity,frame,count", (("image", 1, 1), ("f2", 2, 3)))
def test_T_MAP_02_raster_units_map_to_frame_anchor(core_api, core_data, identity, frame, count):
    u = core_data.unit("p1", page=frame, dpi=0)
    u["source_id"] = identity
    output, placements = run(core_api, core_data, base=pages(count), units=[u], format="tiff" if count > 1 else "png", frames_total=count, pages_total=None)
    assert output.index(f"<!-- mdflow:page {frame} -->") < output.index(f'unit="{identity}"')
    if frame < count:
        assert output.index(f'unit="{identity}"') < output.index(f"<!-- mdflow:page {frame + 1} -->")
    assert placements == {identity: 1}


@pytest.mark.req("REQ-MAP-03")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-16", "FX-17", "FX-21", "FX-22", "FX-23")
def test_T_MAP_03_member_hash_and_extension_case_match(core_api, core_data, core_fx):
    import zipfile
    with zipfile.ZipFile(core_fx.path("FX-17", variant="b")) as archive:
        ids = sorted(n for n in archive.namelist() if n.startswith("word/media/"))
        hashes = {n: core_data.digest(archive.read(n)) for n in ids}
    assert len(ids) == 2 and len(set(hashes.values())) == 1
    c = core_data.Cases(".").classification()
    c["candidates_unique"] = [dict(id=n, kind="image", page=None, priority="normal", priority_core="high", refs=1) for n in ids]
    selected = core_api.select.select(c, core_data.options(media_hashes=hashes))
    assert len(selected["units"]) == 1 and selected["units"][0]["also"] == ids[1:]
    u = core_data.unit(ids[0], media=True, media_file="media/" + hashes[ids[0]][:12] + ".png", also=ids[1:])
    line = f'![image](media/{hashes[ids[0]][:12]}.PNG)'
    output, placements = run(core_api, core_data, base=line, units=[u], format="docx")
    assert placements == {ids[0]: 1} and "## OCR media (unmapped)" not in output


@pytest.mark.req("REQ-MAP-04")
@pytest.mark.cov("S11", "FM11")
@pytest.mark.fx("FX-20")
def test_T_MAP_04_zero_link_units_appendix_in_source_order(core_api, core_data):
    a, z = core_data.unit("word/media/a.png", media=True), core_data.unit("word/media/z.png", media=True)
    output, placements = run(core_api, core_data, base="Own body without links", units=[z, a], format="docx")
    assert output.count("## OCR media (unmapped)") == 1
    assert output.index('unit="word/media/a.png"') < output.index('unit="word/media/z.png"')
    assert placements == {a["source_id"]: 1, z["source_id"]: 1}
    issues = core_api.assemble.media_issues("Own body without links", [a, z])
    assert len(issues) == 2 and {i["code"] for i in issues} == {"W_MEDIA_UNMAPPED"}


@pytest.mark.req("REQ-MAP-05")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-24")
def test_T_MAP_05_hwp_payload_identity_and_stored_stream_pending(core_api, core_data, core_fx):
    report = core_fx.report("FX-24")
    assert report.get("media"), "HWP5 golden needs payload evidence"
    for media in report["media"]:
        assert core_api.select.media_identity(media["id"], "hwp", {}, report["media"]) == media["payload_sha256"][:12]
        supported = media["payload_kind"] == "parser_image_payload"
        u = core_data.unit(media["id"], media=True, status="eligible" if supported else "unsupported_media_format",
                           media_file=f'media/{media["payload_sha256"][:12]}.{media["ext"]}' if supported else None)
        base = f'![HWP image]({u["media_file"]})' if supported else "Own HWP base"
        output, placements = run(core_api, core_data, base=base, units=[u], format="hwp")
        assert placements == {media["id"]: 1}
        if supported:
            assert media["payload_sha256"][:12] in output
        else:
            assert 'reason="unsupported_media_format"' in output
