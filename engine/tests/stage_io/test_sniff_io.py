"""T-SNF-01..10 (TESTPLAN step 5): Sniff IO. RED: stubs raise NotImplementedError.

Ownership note: T-SNF-04 and T-SNF-07 also have a pure part in step 2; these file-level oracles (SPEC 11
SNF-03 / SNF-06) use real files, so they are registered here and must not be duplicated elsewhere.
"""

import hashlib
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

from mdflow import sniff_io, triage

MIB = 1024 * 1024


def _put(directory, name, data):
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _sniff(path, **kwargs):
    return sniff_io.sniff(path, logical=Path(path).name, **kwargs)


def _codes(result):
    return {issue["code"] for issue in result["issues"]}


@pytest.mark.req("REQ-SNF-01")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-51")
@pytest.mark.plat("posix")
def test_T_SNF_01_sorted_walk_skips_and_out_dir_not_walked(tmp_path, gen):
    root = tmp_path / "in"
    for rel in ("b.txt", "a.txt", ".hidden.txt", ".git/f.txt", "sub/c.txt", "sub/.d.txt", "out/old.md"):
        _put(root, rel, b"data")
    os.symlink(root / "a.txt", root / "link.txt")

    first = sniff_io.discover([root], exclude=[root / "out"])

    assert [f["logical"] for f in first["files"]] == ["a.txt", "b.txt", "sub/c.txt"]
    assert all(f["root"] == 0 and f["issues"] == [] and Path(f["path"]).is_absolute() for f in first["files"])
    assert {(s["path"], s["code"]) for s in first["skipped"]} == {
        (".hidden.txt", "W_SKIPPED_HIDDEN"), (".git", "W_SKIPPED_HIDDEN"),
        ("sub/.d.txt", "W_SKIPPED_HIDDEN"), ("link.txt", "W_SKIPPED_SYMLINK"),
    }
    reported = {f["logical"] for f in first["files"]} | {s["path"] for s in first["skipped"]}
    assert not any(p == "out" or p.startswith("out/") for p in reported), "out_dir must never be walked"

    again = sniff_io.discover([root], exclude=[root / "out"])
    assert [f["logical"] for f in again["files"]] == [f["logical"] for f in first["files"]], "replay: same logical paths"

    assert [f["logical"] for f in sniff_io.discover([root / "b.txt"])["files"]] == ["b.txt"]
    assert [f["logical"] for f in sniff_io.discover([root / "sub"])["files"]] == ["c.txt"]


@pytest.mark.req("REQ-SNF-01b")
@pytest.mark.cov("S1", "FM12")
@pytest.mark.fx("FX-52")
def test_T_SNF_02_roots_deduplicated_by_realpath(tmp_path, gen):
    root = tmp_path / "docs"
    x = _put(root, "x.pdf", gen.pdf_text(1))
    _put(root, "y.pdf", gen.pdf_text(1))

    result = sniff_io.discover([x, root])

    assert sorted(f["logical"] for f in result["files"]) == ["x.pdf", "y.pdf"]
    by_logical = {f["logical"]: f for f in result["files"]}
    assert by_logical["x.pdf"]["root"] == 0, "first root wins"
    assert by_logical["y.pdf"]["root"] == 1
    duplicates = [s for s in result["skipped"] if s["code"] == "W_DUPLICATE_INPUT"]
    assert len(duplicates) == 1
    real = [os.path.realpath(f["path"]) for f in result["files"]]
    assert len(real) == len(set(real)), "a file reached through two roots is reported once"

    same_twice = sniff_io.discover([root, root])
    assert sorted(f["logical"] for f in same_twice["files"]) == ["x.pdf", "y.pdf"]
    assert any(s["code"] == "W_DUPLICATE_INPUT" for s in same_twice["skipped"])


@pytest.mark.req("REQ-SNF-02")
@pytest.mark.cov("S1", "FM3")
@pytest.mark.fx("FX-42")
def test_T_SNF_03_byte_bound_applies_to_files_and_members(tmp_path, gen, cli_command):
    big = _put(tmp_path, "big.txt", gen.zero_padded_text(2 * MIB))
    result = _sniff(big, max_bytes=1048576)
    assert "E_TOO_LARGE" in _codes(result)
    assert result["bytes"] == 2 * MIB

    exact = _put(tmp_path, "exact.txt", b"a" * 1048576)
    assert "E_TOO_LARGE" not in _codes(_sniff(exact, max_bytes=1048576)), "only size > bound is too large"

    bundle = _put(tmp_path, "bundle.zip", gen.make_zip({"small.txt": b"s", "huge.txt": b"a" * (2 * MIB)}))
    container = sniff_io.expand_container(bundle, logical="bundle.zip", max_bytes=1048576)
    members = {m["logical"]: m for m in container["members"]}
    assert "E_TOO_LARGE" in _codes(members["bundle.zip/huge.txt"]["sniff"]), "member bound uses the central-directory size"
    assert _codes(members["bundle.zip/small.txt"]["sniff"]) == set()

    proc = subprocess.run(
        cli_command("run", exact, "-o", tmp_path / "o", "--max-bytes", "268435457"),
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 1
    assert "E_USAGE" in proc.stdout + proc.stderr


@pytest.mark.req("REQ-SNF-03")
@pytest.mark.cov("S1", "FM0")
@pytest.mark.fx("FX-09", "FX-40", "FX-41")
def test_T_SNF_04_magic_first_extension_second(tmp_path, gen):
    png, jpeg, pdf = gen.png_noise(), gen.jpeg_noise(), gen.pdf_text(1)
    table = [  # (file name, bytes, format, route)
        ("a.png", png, "png", "NATIVE"), ("b.jpg", jpeg, "jpeg", "NATIVE"), ("c.gif", gen.gif_noise(), "gif", "NATIVE"),
        ("d.bmp", gen.bmp_noise(), "bmp", "NATIVE"), ("e.tif", gen.tiff_single(), "tiff", "NATIVE"),
        ("f.webp", gen.webp_noise(), "webp", "NATIVE"),
        ("big.tif", bytes.fromhex("49492b0008000000") + b"\x00" * 16, "tiff", "NATIVE"),
        ("mm.tif", bytes.fromhex("4d4d002a") + b"\x00" * 16, "tiff", "NATIVE"),
        ("g.pdf", pdf, "pdf", "NATIVE"), ("h.docx", gen.docx_like(), "docx", "NATIVE"),
        ("i.pptx", gen.pptx_like(), "pptx", "NATIVE"), ("j.xlsx", gen.xlsx_like(), "xlsx", "NATIVE"),
        ("k.hwpx", gen.hwpx_like(), "hwpx", "NATIVE"), ("l.epub", gen.epub_like(), "epub", "NATIVE"),
        ("m.odt", gen.odt_like(), "odt", "LEGACY"), ("n.zip", gen.zip_basic(), "zip", "CONTAINER"),
        ("o.rtf", b"{\\rtf1\\ansi hello}", "rtf", "LEGACY"),
        ("p.doc", gen.cfb_legacy("doc"), "doc", "LEGACY"), ("q.xls", gen.cfb_legacy("xls"), "xls", "NATIVE"),
        ("r.msg", gen.cfb_legacy("other"), "msg", "NATIVE"), ("s.hwp", gen.hwp5_min(), "hwp", "NATIVE"),
        ("t.bin", gen.cfb_legacy("other"), "cfb", "UNSUPPORTED"),
        ("u.txt", gen.txt_utf8(), "txt", "NATIVE"), ("v.log", b"log line\n", "log", "NATIVE"),
        ("w.csv", b"a,b\n1,2\n", "csv", "NATIVE"), ("x.md", b"# title\n", "md", "NATIVE"),
        ("y.html", b"<html></html>", "html", "NATIVE"), ("z.json", b"{}", "json", "NATIVE"),
        ("w.pages", b"junk", "pages", "LEGACY"),
    ]
    for name, data, fmt, route in table:
        result = _sniff(_put(tmp_path / "table", name, data))
        assert (result["format"], result["route"]) == (fmt, route), name
        assert "W_EXT_MISMATCH" not in _codes(result), name

    media = _sniff(_put(tmp_path, "song.mp3", b"ID3" + gen.rng_bytes(64, 38)))
    assert (media["route"], media["format"]) == ("UNSUPPORTED", "mp3")
    assert "media_out_of_scope" in media["reasons"]
    unknown = _sniff(_put(tmp_path, "data.xyz", gen.rng_bytes(64, 39)))
    assert unknown["route"] == "UNSUPPORTED" and "unsupported_format" in unknown["reasons"]

    # WebP needs bytes 8-11: 12 bytes are enough and the name does not matter (magic first)
    webp = _sniff(_put(tmp_path, "noext", gen.webp_noise()[:12]))
    assert (webp["format"], webp["route"]) == ("webp", "NATIVE")

    # FX-41: PDF bytes named .docx -> magic wins, mismatch reported; FX-13-style png/webp mismatch
    mismatch = _sniff(_put(tmp_path, "fake.docx", pdf))
    assert mismatch["format"] == "pdf" and "W_EXT_MISMATCH" in _codes(mismatch)
    webp_as_png = _sniff(_put(tmp_path, "really-webp.png", gen.webp_noise()))
    assert webp_as_png["format"] == "webp" and "W_EXT_MISMATCH" in _codes(webp_as_png)
    assert "W_EXT_MISMATCH" not in _codes(_sniff(_put(tmp_path, "UPPER.PDF", pdf))), "extension compare is case-insensitive"

    # FX-40: zero bytes
    empty = _sniff(_put(tmp_path, "empty.pdf", b""))
    assert "E_CORRUPT" in _codes(empty)


@pytest.mark.req("REQ-SNF-04")
@pytest.mark.cov("S1", "FM2")
@pytest.mark.fx("FX-05", "FX-25", "FX-26", "FX-27")
def test_T_SNF_05_encryption_detectors(tmp_path, gen):
    cases = [  # (name, bytes, accepted reasons, format or None)
        ("enc-pypdf.pdf", gen.pdf_encrypted(), {"pdf_password", "pdf_encrypt_trailer"}, "pdf"),
        ("enc-trailer.pdf", gen.pdf_encrypt_trailer(), {"pdf_encrypt_trailer", "pdf_password"}, "pdf"),
        ("flag.zip", gen.zip_flagbit(), {"zip_flag_bit"}, None),
        ("flag.docx", gen.zip_flagbit(docx=True), {"zip_flag_bit"}, None),
        ("office.docx", gen.cfb_encrypted_office(), {"cfb_encrypted_package"}, "docx"),
        ("secret.hwp", gen.hwp5_min(encrypted=True), {"hwp5_encrypted"}, "hwp"),
    ]
    for name, data, accepted, fmt in cases:
        result = _sniff(_put(tmp_path, name, data))
        assert result["route"] == "PROTECTED", name
        assert accepted & set(result["reasons"]), (name, result["reasons"])
        if fmt:
            assert result["format"] == fmt, name

    for name, data in (("plain.pdf", gen.pdf_text(1)), ("plain.hwp", gen.hwp5_min()),
                       ("partial.docx", gen.cfb_encryption_info_only()), ("plain.zip", gen.make_zip({"a.txt": b"a"}))):
        assert _sniff(_put(tmp_path, name, data))["route"] != "PROTECTED", name


@pytest.mark.req("REQ-SNF-05")
@pytest.mark.cov("S1", "FM1")
@pytest.mark.fx("FX-06", "FX-40")
def test_T_SNF_06_corruption_detectors(tmp_path, gen):
    noise = gen.rng_bytes(300, 66)
    for name, data in (
        ("noise.pdf", gen.pdf_corrupt()),
        ("noise.zip", b"PK\x03\x04" + noise),
        ("noise.docx", b"PK\x03\x04" + noise),
        ("badchain.doc", gen.cfb_corrupt()),
        ("empty.pdf", b""),
    ):
        result = _sniff(_put(tmp_path, name, data))
        assert "E_CORRUPT" in _codes(result), name
    for name, data in (("fine.pdf", gen.pdf_text(1)), ("fine.zip", gen.make_zip({"a.txt": b"a"})), ("fine.doc", gen.cfb_legacy("doc"))):
        assert "E_CORRUPT" not in _codes(_sniff(_put(tmp_path, name, data))), name


@pytest.mark.req("REQ-SNF-06")
@pytest.mark.cov("S1", "FM0")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_SNF_07_sniff_result_schema_and_single_hash(tmp_path, gen):
    for name, path in gen.sample_files(tmp_path).items():
        result = sniff_io.sniff(path, logical=f"logical/{name}", root=3)
        assert set(result) == {"path", "root", "bytes", "sha256", "ext", "magic", "format", "route", "reasons", "issues"}, name
        data = path.read_bytes()
        assert result["sha256"] == hashlib.sha256(data).hexdigest(), name
        assert result["bytes"] == len(data)
        assert result["path"] == f"logical/{name}"
        assert result["ext"] == path.suffix.lstrip(".").lower()
        assert result["route"] in {"NATIVE", "CONTAINER", "LEGACY", "PROTECTED", "UNSUPPORTED"}
        assert isinstance(result["magic"], str) and isinstance(result["format"], str)
        assert all(isinstance(r, str) for r in result["reasons"])
        assert all(set(i) >= {"code", "message"} for i in result["issues"])


@pytest.mark.req("REQ-SNF-07")
@pytest.mark.cov("S1", "FM5")
@pytest.mark.fx("FX-53")
def test_T_SNF_08_no_core_calls_and_io_failure_is_a_result(tmp_path, gen, fake_core, monkeypatch):
    for path in gen.sample_files(tmp_path).values():
        _sniff(path)
    assert fake_core.triage_calls == [] and fake_core.init_calls == [] and fake_core.convert_calls == [], "Sniff must not call Core"

    locked = _put(tmp_path, "locked.pdf", gen.pdf_text(1))
    gen.deny_open(monkeypatch, locked)
    result = _sniff(locked)
    assert "E_SNIFF_IO" in _codes(result)
    assert result["route"] == "UNSUPPORTED"
    assert all(str(tmp_path) not in issue["message"] for issue in result["issues"]), "no absolute paths in diagnostics"


@pytest.mark.req("REQ-SNF-08")
@pytest.mark.cov("S1", "FM3")
@pytest.mark.fx("FX-46", "FX-47")
def test_T_SNF_09_archive_preflight_before_triage(tmp_path, gen, fake_core):
    many = _put(tmp_path, "many.docx", gen.docx_like(entries=1001))
    result = _sniff(many, zip_entries=1000)
    assert "E_ZIP_ENTRIES" in _codes(result)
    assert (result["format"], result["route"]) == ("docx", "NATIVE")
    skipped = triage.run_triage(many, result)
    assert fake_core.triage_calls == [], "preflight failure must keep Core away from the bytes"
    assert skipped["ran"] is False
    assert "E_ZIP_ENTRIES" not in _codes(_sniff(many, zip_entries=1001))

    bomb_a = _sniff(_put(tmp_path, "bomb-a.zip", gen.zip_bomb("a")))
    assert "E_ZIP_BOMB" in _codes(bomb_a) and bomb_a["route"] == "CONTAINER"
    assert "E_ZIP_BOMB" in _codes(_sniff(_put(tmp_path, "bomb-b.zip", gen.zip_bomb("b")))), "stored member claiming csize 0"
    bomb_c = _sniff(_put(tmp_path, "bomb-c.docx", gen.zip_bomb("c")))
    assert "E_ZIP_BOMB" in _codes(bomb_c) and bomb_c["route"] == "NATIVE"
    triage.run_triage(tmp_path / "bomb-c.docx", bomb_c)
    assert fake_core.triage_calls == []

    # ratio alone is not a bomb: 5 MiB of zeros (< 10 MiB); 11 MiB of incompressible bytes (ratio ~1)
    assert "E_ZIP_BOMB" not in _codes(_sniff(_put(tmp_path, "zeros5.zip", gen.make_zip({"z.bin": b"\x00" * (5 * MIB)}))))
    assert "E_ZIP_BOMB" not in _codes(_sniff(_put(tmp_path, "noise11.zip", gen.make_zip({"n.bin": gen.rng_bytes(11 * MIB, 46)}, method=0))))

    total = _put(tmp_path, "total.zip", gen.make_zip({"a.bin": gen.rng_bytes(1500, 1), "b.bin": gen.rng_bytes(1500, 2)}, method=0))
    assert "E_ZIP_TOTAL" in _codes(_sniff(total, zip_total_bytes=2000))
    assert "E_ZIP_TOTAL" not in _codes(_sniff(total, zip_total_bytes=3000))


@pytest.mark.req("REQ-SNF-09")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-54")
def test_T_SNF_10_lying_size_aborts_streamed_read(tmp_path, gen):
    lie = _put(tmp_path, "lie.zip", gen.zip_lying_size())
    warm = _put(tmp_path, "warm.zip", gen.make_zip({"a.txt": b"abc"}))
    assert sniff_io.read_member(warm, "a.txt", max_bytes=1000) == b"abc"

    tracemalloc.start()
    try:
        with pytest.raises(sniff_io.ZipReadError) as raised:
            sniff_io.read_member(lie, "lie.bin", max_bytes=200 * MIB)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert raised.value.code == "E_ZIP_BOMB"
    assert peak < MIB, f"read must abort at declared+64KiB, peak was {peak} bytes"

    honest = _put(tmp_path, "honest.zip", gen.make_zip({"big.bin": b"\x00" * 5000}))
    for kwargs in ({"max_bytes": 1000}, {"max_bytes": 200 * MIB, "total_remaining": 1000}):
        with pytest.raises(sniff_io.ZipReadError) as raised:
            sniff_io.read_member(honest, "big.bin", **kwargs)
        assert raised.value.code == "E_ZIP_BOMB", kwargs

    container = sniff_io.expand_container(lie, logical="lie.zip")
    seen = {i["code"] for i in container["issues"]} | {i["code"] for m in container["members"] for i in m["sniff"]["issues"]}
    assert "E_ZIP_BOMB" in seen
