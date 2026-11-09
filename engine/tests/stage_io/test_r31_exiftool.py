"""R31: exiftool integration at the Convert boundary.

``mdflow`` detects exiftool (``EXIFTOOL_PATH`` first, then ``PATH``; minimum 12.24) and hands it to markitdown-gc as
``exiftool_path`` so image EXIF metadata appears in the converted body. Absent, too old or broken exiftool degrades
to a body without metadata, never to ``E_CONVERT_FAIL``. The "absent" paths are produced by the environment (empty
PATH, EXIFTOOL_PATH unset/pointing nowhere), so they run identically on every machine: no skip.
"""

from pathlib import Path

import pytest

from mdflow import convert, exiftool


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """No exiftool anywhere: an empty PATH directory and no EXIFTOOL_PATH (the 'absent' state, by environment)."""
    empty = tmp_path / "empty-path"
    empty.mkdir()
    monkeypatch.delenv("EXIFTOOL_PATH", raising=False)
    monkeypatch.setenv("PATH", str(empty))
    exiftool.reset()
    yield monkeypatch
    exiftool.reset()


def image_sniff(gen, data, fmt="png"):
    return gen.fake_sniff(f"pic.{fmt}", data, fmt=fmt)


@pytest.mark.req("REQ-CNV-06")
@pytest.mark.cov("S5", "FM10")
@pytest.mark.fx("FX-09")
def test_T_CNV_84_exiftool_detection_order_minimum_version_and_graceful_states(tmp_path, clean_env, fake_exiftool):
    env = clean_env
    assert exiftool.detect() == dict(available=False, path=None, version=None, source=None, status="not_found")
    on_path = fake_exiftool(tmp_path / "bin-path", "13.59")
    env.setenv("PATH", str(on_path.parent))
    exiftool.reset()
    found = exiftool.detect()
    assert (found["available"], found["version"], found["source"], found["status"]) == (True, "13.59", "PATH", "ok")
    assert Path(found["path"]).samefile(on_path)
    explicit = fake_exiftool(tmp_path / "bin-env", "12.24")
    env.setenv("EXIFTOOL_PATH", str(explicit))
    exiftool.reset()
    found = exiftool.detect()
    assert (found["available"], found["version"], found["source"]) == (True, "12.24", "EXIFTOOL_PATH"), "12.24 is the minimum"
    env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bin-old", "12.23")))
    exiftool.reset()
    assert exiftool.detect() == dict(available=False, path=None, version="12.23", source="EXIFTOOL_PATH", status="too_old")
    env.setenv("EXIFTOOL_PATH", str(tmp_path / "does-not-exist"))
    exiftool.reset()
    broken = exiftool.detect()
    assert (broken["available"], broken["status"], broken["source"]) == (False, "unusable", "EXIFTOOL_PATH"), \
        "an explicit but unusable setting is not silently replaced by PATH"
    env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bin-garbage", "not-a-version")))
    exiftool.reset()
    assert exiftool.detect()["status"] == "unusable"
    env.setenv("EXIFTOOL_PATH", "")
    exiftool.reset()
    assert exiftool.detect()["source"] == "PATH", "an empty EXIFTOOL_PATH counts as unset"


@pytest.mark.req("REQ-CNV-06")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-09", "FX-10")
def test_T_CNV_85_metadata_lands_in_the_image_body_and_only_images_use_exiftool(tmp_path, gen, run_temp, clean_env,
                                                                                  fake_exiftool):
    clean_env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bin", "13.59")))
    exiftool.reset()
    for fmt in ("png", "jpeg"):
        data = gen.png_noise() if fmt == "png" else gen.jpeg_noise()
        result = convert.convert_source(data, sniff=image_sniff(gen, data, fmt), action="convert_and_ocr", run_temp=run_temp)
        assert result["issues"] == [], fmt
        assert "ImageSize: 32x32" in result["body"] and "Title: Fake Title" in result["body"], fmt
        assert result["tools"] == {"exiftool": "13.59"}, fmt
    for fmt, data in (("pdf", gen.pdf_text(1)), ("txt", gen.txt_utf8())):
        result = convert.convert_source(data, sniff=gen.fake_sniff(f"f.{fmt}", data, fmt=fmt), action="convert_only",
                                        run_temp=run_temp)
        assert "tools" not in result and "ImageSize" not in result["body"], fmt


@pytest.mark.req("REQ-CNV-06")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-09")
def test_T_CNV_86_core_gets_an_explicit_exiftool_path_so_it_never_guesses(tmp_path, gen, fake_core, run_temp, clean_env,
                                                                         fake_exiftool):
    fake = fake_exiftool(tmp_path / "bin", "13.59")
    clean_env.setenv("EXIFTOOL_PATH", str(fake))
    exiftool.reset()
    png, txt = gen.png_noise(), gen.txt_utf8()
    convert.convert_source(png, sniff=image_sniff(gen, png), action="convert_only", run_temp=run_temp)
    convert.convert_source(txt, sniff=gen.fake_sniff("a.txt", txt, fmt="txt"), action="convert_only", run_temp=run_temp)
    (_, png_kwargs), (_, txt_kwargs) = fake_core.init_calls
    assert Path(png_kwargs["exiftool_path"]).samefile(fake)
    assert txt_kwargs["exiftool_path"] == "", "non-image conversions never start exiftool"
    clean_env.delenv("EXIFTOOL_PATH")
    exiftool.reset()
    fake_core.init_calls.clear()
    convert.convert_source(png, sniff=image_sniff(gen, png), action="convert_only", run_temp=run_temp)
    assert fake_core.init_calls[0][1]["exiftool_path"] == "", "empty string disables Core's own environment/PATH probing"


@pytest.mark.req("REQ-CNV-06")
@pytest.mark.cov("S5", "FM10")
@pytest.mark.fx("FX-09")
def test_T_CNV_87_absent_old_or_broken_exiftool_never_fails_the_conversion(tmp_path, gen, run_temp, clean_env, fake_exiftool):
    """Real Core; the 'absent' state comes from the environment, so this never skips."""
    png = gen.png_noise()
    sniff = image_sniff(gen, png)

    def convert_png():
        exiftool.reset()
        return convert.convert_source(png, sniff=sniff, action="convert_and_ocr", run_temp=run_temp)

    absent = convert_png()
    assert absent["issues"] == [] and "tools" not in absent and "ImageSize" not in absent["body"]
    clean_env.setenv("EXIFTOOL_PATH", str(tmp_path / "missing"))  # baseline: Core read this itself and raised
    junk = convert_png()
    assert junk["issues"] == [] and "tools" not in junk
    clean_env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "old", "12.23")))
    old = convert_png()
    assert old["issues"] == [] and "tools" not in old and "ImageSize" not in old["body"]
    clean_env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bad", "13.59", fail_json=True)))
    failing = convert_png()
    assert failing["issues"] == [], "a tool that fails on the file falls back to a plain conversion"
    assert "tools" not in failing


@pytest.mark.req("REQ-CNV-06", "REQ-CNV-04")
@pytest.mark.cov("S5", "FM12")
@pytest.mark.fx("FX-09")
def test_T_CNV_88_image_cache_is_keyed_by_the_exiftool_version_and_restores_the_tools_entry(
        tmp_path, gen, fake_core, clean_env, fake_exiftool):
    cache = tmp_path / "cache"
    png = gen.png_noise()
    sniff = image_sniff(gen, png)

    def run(label):
        temp = tmp_path / f"run-{label}"
        temp.mkdir()
        return convert.convert_source(png, sniff=sniff, action="convert_only", run_temp=temp, cache_dir=cache)

    clean_env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bin", "13.59")))
    exiftool.reset()
    first = run("a")
    assert first["tools"] == {"exiftool": "13.59"} and len(fake_core.convert_calls) == 1
    second = run("b")
    assert second["tools"] == {"exiftool": "13.59"} and len(fake_core.convert_calls) == 1, "warm rerun: no Core call"
    clean_env.delenv("EXIFTOOL_PATH")
    exiftool.reset()
    third = run("c")
    assert "tools" not in third and len(fake_core.convert_calls) == 2, "no exiftool: a different cache entry"
    clean_env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bin2", "13.60")))
    exiftool.reset()
    fourth = run("d")
    assert fourth["tools"] == {"exiftool": "13.60"} and len(fake_core.convert_calls) == 3, "new version: reconvert"


@pytest.mark.req("REQ-CNV-06", "REQ-ASM-04")
@pytest.mark.cov("S12", "FM0")
@pytest.mark.fx("FX-09")
def test_T_ASM_81_frontmatter_records_the_exiftool_version_only_when_it_was_used(tmp_path, gen, clean_env, fake_exiftool):
    from mdflow import orchestrate

    root = tmp_path / "input"
    root.mkdir()
    (root / "pic.png").write_bytes(gen.png_noise())
    (root / "note.txt").write_text("plain text\n", encoding="utf-8")
    clean_env.setenv("EXIFTOOL_PATH", str(fake_exiftool(tmp_path / "bin", "13.59")))
    exiftool.reset()
    report = orchestrate.run([root], dict(out=tmp_path / "out", cache=tmp_path / "cache"))
    assert report["files"] and all(f["outputs"] for f in report["files"])
    image = (tmp_path / "out" / "pic.png.md").read_text(encoding="utf-8")
    text = (tmp_path / "out" / "note.txt.md").read_text(encoding="utf-8")
    assert 'pillow: "' in image and ', exiftool: "13.59"}' in image, "tools mapping appends exiftool after pillow"
    assert "ImageSize: 32x32" in image.split("\n---\n", 1)[1]
    assert "exiftool" not in text, "not used for text"
    clean_env.delenv("EXIFTOOL_PATH")
    exiftool.reset()
    again = orchestrate.run([root], dict(out=tmp_path / "out2", cache=tmp_path / "cache2"))
    assert all(f["outputs"] for f in again["files"])
    assert "exiftool" not in (tmp_path / "out2" / "pic.png.md").read_text(encoding="utf-8")
