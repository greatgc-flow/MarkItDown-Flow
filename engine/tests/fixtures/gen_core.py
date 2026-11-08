"""Deterministic own-work fixture recipes and RED test data builders.

No triage report is authored here. Reports are read from orchestrator goldens;
synthetic cases deep-copy one of those reports and change the targeted fields.
FX-24 is deliberately read from the separately reviewed binary/provenance pair.
"""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import random
import re
import struct
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[3]
NOW = "2026-11-09T00:00:00+00:00"
GENERATED = tuple(f"FX-{n:02}" for n in (
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,
    18, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 48, 49,
))
CORE_CODES = frozenset("corrupt encrypted external_media frame_cap image_probe_failed "
    "media_not_inspected missing_dependency page_cap too_large unresolved_embed "
    "unsupported_compression unsupported_format unsupported_media zip_limit".split())
CORE_REASONS = frozenset("scan_like suspect_text_layer low_text_nonblank image_with_text_layer "
    "standalone_image embedded_image decor_media".split())


class WorkspaceTemps:
    """Test artifacts avoid Python 3.15 Windows mode=0700 sandbox DACLs.

    No production permission behavior is patched. These directories are retained
    with the RED logs, and every resolved target stays inside this worktree.
    """
    def __init__(self, root):
        self.root = Path(root).resolve()
        assert self.root.is_relative_to(ROOT.resolve())
        self.root.mkdir(parents=True, exist_ok=True)
        self.sequence = 0

    def mktemp(self, basename, numbered=True):
        basename = "".join(c if c.isalnum() or c in "-_" else "_" for c in basename)[:80]
        while True:
            self.sequence += 1
            target = self.root / f"{basename}-{os.getpid()}-{self.sequence}"
            assert target.resolve().is_relative_to(self.root)
            try:
                target.mkdir()
            except FileExistsError:
                continue
            return target


def canonical(value):
    """Independent test oracle; never call mdflow's serializer for expectations."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return sha256(value).hexdigest()


def image_bytes(fmt="PNG", *, frames=1, size=(200, 200), seed=7, **kwargs):
    from PIL import Image
    rng = random.Random(seed)
    images = [Image.frombytes("RGB", size, rng.randbytes(size[0] * size[1] * 3))
              for _ in range(frames)]
    out = BytesIO()
    images[0].save(out, format=fmt, save_all=frames > 1,
                   append_images=images[1:] if frames > 1 else [], **kwargs)
    return out.getvalue()


def zip_bytes(members):
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(info, data.encode() if isinstance(data, str) else data)
    return out.getvalue()


def normalize_zip(data):
    with zipfile.ZipFile(BytesIO(data)) as archive:
        members = []
        for name in sorted(archive.namelist()):
            payload = archive.read(name)
            if name == "docProps/core.xml":
                # openpyxl overwrites modified during save even after it is set.
                payload = re.sub(rb"(<dcterms:(?:created|modified)\b[^>]*>)[^<]*(</dcterms:(?:created|modified)>)",
                                 lambda m: m[1] + b"2000-01-01T00:00:00Z" + m[2], payload)
            members.append((name, payload))
        return zip_bytes(members)


def pdf_bytes(kinds, *, big=False, suspect=False):
    """Small raw PDF writer; own text/images, no creation dates or IDs."""
    objects = [b"", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    # RGB noise is deliberately nonblank; one shared image keeps capped PDFs small.
    rng = random.Random(23)
    pixels = rng.randbytes(48 * 48 * 3)
    objects.append(b"<< /Type /XObject /Subtype /Image /Width 48 /Height 48 "
                   b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length "
                   + str(len(pixels)).encode() + b" >>\nstream\n" + pixels + b"\nendstream")
    kids = []
    box = 7200 if big else 612
    for kind in kinds:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {box} {box}] "
                        f"/Resources << /Font << /F1 3 0 R >> /XObject << /Im 4 0 R >> >> "
                        f"/Contents {page_id + 1} 0 R >>").encode())
        if kind == "text":
            content = b"BT /F1 12 Tf 30 500 Td (Own deterministic fixture text. " + b"Readable text " * 30 + b") Tj ET"
        else:
            content = f"q {box} 0 0 {box} 0 0 cm /Im Do Q".encode()
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(kids)}] >>".encode()
    if suspect:
        # Map every printable glyph to U+FFFD through a real PDF ToUnicode CMap.
        cmap = (b"/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
                b"/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
                b"/CMapName /OwnFixture def /CMapType 2 def\n1 begincodespacerange\n<00> <FF>\nendcodespacerange\n"
                b"95 beginbfchar\n" + b"\n".join(f"<{n:02X}> <FFFD>".encode() for n in range(32, 127))
                + b"\nendbfchar\nendcmap CMapName currentdict /CMap defineresource pop end end")
        objects[2] = f"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /ToUnicode {len(objects) + 1} 0 R >>".encode()
        objects.append(b"<< /Length " + str(len(cmap)).encode() + b" >>\nstream\n" + cmap + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        out.extend(f"{offset:010} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(out)


def cfb_bytes(streams):
    """Own CFB v3 writer for tiny deterministic fixtures; streams use mini-FAT."""
    free, end, fat_marker = 0xffffffff, 0xfffffffe, 0xfffffffd
    names = [()]
    for path in sorted(streams):
        parts = tuple(path.split("/"))
        for length in range(1, len(parts) + 1):
            if parts[:length] not in names:
                names.append(parts[:length])
    mini, mini_fat, starts = bytearray(), [], {}
    for path in names[1:]:
        payload = streams.get("/".join(path))
        if payload is None:
            continue
        assert len(payload) < 4096
        count = (len(payload) + 63) // 64
        starts[path] = len(mini_fat) if count else end
        for index in range(count):
            mini_fat.append(len(mini_fat) + 1 if index + 1 < count else end)
        mini.extend(payload + b"\0" * (count * 64 - len(payload)))
    directory_count = (len(names) * 128 + 511) // 512
    mini_count = (len(mini) + 511) // 512
    minifat_count = (len(mini_fat) * 4 + 511) // 512
    mini_start, minifat_start = directory_count, directory_count + mini_count
    fat_start = minifat_start + minifat_count
    assert fat_start < 127, "Tiny CFB writer only supports one FAT sector"
    directory = bytearray(directory_count * 512)
    for index, path in enumerate(names):
        payload = streams.get("/".join(path))
        name = (path[-1] if path else "Root Entry").encode("utf-16-le") + b"\0\0"
        offset = index * 128
        directory[offset:offset + len(name)] = name
        children = [i for i, p in enumerate(names) if p and p[:-1] == path]
        siblings = [i for i, p in enumerate(names) if p and path and p[:-1] == path[:-1]]
        right = siblings[siblings.index(index) + 1] if path and siblings.index(index) + 1 < len(siblings) else free
        struct.pack_into("<HBBIII", directory, offset + 64, len(name), 5 if not path else 2 if payload is not None else 1,
                         1, free, right, children[0] if children else free)
        start = mini_start if not path and mini_count else starts.get(path, end)
        size = len(mini) if not path else len(payload) if payload is not None else 0
        struct.pack_into("<IQ", directory, offset + 116, start, size)
    header = bytearray(512)
    header[:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<HHHHH", header, 24, 0x3e, 3, 0xfffe, 9, 6)
    struct.pack_into("<IIIIIIIII", header, 40, 0, 1, 0, 0, 4096,
                     minifat_start if minifat_count else end, minifat_count, end, 0)
    struct.pack_into("<109I", header, 76, fat_start, *([free] * 108))
    fat = [free] * 128
    for start, count in ((0, directory_count), (mini_start, mini_count), (minifat_start, minifat_count)):
        for n in range(count):
            fat[start + n] = start + n + 1 if n + 1 < count else end
    fat[fat_start] = fat_marker
    mini_fat += [free] * (minifat_count * 128 - len(mini_fat))
    return bytes(header + directory + mini + b"\0" * (mini_count * 512 - len(mini))
                 + struct.pack(f"<{len(mini_fat)}I", *mini_fat) + struct.pack("<128I", *fat))


def hwp5_bytes(*, encrypted=False):
    """FX-24 materialization recipe; orchestrator owns committed binary/provenance."""
    from PIL import Image
    picture = BytesIO()
    Image.new("RGB", (200, 200), (80, 120, 160)).save(picture, format="PNG", compress_level=6)
    compressor = zlib.compressobj(level=6, wbits=-15)
    stored = compressor.compress(picture.getvalue()) + compressor.flush()
    header = b"HWP Document File".ljust(32, b"\0") + struct.pack("<II", 0x05000300, 3 if encrypted else 1) + b"\0" * 216
    text = "Own deterministic HWP fixture".encode("utf-16-le")
    records = struct.pack("<I", 67 | (len(text) << 20)) + text
    compressor = zlib.compressobj(level=6, wbits=-15)
    body = compressor.compress(records) + compressor.flush()
    data = cfb_bytes({"FileHeader": header, "DocInfo": b"", "BodyText/Section0": body,
                      "BinData/BIN0001.png": stored, "BinData/BIN0002.wmf": b"own unsupported OLE payload"})
    assert len(data) < 8192
    return data


def docx_bytes(variant="mixed"):
    from docx import Document
    from docx.shared import Inches
    doc = Document()
    doc.core_properties.created = doc.core_properties.modified = __import__("datetime").datetime(2000, 1, 1)
    doc.add_paragraph("Own deterministic fixture text. " * 8)
    first = image_bytes(seed=1)
    if variant == "decor":
        doc.sections[0].header.paragraphs[0].add_run().add_picture(BytesIO(first), width=Inches(2))
        doc.add_picture(BytesIO(image_bytes(size=(8, 8))), width=Inches(.1))
    else:
        doc.add_picture(BytesIO(first), width=Inches(2))
        doc.add_picture(BytesIO(first if variant in {"dup", "twomembers"} else image_bytes(seed=2)), width=Inches(2))
    out = BytesIO()
    doc.save(out)
    with zipfile.ZipFile(BytesIO(out.getvalue())) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    if variant == "twomembers":
        members["word/media/image2.png"] = first
        rel = "word/_rels/document.xml.rels"
        members[rel] = members[rel].replace(b"</Relationships>", b'<Relationship Id="rIdDuplicate" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/></Relationships>')
        # Relate the second occurrence to a distinct member with identical bytes.
        xml = members["word/document.xml"]
        target = b'r:embed="rId9"'
        position = xml.rfind(target)
        assert position >= 0, "Fixture recipe drift: first image relationship"
        members["word/document.xml"] = xml[:position] + xml[position:].replace(target, b'r:embed="rIdDuplicate"', 1)
    if variant == "emf":
        members["word/media/image1.emf"] = b"\x01\x00\x00\x00" + b"\x00" * 36 + b" EMF" + b"\x00" * 44
        del members["word/media/image1.png"]
        rel = "word/_rels/document.xml.rels"
        members[rel] = members[rel].replace(b"image1.png", b"image1.emf")
    if variant == "unref":
        members["word/media/orphan.png"] = image_bytes(seed=3)
    # Low-priority candidates are asserted from the generated golden, never assumed.
    return zip_bytes(sorted(members.items()))


def generate(fx, directory, *, variant="a", pages=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    number = int(fx.split("-")[1])
    ext, data = "bin", None
    if number in {1, 2, 3, 4, 7, 8, 41}:
        ext = "docx" if number == 41 else "pdf"
        kinds = {1: ["text"] * 2, 2: ["image"] * (pages or 3),
                 3: ["text", "image", "text", "image"], 4: ["text"], 7: ["image"] * 1001,
                 8: ["image"], 41: ["text"] * 2}[number]
        data = pdf_bytes(kinds, big=number == 8, suspect=number == 4)
    elif number == 5:
        # Manifest's FX-05b: a bare /Encrypt trailer, deliberately no random AES.
        ext = "pdf"
        data = pdf_bytes(["text"] * 2).replace(b"/Root 1 0 R >>", b"/Root 1 0 R /Encrypt << /Filter /Standard >> >>")
    elif number in {6, 40}:
        ext, data = "pdf", b"%PDF-1.4\n" + random.Random(31).randbytes(64) if number == 6 else b""
    elif number in range(9, 16):
        fmt = {9: "PNG", 10: "JPEG", 11: "TIFF", 12: "GIF", 13: "WEBP", 14: "BMP", 15: "PNG"}[number]
        ext = fmt.lower()
        kwargs = {"exif": b"Exif\x00\x00MM\x00*\x00\x00\x00\x08\x00\x01\x01\x12\x00\x03\x00\x00\x00\x01\x00\x06\x00\x00\x00\x00\x00\x00"} if number == 10 else {}
        data = image_bytes(fmt, frames=3 if number == 11 else 2 if number == 12 else 1, **kwargs)
        if number == 15:
            data = data[:20]
    elif number in {16, 17, 18, 19, 20}:
        ext = "docx"
        data = docx_bytes({16: "mixed", 17: "dup" if variant == "a" else "twomembers",
                           18: "emf", 19: "decor", 20: "unref"}[number])
    elif number == 21:
        from pptx import Presentation
        from pptx.util import Inches
        presentation = Presentation()
        presentation.core_properties.created = presentation.core_properties.modified = __import__("datetime").datetime(2000, 1, 1)
        for seed in (1, 2):
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            slide.shapes.add_picture(BytesIO(image_bytes(seed=seed)), Inches(1), Inches(1))
        out = BytesIO()
        presentation.save(out)
        ext, data = "pptx", normalize_zip(out.getvalue())
    elif number == 22:
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image
        workbook = Workbook()
        workbook.properties.created = workbook.properties.modified = __import__("datetime").datetime(2000, 1, 1)
        workbook.active["A1"] = "Own fixture text"
        workbook.active.add_image(Image(BytesIO(image_bytes())), "B2")
        out = BytesIO()
        workbook.save(out)
        ext, data = "xlsx", normalize_zip(out.getvalue())
    elif number == 23:
        ext, data = "hwpx", zip_bytes([
            ("Contents/content.hpf", '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="section0" href="section0.xml" media-type="application/xml"/><item id="image1" href="../BinData/image1.png" media-type="image/png"/></manifest><spine><itemref idref="section0"/></spine></package>'),
            ("Contents/section0.xml", '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"><hp:p><hp:run><hp:t>Own fixture text</hp:t><hp:pic><hc:img binaryItemIDRef="image1"/></hp:pic></hp:run></hp:p></hs:sec>'),
            ("BinData/image1.png", image_bytes()),
        ])
    elif number == 24:
        if variant == "recipe":
            ext, data = "hwp", hwp5_bytes()
        else:
            path = ROOT / "engine/tests/fixtures/FX-24.hwp"
            assert path.is_file(), f"{fx}: orchestrator must supply own-work CFB fixture and provenance: {path}"
            ext, data = "hwp", path.read_bytes()
    elif number in {25, 27, 34, 35}:
        ext = {25: "docx", 27: "hwp", 34: "xls", 35: "doc"}[number]
        data = hwp5_bytes(encrypted=True) if number == 27 else cfb_bytes(
            {"EncryptionInfo": b"own encryption stub", "EncryptedPackage": b"own package stub"}
            if number == 25 else {"Workbook" if number == 34 else "WordDocument": b"own legacy fixture"})
    elif number in {26, 33, 37, 43, 45, 46, 47, 48, 49}:
        ext = {33: "epub", 37: "odt", 48: "docx"}.get(number, "zip")
        members = [("a.txt", b"own fixture text")]
        if number == 33:
            members = [("META-INF/container.xml", "<container/>")]
        elif number == 37:
            members = [("META-INF/manifest.xml", "<manifest/>")]
        elif number == 43:
            members = [("text.pdf", pdf_bytes(["text"] * 2)), ("text.txt", "Own fixture text"), ("mixed.docx", docx_bytes())]
        elif number == 45:
            nested = zip_bytes(members)
            for _ in range(3):
                nested = zip_bytes([("nested.zip", nested)])
            members = [("nested.zip", nested)]
        elif number == 46:
            members = [("zeros.txt", b"\0" * (11 * 1024**2))]
        elif number in {47, 48}:
            members = [(f"item{i}.txt", b"x") for i in range(1001)]
            if number == 48:
                members[0] = ("word/document.xml", b"<document/>")
        elif number == 49:
            members = [(n, b"own fixture") for n in ("CON.txt", "aux", "COM1.md")]
        data = zip_bytes(members)
        if number == 26:
            patched = bytearray(data)
            for magic, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
                pos = patched.index(magic) + offset
                struct.pack_into("<H", patched, pos, struct.unpack_from("<H", patched, pos)[0] | 1)
            data = bytes(patched)
    else:
        ext, data = {
            28: ("txt", "Own UTF-8 fixture. 한국어\n".encode()),
            29: ("txt", b"\xff\xfe\x00\x80"), 30: ("csv", b"name,value\na,1\n"),
            31: ("html", b'<html><body>Own fixture<img src="x.png"></body></html>'),
            32: ("md", b"# Own fixture\n"),
            36: ("rtf", b"{\\rtf1 Own fixture}"), 38: ("mp3", b"ID3" + random.Random(3).randbytes(64)),
            39: ("xyz", random.Random(4).randbytes(64)), 42: ("txt", b"x" * (2 * 1024**2)),
        }[number]
    suffix = f"-{variant}" if fx == "FX-17" else f"-{pages}p" if pages else ""
    target = directory / f"{fx}{suffix}.{ext}"
    target.write_bytes(data)
    return target


class Cases:
    def __init__(self, directory):
        self.directory = Path(directory)

    def path(self, fx, **kwargs):
        return generate(fx, self.directory, **kwargs)

    def report(self, fx, *, suffix=""):
        path = ROOT / "engine/tests/golden" / fx / f"triage{suffix}.json"
        assert path.is_file(), f"Orchestrator golden pending: tools/golden.py gen ({fx})"
        return json.loads(path.read_text(encoding="utf-8"))

    def sniff(self, fx="FX-03", *, format="pdf", route="NATIVE", issues=(), pages=None):
        # A SniffResult is test-owned data, never a fabricated Core report.
        path = self.path(fx, pages=pages)
        data = path.read_bytes()
        return dict(path=path.name, root=".", bytes=len(data), sha256=digest(data),
                    ext=path.suffix[1:], magic=format, format=format, route=route,
                    reasons=[], issues=[dict(code=c, message="fixture") for c in issues])

    def classification(self, *, ids=("p2", "p4"), low=False):
        return dict(route="NATIVE", need="PARTIAL", label="M", action="convert_and_ocr",
                    decision="review" if low else "ocr_recommended", coverage_state="complete",
                    candidates_unique=[dict(id=identity, kind="page", page=int(identity[1:]),
                        priority="low" if low else "normal", priority_core="low" if low else "high", refs=1)
                        for identity in ids], uninspected_pages=0, reasons=[], issues=[])


def unit(source_id="p2", *, status="eligible", raster=None, media=False, **changes):
    u = dict(kind="media" if media else "page", source_id=source_id,
             page=None if media else int(source_id.lstrip("pf")), status=status,
             raster_sha256=raster or digest(source_id.encode()), dpi=0 if media else 200,
             mime="image/png", bytes=100, priority="normal", priority_core="high")
    if status not in {"eligible", "cached"}:
        u.update(raster_sha256=None, mime=None, bytes=None)
    if media:
        u.update(also=[], media_file="media/0123456789ab.png")
    u.update(changes)
    return u


def provider(**changes):
    p = dict(name="openai-compatible", model="fixture-model", egress=True,
             cost_hint="0.004000", max_batch=1, retries=2,
             destination="https://example.invalid/v1/chat/completions", command_env_names=[], accepts=["image/png", "image/jpeg"])
    p.update(changes)
    return p


def options(**changes):
    o = dict(file=dict(path="reports/q3.pdf", sha256="a" * 64, bytes=1024, format="pdf"),
             classification={k: v for k, v in Cases(".").classification().items()
                             if k in {"route", "need", "label", "action", "decision", "coverage_state"}},
             dpi=200, min_priority="low", max_units=200, approve_threshold=20,
             sensitive=[], prompt_version="p1", proxy=None)
    o.update(changes)
    return o


def entry(u=None, p=None, *, status="ok", text="Own OCR text", **changes):
    u, p = u or unit(), p or provider()
    fields = {k: p[k] for k in ("name", "model", "destination", "egress", "command_env_names")}
    fields["command_env_names"] = sorted(set(fields["command_env_names"]))
    fields["prompt_version"] = "p1"
    key = dict(raster_sha256=u["raster_sha256"], provider_fingerprint=digest(canonical(fields)), dpi=u["dpi"])
    e = dict(v=1, key_id=digest(canonical(key)), key=key, provider=fields,
             unit={k: u[k] for k in ("kind", "dpi", "mime", "bytes")}, status=status,
             text=text if status == "ok" else None,
             error=None if status == "ok" else dict(code="E_PROVIDER_HTTP", message="fixture", exit=None),
             consent=None, tools={"mdflow": "2.0.0", "markitdown-gc": "0.3.5"}, created=NOW, duration_ms=1)
    e.update(changes)
    return e


def assembly_meta(**changes):
    m = dict(source="reports/q3.pdf", sha256="a" * 64, bytes=1024, format="pdf",
             route="NATIVE", need="PARTIAL", label="M", triage_decision="ocr_recommended",
             coverage_state="complete", provider="openai-compatible", model="fixture-model",
             prompt_version="p1", dpi=200, tools={"mdflow": "2.0.0", "markitdown-gc": "0.3.5",
             "pypdfium2": "fixture", "pillow": "fixture"}, now=NOW, pages_total=4,
             frames_total=None, pending_reason="no_provider")
    m.update(changes)
    return m


def approval_plan():
    """One complete, independently constructed SPEC 7.1 input for PURE isolation."""
    u, p = unit(), provider()
    e, o = entry(u, p), options()
    approved_provider = {k: p[k] for k in ("name", "model", "egress", "cost_hint", "max_batch", "retries", "destination", "command_env_names")}
    approved_provider["proxy"] = None
    a = dict(file=o["file"], classification=o["classification"], provider=approved_provider,
             provider_fingerprint=e["key"]["provider_fingerprint"], prompt_version="p1", dpi=200,
             units=[u], units_total=1, keys_unique=1, max_requests=3, est_max_cost="0.012000",
             cost_known=True, approve_threshold=20, threshold_exceeded=False, sensitive_hits=[], oversize=False)
    counts = dict(eligible=1, cached=0, skipped_low_priority=0, oversize=0, render_failed=0, unsupported_media_format=0)
    return dict(v=1, approved=a, status=dict(units=counts, requests_to_send=1, uninspected_pages=0,
                frames_total=None), plan_hash=digest(canonical(a)))
