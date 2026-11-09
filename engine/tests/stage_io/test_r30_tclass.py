"""R30: the no-OCR (T-class) path through the real pipeline and real Core.

Born-digital sources of every group are generated here (python-docx / python-pptx / openpyxl / hand-built PDF, HWPX,
HWP5, EPUB) and run through ``orchestrate.run`` with provider ``none``. For each the output is checked for: an
untouched frontmatter contract, no pending/OCR markers, headings and tables preserved, media links that resolve.
Legacy-encoded ``.txt`` (CP949 ...) is converted instead of rejected (row 9d).
"""

import io
import json
import re
import struct
import zlib
from pathlib import Path

import pytest

from mdflow import orchestrate, sniff_io

KO_TEXT = "한국어 텍스트입니다. 두 번째 문장도 있습니다.\n세 번째 줄입니다. 문서 변환 시험용 문장입니다.\n"
GEN_CORE = Path(__file__).resolve().parents[1] / "fixtures" / "gen_core.py"


@pytest.fixture(scope="module")
def core_data():
    import importlib.util

    spec = importlib.util.spec_from_file_location("mdflow_r30_gen_core", GEN_CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frontmatter(text):
    head, sep, body = text.partition("\n---\n")
    assert head.startswith("---\n") and sep, "output begins with a frontmatter block"
    values = {}
    for line in head.splitlines()[1:]:
        key, _, value = line.partition(": ")
        values[key] = json.loads(value) if value.startswith('"') else value
    return values, body


def run_files(tmp_path, files):
    root = tmp_path / "input"
    root.mkdir()
    for name, data in files.items():
        (root / name).write_bytes(data)
    report = orchestrate.run([root], dict(out=tmp_path / "out", cache=tmp_path / "cache"))
    by_name = {f["path"]: f for f in report["files"]}
    return report, by_name, tmp_path / "out"


# --------------------------------------------------------------------------------- generators

def make_docx(png):
    from docx import Document
    from docx.shared import Inches

    doc = Document()
    doc.add_heading("Goals", 1)
    paragraph = doc.add_paragraph("Ship the ")
    paragraph.add_run("engine").bold = True
    doc.add_paragraph("First item", style="List Bullet")
    doc.add_paragraph("Step one", style="List Number")
    doc.add_heading("Budget", 2)
    table = doc.add_table(rows=2, cols=3)
    for r, row in enumerate([("Item", "Cost", "Owner"), ("Server", "100", "Kim")]):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    doc.add_paragraph("한국어 문단입니다.")
    doc.add_picture(io.BytesIO(png), width=Inches(1.5))
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def make_pptx(png):
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Launch Deck"
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Agenda"
    slide.placeholders[1].text_frame.text = "Point A"
    slide.notes_slide.notes_text_frame.text = "Speaker notes text"
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "Numbers"
    table = slide.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
    for r, row in enumerate([("Metric", "Value"), ("Users", "10")]):
        for c, value in enumerate(row):
            table.cell(r, c).text = value
    slide.shapes.add_picture(io.BytesIO(png), Inches(1), Inches(4), Inches(1.5))
    out = io.BytesIO()
    prs.save(out)
    return out.getvalue()


def make_xlsx():
    import openpyxl

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Sales"
    sheet.append(["Region", "Q1", "Q2"])
    sheet.append(["North", 10, 12])
    book.create_sheet("Notes").append(["owner", "한국"])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def make_pdf():
    lines = [(24, 50, 700, "Annual Report 2026"), (16, 50, 660, "1. Overview"),
             (11, 50, 635, "Revenue grew by twelve percent."), (16, 50, 580, "2. Results"),
             (11, 50, 555, "Region"), (11, 200, 555, "Revenue"), (11, 320, 555, "Growth"),
             (11, 50, 540, "North"), (11, 200, 540, "120"), (11, 320, 540, "5%"),
             (11, 50, 525, "South"), (11, 200, 525, "98"), (11, 320, 525, "9%")]
    content = b"".join(b"BT /F1 %d Tf %d %d Td (%s) Tj ET\n" % (s, x, y, t.encode()) for s, x, y, t in lines)
    objs = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 2: b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
            3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
            5: b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream"}
    out, offsets = bytearray(b"%PDF-1.4\n"), {}
    for number in sorted(objs):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objs[number] + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(b"%010d 00000 n \n" % offsets[n] for n in range(1, 6))
    return bytes(out + b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref)


def make_hwpx(gen):
    hp, hs = "http://www.hancom.co.kr/hwpml/2011/paragraph", "http://www.hancom.co.kr/hwpml/2011/section"

    def para(text):
        return f"<hp:p><hp:run><hp:t>{text}</hp:t></hp:run></hp:p>"

    def cell(text):
        return f"<hp:tc><hp:subList>{para(text)}</hp:subList></hp:tc>"

    section = (f'<?xml version="1.0" encoding="UTF-8"?><hs:sec xmlns:hs="{hs}" xmlns:hp="{hp}">'
               + para("한글 문서 제목") + para("본문 첫 문단입니다.")
               + '<hp:p><hp:run><hp:tbl rowCnt="2" colCnt="2">'
               + f"<hp:tr>{cell('항목')}{cell('값')}</hp:tr><hp:tr>{cell('가')}{cell('1')}</hp:tr>"
               + "</hp:tbl></hp:run></hp:p></hs:sec>")
    return gen.make_zip({"mimetype": b"application/hwp+zip", "Contents/content.hpf": b"<hpf/>",
                         "Contents/header.xml": b"<hh:head xmlns:hh='http://www.hancom.co.kr/hwpml/2011/head'/>",
                         "Contents/section0.xml": section.encode("utf-8")})


def make_hwp(core_data):
    """FX-24 recipe without pictures: a text-only HWP5."""
    header = b"HWP Document File".ljust(32, b"\0") + struct.pack("<II", 0x05000300, 1) + b"\0" * 216
    text = "Own deterministic HWP fixture".encode("utf-16-le")
    records = struct.pack("<I", 67 | (len(text) << 20)) + text
    compressor = zlib.compressobj(level=6, wbits=-15)
    body = compressor.compress(records) + compressor.flush()
    return core_data.cfb_bytes({"FileHeader": header, "DocInfo": b"", "BodyText/Section0": body})


def make_epub(gen):
    chapter = ('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>Ch1</title>'
               "</head><body><h1>Chapter One</h1><p>Epub paragraph.</p></body></html>")
    package = ('<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
               '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>My Book</dc:title><dc:creator>Author A'
               '</dc:creator><dc:identifier id="id">urn:x</dc:identifier><dc:language>en</dc:language></metadata>'
               '<manifest><item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/></manifest>'
               '<spine><itemref idref="c1"/></spine></package>')
    container = ('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
                 "</rootfiles></container>")
    return gen.make_zip({"mimetype": b"application/epub+zip", "META-INF/container.xml": container.encode(),
                         "OEBPS/content.opf": package.encode(), "OEBPS/ch1.xhtml": chapter.encode()})


HTML = ("<html><head><title>Doc Title</title></head><body><h1>Heading One</h1><p>Intro <b>bold</b> and "
        "<a href='https://example.com/x'>a link</a>.</p><ul><li>A</li><li>B</li></ul>"
        "<table><tr><th>K</th><th>V</th></tr><tr><td>a</td><td>1</td></tr></table><script>var hidden=1;</script>"
        "</body></html>")

# name -> (expected substrings, absent substrings, label)
EXPECTED = {
    "plan.docx": (["# Goals", "## Budget", "**engine**", "* First item", "1. Step one", "| Server | 100 | Kim |",
                   "한국어 문단입니다.", "![Image](media/"], [], "T"),
    "deck.pptx": (["# Launch Deck", "# Agenda", "Point A", "### Notes:", "Speaker notes text", "# Numbers",
                   "| Metric | Value |", "| Users | 10 |", "![image.png](media/"], [], "T"),
    "book.xlsx": (["## Sales", "| Region | Q1 | Q2 |", "| North |", "## Notes", "| owner | 한국 |"], [], "T"),
    "report.pdf": (["<!-- mdflow:page 1 -->", "Annual Report 2026", "Revenue grew by twelve percent.",
                    "| Region | Revenue | Growth |", "| North  | 120     | 5%     |"], [], "T"),
    "doc.hwpx": (["한글 문서 제목", "본문 첫 문단입니다.", "| 항목 | 값 |", "| 가 | 1 |"], [], "T"),
    "doc.hwp": (["Own deterministic HWP fixture"], [], "T"),
    "data.csv": (["| name | qty | note |", "| widget | 3 | has, comma |"], [], "T"),
    "page.html": (["# Heading One", "**bold**", "[a link](https://example.com/x)", "* A", "| K | V |", "| a | 1 |"],
                  ["hidden", "<script"], "T"),
    "book.epub": (["**Title:** My Book", "**Authors:** Author A", "# Chapter One", "Epub paragraph."], [], "T"),
    "note.txt": (["First line", "Second line", "한국어"], [], "T"),
    "run.log": (["2026-01-01 INFO start", "2026-01-01 WARN second"], [], "T"),
    "readme.md": (["# Title", "Some *text*.", "| a | b |"], [], "T"),
    "conf.json": (['"name": "x"', '"nested": {'], [], "T"),
}


@pytest.mark.req("REQ-CNV-03", "REQ-CLS-07")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-16", "FX-21", "FX-22", "FX-23", "FX-28", "FX-30", "FX-31", "FX-32", "FX-33")
def test_T_CNV_89_born_digital_sources_convert_with_structure_media_and_clean_frontmatter(tmp_path, gen, core_data):
    png = gen.png_noise(64, 48, seed=5)
    files = {
        "plan.docx": make_docx(png), "deck.pptx": make_pptx(gen.png_noise(64, 48, seed=6)), "book.xlsx": make_xlsx(),
        "report.pdf": make_pdf(), "doc.hwpx": make_hwpx(gen), "doc.hwp": make_hwp(core_data),
        "data.csv": b'name,qty,note\nwidget,3,"has, comma"\ngadget,5,plain\n', "page.html": HTML.encode(),
        "book.epub": make_epub(gen), "note.txt": "First line\nSecond line\n한국어\n".encode(),
        "run.log": b"2026-01-01 INFO start\n2026-01-01 WARN second\n",
        "readme.md": b"# Title\n\nSome *text*.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n",
        "conf.json": json.dumps({"name": "x", "nested": {"k": "v"}}, indent=2).encode(),
    }
    assert set(files) == set(EXPECTED)
    report, by_name, out = run_files(tmp_path, files)
    assert report["exit"] == 0, [(n, [i["code"] for i in f["issues"]]) for n, f in by_name.items()]
    for name, (present, absent, label) in sorted(EXPECTED.items()):
        entry = by_name[name]
        assert not [i["code"] for i in entry["issues"] if i["code"].startswith("E_")], name
        assert entry["label"] == label and entry["units"]["total"] == 0 and entry["outputs"] == [f"{name}.md"], name
        meta, body = frontmatter((out / f"{name}.md").read_text(encoding="utf-8"))
        assert meta["mdflow"] == "2" and meta["source"] == name and meta["route"] == "NATIVE", name
        assert meta["format"] == name.rsplit(".", 1)[1] and meta["label"] == label, name
        assert meta["sha256"] == gen.sha256(files[name]) and int(meta["bytes"]) == len(files[name]), name
        assert re.fullmatch(r"[0-9a-f]{64}", meta["content_sha256"]), name
        assert "provider" not in meta and meta["units"] == "{total: 0, done: 0, pending: 0, failed: 0}", name
        assert "mdflow:pending" not in body and "mdflow:ocr" not in body and "OCR media" not in body, name
        for text in present:
            assert text in body, f"{name}: missing {text!r}"
        for text in absent:
            assert text not in body, f"{name}: unexpected {text!r}"
        # every media link in the body resolves to a published file next to the .md
        for link in re.findall(r"!\[[^\]]*\]\((media/[^)]+)\)", body):
            assert (out / link).is_file(), f"{name}: dangling media link {link}"
    assert (out / "report.pdf.md").read_text(encoding="utf-8").count("<!-- mdflow:page ") == 1
    assert by_name["data.csv"]["issues"] == [], "R33 csv is T without media warning"
    assert not (out / "media").exists() or all(p.suffix in {".png", ".jpg", ".jpeg"} for p in (out / "media").iterdir())


@pytest.mark.req("REQ-CLS-07")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-28", "FX-38")
def test_T_SNF_83_sniff_marks_only_legacy_encoded_txt_and_log(tmp_path, gen):
    cases = {
        "cp949.txt": (KO_TEXT.encode("cp949"), ["legacy_text"]),
        "cp949.log": (KO_TEXT.encode("cp949"), ["legacy_text"]),
        "latin.txt": ("Café déjà vu — résumé naïve\n".encode("cp1252"), ["legacy_text"]),
        "utf8.txt": (KO_TEXT.encode("utf-8"), []),
        "utf16.txt": (KO_TEXT.encode("utf-16"), []),
        "audio.txt": (b"ID3" + gen.rng_bytes(256, 38), []),
        "cp949.csv": (KO_TEXT.encode("cp949"), []),
        "cp949.md": (KO_TEXT.encode("cp949"), []),
    }
    for name, (data, reasons) in cases.items():
        path = tmp_path / name
        path.write_bytes(data)
        result = sniff_io.sniff(path, logical=name)
        assert (result["format"], result["route"]) == (name.rsplit(".", 1)[1], "NATIVE"), name
        assert result["reasons"] == reasons, name
    # zip members are sniffed by the same code path
    archive = gen.make_zip({"docs/ko.txt": KO_TEXT.encode("cp949"), "docs/en.txt": b"plain\n"})
    members = sniff_io.expand_container(archive, logical="pack.zip")["members"]
    reasons = {m["sniff"]["path"]: m["sniff"]["reasons"] for m in members}
    assert reasons == {"pack.zip/docs/ko.txt": ["legacy_text"], "pack.zip/docs/en.txt": []}


@pytest.mark.req("REQ-CLS-07", "REQ-CNV-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-28", "FX-38")
def test_T_CNV_90_legacy_encoded_text_is_converted_as_t_class_and_binary_is_still_refused(tmp_path, gen):
    files = {"korean.txt": KO_TEXT.encode("cp949"), "korean.log": KO_TEXT.encode("cp949"),
             "audio.txt": b"ID3" + gen.rng_bytes(256, 38)}
    report, by_name, out = run_files(tmp_path, files)
    for name in ("korean.txt", "korean.log"):
        entry = by_name[name]
        assert (entry["route"], entry["need"], entry["label"], entry["action"]) == ("NATIVE", "NONE", "T", "convert_only"), name
        assert not [i for i in entry["issues"] if i["code"].startswith(("E_", "W_"))], name
        meta, body = frontmatter((out / f"{name}.md").read_text(encoding="utf-8"))
        assert meta["label"] == "T" and "한국어 텍스트입니다." in body and "�" not in body, name
    refused = by_name["audio.txt"]
    assert (refused["label"], refused["action"], refused["outputs"]) == ("X", "report_only", [])
    assert "E_UNSUPPORTED" in [i["code"] for i in refused["issues"]]
    assert report["exit"] == 2, "the binary file still fails the run; the legacy text does not"
