"""Stage 6: Render (SPEC 2.6, REQ-MAP-06). RED-PHASE STUB.

``render_units(data, *, sniff, units, run_temp, dpi=200, max_pixels=50_000_000) -> RenderResult``

* ``units`` come from Select (status ``eligible``, raster fields still ``None``). Returned units carry
  the updated ``status`` (``eligible|render_failed|unsupported_media_format``), ``raster_sha256``,
  ``mime``, ``bytes`` and ``dpi`` (page dpi for PDF, 0 for rasters/media).
* ``rasters`` maps ``source_id`` -> path of the raster file inside ``run_temp``; the result never holds
  raster bytes (at most one raster resident at a time, REQ-RND-05).
* PDF pages use ``pypdfium2.PdfPage.render`` + Pillow PNG (``optimize=False, compress_level=6``).
* Standalone rasters: candidate ``image`` -> page 1, ``fN`` -> frame ``N-1``; single-frame PNG/JPEG
  pass through byte for byte; ``frames_total`` is Pillow's ``n_frames`` (None for non-raster sources).
* Media units read ``<run_temp>/<unit.media_file>`` when set, else the zip member ``source_id`` of
  ``data`` (streamed, bounded); PNG/JPEG pass through, other Pillow formats become PNG (frame 0).
* Issues are ``{"code", "message", "unit"}`` dicts: ``E_RENDER_FAIL`` (message ``pixel_bound`` for the
  pixel bound), ``W_MEDIA_FORMAT``, ``W_MEDIA_MULTIFRAME``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, TypedDict

from .contracts import SniffResult, Unit


class RenderResult(TypedDict):
    units: list[Unit]
    rasters: dict[str, str]
    frames_total: int | None
    issues: list[dict]


def render_units(
    data: bytes,
    *,
    sniff: SniffResult,
    units: Sequence[Unit],
    run_temp: str | Path,
    dpi: int = 200,
    max_pixels: int = 50_000_000,
) -> RenderResult:
    raise NotImplementedError("Step 5 green: render")
