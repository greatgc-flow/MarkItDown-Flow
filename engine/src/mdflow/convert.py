"""Stage 5: Convert (SPEC 2.5).

``core_convert`` is the ONLY function that touches Core; tests replace ``mdflow.convert.core_convert``
(always called through the module attribute) or, for REQ-CNV-05, install a fake ``markitdown`` package.

* ``core_convert(data, ext, *, extract_media=None, media_base_dir=None) -> str`` builds a ``MarkItDown``
  with plugins disabled and no LLM / Document Intelligence settings (``MarkItDown(enable_plugins=False)``;
  ``markitdown`` is resolved at call time, no module-level singleton), passes ``data`` as a bytes stream
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

from . import write
from .contracts import Issue, SniffResult

_MEDIA_FORMATS = frozenset({"docx", "pptx", "xlsx", "hwp", "hwpx"})
_PAGE_JOIN = "\n\n"
_SAFE_VERSION = re.compile(r"[^0-9A-Za-z._+-]")


class ConvertResult(TypedDict):
    body: str
    pages: list[str] | None
    media: dict[str, str]
    issues: list[Issue]


def core_convert(
    data: bytes, ext: str, *, extract_media: str | None = None, media_base_dir: str | None = None
) -> str:
    import markitdown

    converter = markitdown.MarkItDown(enable_plugins=False)
    options: dict[str, str] = {}
    if extract_media is not None:
        options["extract_media"] = extract_media
    if media_base_dir is not None:
        options["media_base_dir"] = media_base_dir
    result = converter.convert_stream(io.BytesIO(data), file_extension=ext, **options)
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


def _hint(fmt: str) -> str:
    return "." + fmt.lstrip(".")


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


def _cache_paths(cache_dir: str | Path, sha256: str) -> tuple[Path, Path, Path]:
    stem = f"{sha256}-{_core_version()}"
    base = Path(cache_dir) / "base"
    return base / f"{stem}.md", base / f"{stem}.json", base / f"{stem}.media"


def _load_cache(cache_dir: str | Path, sha256: str, run_temp: Path) -> ConvertResult | None:
    body_path, meta_path, media_cache = _cache_paths(cache_dir, sha256)
    try:
        body = body_path.read_text(encoding="utf-8")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pages = meta["pages"]
        names = meta["media"]
        if pages is not None and not (isinstance(pages, list) and all(isinstance(p, str) for p in pages)):
            return None
        if not (isinstance(names, list) and all(isinstance(n, str) and n == os.path.basename(n) for n in names)):
            return None
        media: dict[str, str] = {}
        if names:
            target = run_temp / "media"
            target.mkdir(parents=True, exist_ok=True)
            for name in names:
                shutil.copyfile(media_cache / name, target / name)
                media[name] = str(target / name)
        return {"body": body, "pages": pages, "media": media, "issues": []}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _store_cache(cache_dir: str | Path, sha256: str, result: ConvertResult) -> None:
    body_path, meta_path, media_cache = _cache_paths(cache_dir, sha256)
    try:
        for name, source in result["media"].items():
            write.atomic_write(media_cache / name, Path(source).read_bytes(), dir_mode=0o700)
        meta = {"pages": result["pages"], "media": sorted(result["media"])}
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
    result: ConvertResult = {"body": "", "pages": None, "media": {}, "issues": []}
    if action not in ("convert_only", "convert_and_ocr"):
        return result
    temp = Path(run_temp)
    fmt = sniff["format"]
    if cache_dir is not None:
        cached = _load_cache(cache_dir, sniff["sha256"], temp)
        if cached is not None:
            return cached
    ext = _hint(fmt)
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
            result["body"] = core_convert(data, ext)
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
        _store_cache(cache_dir, sniff["sha256"], result)
    return result
