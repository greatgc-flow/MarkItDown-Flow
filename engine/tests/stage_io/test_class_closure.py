"""M1-H class x stage closure (MECE round 1, horizontal): dedicated tests for the cells that were declared
N/A by delegation (S5:K01 K02 K04 K05 K06 K11 K18, S4:K03 K04, S6:K03, S10:K02) and for the WEAK high-risk
cells (S10:K03 K07, S12:K07 K14, S8:K14 K15 K16, S11:K15 K16).

Each test names a fixture of the class it closes in ``fx`` so the generated class x stage matrix credits the
cell from a marker, not from a blanket ``fx("all")``. Engine bugs found here stay as ``xfail(strict=True,
reason="M1-H: ...")`` rather than being fixed (engine/src belongs to another worktree).
"""

import io
import json
import re
import types
from pathlib import Path

import pytest

from mdflow import assemble, convert, render, sniff_io, transcribe, write
from mdflow import select as mdselect

SHA_HEX = re.compile(r"[0-9a-f]{64}")


# --------------------------------------------------------------------------- helpers

def _golden_classification(repo_root, fx):
    path = repo_root / "engine" / "tests" / "golden" / fx / "classification.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _select_options(fmt="pdf", **changes):
    return dict({"file": {"format": fmt}, "dpi": 200, "media_hashes": {}, "triage_media": []}, **changes)


def _convert(gen, data, name, fmt, run_temp, action="convert_and_ocr"):
    Path(run_temp).mkdir(parents=True, exist_ok=True)
    return convert.convert_source(
        data, sniff=gen.fake_sniff(name, data, fmt=fmt), action=action, run_temp=run_temp)


def _render(gen, data, fmt, units, directory):
    Path(directory).mkdir(parents=True, exist_ok=True)
    return render.render_units(
        data, sniff=gen.fake_sniff(f"x.{fmt}", data, fmt=fmt), units=units, run_temp=directory)


def _jobs(gen, result):
    """KeyJobs for every unit Render left eligible (one Key per unit)."""
    jobs = []
    for unit in result["units"]:
        if unit["status"] != "eligible":
            continue
        key = {"raster_sha256": unit["raster_sha256"], "provider_fingerprint": gen.FINGERPRINT, "dpi": unit["dpi"]}
        jobs.append({
            "key_id": gen.sha256(gen.canonical(key)), "key": key, "units": [unit],
            "raster_path": result["rasters"][unit["source_id"]], "hit": False})
    return jobs


def _transcribe(gen, jobs, provider, **changes):
    entries = []
    settings = dict(
        prompt=transcribe.load_prompt("p1"), force=False, max_requests=99, consent=None, tools=gen.TOOLS,
        now=gen.NOW, publish=entries.append, postprocess=gen.identity_post)
    settings.update(changes)
    return transcribe.run_transcribe(jobs, provider, **settings), entries


@pytest.fixture
def flow(tmp_path, gen, core_spy):
    """Real orchestrator over files in ``input/``; Core is the spy and the provider is injectable."""
    from mdflow import orchestrate

    inputs = tmp_path / "input"
    inputs.mkdir()
    options = dict(
        out=tmp_path / "out", cache=tmp_path / "cache", provider="none", model=None, dpi=200,
        min_priority="low", max_units=200, approve_threshold=20, force=False, prompt_version="p1",
        max_bytes=209715200, max_pixels=50000000, zip_depth=3, zip_entries=1000,
        zip_total_bytes=1073741824, sensitive=[], yes=False, yes_hashes=[], approved_by=None, progress="none")

    def put(name, data):
        path = inputs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run(*, provider=None, **changes):
        opts = dict(options, **changes)
        if provider is not None:
            opts.update(provider=provider.meta["name"], model=provider.meta["model"])
        return orchestrate.run([inputs], opts, provider=provider, now=gen.NOW)

    return types.SimpleNamespace(put=put, run=run, inputs=inputs, out=options["out"], core=core_spy)


def _by_path(report):
    return {f["path"]: f for f in report["files"]}


def _out_files(out):
    return sorted(p.relative_to(out).as_posix() for p in Path(out).rglob("*") if p.is_file()) if Path(out).exists() else []


def _codes(entry):
    return [i["code"] for i in entry["issues"]]


# --------------------------------------------------------------------------- S5 Convert x K01 K02 K04 K05 K06 K11 K18

@pytest.mark.req("REQ-CNV-02")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-01")
def test_T_CNV_06_native_text_pdf_converts_per_page_through_real_core(gen, run_temp):
    data = gen.pdf_text(2)

    result = _convert(gen, data, "x.pdf", "pdf", run_temp, action="convert_only")

    assert result["issues"] == [], "native text converts cleanly"
    assert len(result["pages"]) == 2 and result["media"] == {}
    for number, page in enumerate(result["pages"], start=1):
        assert gen.page_text(number) in page, "each page keeps its own text layer"
        for other in range(1, 3):
            assert (gen.page_text(other) in page) is (other == number), "no text leaks between pages"
    assert result["body"] == "\n\n".join(result["pages"])
    assert "mdflow:ocr" not in result["body"] and "mdflow:pending" not in result["body"], "Convert never emits OCR markers"


@pytest.mark.req("REQ-CNV-02")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-02")
def test_T_CNV_07_scanned_pdf_converts_to_empty_pages_without_failing(gen, run_temp):
    data = gen.pdf_scan(3)

    result = _convert(gen, data, "scan.pdf", "pdf", run_temp)

    assert result["issues"] == [], "an image-only PDF is a clean Convert, not E_CONVERT_FAIL"
    assert len(result["pages"]) == 3, "page structure is kept so Assemble anchors stay complete"
    assert [page.strip() for page in result["pages"]] == ["", "", ""], "scanned page text is empty (CT-05)"
    assert result["media"] == {}


@pytest.mark.req("REQ-CNV-02", "REQ-ASM-04")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-07")
def test_T_CNV_08_capped_pdf_converts_every_page_beyond_the_inspection_cap(gen, core_spy, run_temp):
    import pypdfium2 as pdfium

    data = gen.make_pdf([{"box": (50, 50)} for _ in range(1001)])

    result = _convert(gen, data, "huge.pdf", "pdf", run_temp)

    assert len(core_spy.calls) == 1001, "one Core call per page, including the page past Core's cap"
    assert len(result["pages"]) == 1001 and result["pages"][0] == "converted-1" and result["pages"][-1] == "converted-1001"
    assert result["issues"] == []
    for call in (core_spy.calls[0], core_spy.calls[-1]):
        document = pdfium.PdfDocument(call["data"])
        try:
            assert len(document) == 1, "no out-of-bounds slice: every Core input is a one-page PDF"
        finally:
            document.close()


@pytest.mark.req("REQ-CNV-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-09", "FX-10")
def test_T_CNV_09_standalone_image_is_one_core_call_with_the_original_bytes(gen, fake_core, run_temp):
    for fmt, data in (("png", gen.png_noise(seed=91)), ("jpeg", gen.jpeg_noise(seed=92, orientation=6))):
        fake_core.convert_calls.clear()

        result = _convert(gen, data, f"photo.{fmt}", fmt, run_temp / fmt)

        assert len(fake_core.convert_calls) == 1, fmt
        args, kwargs = fake_core.convert_calls[0]
        assert args[0].getvalue() == data, f"{fmt}: Core gets the unmodified bytes"
        assert kwargs.get("file_extension") == f".{fmt}", f"{fmt}: hint follows the sniffed format"
        assert "extract_media" not in kwargs and "media_base_dir" not in kwargs, fmt
        assert result["pages"] is None and result["media"] == {} and result["issues"] == [], fmt
        assert result["body"] == fake_core.convert_text

    broken = gen.png_truncated()
    fake_core.convert_text = ""
    empty = _convert(gen, broken, "broken.png", "png", run_temp / "broken")
    assert empty["body"] == "" and empty["issues"] == [], "an image with no extractable text is an empty body, not a failure"


@pytest.mark.req("REQ-CNV-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-11", "FX-12")
def test_T_CNV_10_multiframe_raster_is_converted_once_not_per_frame(gen, fake_core, run_temp):
    for fmt, data, frames in (("tiff", gen.tiff_frames(3), 3), ("gif", gen.gif_anim(2), 2)):
        fake_core.convert_calls.clear()

        result = _convert(gen, data, f"frames.{fmt}", fmt, run_temp / fmt)

        assert len(fake_core.convert_calls) == 1, f"{fmt}: {frames} frames are NOT {frames} Core calls"
        args, kwargs = fake_core.convert_calls[0]
        assert args[0].getvalue() == data and kwargs.get("file_extension") == f".{fmt}"
        assert result["pages"] is None, "frame structure belongs to Render, not Convert"
        assert result["media"] == {} and result["issues"] == []


@pytest.mark.req("REQ-CNV-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-30", "FX-31", "FX-32", "FX-33")
def test_T_CNV_11_tabular_and_markup_formats_are_converted_once_with_their_hint(gen, fake_core, run_temp):
    cases = [
        ("csv", b"name,value\na,1\n"),
        ("html", b'<html><body>Own fixture<img src="x.png"></body></html>'),
        ("md", b"# Own fixture\n"),
        ("epub", gen.epub_like()),
    ]
    for fmt, data in cases:
        fake_core.convert_calls.clear()

        result = _convert(gen, data, f"doc.{fmt}", fmt, run_temp / fmt, action="convert_only")

        assert len(fake_core.convert_calls) == 1, fmt
        args, kwargs = fake_core.convert_calls[0]
        assert args[0].getvalue() == data and kwargs.get("file_extension") == f".{fmt}", fmt
        assert "extract_media" not in kwargs, f"{fmt}: only docx|pptx|xlsx|hwp|hwpx extract media"
        assert result["pages"] is None and result["media"] == {} and result["issues"] == [], fmt

    fake_core.convert_calls.clear()
    skipped = _convert(gen, b"x,y\n", "x.csv", "csv", run_temp / "none", action="report_only")
    assert fake_core.convert_calls == [] and skipped["body"] == "", "report_only never reaches Core"


@pytest.mark.req("REQ-CNV-02", "REQ-CNV-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-41")
def test_T_CNV_12_extension_mismatch_dispatches_on_the_sniffed_format(tmp_path, gen, core_spy, run_temp):
    pdf_as_docx = tmp_path / "report.docx"
    pdf_as_docx.write_bytes(gen.pdf_text(2))
    sniffed = sniff_io.sniff(pdf_as_docx, logical="report.docx")
    assert sniffed["format"] == "pdf" and "W_EXT_MISMATCH" in [i["code"] for i in sniffed["issues"]]

    result = convert.convert_source(
        pdf_as_docx.read_bytes(), sniff=sniffed, action="convert_and_ocr", run_temp=run_temp)

    assert len(core_spy.calls) == 2 and len(result["pages"]) == 2, "treated as the PDF it is: one call per page"
    assert all(str(c["ext"]).lstrip(".") == "pdf" and c["extract_media"] is None for c in core_spy.calls)

    docx_as_pdf = tmp_path / "memo.pdf"
    docx_as_pdf.write_bytes(gen.docx_like({"image1.png": gen.png_noise(seed=12)}))
    sniffed = sniff_io.sniff(docx_as_pdf, logical="memo.pdf")
    assert sniffed["format"] == "docx"
    core_spy.calls.clear()
    other = run_temp / "second"
    other.mkdir()

    convert.convert_source(docx_as_pdf.read_bytes(), sniff=sniffed, action="convert_only", run_temp=other)

    assert len(core_spy.calls) == 1, "a docx named .pdf is converted once, not per page"
    assert str(core_spy.calls[0]["ext"]).lstrip(".") == "docx"
    assert Path(core_spy.calls[0]["extract_media"]) == other / "media", "media extraction follows the sniffed format"


# --------------------------------------------------------------------------- S4 Select x K03 K04

@pytest.mark.req("REQ-SEL-01")
@pytest.mark.cov("S4", "FM0")
@pytest.mark.fx("FX-03")
def test_T_SEL_05_mixed_pdf_selects_only_the_scan_pages(repo_root):
    classification = _golden_classification(repo_root, "FX-03")

    selected = mdselect.select(classification, _select_options())

    assert not selected["oversize"]
    assert [u["source_id"] for u in selected["units"]] == ["p2", "p4"]
    assert [u["page"] for u in selected["units"]] == [2, 4], "text pages 1 and 3 are not units"
    assert all(u["status"] == "eligible" and u["raster_sha256"] is None for u in selected["units"])
    assert {"p1", "p3"}.isdisjoint(u["source_id"] for u in selected["units"])


@pytest.mark.req("REQ-SEL-01", "REQ-SEL-02")
@pytest.mark.cov("S4", "FM3")
@pytest.mark.fx("FX-07")
def test_T_SEL_06_capped_pdf_never_selects_the_uninspected_page_and_obeys_the_unit_bound(repo_root):
    classification = _golden_classification(repo_root, "FX-07")
    assert classification["coverage_state"] == "partial" and classification["uninspected_pages"] == 1

    allowed = mdselect.select(classification, _select_options(max_units=1000))
    assert not allowed["oversize"] and len(allowed["units"]) == 1000
    assert allowed["units"][0]["source_id"] == "p1" and allowed["units"][-1]["source_id"] == "p1000"
    assert "p1001" not in {u["source_id"] for u in allowed["units"]}, "the page past the cap has no candidate"
    assert [u["page"] for u in allowed["units"]] == list(range(1, 1001)), "natural page order, no gaps"

    default = mdselect.select(classification, _select_options())
    assert default["oversize"] is True and len(default["units"]) == 1000
    assert {u["status"] for u in default["units"]} == {"oversize"}, "over the default 200-unit bound: all or none"


# --------------------------------------------------------------------------- S6 Render x K03

@pytest.mark.req("REQ-RND-01", "REQ-MAP-01")
@pytest.mark.cov("S6", "FM0")
@pytest.mark.fx("FX-03")
def test_T_RND_09_mixed_pdf_renders_only_the_selected_scan_pages(gen, repo_root, run_temp):
    from PIL import Image

    selected = mdselect.select(_golden_classification(repo_root, "FX-03"), _select_options())
    data = gen.pdf_mixed()

    result = _render(gen, data, "pdf", selected["units"], run_temp / "work")

    assert [u["source_id"] for u in result["units"]] == ["p2", "p4"]
    assert set(result["rasters"]) == {"p2", "p4"}, "no raster for the native text pages 1 and 3"
    on_disk = [p for p in (run_temp / "work").rglob("*") if p.is_file()]
    assert len(on_disk) == 2, "exactly the selected pages were rasterised"
    hashes = set()
    for unit in result["units"]:
        raster = Path(result["rasters"][unit["source_id"]]).read_bytes()
        assert unit["status"] == "eligible" and unit["mime"] == "image/png" and unit["dpi"] == 200
        assert unit["raster_sha256"] == gen.sha256(raster) and raster.startswith(gen.PNG_SIGNATURE)
        assert abs(Image.open(io.BytesIO(raster)).size[0] - 100 * 200 / 72) <= 1.5
        hashes.add(unit["raster_sha256"])
    assert len(hashes) == 2, "pages 2 and 4 are different images"


# --------------------------------------------------------------------------- S10 Transcribe x K02 K03 K07

@pytest.mark.req("REQ-TRX-01")
@pytest.mark.cov("S10", "FM12")
@pytest.mark.fx("FX-02")
def test_T_TRX_07_pure_scan_pdf_pages_are_transcribed_from_their_rendered_rasters(gen, mock_provider, run_temp):
    data = gen.pdf_scan(3)
    units = [gen.pre_render_unit(f"p{n}", n) for n in (1, 2, 3)]
    rendered = _render(gen, data, "pdf", units, run_temp / "work")
    provider = mock_provider()

    result, published = _transcribe(gen, _jobs(gen, rendered), provider)

    assert [c["unit"]["source_id"] for c in provider.calls] == ["p1", "p2", "p3"]
    for call in provider.calls:
        assert call["raster"] == Path(rendered["rasters"][call["unit"]["source_id"]]).read_bytes(), "the rendered PNG is what is sent"
        assert call["raster"].startswith(gen.PNG_SIGNATURE) and call["unit"]["mime"] == "image/png"
    assert (result["sent"], result["ok"], result["failed"], result["denied"]) == (3, 3, 0, [])
    assert len(published) == 3 and {e["status"] for e in published} == {"ok"}
    assert {e["unit"]["dpi"] for e in published} == {200}
    assert [e["text"] for e in published] == [f"text for p{n}" for n in (1, 2, 3)]


@pytest.mark.req("REQ-TRX-01", "REQ-TRX-03", "REQ-APR-07")
@pytest.mark.cov("S10", "FM6")
@pytest.mark.fx("FX-03")
def test_T_TRX_08_mixed_pdf_partial_provider_failure_is_per_page(gen, repo_root, mock_provider, run_temp):
    selected = mdselect.select(_golden_classification(repo_root, "FX-03"), _select_options())
    rendered = _render(gen, gen.pdf_mixed(), "pdf", selected["units"], run_temp / "work")
    jobs = _jobs(gen, rendered)
    assert [j["units"][0]["source_id"] for j in jobs] == ["p2", "p4"]

    failing_first = mock_provider()
    failing_first.script = [("fail", "E_PROVIDER_HTTP"), ("ok", "page four text")]
    result, published = _transcribe(gen, jobs, failing_first)
    assert (result["sent"], result["ok"], result["failed"]) == (2, 1, 1), "p4 is still sent after p2 failed"
    by_page = {e["key"]["raster_sha256"]: e for e in published}
    failed = by_page[jobs[0]["key"]["raster_sha256"]]
    assert failed["status"] == "failed" and failed["error"]["code"] == "E_PROVIDER_HTTP" and failed["text"] is None
    assert by_page[jobs[1]["key"]["raster_sha256"]]["text"] == "page four text"
    assert [i["code"] for i in result["issues"]] == ["E_PROVIDER_HTTP"]

    raising = mock_provider()
    raising.script = [("raise", RuntimeError("boom")), ("ok", "page four text")]
    result, _ = _transcribe(gen, jobs, raising)
    assert (result["ok"], result["failed"]) == (1, 1)
    assert result["entries"][jobs[0]["key_id"]]["error"]["code"] == "E_PROVIDER_CONFIG"

    Path(jobs[1]["raster_path"]).write_bytes(gen.png_noise(seed=999))  # raster replaced after approval
    guarded = mock_provider()
    result, published = _transcribe(gen, jobs, guarded)
    assert [c["unit"]["source_id"] for c in guarded.calls] == ["p2"], "the swapped page is never sent"
    assert result["denied"] == [jobs[1]["key_id"]] and len(published) == 1
    assert [i["code"] for i in result["issues"]] == ["E_APPROVAL_DENIED"]


@pytest.mark.req("REQ-TRX-01", "REQ-TRX-03")
@pytest.mark.cov("S10", "FM6")
@pytest.mark.fx("FX-16", "FX-18")
def test_T_TRX_09_embedded_media_types_are_sent_as_rendered_or_refused_by_mime(gen, mock_provider, run_temp):
    png, jpeg, gif = gen.png_noise(seed=81), gen.jpeg_noise(seed=82), gen.gif_noise()
    members = {"photo.png": png, "scan.jpg": jpeg, "logo.gif": gif, "logo.emf": gen.emf_stub()}
    data = gen.docx_like(members)
    units = [gen.media_unit(f"word/media/{name}") for name in members]
    rendered = _render(gen, data, "docx", units, run_temp / "work")
    by_id = {u["source_id"]: u for u in rendered["units"]}
    assert by_id["word/media/logo.emf"]["status"] == "unsupported_media_format"
    jobs = _jobs(gen, rendered)
    assert len(jobs) == 3, "the unsupported member never becomes a request"

    both = mock_provider()
    result, _ = _transcribe(gen, jobs, both)
    assert result["ok"] == 3 and len(both.calls) == 3
    sent = {c["unit"]["source_id"]: c for c in both.calls}
    assert sent["word/media/photo.png"]["raster"] == png and sent["word/media/photo.png"]["unit"]["mime"] == "image/png"
    assert sent["word/media/scan.jpg"]["raster"] == jpeg and sent["word/media/scan.jpg"]["unit"]["mime"] == "image/jpeg"
    assert sent["word/media/logo.gif"]["raster"].startswith(gen.PNG_SIGNATURE), "GIF is re-encoded to PNG before sending"
    assert sent["word/media/logo.gif"]["unit"]["mime"] == "image/png"

    png_only = mock_provider(accepts=("image/png",))
    result, published = _transcribe(gen, jobs, png_only)
    assert sorted(c["unit"]["source_id"] for c in png_only.calls) == ["word/media/logo.gif", "word/media/photo.png"]
    refused = [e for e in published if e["status"] == "failed"]
    assert len(refused) == 1 and refused[0]["error"]["code"] == "E_PROVIDER_CONFIG", "JPEG is refused before any send"
    assert refused[0]["unit"]["mime"] == "image/jpeg"
    assert (result["ok"], result["failed"], result["sent"]) == (2, 1, 2)


# --------------------------------------------------------------------------- S12 Write x K07 K14

@pytest.mark.req("REQ-WRT-01", "REQ-CNV-03")
@pytest.mark.cov("S12", "FM9")
@pytest.mark.fx("FX-16", "FX-21")
def test_T_WRT_04_office_output_publishes_awkward_media_names_inside_its_own_media_dir(tmp_path, gen, out_dir):
    source = tmp_path / "src"
    source.mkdir()
    names = {}
    for label, blob in (("plain", gen.png_noise(seed=41)), ("spaced", gen.png_noise(seed=42)), ("korean", gen.png_noise(seed=43))):
        name = {"plain": gen.h12(blob) + ".png", "spaced": "my image (1).png", "korean": "그림-" + gen.h12(blob) + ".png"}[label]
        path = source / f"{label}.bin"
        path.write_bytes(blob)
        names[name] = path

    first = write.publish_source(out_dir, "docs/sub/memo.docx.md", b"# memo\n", names)

    assert first["ok"] is True and first["issues"] == []
    assert first["written"][-1] == "docs/sub/memo.docx.md", "the markdown is published last"
    for name, path in names.items():
        assert (out_dir / "docs" / "sub" / "media" / name).read_bytes() == path.read_bytes(), name
    assert sorted(_out_files(out_dir)) == sorted(
        ["docs/sub/memo.docx.md", *[f"docs/sub/media/{n}" for n in names]]), "nothing outside the media dir and the .md"

    again = write.publish_source(out_dir, "docs/sub/memo.docx.md", b"# memo\n", names)
    assert again["ok"] is True and again["written"] == [] and len(again["unchanged"]) == len(names) + 1

    for hostile in ("../evil.png", "sub/evil.png", ".."):
        outcome = write.publish_source(out_dir, "docs/other/page.docx.md", b"# page\n", {hostile: next(iter(names.values()))})
        assert outcome["ok"] is False and [i["code"] for i in outcome["issues"]] == ["E_OUTPUT_IO"], hostile
        assert not (out_dir / "docs" / "other" / "page.docx.md").exists(), f"{hostile}: no markdown links to refused media"
    assert not (out_dir / "docs" / "evil.png").exists() and not (out_dir / "evil.png").exists()
    leftovers = [p for p in out_dir.rglob("*") if ".tmp-" in p.name]
    assert leftovers == [], "no temp file survives a refused publication"


@pytest.mark.req("REQ-WRT-01", "REQ-CTR-01")
@pytest.mark.cov("S12", "FM9")
@pytest.mark.fx("FX-43", "FX-44")
def test_T_WRT_05_container_outputs_stay_inside_the_output_tree(tmp_path, gen, flow):
    direct = tmp_path / "direct"
    direct.mkdir()
    nested = write.publish_source(direct, "pack.zip/docs/report.pdf.md", b"# report\n")
    assert nested["ok"] is True and nested["written"] == ["pack.zip/docs/report.pdf.md"]
    assert write.publish_source(direct, "pack.zip/docs/report.pdf.md", b"# report\n")["unchanged"] == ["pack.zip/docs/report.pdf.md"]

    for escape in ("pack.zip/../../escape.md", "../escape.md", "/abs/escape.md"):
        outcome = write.publish_source(direct, escape, b"# escape\n")
        assert outcome["ok"] is False and [i["code"] for i in outcome["issues"]] == ["E_OUTPUT_IO"], escape
    assert not (tmp_path / "escape.md").exists()
    assert _out_files(direct) == ["pack.zip/docs/report.pdf.md"], "refused writes leave nothing behind"

    flow.put("slip.zip", gen.zip_slip())
    report = flow.run()
    files = _by_path(report)
    unsafe = {path: f for path, f in files.items() if "E_ZIP_PATH" in _codes(f)}
    assert unsafe, "the hostile member names are flagged"
    assert all(f["outputs"] == [] and f["action"] == "report_only" for f in unsafe.values())
    root = flow.out.resolve()
    for relative in _out_files(flow.out):
        assert ".." not in relative.split("/") and not relative.startswith("/")
        assert (flow.out / relative).resolve().is_relative_to(root), relative
    assert {p.name for p in tmp_path.iterdir()} <= {"input", "out", "cache", "direct"}, "nothing was written beside the output tree"


# --------------------------------------------------------------------------- S8 Plan / S11 Assemble x K14 K15 K16

@pytest.mark.req("REQ-PLN-01", "REQ-CTR-03")
@pytest.mark.cov("S8", "FM0")
@pytest.mark.fx("FX-43")
def test_T_PLN_11_zip_container_has_its_own_zero_cost_plan_and_members_plan_separately(gen, flow, mock_provider):
    flow.put("pack.zip", gen.zip_basic())
    provider = mock_provider()

    report = flow.run(provider=provider)

    files = _by_path(report)
    container = files["pack.zip"]
    assert container["route"] == "CONTAINER" and container["action"] == "recurse"
    assert SHA_HEX.fullmatch(container["plan_hash"]), "the container itself is planned"
    assert container["units"]["total"] == 0 and container["requests"] == dict(to_send=0, sent=0, ok=0, failed=0)
    members = {path: f for path, f in files.items() if path.startswith("pack.zip/")}
    assert set(members) == {"pack.zip/docs/report.pdf", "pack.zip/notes.txt", "pack.zip/files/memo.docx"}
    assert all(SHA_HEX.fullmatch(f["plan_hash"]) for f in members.values()), "each member has its own Plan"
    assert len({f["plan_hash"] for f in files.values()}) == len(files), "container and member plans are distinct identities"
    assert provider.calls == [], "planning a container sends nothing"


@pytest.mark.req("REQ-PLN-01", "REQ-APR-01")
@pytest.mark.cov("S8", "FM0")
@pytest.mark.fx("FX-05", "FX-25")
def test_T_PLN_12_protected_files_get_a_zero_cost_plan_without_reading_the_content(gen, flow, mock_provider):
    flow.put("locked.pdf", gen.pdf_encrypt_trailer())
    flow.put("secret.docx", gen.cfb_encrypted_office())
    provider = mock_provider()

    report = flow.run(provider=provider)

    files = _by_path(report)
    assert set(files) == {"locked.pdf", "secret.docx"}
    for path, entry in files.items():
        assert entry["route"] == "PROTECTED" and entry["action"] == "report_only", path
        assert SHA_HEX.fullmatch(entry["plan_hash"]), path
        assert entry["units"]["total"] == 0 and entry["requests"] == dict(to_send=0, sent=0, ok=0, failed=0), path
        assert "E_APPROVAL_REQUIRED" not in _codes(entry), f"{path}: no consent is requested without units"
    assert provider.calls == [], "nothing is sent"
    assert flow.core.calls == [], "Core never opens an encrypted file"


@pytest.mark.req("REQ-PLN-01", "REQ-APR-01")
@pytest.mark.cov("S8", "FM0")
@pytest.mark.fx("FX-06", "FX-40")
def test_T_PLN_13_corrupt_and_empty_files_get_a_zero_cost_plan(gen, flow, mock_provider):
    flow.put("broken.pdf", gen.pdf_corrupt())
    flow.put("empty.pdf", b"")
    provider = mock_provider()

    report = flow.run(provider=provider)

    files = _by_path(report)
    assert set(files) == {"broken.pdf", "empty.pdf"}
    for path, entry in files.items():
        assert "E_CORRUPT" in _codes(entry), path
        assert entry["action"] == "report_only" and entry["units"]["total"] == 0, path
        assert SHA_HEX.fullmatch(entry["plan_hash"]), path
        assert entry["requests"] == dict(to_send=0, sent=0, ok=0, failed=0), path
        assert "E_APPROVAL_REQUIRED" not in _codes(entry), path
    assert provider.calls == [] and flow.core.calls == []


@pytest.mark.req("REQ-ASM-06", "REQ-RPT-03")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-05", "FX-25")
def test_T_ASM_17_protected_files_assemble_no_markdown_and_report_the_protection(gen, flow):
    flow.put("locked.pdf", gen.pdf_encrypt_trailer())
    flow.put("secret.docx", gen.cfb_encrypted_office())

    report = flow.run()

    for path, entry in _by_path(report).items():
        assert entry["label"] == "P" and "E_ENCRYPTED" in _codes(entry), path
        assert entry["outputs"] == [] and entry["placements"] == 0, f"{path}: no Markdown, hence no marker, is produced"
    assert _out_files(flow.out) == [], "protected sources leave no file in the output tree"
    assert report["exit"] == assemble.exit_code(["E_ENCRYPTED"]) != 0


@pytest.mark.req("REQ-ASM-06", "REQ-RPT-03")
@pytest.mark.cov("S11", "FM0")
@pytest.mark.fx("FX-06", "FX-40")
def test_T_ASM_18_corrupt_files_assemble_no_markdown_and_report_the_corruption(gen, flow):
    flow.put("broken.pdf", gen.pdf_corrupt())
    flow.put("empty.pdf", b"")

    report = flow.run()

    for path, entry in _by_path(report).items():
        assert "E_CORRUPT" in _codes(entry), path
        assert entry["outputs"] == [] and entry["placements"] == 0, path
    assert _out_files(flow.out) == []
    assert report["exit"] == assemble.exit_code(["E_CORRUPT"]) != 0
