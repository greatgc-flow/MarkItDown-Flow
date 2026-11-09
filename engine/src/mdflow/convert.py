"""Stage 5: Convert (SPEC 2.5).

``core_convert`` is the ONLY function that touches Core; tests replace ``mdflow.convert.core_convert``
(always called through the module attribute) or, for REQ-CNV-05, install a fake ``markitdown`` package.

* ``core_convert(data, ext, *, extract_media=None, media_base_dir=None, exiftool_path="") -> str`` builds a
  ``MarkItDown`` with plugins disabled and no LLM / Document Intelligence settings of any kind (R29;
  ``MarkItDown(enable_plugins=False, exiftool_path=...)`` is the complete argument set; ``markitdown`` is resolved at
  call time, no module-level singleton). ``exiftool_path`` is the empty string unless ``mdflow.exiftool`` found a usable
  tool for a standalone image (R31, REQ-CNV-06); a tool that fails falls back to a plain conversion. It passes ``data`` as a bytes stream
  with ``ext`` (``".pdf"``-style hint; never a path or URI) to ``convert_stream`` and returns Markdown text.
* ``convert_source(data, *, sniff, action, run_temp, cache_dir=None) -> ConvertResult``
  - ``action`` not in ``convert_only|convert_and_ocr``: no Core call, empty result.
  - PDF: per page ``N`` a one-page PDF (pypdfium2) is converted; ``pages`` holds one string per page.
  - ``docx|pptx|xlsx|hwp|hwpx``: ``extract_media=str(run_temp/'media')``, ``media_base_dir=str(run_temp)``.
  - any Core exception -> ``E_CONVERT_FAIL`` issue, ``body == ""``, never raises.
  - ``media`` maps file name (e.g. ``3f9a1c2b7d10.png``) -> absolute path under ``run_temp/media``.
  - ``cache_dir``: base body + media cached at ``<cache>/base/<sha256>-<core_version>.md`` / ``.media/``.
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
from pathlib import Path
from typing import TypedDict

from . import core_guard, exiftool, write
from .contracts import Issue, SniffResult

_MEDIA_FORMATS = frozenset({"docx", "pptx", "xlsx", "hwp", "hwpx"})
_PAGE_JOIN = "\n\n"
_SAFE_VERSION = re.compile(r"[^0-9A-Za-z._+-]")


class _ConvertBase(TypedDict):
    body: str
    pages: list[str] | None
    media: dict[str, str]
    issues: list[Issue]


class ConvertResult(_ConvertBase, total=False):
    tools: dict[str, str]  # extra tools that shaped the body, e.g. {"exiftool": "13.59"} (REQ-CNV-06)


def core_convert(
    data: bytes, ext: str, *, extract_media: str | None = None, media_base_dir: str | None = None,
    exiftool_path: str = "",
) -> str:
    core_guard.check()
    import markitdown

    # R29: the only Core options are plugins off and the exiftool path ("" = none; it also stops Core's own probing).
    converter = markitdown.MarkItDown(enable_plugins=False, exiftool_path=exiftool_path)
    options: dict[str, str] = {}
    if extract_media is not None:
        options["extract_media"] = extract_media
    if media_base_dir is not None:
        options["media_base_dir"] = media_base_dir
    try:
        result = converter.convert_stream(io.BytesIO(data), file_extension=ext, **options)
    except Exception as exc:
        # Core has no base converter for several supported OCR raster formats.
        # Only its explicit format refusal is a clean empty base; real conversion
        # faults still propagate to E_CONVERT_FAIL, and Render validates the bytes.
        if ext in {'.gif', '.tiff', '.bmp', '.webp'} and isinstance(
                exc, getattr(markitdown, 'UnsupportedFormatException', ())):
            return ''
        raise
    text = getattr(result, "markdown", None)
    if text is None:
        text = getattr(result, "text_content", "")
    return text or ""


def _core_version() -> str:
    try:
        from importlib import metadata

        return _SAFE_VERSION.sub("_", metadata.version("markitdown-gc"))
    except Exception:
        return "unknown"


_CORE_HINTS = {"log": ".txt"}  # Core's plain-text converter has no ".log" (R30: every .log failed E_CONVERT_FAIL)


def _hint(fmt: str) -> str:
    return _CORE_HINTS.get(fmt) or "." + fmt.lstrip(".")


def _convert_with_exiftool(data: bytes, ext: str, found: dict | None) -> tuple[str, dict[str, str]]:
    """One Core call; images use exiftool when available, and fall back to a plain conversion if it misbehaves."""
    if found is not None:
        try:
            return core_convert(data, ext, exiftool_path=found["path"]), {"exiftool": found["version"]}
        except Exception:
            pass  # exiftool is optional enrichment: a tool failing on this file never fails the conversion
    return core_convert(data, ext), {}


def _pdf_pages(data: bytes, ext: str, issues: list[Issue]) -> list[str]:
    """Convert a PDF one page at a time; a page that Core cannot read stays empty."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        total = len(document)
        pages: list[str] = []
        failed = False
        for index in range(total):
            single = pdfium.PdfDocument.new()
            try:
                single.import_pages(document, [index])
                buffer = io.BytesIO()
                single.save(buffer)
            finally:
                single.close()
            try:
                pages.append(core_convert(buffer.getvalue(), ext))
            except Exception as exc:
                failed = True
                pages.append("")
                if not issues:
                    issues.append({"code": "E_CONVERT_FAIL", "message": f"Core conversion failed ({type(exc).__name__})"})
        if failed:
            return ["" for _ in pages]
        return pages
    finally:
        document.close()


def _collect_media(media_dir: Path) -> dict[str, str]:
    if not media_dir.is_dir():
        return {}
    return {entry.name: str(entry) for entry in sorted(media_dir.iterdir(), key=lambda p: p.name) if entry.is_file()}


def _cache_paths(cache_dir: str | Path, sha256: str, variant: str = "") -> tuple[Path, Path, Path]:
    # ``variant`` (e.g. the exiftool version for images) keeps entries made with different helper tools apart.
    stem = f"{sha256}-{_core_version()}" + (f"+{_SAFE_VERSION.sub('_', variant)}" if variant else "")
    base = Path(cache_dir) / "base"
    return base / f"{stem}.md", base / f"{stem}.json", base / f"{stem}.media"


def _load_cache(cache_dir: str | Path, sha256: str, run_temp: Path, variant: str = "") -> ConvertResult | None:
    body_path, meta_path, media_cache = _cache_paths(cache_dir, sha256, variant)
    try:
        body = body_path.read_text(encoding="utf-8")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pages = meta["pages"]
        names = meta["media"]
        tools = meta.get("tools", {})
        if pages is not None and not (isinstance(pages, list) and all(isinstance(p, str) for p in pages)):
            return None
        if not (isinstance(names, list) and all(isinstance(n, str) and n == os.path.basename(n) for n in names)):
            return None
        if not (isinstance(tools, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in tools.items())):
            return None
        media: dict[str, str] = {}
        if names:
            target = run_temp / "media"
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                shutil.copyfile(media_cache / name, target / name)
                media[name] = str(target / name)
        cached: ConvertResult = {"body": body, "pages": pages, "media": media, "issues": []}
        if tools:
            cached["tools"] = dict(tools)
        return cached
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _store_cache(cache_dir: str | Path, sha256: str, result: ConvertResult, variant: str = "") -> None:
    body_path, meta_path, media_cache = _cache_paths(cache_dir, sha256, variant)
    try:
        for name, source in result["media"].items():
            write.atomic_write(media_cache / name, Path(source).read_bytes(), dir_mode=0o700)
        meta = {"pages": result["pages"], "media": sorted(result["media"])}
        if result.get("tools"):
            meta["tools"] = result["tools"]
        write.atomic_write(meta_path, json.dumps(meta, ensure_ascii=False).encode("utf-8"), dir_mode=0o700)
        write.atomic_write(body_path, result["body"].encode("utf-8"), dir_mode=0o700)
    except OSError:
        pass  # the cache is an optimisation (SHOULD); a failed write never fails the file


def convert_source(
    data: bytes,
    *,
    sniff: SniffResult,
    action: str,
    run_temp: str | Path,
    cache_dir: str | Path | None = None,
) -> ConvertResult:
    core_guard.check()
    result: ConvertResult = {"body": "", "pages": None, "media": {}, "issues": []}
    if action not in ("convert_only", "convert_and_ocr"):
        return result
    temp = Path(run_temp)
    fmt = sniff["format"]
    ext = _hint(fmt)
    found = exiftool.for_extension(ext)  # None for everything but standalone images (R31)
    variant = "exiftool" + found["version"] if found else ""
    if cache_dir is not None:
        cached = _load_cache(cache_dir, sniff["sha256"], temp, variant)
        if cached is not None:
            return cached
    try:
        if fmt == "pdf":
            pages = _pdf_pages(data, ext, result["issues"])
            result["pages"] = pages
            result["body"] = _PAGE_JOIN.join(pages)
        elif fmt in _MEDIA_FORMATS:
            media_dir = temp / "media"
            result["body"] = core_convert(data, ext, extract_media=str(media_dir), media_base_dir=str(temp))
            result["media"] = _collect_media(media_dir)
        else:
            result["body"], used = _convert_with_exiftool(data, ext, found)
            if used:
                result["tools"] = used
    except Exception as exc:
        result = {
            "body": "", "pages": None, "media": {},
            "issues": [{"code": "E_CONVERT_FAIL", "message": f"Core conversion failed ({type(exc).__name__})"}],
        }
    if result["issues"]:
        # a failed conversion yields an empty body; page structure is kept so anchors stay complete
        result["body"] = ""
        return result
    if cache_dir is not None:
        # a fallback conversion (exiftool failed on this file) is cached under the plain key, never the tool's
        _store_cache(cache_dir, sniff["sha256"], result, variant if result.get("tools") else "")
    return result
