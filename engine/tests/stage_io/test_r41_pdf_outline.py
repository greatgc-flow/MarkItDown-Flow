"""R41: a PDF with bookmarks is converted whole so Core's outline headings reach the output, on the right page.

Core's conversion is replaced by an emulation of what Core 0.3.8 does with a PDF (CT-05/CT-16 pin the real thing):
one form feed between pages, trailing pages without text dropped, and, for a PDF that has bookmarks, a ``# `` heading
for the line a bookmark names. The pipeline under test is real: sniff, triage, class, convert, render, OCR provider,
assemble. T = every page has text; M = a text page plus a scanned page (provider OCR); S = scanned pages only.
"""

import importlib.util
import re
from pathlib import Path

import pytest

from mdflow import convert, orchestrate

_spec = importlib.util.spec_from_file_location(
    "mdflow_pdf_outline_fixture", Path(__file__).resolve().parents[1] / "pdf_outline_fixture.py")
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
PAGE_TEXT, TITLES, outline_pdf = _fixture.PAGE_TEXT, _fixture.TITLES, _fixture.outline_pdf

OPTIONS = dict(provider="none", model=None, dpi=200, min_priority="low", max_units=200, approve_threshold=20,
               force=False, prompt_version="p1", max_bytes=209715200, max_pixels=50000000, zip_depth=3,
               zip_entries=1000, zip_total_bytes=1073741824, sensitive=[], yes=False, yes_hashes=[],
               approved_by=None, progress="none")


def emulated_core(spy, index, data, ext, extract_media, media_base_dir):
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        bookmarked = next(iter(document.get_toc()), None) is not None
        pages = []
        for page in document:
            textpage = page.get_textpage()
            lines = [line.strip() for line in textpage.get_text_range().splitlines() if line.strip()]
            textpage.close()
            if bookmarked and lines and lines[0] in TITLES:
                lines[0] = "# " + lines[0]
            pages.append("\n\n".join(lines) + "\n\n" if lines else "")
        return "\f".join(pages).rstrip("\f")
    finally:
        document.close()


def run_pdf(tmp_path, gen, data, provider=None):
    root = tmp_path / "input"
    root.mkdir(parents=True)
    (root / "book.pdf").write_bytes(data)
    options = dict(OPTIONS, out=tmp_path / "out", cache=tmp_path / "cache")
    if provider is not None:
        options.update(provider=provider.meta["name"], model=provider.meta["model"], yes=True)
    report = orchestrate.run([root], options, provider=provider, now=gen.NOW)
    entry, = report["files"]
    return entry, (tmp_path / "out" / "book.pdf.md").read_text(encoding="utf-8")


def page_sections(body):
    """{page number: text after its anchor up to the next anchor}"""
    parts = re.split(r"<!-- mdflow:page (\d+) -->", body)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def heading(section, title):
    return re.search(rf"^#{{1,6}} {title}\s*$", section, re.M) is not None


@pytest.fixture
def emulated(core_spy):
    core_spy.behavior = emulated_core
    return core_spy


@pytest.mark.req("REQ-CNV-02")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-01")
def test_T_ASM_92_born_digital_pdf_bookmarks_become_headings_under_their_own_page_anchor(tmp_path, gen, emulated):
    entry, body = run_pdf(tmp_path, gen, outline_pdf())

    assert not [i for i in entry["issues"] if i["code"].startswith("E_")] and entry["label"] == "T"
    assert len(emulated.calls) == 1, "one whole-document Core call, no per-page calls"
    sections = page_sections(body)
    assert sorted(sections) == [1, 2]
    assert heading(sections[1], "Chapter One") and PAGE_TEXT[0] in sections[1] and "Chapter Two" not in sections[1]
    assert heading(sections[2], "Chapter Two") and PAGE_TEXT[1] in sections[2] and "Chapter One" not in sections[2]


@pytest.mark.req("REQ-CNV-02", "REQ-ASM-04")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-01", "FX-03")
def test_T_ASM_93_bookmarked_mixed_and_scanned_pdfs_keep_headings_and_the_ocr_blocks(tmp_path, gen, emulated, mock_provider):
    scan = ("image", None)
    mixed = outline_pdf(pages=(("text", (TITLES[0], PAGE_TEXT[0])), scan), titles=(TITLES[0], TITLES[1]))
    entry, body = run_pdf(tmp_path / "m", gen, mixed, mock_provider())
    assert entry["label"] == "M" and entry["units"]["transcribed"] == 1
    sections = page_sections(body)
    assert sorted(sections) == [1, 2]
    assert heading(sections[1], "Chapter One") and PAGE_TEXT[0] in sections[1], "text page keeps its bookmark heading"
    assert "text for" in sections[2], "the scanned trailing page, dropped by Core, still gets its OCR text"
    assert "Chapter" not in sections[2]

    entry, body = run_pdf(tmp_path / "s", gen, outline_pdf(pages=(scan, scan), titles=(TITLES[0], TITLES[1])), mock_provider())
    assert entry["label"] == "S" and entry["units"]["transcribed"] == 2
    sections = page_sections(body)
    assert sorted(sections) == [1, 2] and all("text for" in sections[n] for n in (1, 2))


@pytest.mark.req("REQ-CNV-02")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-01")
def test_T_ASM_94_unmatchable_whole_document_text_falls_back_to_one_core_call_per_page(gen, core_spy, run_temp):
    import pypdfium2 as pdfium

    data, sniff = outline_pdf(), None

    def convert_pdf(payload, name):
        return convert.convert_source(
            payload, sniff=gen.fake_sniff(name, payload, fmt="pdf"), action="convert_only", run_temp=run_temp)

    def page_counts():
        sizes = []
        for call in core_spy.calls:
            document = pdfium.PdfDocument(call["data"])
            try:
                sizes.append(len(document))
            finally:
                document.close()
        return sizes

    # no form feed: the pieces cannot be matched to two text pages
    core_spy.behavior = lambda spy, index, *rest: "whole document without page breaks" if index == 0 else f"page-{index}"
    result = convert_pdf(data, "a.pdf")
    assert page_counts() == [2, 1, 1] and result["pages"] == ["page-1", "page-2"] and result["issues"] == []

    # too many pieces
    core_spy.calls.clear()
    core_spy.behavior = lambda spy, index, *rest: "a\fb\fc" if index == 0 else f"page-{index}"
    assert convert_pdf(outline_pdf(), "b.pdf")["pages"] == ["page-1", "page-2"] and page_counts() == [2, 1, 1]

    # a dropped page that does have text: the missing trailing page cannot be assumed empty
    core_spy.calls.clear()
    core_spy.behavior = lambda spy, index, *rest: "only the first page" if index == 0 else f"page-{index}"
    assert convert_pdf(outline_pdf(), "c.pdf")["pages"] == ["page-1", "page-2"] and page_counts() == [2, 1, 1]

    # Core failing on the whole document is not a file failure while single pages convert
    core_spy.calls.clear()

    def whole_fails(spy, index, *rest):
        if index == 0:
            raise RuntimeError("whole-document failure")
        return f"page-{index}"

    core_spy.behavior = whole_fails
    result = convert_pdf(outline_pdf(), "d.pdf")
    assert result["pages"] == ["page-1", "page-2"] and result["issues"] == []

    # a splittable result needs no per-page calls
    core_spy.calls.clear()
    core_spy.behavior = lambda spy, index, *rest: "# Chapter One\n\nfirst\f# Chapter Two\n\nsecond\f"
    result = convert_pdf(outline_pdf(), "e.pdf")
    assert len(core_spy.calls) == 1 and result["pages"] == ["# Chapter One\n\nfirst", "# Chapter Two\n\nsecond"]

    # a PDF without bookmarks never takes the whole-document path
    core_spy.calls.clear()
    core_spy.behavior = None
    convert_pdf(outline_pdf(titles=(None, None)), "f.pdf")
    assert page_counts() == [1, 1]
