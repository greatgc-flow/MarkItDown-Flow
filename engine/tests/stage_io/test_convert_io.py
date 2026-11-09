"""T-CNV-01..05 (TESTPLAN step 5): Convert. RED: stubs raise NotImplementedError.

Core is replaced by ``core_spy`` (the ``mdflow.convert.core_convert`` seam) except in T-CNV-05, which
installs a fake ``markitdown`` package to inspect how the real seam builds and calls Core.
"""

import inspect
import io
import os
import zipfile
from pathlib import Path

import pytest

from mdflow import convert, write

MEDIA_ZIP_FORMATS = {"docx", "pptx", "xlsx", "hwp", "hwpx"}


def _extract_media_behavior(spy, index, data, ext, extract_media, media_base_dir):
    """Imitates Core's extract_media: writes <sha256[:12]>.<ext> files and links them relative to the base dir."""
    import hashlib

    lines = ["# Title"]
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            if "/media/" in name or name.startswith("BinData/"):
                member = archive.read(name)
                filename = hashlib.sha256(member).hexdigest()[:12] + os.path.splitext(name)[1]
                os.makedirs(extract_media, exist_ok=True)
                with open(os.path.join(extract_media, filename), "wb") as handle:
                    handle.write(member)
                lines.append(f"![alt](media/{filename})")
    return "\n\n".join(lines)


@pytest.mark.req("REQ-CNV-01")
@pytest.mark.cov("S5", "FM1")
@pytest.mark.fx("FX-03")
def test_T_CNV_01_core_exception_gives_empty_body_not_a_crash(tmp_path, gen, core_spy, run_temp):
    def explode(*args):
        raise RuntimeError(f"core exploded on {tmp_path}")

    core_spy.behavior = explode
    for fmt, data in (("docx", gen.docx_like()), ("pdf", gen.pdf_mixed())):
        result = convert.convert_source(
            data, sniff=gen.fake_sniff(f"x.{fmt}", data, fmt=fmt), action="convert_and_ocr", run_temp=run_temp)
        assert [i["code"] for i in result["issues"]] == ["E_CONVERT_FAIL"], fmt
        assert result["body"] == "", fmt
        assert all(page == "" for page in (result["pages"] or [])), fmt
        assert str(tmp_path) not in result["issues"][0]["message"], "no absolute path in the diagnostic"
    assert len(core_spy.calls) >= 2


@pytest.mark.req("REQ-CNV-02")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-03")
def test_T_CNV_02_pdf_is_converted_one_page_at_a_time(gen, core_spy, run_temp):
    core_spy.behavior = lambda spy, index, *rest: f"page-{index + 1}"
    data = gen.pdf_text(3)

    result = convert.convert_source(
        data, sniff=gen.fake_sniff("x.pdf", data, fmt="pdf"), action="convert_and_ocr", run_temp=run_temp)

    assert len(core_spy.calls) == 3, "one Core call per page"
    assert result["pages"] == ["page-1", "page-2", "page-3"]
    assert result["issues"] == []
    import pypdfium2 as pdfium

    for number, call in enumerate(core_spy.calls, start=1):
        assert str(call["ext"]).lstrip(".") == "pdf" and call["extract_media"] is None
        document = pdfium.PdfDocument(call["data"])
        try:
            assert len(document) == 1, "Core receives a one-page PDF"
            assert gen.page_text(number) in document[0].get_textpage().get_text_range()
        finally:
            document.close()

    skipped = convert.convert_source(
        data, sniff=gen.fake_sniff("x.pdf", data, fmt="pdf"), action="report_only", run_temp=run_temp)
    assert len(core_spy.calls) == 3, "report_only never reaches Core"
    assert skipped["body"] == "" and skipped["issues"] == []


@pytest.mark.req("REQ-CNV-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-16", "FX-21", "FX-23", "FX-24")
def test_T_CNV_03_media_published_before_markdown_and_not_rewritten(tmp_path, gen, core_spy, run_temp, out_dir, monkeypatch):
    core_spy.behavior = _extract_media_behavior
    first, second = gen.png_noise(seed=31), gen.jpeg_noise(seed=32)
    packages = {
        "docx": gen.docx_like({"image1.png": first, "image2.jpg": second}),
        "pptx": gen.pptx_like({"image1.png": first}),
        "xlsx": gen.xlsx_like({"image1.jpg": second}),
        "hwpx": gen.hwpx_like({"image1.png": first}),
    }
    for fmt, data in packages.items():
        for action in ("convert_and_ocr", "convert_only"):  # media is published when Need is NONE too
            temp = run_temp / f"{fmt}-{action}"
            temp.mkdir()
            result = convert.convert_source(
                data, sniff=gen.fake_sniff(f"x.{fmt}", data, fmt=fmt), action=action, run_temp=temp)
            call = core_spy.calls[-1]
            assert Path(call["extract_media"]) == temp / "media" and Path(call["media_base_dir"]) == temp
            assert result["media"], (fmt, action)
            for filename, path in result["media"].items():
                assert Path(path).parent == temp / "media" and Path(path).is_file()
                assert Path(filename).stem == gen.h12(Path(path).read_bytes()), "name is sha256(member)[:12]"
                assert f"media/{filename}" in result["body"]

    data = packages["docx"]
    temp = run_temp / "publish"
    temp.mkdir()
    result = convert.convert_source(data, sniff=gen.fake_sniff("x.docx", data, fmt="docx"), action="convert_and_ocr", run_temp=temp)
    order = []
    real_replace = os.replace
    monkeypatch.setattr(os, "replace", lambda src, dst, *a, **k: (order.append(Path(dst).name), real_replace(src, dst, *a, **k))[1])

    published = write.publish_source(out_dir, "docs/x.docx.md", result["body"].encode(), result["media"])

    assert published["ok"] is True
    assert order[-1] == "x.docx.md" and set(order[:-1]) == set(result["media"]), f"media first, markdown last: {order}"
    for filename in result["media"]:
        assert (out_dir / "docs" / "media" / filename).is_file()

    order.clear()
    stamp = (out_dir / "docs" / "media" / next(iter(result["media"]))).stat().st_mtime_ns
    again = write.publish_source(out_dir, "docs/x.docx.md", result["body"].encode(), result["media"])
    assert again["ok"] is True and order == [], "identical media and markdown are not rewritten"
    assert (out_dir / "docs" / "media" / next(iter(result["media"]))).stat().st_mtime_ns == stamp
    write.publish_source(out_dir, "docs/x.docx.md", b"changed body\n", result["media"])
    assert order == ["x.docx.md"], "only the changed artifact is replaced"

    hwp = gen.hwp5_min()
    core_spy.behavior = None
    convert.convert_source(hwp, sniff=gen.fake_sniff("x.hwp", hwp, fmt="hwp"), action="convert_and_ocr", run_temp=run_temp)
    assert core_spy.calls[-1]["extract_media"] == str(run_temp / "media"), "HWP5 also uses extract_media"
    plain = gen.txt_utf8()
    convert.convert_source(plain, sniff=gen.fake_sniff("x.txt", plain, fmt="txt"), action="convert_only", run_temp=run_temp)
    assert core_spy.calls[-1]["extract_media"] is None, "extract_media only for docx|pptx|xlsx|hwp|hwpx"


@pytest.mark.req("REQ-CNV-04")
@pytest.mark.cov("S5", "FM12")
@pytest.mark.fx("FX-03", "FX-16")
def test_T_CNV_04_base_body_and_media_cached(tmp_path, gen, core_spy, run_temp):
    cache = tmp_path / "cache"
    cases = [("pdf", gen.pdf_text(2), None), ("docx", gen.docx_like({"image1.png": gen.png_noise(seed=44)}), _extract_media_behavior)]
    for fmt, data, behavior in cases:
        core_spy.behavior = behavior
        sniff_result = gen.fake_sniff(f"x.{fmt}", data, fmt=fmt)
        first_temp = run_temp / f"{fmt}-1"
        second_temp = run_temp / f"{fmt}-2"
        first_temp.mkdir()
        second_temp.mkdir()
        first = convert.convert_source(data, sniff=sniff_result, action="convert_and_ocr", run_temp=first_temp, cache_dir=cache)
        calls_after_first = len(core_spy.calls)
        assert calls_after_first >= 1
        assert list((cache / "base").glob(f"{sniff_result['sha256']}-*")), "cache entry named <sha256>-<core_version>"

        second = convert.convert_source(data, sniff=sniff_result, action="convert_and_ocr", run_temp=second_temp, cache_dir=cache)

        assert len(core_spy.calls) == calls_after_first, f"{fmt}: rerun must not call Core"
        assert second["body"] == first["body"] and second["pages"] == first["pages"]
        assert set(second["media"]) == set(first["media"])
        for filename, path in second["media"].items():
            assert Path(path).parent == second_temp / "media"
            assert Path(path).read_bytes() == Path(first["media"][filename]).read_bytes()


@pytest.mark.req("REQ-CNV-05")
@pytest.mark.cov("S5", "FM9")
@pytest.mark.fx("FX-38", "FX-64")
def test_T_CNV_05_core_is_offline_and_never_given_a_path_or_uri(tmp_path, gen, fake_core, run_temp, socket_guard):
    signature = inspect.signature(convert.convert_source)
    assert not {"path", "source_path", "uri", "url", "filename"} & set(signature.parameters), "Convert takes bytes only"

    names = ["http_example.invalid_secret.txt", "file_etc_passwd.txt", "data_text_plain_base64.txt"]
    if os.name != "nt":
        names += ["http:__example.invalid_x.txt", "file:__etc_passwd.txt", "data:text,hi.txt"]
    renamed_audio = b"ID3" + gen.rng_bytes(256, 38)
    for name in names:
        path = tmp_path / name
        path.write_bytes(renamed_audio)
        convert.convert_source(
            renamed_audio, sniff=gen.fake_sniff(path, renamed_audio, fmt="txt"), action="convert_only", run_temp=run_temp)

    assert socket_guard.attempts == [], "Convert must not open sockets"
    assert fake_core.init_calls, "Core was constructed"
    for args, kwargs in fake_core.init_calls:
        assert not kwargs.get("enable_plugins"), "plugins disabled"
        assert not args and kwargs.get("llm_client") is None and kwargs.get("llm_model") is None
        assert not kwargs.get("docintel_endpoint")
    assert fake_core.forbidden_calls == [], "convert()/convert_local()/convert_uri() accept paths and URIs"
    assert len(fake_core.convert_calls) == len(names)
    for args, kwargs in fake_core.convert_calls:
        stream = args[0]
        assert isinstance(stream, (bytes, bytearray)) or hasattr(stream, "read"), "input is a bytes stream"
        assert ".txt" in repr(args[1:]) + repr(kwargs), "the Sniff format is passed as the extension hint"
