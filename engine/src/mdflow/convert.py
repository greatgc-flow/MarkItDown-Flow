"""Stage 5: Convert (SPEC 2.5). RED-PHASE STUB.

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

from pathlib import Path
from typing import TypedDict

from .contracts import Issue, SniffResult


class ConvertResult(TypedDict):
    body: str
    pages: list[str] | None
    media: dict[str, str]
    issues: list[Issue]


def core_convert(
    data: bytes, ext: str, *, extract_media: str | None = None, media_base_dir: str | None = None
) -> str:
    raise NotImplementedError("Step 5 green: Core call")


def convert_source(
    data: bytes,
    *,
    sniff: SniffResult,
    action: str,
    run_temp: str | Path,
    cache_dir: str | Path | None = None,
) -> ConvertResult:
    raise NotImplementedError("Step 5 green: convert")
