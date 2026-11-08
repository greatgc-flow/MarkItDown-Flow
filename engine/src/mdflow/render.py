"""Stage 6: Render (SPEC 2.6, REQ-MAP-06).

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

import hashlib
import io
import os
import re
from pathlib import Path
from typing import Sequence, TypedDict

from . import sniff_io
from .contracts import SniffResult, Unit

_RASTER_FORMATS = frozenset({"png", "jpeg", "gif", "bmp", "tiff", "webp"})
_MEDIA_PILLOW_FORMATS = frozenset({"PNG", "JPEG", "GIF", "BMP", "TIFF", "WEBP", "MPO"})
_PASSTHROUGH = {"PNG": ("image/png", "png"), "JPEG": ("image/jpeg", "jpg")}
_FRAME_ID = re.compile(r"^f([0-9]+)$")


class RenderResult(TypedDict):
    units: list[Unit]
    rasters: dict[str, str]
    frames_total: int | None
    issues: list[dict]


class _Failure(Exception):
    """A unit that cannot be rendered; ``message`` is safe for diagnostics."""

    def __init__(self, message: str, *, unsupported: bool = False, code: str = 'E_RENDER_FAIL') -> None:
        super().__init__(message)
        self.unsupported = unsupported
        self.code = code


def _png_bytes(image) -> bytes:
    from PIL import Image

    if image.mode not in ("RGB",):
        if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=False, compress_level=6, pnginfo=None)
    return buffer.getvalue()


def _raster_path(run_temp: Path, source_id: str, suffix: str) -> Path:
    return run_temp / (hashlib.sha256(source_id.encode("utf-8", "replace")).hexdigest()[:16] + "." + suffix)


def _store(run_temp: Path, source_id: str, payload: bytes, mime: str, suffix: str) -> tuple[Path, dict]:
    path = _raster_path(run_temp, source_id, suffix)
    path.write_bytes(payload)
    return path, {
        "status": "eligible", "raster_sha256": hashlib.sha256(payload).hexdigest(), "mime": mime, "bytes": len(payload),
    }


def _check_pixels(width: int, height: int, max_pixels: int) -> None:
    if width * height > max_pixels:
        raise _Failure("pixel_bound")


def _render_pdf_page(document, unit: Unit, dpi: int, max_pixels: int) -> bytes:
    number = unit["page"]
    if not isinstance(number, int) or number < 1 or number > len(document):
        raise _Failure("page out of range")
    page = document[number - 1]
    try:
        width, height = page.get_size()
        scale = dpi / 72
        _check_pixels(int(round(width * scale)), int(round(height * scale)), max_pixels)
        bitmap = page.render(scale=scale)
        try:
            return _png_bytes(bitmap.to_pil())
        finally:
            if hasattr(bitmap, "close"):
                bitmap.close()
    finally:
        page.close()


def _frame_index(unit: Unit) -> int:
    match = _FRAME_ID.match(unit["source_id"])
    if match:
        return max(0, int(match.group(1)) - 1)
    page = unit.get("page")
    return max(0, (page or 1) - 1)


def _render_raster_frame(data: bytes, unit: Unit, max_pixels: int) -> tuple[bytes, str, str]:
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(data)) as image:
            _check_pixels(image.width, image.height, max_pixels)
            frames = getattr(image, "n_frames", 1)
            index = _frame_index(unit)
            if image.format in _PASSTHROUGH and frames == 1 and index == 0:
                image.verify()
                mime, suffix = _PASSTHROUGH[image.format]
                return data, mime, suffix
            if index >= frames:
                raise _Failure("frame out of range")
            image.seek(index)
            _check_pixels(image.width, image.height, max_pixels)
            image.load()
            return _png_bytes(ImageOps.exif_transpose(image)), "image/png", "png"
    except _Failure:
        raise
    except Image.DecompressionBombError:
        raise _Failure("pixel_bound") from None
    except Exception as exc:
        raise _Failure(f"image could not be decoded ({type(exc).__name__})") from None


def _frame_count(data: bytes) -> int:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as image:
            return max(1, int(getattr(image, "n_frames", 1)))
    except Exception:
        return 1


def _render_media(
    data: bytes, unit: Unit, run_temp: Path, max_pixels: int, issues: list[dict],
    *, format: str, max_bytes: int, remaining: list[int],
) -> tuple[bytes, str, str]:
    from PIL import Image, ImageOps

    media_file = unit.get("media_file")
    if format == 'hwp' and (unit.get('_payload_kind', unit.get('payload_kind')) == 'stored_ole_stream' or not media_file):
        raise _Failure('HWP5 media is an unsupported stored stream or was not extracted', unsupported=True)
    try:
        if media_file:
            candidate = (run_temp / media_file)
            declared = candidate.stat().st_size
            collected = bytearray()
            with candidate.open('rb') as stream:
                while chunk := stream.read(65536):
                    collected.extend(chunk)
                    sniff_io._check_limits(len(collected), declared, max_bytes, remaining[0])
            raw = bytes(collected)
        else:
            try:
                raw = sniff_io.read_member_bytes(data, unit["source_id"], max_bytes=max_bytes,
                                                 total_remaining=remaining[0])
            except KeyError:
                raise _Failure("media member is not present", unsupported=True) from None
            except sniff_io.ZipReadError as exc:
                if exc.code == "E_CORRUPT":
                    raise _Failure("media member is not readable", unsupported=True) from None
                raise _Failure(f"media member is unreadable ({exc.code})", code=exc.code) from None
        remaining[0] -= len(raw)
    except sniff_io.ZipReadError as exc:
        raise _Failure('media exceeds a source byte bound', code=exc.code) from None
    except OSError as exc:
        raise _Failure(f"media file could not be read ({type(exc).__name__})", unsupported=True) from None
    try:
        image = Image.open(io.BytesIO(raw))
    except Exception:
        raise _Failure("format is not rasterisable", unsupported=True) from None
    with image:
        if image.format not in _MEDIA_PILLOW_FORMATS:
            raise _Failure("format is not rasterisable", unsupported=True)
        _check_pixels(image.width, image.height, max_pixels)
        frames = getattr(image, "n_frames", 1)
        if image.format in _PASSTHROUGH:
            mime, suffix = _PASSTHROUGH[image.format]
            return raw, mime, suffix
        try:
            image.load()
            payload = _png_bytes(ImageOps.exif_transpose(image))
        except Exception as exc:
            raise _Failure(f"image could not be decoded ({type(exc).__name__})") from None
        if frames > 1:
            issues.append({
                "code": "W_MEDIA_MULTIFRAME", "unit": unit["source_id"],
                "message": f"media has {frames} frames; the first frame is used",
            })
        return payload, "image/png", "png"


def render_units(
    data: bytes,
    *,
    sniff: SniffResult,
    units: Sequence[Unit],
    run_temp: str | Path,
    dpi: int = 200,
    max_pixels: int = 50_000_000,
    max_bytes: int = sniff_io.DEFAULT_MAX_BYTES,
    total_remaining: int | None = None,
) -> RenderResult:
    temp = Path(run_temp)
    temp.mkdir(parents=True, exist_ok=True)
    fmt = sniff["format"]
    remaining = [sniff_io.DEFAULT_ZIP_TOTAL_BYTES if total_remaining is None else total_remaining]
    result: RenderResult = {"units": [], "rasters": {}, "frames_total": None, "issues": []}
    if fmt in _RASTER_FORMATS:
        result["frames_total"] = _frame_count(data)
    document = None
    document_error: str | None = None
    if fmt == "pdf":
        try:
            import pypdfium2 as pdfium

            document = pdfium.PdfDocument(data)
        except Exception as exc:
            document_error = f"PDF could not be opened ({type(exc).__name__})"
    try:
        for unit in units:
            updated: Unit = dict(unit)  # type: ignore[assignment]
            source_id = unit["source_id"]
            try:
                if unit["kind"] == "media":
                    payload, mime, suffix = _render_media(data, unit, temp, max_pixels, result["issues"],
                        format=fmt, max_bytes=max_bytes, remaining=remaining)
                    updated["dpi"] = 0
                elif fmt == "pdf":
                    if document is None:
                        raise _Failure(document_error or "PDF could not be opened")
                    payload, mime, suffix = _render_pdf_page(document, unit, dpi, max_pixels), "image/png", "png"
                    updated["dpi"] = dpi
                elif fmt in _RASTER_FORMATS:
                    payload, mime, suffix = _render_raster_frame(data, unit, max_pixels)
                    updated["dpi"] = 0
                else:
                    raise _Failure("source format has no renderable units")
                path, fields = _store(temp, source_id, payload, mime, suffix)
                del payload
                updated.update(fields)  # type: ignore[typeddict-item]
                result["rasters"][source_id] = str(path)
            except _Failure as failure:
                updated["raster_sha256"] = None
                updated["mime"] = None
                updated["bytes"] = None
                if unit["kind"] == "media":
                    updated["dpi"] = 0
                if failure.unsupported:
                    updated["status"] = "unsupported_media_format"
                    result["issues"].append({"code": "W_MEDIA_FORMAT", "unit": source_id, "message": str(failure)})
                else:
                    updated["status"] = "render_failed"
                    result["issues"].append({"code": failure.code, "unit": source_id, "message": str(failure)})
            except Exception as exc:
                updated["raster_sha256"] = None
                updated["mime"] = None
                updated["bytes"] = None
                updated["status"] = "render_failed"
                message = f"render failed ({type(exc).__name__})"
                result["issues"].append({"code": "E_RENDER_FAIL", "unit": source_id, "message": message})
            result["units"].append(updated)
    finally:
        if document is not None:
            try:
                document.close()
            except Exception:
                pass
    return result
