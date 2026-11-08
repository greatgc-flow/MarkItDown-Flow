"""T-RND-01..08 and T-MAP-06 (TESTPLAN step 5): Render. RED: stubs raise NotImplementedError."""

import io
from pathlib import Path

import pytest

from mdflow import render

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _render(gen, data, fmt, units, directory, **kwargs):
    Path(directory).mkdir(parents=True, exist_ok=True)
    return render.render_units(
        data, sniff=gen.fake_sniff(f"x.{fmt}", data, fmt=fmt), units=units, run_temp=directory, **kwargs)


def _by_id(result):
    return {unit["source_id"]: unit for unit in result["units"]}


def _raster(result, source_id):
    return Path(result["rasters"][source_id]).read_bytes()


def _holds_bytes(value):
    if isinstance(value, (bytes, bytearray)):
        return True
    if isinstance(value, dict):
        return any(_holds_bytes(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_holds_bytes(v) for v in value)
    return False


@pytest.mark.req("REQ-RND-01")
@pytest.mark.cov("S6", "FM12")
@pytest.mark.fx("FX-02")
def test_T_RND_01_pdf_pages_render_to_deterministic_plain_png(gen, run_temp):
    from PIL import Image

    data = gen.pdf_scan(3)
    units = [gen.pre_render_unit(f"p{n}", n) for n in (1, 2, 3)]
    first = _render(gen, data, "pdf", units, run_temp / "a")
    second = _render(gen, data, "pdf", units, run_temp / "b")

    assert [u["status"] for u in first["units"]] == ["eligible"] * 3
    for unit in first["units"]:
        raster = _raster(first, unit["source_id"])
        assert raster == _raster(second, unit["source_id"]), "identical pixels -> identical bytes"
        assert unit["mime"] == "image/png" and unit["dpi"] == 200 and unit["bytes"] == len(raster)
        assert unit["raster_sha256"] == gen.sha256(raster)
        chunks = gen.png_chunks(raster)
        assert chunks[0] == "IHDR" and chunks[-1] == "IEND" and set(chunks) <= {"IHDR", "IDAT", "IEND"}, chunks
        image = Image.open(io.BytesIO(raster))
        assert image.mode == "RGB"
        assert abs(image.size[0] - 100 * 200 / 72) <= 1.5
        fresh = Image.frombytes("RGB", image.size, image.tobytes())
        buffer = io.BytesIO()
        fresh.save(buffer, "PNG", optimize=False, compress_level=6)
        assert buffer.getvalue() == raster, "PNG parameters are optimize=False, compress_level=6"

    high = _render(gen, data, "pdf", [gen.pre_render_unit("p1", 1, dpi=300)], run_temp / "c", dpi=300)
    assert high["units"][0]["dpi"] == 300
    assert abs(Image.open(io.BytesIO(_raster(high, "p1"))).size[0] - 100 * 300 / 72) <= 1.5


@pytest.mark.req("REQ-RND-02")
@pytest.mark.cov("S6", "FM0")
@pytest.mark.fx("FX-09", "FX-11")
def test_T_RND_02_raster_units_frames_and_passthrough(gen, run_temp):
    from PIL import Image

    png, jpeg = gen.png_noise(seed=51), gen.jpeg_noise(seed=52, orientation=6)
    for fmt, data, mime in (("png", png, "image/png"), ("jpeg", jpeg, "image/jpeg")):
        result = _render(gen, data, fmt, [gen.pre_render_unit("image", 1, dpi=0)], run_temp / fmt)
        unit = result["units"][0]
        assert (unit["status"], unit["mime"], unit["dpi"]) == ("eligible", mime, 0), fmt
        assert _raster(result, "image") == data, f"{fmt}: single-frame PNG/JPEG bytes pass through"
        assert result["frames_total"] == 1

    tiff = gen.tiff_frames(3)
    units = [gen.pre_render_unit(f"f{n}", n, dpi=0) for n in (1, 2, 3)]
    result = _render(gen, tiff, "tiff", units, run_temp / "tiff")
    assert result["frames_total"] == 3
    assert [u["source_id"] for u in result["units"]] == ["f1", "f2", "f3"]
    hashes = set()
    for unit in result["units"]:
        raster = _raster(result, unit["source_id"])
        assert raster.startswith(PNG_SIGNATURE) and unit["mime"] == "image/png" and unit["dpi"] == 0
        hashes.add(unit["raster_sha256"])
    assert len(hashes) == 3, "each frame is its own raster"

    pdf = _render(gen, gen.pdf_scan(1), "pdf", [gen.pre_render_unit("p1", 1)], run_temp / "pdf")
    assert pdf["frames_total"] is None, "frames_total is for raster sources only"

    for fmt, data in (("webp", gen.webp_noise()), ("bmp", gen.bmp_noise()), ("gif", gen.gif_noise())):
        result = _render(gen, data, fmt, [gen.pre_render_unit("image", 1, dpi=0)], run_temp / fmt)
        raster = _raster(result, "image")
        assert raster.startswith(PNG_SIGNATURE) and raster != data and result["units"][0]["mime"] == "image/png", fmt

    oriented = gen.webp_noise(40, 20, orientation=6)
    result = _render(gen, oriented, "webp", [gen.pre_render_unit("image", 1, dpi=0)], run_temp / "oriented")
    assert Image.open(io.BytesIO(_raster(result, "image"))).size == (20, 40), "EXIF orientation applied on re-encode"


@pytest.mark.req("REQ-RND-03")
@pytest.mark.cov("S6", "FM4")
@pytest.mark.fx("FX-11", "FX-16", "FX-18")
def test_T_RND_03_media_units_passthrough_reencode_or_unsupported(gen, run_temp):
    png, jpeg = gen.png_noise(seed=71), gen.jpeg_noise(seed=72)
    members = {
        "image1.png": png, "image2.jpg": jpeg, "image3.gif": gen.gif_noise(), "image4.bmp": gen.bmp_noise(),
        "image5.webp": gen.webp_noise(), "image6.tif": gen.tiff_single(), "logo.emf": gen.emf_stub(),
        "vector.svg": b"<svg xmlns='http://www.w3.org/2000/svg'/>",
    }
    data = gen.docx_like(members)
    media_dir = run_temp / "media"
    media_dir.mkdir()
    units = []
    for name, blob in members.items():
        media_file = None
        if name in ("image1.png", "image2.jpg", "image3.gif"):  # present as Core's extract_media output
            filename = gen.h12(blob) + Path(name).suffix
            (media_dir / filename).write_bytes(blob)
            media_file = f"media/{filename}"
        units.append(gen.media_unit(f"word/media/{name}", media_file=media_file))  # others: zip fallback

    result = _render(gen, data, "docx", units, run_temp)
    by_id = _by_id(result)

    assert _raster(result, "word/media/image1.png") == png and by_id["word/media/image1.png"]["mime"] == "image/png"
    assert _raster(result, "word/media/image2.jpg") == jpeg and by_id["word/media/image2.jpg"]["mime"] == "image/jpeg"
    for name in ("image3.gif", "image4.bmp", "image5.webp", "image6.tif"):
        unit = by_id[f"word/media/{name}"]
        raster = _raster(result, unit["source_id"])
        assert unit["status"] == "eligible" and unit["mime"] == "image/png" and raster.startswith(PNG_SIGNATURE), name
        assert raster != members[name]
    for name in ("logo.emf", "vector.svg"):
        unit = by_id[f"word/media/{name}"]
        assert unit["status"] == "unsupported_media_format", name
        assert unit["raster_sha256"] is None and unit["mime"] is None and unit["bytes"] is None, name
        assert unit["source_id"] not in result["rasters"]
    flagged = {i["unit"] for i in result["issues"] if i["code"] == "W_MEDIA_FORMAT"}
    assert flagged == {"word/media/logo.emf", "word/media/vector.svg"}
    assert all(unit["dpi"] == 0 for unit in result["units"])


@pytest.mark.req("REQ-RND-04")
@pytest.mark.cov("S6", "FM1")
@pytest.mark.fx("FX-02")
def test_T_RND_04_one_failing_page_does_not_stop_the_others(gen, run_temp, monkeypatch):
    import pypdfium2 as pdfium

    real = pdfium.PdfPage.render
    state = {"calls": 0}

    def flaky(self, *args, **kwargs):
        state["calls"] += 1
        if state["calls"] == 2:
            raise RuntimeError("injected render failure on page 2")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(pdfium.PdfPage, "render", flaky)
    units = [gen.pre_render_unit(f"p{n}", n) for n in (1, 2, 3)]

    result = _render(gen, gen.pdf_scan(3), "pdf", units, run_temp)

    by_id = _by_id(result)
    assert (by_id["p1"]["status"], by_id["p2"]["status"], by_id["p3"]["status"]) == ("eligible", "render_failed", "eligible")
    assert by_id["p2"]["raster_sha256"] is None and by_id["p2"]["mime"] is None and by_id["p2"]["bytes"] is None
    assert set(result["rasters"]) == {"p1", "p3"}
    failed = [i for i in result["issues"] if i["code"] == "E_RENDER_FAIL"]
    assert [i["unit"] for i in failed] == ["p2"]
    assert state["calls"] == 3, "p3 is still rendered after p2 failed"


@pytest.mark.req("REQ-RND-05")
@pytest.mark.cov("S6", "FM0")
@pytest.mark.fx("FX-02")
def test_T_RND_05_rasters_live_in_run_temp_only_and_are_not_held_in_memory(gen, run_temp, out_dir):
    units = [gen.pre_render_unit(f"p{n}", n) for n in (1, 2, 3, 4)]
    result = _render(gen, gen.pdf_scan(4), "pdf", units, run_temp / "work")

    root = (run_temp / "work").resolve()
    paths = [Path(p).resolve() for p in result["rasters"].values()]
    assert len(paths) == 4 and len(set(paths)) == 4
    assert all(p.is_file() and root in p.parents for p in paths)
    on_disk = {p.resolve() for p in (run_temp / "work").rglob("*") if p.is_file()}
    assert on_disk == set(paths), "exactly one raster file per unit under the run temp dir"
    assert list(out_dir.iterdir()) == [], "never under out_dir"
    assert not _holds_bytes(result), "the result carries paths and hashes, not raster bytes"


@pytest.mark.req("REQ-RND-06")
@pytest.mark.cov("S6", "FM3")
@pytest.mark.fx("FX-08")
def test_T_RND_06_pixel_bound_checked_before_decoding(gen, run_temp):
    from PIL import Image

    result = _render(gen, gen.pdf_bigpage(), "pdf", [gen.pre_render_unit("p1", 1)], run_temp / "big")
    unit = result["units"][0]
    assert unit["status"] == "render_failed" and unit["raster_sha256"] is None
    issue = next(i for i in result["issues"] if i["code"] == "E_RENDER_FAIL")
    assert issue["unit"] == "p1" and "pixel_bound" in issue["message"]
    assert Image.MAX_IMAGE_PIXELS is not None, "Pillow's decompression-bomb check stays enabled"

    medium = gen.pdf_with_page_boxes([(600, 600)])  # 600 pt at 200 dpi is about 2.8 Mpx
    tight = _render(gen, medium, "pdf", [gen.pre_render_unit("p1", 1)], run_temp / "tight", max_pixels=2_000_000)
    assert tight["units"][0]["status"] == "render_failed" and "pixel_bound" in tight["issues"][0]["message"]
    loose = _render(gen, medium, "pdf", [gen.pre_render_unit("p1", 1)], run_temp / "loose", max_pixels=3_000_000)
    assert loose["units"][0]["status"] == "eligible"

    huge = gen.png_huge_1bit()  # 64 Mpx header, a few KiB of data
    refused = _render(gen, huge, "png", [gen.pre_render_unit("image", 1, dpi=0)], run_temp / "huge")
    assert refused["units"][0]["status"] == "render_failed" and "pixel_bound" in refused["issues"][0]["message"]
    allowed = _render(gen, huge, "png", [gen.pre_render_unit("image", 1, dpi=0)], run_temp / "huge-ok", max_pixels=10**8)
    assert allowed["units"][0]["status"] == "eligible"


@pytest.mark.req("REQ-RND-03")
@pytest.mark.cov("S6", "FM11")
@pytest.mark.fx("FX-11", "FX-16")
def test_T_RND_07_animated_media_uses_first_frame_and_warns(gen, run_temp):
    from PIL import Image

    animated = gen.gif_anim(2, size=16)
    data = gen.docx_like({"anim.gif": animated, "still.png": gen.png_noise(seed=75)})
    units = [gen.media_unit("word/media/anim.gif"), gen.media_unit("word/media/still.png")]

    result = _render(gen, data, "docx", units, run_temp)

    by_id = _by_id(result)
    assert by_id["word/media/anim.gif"]["status"] == "eligible" and by_id["word/media/anim.gif"]["mime"] == "image/png"
    assert Image.open(io.BytesIO(_raster(result, "word/media/anim.gif"))).size == (16, 16)
    multiframe = [i for i in result["issues"] if i["code"] == "W_MEDIA_MULTIFRAME"]
    assert [i["unit"] for i in multiframe] == ["word/media/anim.gif"], "only the multi-frame member is flagged"


@pytest.mark.req("REQ-RND-02", "REQ-RND-04")
@pytest.mark.cov("S6", "FM10")
@pytest.mark.fx("FX-15")
def test_T_RND_08_image_probe_failure_is_attempted_then_fails_cleanly(gen, run_temp):
    broken = gen.png_truncated()
    result = _render(gen, broken, "png", [gen.pre_render_unit("image", 1, dpi=0)], run_temp / "broken")
    unit = result["units"][0]
    assert unit["status"] == "render_failed" and unit["raster_sha256"] is None
    assert [i["code"] for i in result["issues"]] == ["E_RENDER_FAIL"] and result["issues"][0]["unit"] == "image"
    assert result["rasters"] == {}

    lenient = gen.png_trailing_garbage()
    result = _render(gen, lenient, "png", [gen.pre_render_unit("image", 1, dpi=0)], run_temp / "lenient")
    assert result["units"][0]["status"] == "eligible", "frame 0 is attempted even when a probe would have failed"
    assert _raster(result, "image") == lenient


@pytest.mark.req("REQ-MAP-06")
@pytest.mark.cov("S6", "FM0")
@pytest.mark.fx("FX-09", "FX-11")
def test_T_MAP_06_raster_hash_is_hash_of_the_bytes_actually_sent(gen, run_temp):
    cases = [
        ("jpeg", gen.jpeg_noise(seed=61, orientation=6), ["image"]),
        ("tiff", gen.tiff_frames(3), ["f1", "f2", "f3"]),
        ("gif", gen.gif_anim(2), ["f1", "f2"]),
    ]
    for fmt, data, ids in cases:
        units = [gen.pre_render_unit(sid, 1 if sid == "image" else int(sid[1:]), dpi=0) for sid in ids]
        result = _render(gen, data, fmt, units, run_temp / fmt)
        seen = set()
        for unit in result["units"]:
            sent = _raster(result, unit["source_id"])
            assert unit["raster_sha256"] == gen.sha256(sent), (fmt, unit["source_id"])
            assert unit["bytes"] == len(sent)
            seen.add(unit["raster_sha256"])
            if fmt == "jpeg":
                assert sent == data and unit["raster_sha256"] == gen.sha256(data)
            else:
                assert unit["raster_sha256"] != gen.sha256(data), "re-encoded frame is hashed, not the source file"
        assert len(seen) == len(ids)
