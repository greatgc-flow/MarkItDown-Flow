"""Deterministic, local OCR triage observations; never performs OCR or conversion."""

import hashlib
import io
import os
import posixpath
import re
import struct
import zipfile
from urllib.parse import unquote, urlsplit
from ._text import strict_text

MAX_BYTES = 256 * 1024**2
MAX_PAGES = 1000
MAX_FRAMES = 100
MAX_IMAGES = 20
_HASH_CHUNK = 1024**2
MAX_ZIP_ENTRIES = 10000
MAX_ZIP_TOTAL_BYTES = 512 * 1024**2
MAX_ZIP_READ_BYTES = 16 * 1024**2
MAX_XML_BYTES = 2 * 1024**2
MAX_MEDIA_READ_BYTES = 64 * 1024**2
MAX_MEDIA_PROBE_BYTES = 64 * 1024
MAX_MEDIA_REFERENCES = 10000
_IMAGE_EXTENSIONS = frozenset(
    "png jpg jpeg jpe jfif gif tif tiff bmp dib webp ico emf emz wmf wmz svg svgz eps wdp hdp pict pct".split()
)


def _report(samples):
    # Verdict first; bounded evidence last. Do not sort these keys at serialization.
    return {
        "decision": "unknown",
        "coverage": {
            "state": "none",
            "pages_total": None,
            "pages_inspected": 0,
            "limits": {"max_bytes": MAX_BYTES, "max_pages": MAX_PAGES},
        },
        "summary": {
            "scope": "inspected",
            "pages_with_text": 0,
            "nonspace_chars": 0,
            "image_occurrences": 0,
            "candidates_high": 0,
            "candidates_low": 0,
        },
        "candidates": [],
        "issues": [],
        "file": {"sha256": None, "bytes": 0, "format": "unknown"},
        "options": {"samples": bool(samples)},
        "schema_version": 1,
        "rules_version": "1",
        "pages": [],
        "rasters": [],
    }


def _issue(report, code, detail):
    report["issues"].append({"code": code, "detail": detail})


def _candidate(report, identity, kind, page, priority, reasons):
    report["candidates"].append(
        {
            "id": identity,
            "kind": kind,
            "page": page,
            "priority": priority,
            "reasons": reasons,
        }
    )
    report["summary"]["candidates_" + priority] += 1


def _format(header):
    if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "hwp"
    if header.startswith(b"%PDF-"):
        return "pdf"
    if header.startswith(
        (
            b"\x89PNG\r\n\x1a\n",
            b"\xff\xd8\xff",
            b"GIF87a",
            b"GIF89a",
            b"II*\0",
            b"MM\0*",
            b"II+\0",
            b"MM\0+",
            b"BM",
        )
    ) or (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
        return "image"
    return "unknown"


class _Borrowed:
    """Libraries may close this view without closing the caller's stream."""

    def __init__(self, stream):
        self.stream = stream

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def close(self):
        pass


def triage(source, *, samples=False):
    """Inspect a local path or seekable binary stream, restoring stream position.

    Failures are recorded as stable issues, without paths or exception messages.
    Optional samples contain at most 120 whitespace-normalized text characters.
    """
    report = _report(samples)
    stream = None
    owned = False
    position = None
    fatal = False
    try:
        if isinstance(source, (str, bytes, os.PathLike)):
            stream = open(source, "rb")
            owned = True
        else:
            stream = source
            position = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        report["file"]["bytes"] = size
        stream.seek(0)
        report["file"]["format"] = _format(stream.read(16))
        if size > MAX_BYTES:
            _issue(
                report, "too_large", "Input exceeds max_bytes; not inspected or hashed."
            )
            fatal = True
        else:
            stream.seek(0)
            digest = hashlib.sha256()
            while chunk := stream.read(_HASH_CHUNK):
                digest.update(chunk)
            report["file"]["sha256"] = digest.hexdigest()
            stream.seek(0)
            if report["file"]["format"] == "pdf":
                fatal = not _pdf(report, _Borrowed(stream), samples)
            elif report["file"]["format"] == "image":
                _image(report, _Borrowed(stream))
            elif report["file"]["format"] == "hwp":
                _hwp(report, stream)
            elif stream.read(4) == b"PK\x03\x04":
                _office(report, stream)
            else:
                extension = (
                    os.path.splitext(os.fsdecode(source))[1].lower() if owned else ""
                )
                handled = False
                if size and extension in {
                    ".md",
                    ".markdown",
                    ".html",
                    ".htm",
                    ".xml",
                    ".rtf",
                }:
                    _issue(
                        report,
                        "media_not_inspected",
                        "Embedded or linked media in this format were not inspected.",
                    )
                    handled = True
                if size and extension in {".txt", ".log"}:
                    stream.seek(0)
                    try:
                        text = strict_text(stream.read())
                    except (UnicodeError, ValueError):
                        text = None
                    if text is not None and not text.lstrip().lower().startswith(
                        ("<", "{\\rtf")
                    ):
                        report["coverage"]["state"] = "not_applicable"
                        report["coverage"][
                            "reason"
                        ] = "Validated plain text has no embedded media to inspect."
                        handled = True
                if not handled:
                    code = "corrupt" if size == 0 else "unsupported_format"
                    _issue(
                        report,
                        code,
                        (
                            "Empty input."
                            if size == 0
                            else "Supported formats: PDF, raster, DOCX, PPTX, XLSX, HWPX."
                        ),
                    )
                    fatal = True
    except Exception:
        _issue(report, "corrupt", "Input could not be read or inspected.")
        fatal = True
    finally:
        if stream is not None:
            try:
                if owned:
                    stream.close()
                elif position is not None:
                    stream.seek(position)
            except Exception:
                _issue(
                    report, "corrupt", "Input stream position could not be restored."
                )
                fatal = True
    if not fatal:
        if report["summary"]["candidates_high"]:
            report["decision"] = "ocr_recommended"
        elif report["summary"]["candidates_low"]:
            report["decision"] = "review"
        elif report["coverage"]["state"] in {"complete", "not_applicable"}:
            report["decision"] = "no_candidates"
    return report


def _clip(box, bounds):
    x0, top, x1, bottom = box
    bx0, btop, bx1, bbottom = bounds
    return (max(x0, bx0), max(top, btop), min(x1, bx1), min(bottom, bbottom))


def _area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def _union_area(boxes):
    """Sweep x slabs and merge y intervals; overlapping placements count once."""
    boxes = [box for box in boxes if _area(box)]
    xs = sorted({x for box in boxes for x in (box[0], box[2])})
    area = 0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((b[1], b[3]) for b in boxes if b[0] < right and b[2] > left)
        end = float("-inf")
        height = 0
        for top, bottom in intervals:
            height += max(0, bottom - max(top, end))
            end = max(end, bottom)
        area += (right - left) * height
    return area


def _names(value):
    from pdfminer.pdftypes import resolve1
    from pdfminer.psparser import PSLiteral

    value = resolve1(value)
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        value = [value]
    return [item.name for item in map(resolve1, value) if isinstance(item, PSLiteral)]


def _bbox(image):
    return (image["x0"], image["top"], image["x1"], image["bottom"])


def _image_row(image, bounds, page_area, skewed=False):
    box = _bbox(image)
    width, height = box[2] - box[0], box[3] - box[1]
    size = image.get("srcsize")
    dpi = None
    if size and width > 0 and height > 0 and not skewed:
        dpi = [round(size[0] * 72 / width, 1), round(size[1] * 72 / height, 1)]
    stream = image.get("stream")
    attrs = stream.attrs if stream is not None else {}
    return {
        "name": image.get("name"),
        "bbox_pt": [round(v, 1) for v in box],
        "px": list(size) if size else None,
        "dpi_xy": dpi,
        "area_ratio": (
            round(_area(_clip(box, bounds)) / page_area, 3) if page_area else 0.0
        ),
        "colorspace": _names(attrs.get("ColorSpace", attrs.get("CS"))),
        "bits": attrs.get("BitsPerComponent", attrs.get("BPC")),
        "imagemask": bool(attrs.get("ImageMask", attrs.get("IM", False))),
        "filter": _names(attrs.get("Filter", attrs.get("F"))),
    }


def _private(text):
    return any(
        0xE000 <= ord(c) <= 0xF8FF
        or 0xF0000 <= ord(c) <= 0xFFFFD
        or 0x100000 <= ord(c) <= 0x10FFFD
        for c in text
    )


def _placement_skews(page):
    """pdfplumber omits placement matrices; retain them from pdfminer's figures.

    The flattened layout order is also the order used by page.images. Right-angle
    rotations remain axis aligned and have meaningful bounding-box DPI.
    """
    from pdfminer.layout import LTFigure, LTImage

    flags = []

    def walk(container, skewed=False):
        if isinstance(container, LTFigure):
            a, b, c, d, _, _ = container.matrix
            skewed = not (
                (abs(b) < 1e-9 and abs(c) < 1e-9) or (abs(a) < 1e-9 and abs(d) < 1e-9)
            )
        if isinstance(container, LTImage):
            flags.append(skewed)
        elif hasattr(container, "__iter__"):
            for child in container:
                walk(child, skewed)

    walk(page.layout)
    return flags


def _page(page, n, samples):
    texts = [char.get("text", "") for char in page.chars]
    cid = [bool(re.fullmatch(r"\(cid:\d+\)", text)) for text in texts]
    replacement = ["\ufffd" in text for text in texts]
    private = [_private(text) for text in texts]
    bad = sum(a or b or c for a, b, c in zip(cid, replacement, private))
    share = bad / len(texts) if texts else 0.0
    # A cid placeholder is one extracted glyph, not seven printable characters.
    nonspace = sum(bool(text.strip()) for text in texts)
    bounds = page.bbox
    page_area = _area(bounds)
    images = page.images
    ratio = (
        _union_area([_clip(_bbox(image), bounds) for image in images]) / page_area
        if page_area
        else 0.0
    )
    vectors = len(page.lines) + len(page.rects) + len(page.curves)
    skews = _placement_skews(page)
    ordered = sorted(
        enumerate(images),
        key=lambda item: (round(item[1]["top"], 1), round(item[1]["x0"], 1)),
    )
    row = {
        "n": n,
        "bbox_pt": [round(v, 1) for v in bounds],
        "rotation": page.rotation,
        "chars": len(texts),
        "nonspace_chars": nonspace,
        "unresolved_glyph_share": round(share, 3),
        "cid_count": sum(cid),
        "replacement_count": sum(replacement),
        "private_use_count": sum(private),
        "vector_objects": vectors,
        "image_area_ratio": round(ratio, 3),
        "image_count": len(images),
        "images_truncated": len(images) > MAX_IMAGES,
        "images": [
            _image_row(
                image, bounds, page_area, skews[index] if index < len(skews) else True
            )
            for index, image in ordered[:MAX_IMAGES]
        ],
    }
    if samples:
        row["text_sample"] = " ".join("".join(texts).split())[:120]
    reasons = []
    high = False
    if nonspace < 30:
        if ratio >= 0.5:
            reasons.append("scan_like")
            high = True
        elif ratio >= 0.1 or vectors >= 50:
            reasons.append("low_text_nonblank")
    elif ratio >= 0.15:
        reasons.append("image_with_text_layer")
    if share > 0.10 and len(texts) >= 5:
        reasons.append("suspect_text_layer")
        high = True
    return row, reasons, "high" if high else "low"


def _pdf(report, stream, samples):
    try:
        import pdfplumber
    except ImportError:
        _issue(
            report,
            "missing_dependency",
            'Install PDF support: pip install "markitdown-gc[pdf]".',
        )
        return False
    try:
        from pdfminer.pdfdocument import PDFPasswordIncorrect

        with pdfplumber.open(stream) as document:
            if document.doc.encryption:
                _issue(report, "encrypted", "Encrypted PDF is not inspected.")
                return False
            total = len(document.pages)
            report["coverage"]["pages_total"] = total
            if total > MAX_PAGES:
                _issue(
                    report, "page_cap", "Only the first max_pages pages were inspected."
                )
            for n, page in enumerate(document.pages[:MAX_PAGES], 1):
                row, reasons, priority = _page(page, n, samples)
                report["pages"].append(row)
                report["coverage"]["pages_inspected"] += 1
                summary = report["summary"]
                summary["pages_with_text"] += bool(row["nonspace_chars"])
                summary["nonspace_chars"] += row["nonspace_chars"]
                summary["image_occurrences"] += row["image_count"]
                if reasons:
                    _candidate(report, f"p{n}", "page", n, priority, reasons)
                page.close()
            report["coverage"]["state"] = "partial" if total > MAX_PAGES else "complete"
        return True
    except PDFPasswordIncorrect:
        _issue(report, "encrypted", "Encrypted PDF is not inspected.")
    except Exception:
        _issue(report, "corrupt", "PDF could not be inspected.")
    report["coverage"]["state"] = "partial" if report["pages"] else "none"
    return False


def _image(report, stream):
    try:
        from PIL import Image

        with Image.open(stream) as image:
            frames = getattr(image, "n_frames", 1)
            for index in range(min(frames, MAX_FRAMES)):
                image.seek(index)
                identity = "image" if frames == 1 else f"f{index + 1}"
                dpi = image.info.get("dpi")
                report["rasters"].append(
                    {
                        "id": identity,
                        "frame": index + 1,
                        "px": list(image.size),
                        "mode": image.mode,
                        "dpi_tag": [round(float(v), 1) for v in dpi] if dpi else None,
                        "exif_orientation": image.getexif().get(274, 1),
                        "bytes": report["file"]["bytes"],
                    }
                )
                _candidate(
                    report, identity, "image", None, "high", ["standalone_image"]
                )
            report["coverage"]["state"] = (
                "partial" if frames > MAX_FRAMES else "complete"
            )
            if frames > MAX_FRAMES:
                _issue(
                    report,
                    "frame_cap",
                    "Only the first max_frames (100) frames were inspected.",
                )
    except Exception:
        # A failed multi-frame probe cannot establish a reliable frame inventory.
        report["rasters"].clear()
        report["rasters"].append(
            {
                "id": "image",
                "frame": None,
                "px": None,
                "mode": None,
                "dpi_tag": None,
                "exif_orientation": None,
                "bytes": report["file"]["bytes"],
            }
        )
        report["candidates"].clear()
        report["summary"]["candidates_high"] = 0
        _candidate(report, "image", "image", None, "high", ["standalone_image"])
        _issue(
            report,
            "image_probe_failed",
            "Image header or frames unavailable; install Pillow or check input.",
        )


class _ZipLimit(Exception):
    pass


def _zip_preflight(stream):
    """Count real directory records before ZipFile allocates a ZipInfo per entry."""
    stream.seek(0, 2)
    end = stream.tell()
    stream.seek(max(0, end - 65557))
    tail = stream.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise zipfile.BadZipFile()
    disk, start_disk, disk_count, count, length, start, comment = struct.unpack_from(
        "<4H2IH", tail, offset + 4
    )
    if disk or start_disk or disk_count != count:
        raise zipfile.BadZipFile()
    # ZIP64 is outside these deliberately small inspection limits.
    if count == 65535 or count > MAX_ZIP_ENTRIES or length > MAX_ZIP_ENTRIES * 1024:
        raise _ZipLimit()
    # ZipFile adjusts offsets for concatenated archives. Require one directory
    # directly before EOCD so preflight and ZipFile inspect identical bytes.
    if start + length != end - len(tail) + offset or offset + 22 + comment != len(tail):
        raise zipfile.BadZipFile()
    stream.seek(start)
    records = total = 0
    while stream.tell() < start + length:
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise zipfile.BadZipFile()
        records += 1
        total += struct.unpack_from("<I", header, 24)[0]
        if records > MAX_ZIP_ENTRIES or total > MAX_ZIP_TOTAL_BYTES:
            raise _ZipLimit()
        name, extra, note = struct.unpack_from("<3H", header, 28)
        stream.seek(name + extra + note, 1)
    if records != count or stream.tell() != start + length:
        raise zipfile.BadZipFile()
    stream.seek(0)


def _target(part, target):
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    resolved = posixpath.normpath(
        path.lstrip("/")
        if path.startswith("/")
        else posixpath.join(posixpath.dirname(part), path)
    )
    if resolved.startswith("../") or "\\" in resolved:
        return None
    return resolved


class _Package:
    def __init__(self, report, archive):
        self.report = report
        self.archive = archive
        self.members = {item.filename: item for item in archive.infolist()}
        if len(self.members) != len(archive.infolist()):
            raise zipfile.BadZipFile()
        self.read_bytes = 0
        self.media_read_bytes = 0

    def issue(self, code, detail):
        self.report["coverage"]["state"] = "partial"
        # Stable bounded diagnostics, without member paths or exception text.
        if not any(i["code"] == code for i in self.report["issues"]):
            _issue(self.report, code, detail)

    def limit(self):
        self.issue(
            "zip_limit", "Package inspection limit reached; evidence is incomplete."
        )

    def read(self, name, cap, *, xml=False):
        member = self.members[name]
        if member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            self.issue(
                "unsupported_compression",
                "Only stored/deflated members can be probed within the decompression budget.",
            )
            return None
        if xml and member.file_size > cap:
            self.limit()
            return None
        remaining = (
            MAX_ZIP_READ_BYTES - self.read_bytes
            if xml
            else MAX_MEDIA_READ_BYTES - self.media_read_bytes
        )
        size = min(member.file_size, cap)
        if size > remaining:
            self.limit()
            return None
        # A failing CRC can occur after decompression, so reserve before reading.
        if xml:
            self.read_bytes += size
        else:
            self.media_read_bytes += size
        try:
            with self.archive.open(member) as source:
                # ZipExtFile otherwise decompresses at least 4 KiB per read.
                # DEFLATE honors this instance-level minimum with max_length;
                # other codecs can decompress without a bound and are refused.
                source.MIN_READ_SIZE = 1
                data = source.read(size)
            return data
        except Exception:
            self.issue("corrupt", "Package member could not be read.")
            return None

    def xml(self, name):
        from defusedxml.ElementTree import fromstring

        data = self.read(name, MAX_XML_BYTES, xml=True)
        if data is not None:
            try:
                return fromstring(data, forbid_dtd=True)
            except Exception:
                self.issue("corrupt", "Package XML could not be inspected.")
        return None


def _office(report, stream):
    limits = report["coverage"]["limits"]
    limits.update(
        max_zip_entries=MAX_ZIP_ENTRIES,
        max_zip_total_bytes=MAX_ZIP_TOTAL_BYTES,
        max_zip_read_bytes=MAX_ZIP_READ_BYTES,
        max_xml_bytes=MAX_XML_BYTES,
        max_media_probe_bytes=MAX_MEDIA_PROBE_BYTES,
        max_media_read_bytes=MAX_MEDIA_READ_BYTES,
        max_media_references=MAX_MEDIA_REFERENCES,
    )
    report["summary"]["media_small"] = 0
    report["media"] = []
    try:
        _zip_preflight(stream)
        with zipfile.ZipFile(stream) as archive:
            package = _Package(report, archive)
            names = package.members
            fmt = next(
                (
                    fmt
                    for fmt, marker in (
                        ("docx", "word/document.xml"),
                        ("pptx", "ppt/presentation.xml"),
                        ("xlsx", "xl/workbook.xml"),
                        ("hwpx", "Contents/content.hpf"),
                    )
                    if marker in names
                ),
                None,
            )
            if fmt is None:
                _issue(
                    report,
                    "unsupported_format",
                    "ZIP is not a supported Office/HWPX package.",
                )
                return
            report["file"]["format"] = fmt
            report["coverage"]["state"] = "complete"
            _package_media(report, package, fmt)
    except _ZipLimit:
        _issue(report, "zip_limit", "Package directory exceeds inspection limits.")
    except Exception:
        report["coverage"]["state"] = "partial" if report["media"] else "none"
        _issue(report, "corrupt", "Package could not be inspected.")


def _package_media(report, package, fmt):
    names = package.members
    root = {"docx": "word/", "pptx": "ppt/", "xlsx": "xl/", "hwpx": "Contents/"}[fmt]
    media_root = "BinData/" if fmt == "hwpx" else root + "media/"
    media_members = {
        name for name in names if name.startswith(media_root) and not name.endswith("/")
    }
    media = {
        name
        for name in media_members
        if posixpath.splitext(name)[1][1:].lower() in _IMAGE_EXTENSIONS
    }
    relationships = {}
    for name in sorted(names):
        if (
            not name.startswith(root)
            or not name.endswith(".rels")
            or "/_rels/" not in name
        ):
            continue
        folder, leaf = name.rsplit("/_rels/", 1)
        part = folder + "/" + leaf[:-5]
        tree = package.xml(name)
        mapping = {}
        if tree is not None:
            for rel in tree:
                rid = rel.get("Id")
                target = rel.get("Target", "")
                external = (
                    rel.get("TargetMode") == "External" or _target(part, target) is None
                )
                image = rel.get("Type", "").endswith("/image")
                if external:
                    if image:
                        package.issue(
                            "external_media",
                            "External image relationship was not fetched.",
                        )
                    continue
                resolved = _target(part, target)
                mapping[rid] = resolved
                if image:
                    if resolved in names:
                        media.add(resolved)
                    else:
                        package.issue(
                            "corrupt", "Image relationship member is missing."
                        )
        relationships[part] = mapping
    slides = {}
    if fmt == "pptx":
        tree = package.xml("ppt/presentation.xml")
        if tree is not None:
            mapping = relationships.get("ppt/presentation.xml", {})
            for element in tree.iter():
                if element.tag.rsplit("}", 1)[-1] == "sldId":
                    rid = next(
                        (v for k, v in element.attrib.items() if k.endswith("}id")),
                        None,
                    )
                    target = mapping.get(rid)
                    if target in names:
                        slides[target] = len(slides) + 1
                    else:
                        package.issue(
                            "corrupt", "Presentation slide relationship is missing."
                        )
    occurrences = []
    hwpx_ids = {}
    if fmt == "hwpx":
        # OWPML sections use binaryItemIDRef; fixture uses the BinData stem.
        for name in sorted(media_members):
            hwpx_ids.setdefault(
                posixpath.splitext(posixpath.basename(name))[0], []
            ).append(name)
        tree = package.xml("Contents/content.hpf")
        if tree is not None:
            for item in tree.iter():
                if item.get("id") and item.get("href"):
                    href = item.get("href")
                    target = (
                        href if href in names else _target("Contents/content.hpf", href)
                    )
                    if target in media_members:
                        hwpx_ids[item.get("id")] = [target]
    parts = sorted(
        (
            n
            for n in names
            if n.startswith(root)
            and n.endswith(".xml")
            and (fmt != "hwpx" or re.fullmatch(r"Contents/section\d+\.xml", n))
        ),
        key=lambda n: (slides.get(n, MAX_ZIP_ENTRIES + 1), n),
    )
    text_namespaces = {
        "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "http://schemas.openxmlformats.org/drawingml/2006/main",
        "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "http://purl.oclc.org/ooxml/wordprocessingml/main",
        "http://purl.oclc.org/ooxml/drawingml/main",
        "http://purl.oclc.org/ooxml/spreadsheetml/main",
        "http://www.hancom.co.kr/hwpml/2011/paragraph",
    }
    text_tags = {"{" + ns + "}t" for ns in text_namespaces}
    for part in parts:
        tree = package.xml(part)
        if tree is None:
            continue
        for element in tree.iter():
            if element.tag in text_tags and (
                fmt != "pptx" or part.startswith("ppt/slides/")
            ):
                report["summary"]["nonspace_chars"] += sum(
                    not char.isspace() for text in element.itertext() for char in text
                )
            for attr, rid in sorted(element.attrib.items()):
                targets = []
                if fmt == "hwpx" and attr.rsplit("}", 1)[-1] == "binaryItemIDRef":
                    targets = hwpx_ids.get(rid, [])
                    if not targets:
                        package.issue(
                            "corrupt", "HWPX image reference member is missing."
                        )
                elif attr.startswith(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
                ) or attr.startswith(
                    "{http://purl.oclc.org/ooxml/officeDocument/relationships}"
                ):
                    target = relationships.get(part, {}).get(rid)
                    if target in media:
                        targets = [target]
                    elif attr.rsplit("}", 1)[-1] == "embed" and target is None:
                        package.issue(
                            "unresolved_embed",
                            "Embedded image relationship is missing.",
                        )
                for target in targets:
                    media.add(target)
                    if len(occurrences) >= MAX_MEDIA_REFERENCES:
                        package.limit()
                        break
                    occurrences.append((target, part, rid))
    referenced = {name for name, _, _ in occurrences}
    # Retain orphaned media too: unavailable references cannot justify decor skipping.
    for name in sorted(media - referenced):
        if len(occurrences) >= MAX_MEDIA_REFERENCES:
            package.limit()
            break
        occurrences.append((name, None, None))

    def decor_part(part):
        return bool(
            part
            and (
                (
                    fmt == "docx"
                    and re.fullmatch(r"word/(header|footer)[^/]*\.xml", part)
                )
                or (
                    fmt == "pptx"
                    and part.startswith(("ppt/slideMasters/", "ppt/slideLayouts/"))
                )
            )
        )

    decor = {name: True for name in referenced}
    for name, part, _ in occurrences:
        decor[name] = decor.get(name, True) and decor_part(part)
    sizes = {}
    for name, part, rid in occurrences:
        ext = posixpath.splitext(name)[1][1:].lower()
        if name not in sizes:
            sizes[name] = None
            if fmt == "hwpx" and ext in ("wmf", "emf", "wmz", "emz"):
                _issue(
                    report,
                    "unsupported_media",
                    "Unsupported embedded image encoding; candidate retained.",
                )
            if ext not in ("emf", "wmf", "svg"):
                data = package.read(name, MAX_MEDIA_PROBE_BYTES)
                if data is not None:
                    try:
                        from PIL import Image

                        with Image.open(io.BytesIO(data)) as image:
                            sizes[name] = list(image.size)
                    except Exception:
                        pass
            if sizes[name] is None:
                # Probe failure does not make known references incomplete.
                if not any(i["code"] == "image_probe_failed" for i in report["issues"]):
                    _issue(
                        report,
                        "image_probe_failed",
                        "Embedded image dimensions unavailable; candidate retained.",
                    )
    for name, part, rid in occurrences:
        ext = posixpath.splitext(name)[1][1:].lower()
        px = sizes[name]
        # Incomplete reference inspection cannot prove exclusive decor use.
        decorative = (
            decor.get(name, False) and report["coverage"]["state"] == "complete"
        )
        report["media"].append(
            {
                "id": name,
                "where": {"slide": slides[part]} if part in slides else None,
                "px": px,
                "bytes": names[name].file_size,
                "ext": ext,
                "decor": bool(decorative),
                "references": [{"part": part, "id": rid}] if part else [],
            }
        )
        report["summary"]["image_occurrences"] += 1
        small = px is not None and (min(px) < 24 or px[0] * px[1] < 15000)
        if small:
            report["summary"]["media_small"] += 1
        if decorative:
            _candidate(report, name, "image", None, "low", ["decor_media"])
            report["candidates"][-1]["decor"] = True
        elif not small:
            scan_like = report["summary"]["nonspace_chars"] < 30
            _candidate(
                report,
                name,
                "image",
                None,
                "high" if scan_like else "low",
                ["embedded_image", "scan_like"] if scan_like else ["embedded_image"],
            )


def _hwp(report, stream):
    from ._hwp_media import hwp_reader, hwp_images

    report["summary"]["media_small"] = 0
    report["media"] = []
    stream.seek(0)
    data = stream.read(MAX_BYTES + 1)
    try:
        with hwp_reader(data, ".hwp") as reader:
            rows = hwp_images(data, ".hwp", reader)
    except ImportError:
        _issue(
            report,
            "missing_dependency",
            "Install markitdown-gc[hwp] for HWP5 media inspection.",
        )
        return
    except Exception:
        _issue(report, "corrupt", "HWP5 media could not be inspected.")
        return
    stored = {}
    try:
        import olefile

        with olefile.OleFileIO(io.BytesIO(data)) as ole:
            for path in ole.listdir():
                if len(path) == 2 and path[0] == "BinData":
                    payload = ole.openstream(path).read()
                    stored["/".join(path)] = (
                        len(payload),
                        hashlib.sha256(payload).hexdigest(),
                    )
    except (OSError, ValueError):
        pass
    report["coverage"]["state"] = "complete"
    spent = 0
    for name, payload, ext, supported in rows[:MAX_MEDIA_REFERENCES]:
        spent += len(payload)
        px = None
        if spent <= MAX_MEDIA_READ_BYTES and supported:
            try:
                from PIL import Image

                with Image.open(io.BytesIO(payload[:MAX_MEDIA_PROBE_BYTES])) as image:
                    px = list(image.size)
            except Exception:
                pass
        if not supported or ext in ("wmf", "emf", "wmz", "emz"):
            _issue(
                report,
                "unsupported_media",
                "Unsupported HWP5 image encoding; candidate retained.",
            )
        report["media"].append(
            {
                "id": name,
                "where": None,
                "px": px,
                "bytes": len(payload),
                "ext": ext,
                "decor": False,
                "references": [],
                "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "payload_kind": (
                    "parser_image_payload" if supported else "stored_ole_stream"
                ),
                "stored_bytes": stored.get(name, (None, None))[0],
                "stored_sha256": stored.get(name, (None, None))[1],
            }
        )
        report["summary"]["image_occurrences"] += 1
        small = px is not None and (min(px) < 24 or px[0] * px[1] < 15000)
        if small:
            report["summary"]["media_small"] += 1
        else:
            _candidate(report, name, "image", None, "low", ["embedded_image"])
            report["candidates"][-1]["decor"] = False
    if len(rows) > MAX_MEDIA_REFERENCES or spent > MAX_MEDIA_READ_BYTES:
        report["coverage"]["state"] = "partial"
        _issue(report, "zip_limit", "HWP5 media observation limit reached.")
