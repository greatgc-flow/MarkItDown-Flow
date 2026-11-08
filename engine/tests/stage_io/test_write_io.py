"""T-WRT-01..03, T-GEN-05, T-GEN-11, T-SEC-09 (TESTPLAN step 6): Write. RED: stubs raise NotImplementedError."""

import errno
import os
import re
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from mdflow import contracts, convert, sniff_io, write


def _tmp_names(directory, target):
    return [p for p in Path(directory).iterdir() if p.name != target.name]


def _is_private(path):
    return stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.req("REQ-GEN-05")
@pytest.mark.cov("S12", "FM7")
@pytest.mark.fx("FX-01", "FX-65")
def test_T_GEN_05_fault_after_temp_leaves_target_absent_or_complete(tmp_path, gen, monkeypatch, cli_command):
    old, new = b"old complete content", gen.pdf_text(1)
    for fault in ("fsync", "replace"):
        for preexisting in (False, True):
            directory = tmp_path / f"{fault}-{preexisting}"
            directory.mkdir()
            target = directory / "report.pdf.md"
            if preexisting:
                target.write_bytes(old)

            def boom(*args, **kwargs):
                raise OSError(errno.EIO, "injected fault")

            with monkeypatch.context() as patched:
                patched.setattr(os, fault, boom)
                with pytest.raises(OSError):
                    write.atomic_write(target, new)

            if preexisting:
                assert target.read_bytes() == old, f"{fault}: old file must stay complete"
            else:
                assert not target.exists(), f"{fault}: target must be absent"
            for stray in _tmp_names(directory, target):
                assert re.fullmatch(re.escape(target.name) + r"\.tmp-\d+-\d+", stray.name), stray.name
                if os.name == "posix":
                    assert _is_private(stray), "temp files are created 0o600"
            assert write.atomic_write(target, new) is True, "a stale temp never blocks the next write"
            assert target.read_bytes() == new

    # real process death between fsync and replace
    child = textwrap.dedent("""
        import os, sys
        def die(*args, **kwargs):
            os._exit(7)
        os.replace = die
        from mdflow import write
        write.atomic_write(sys.argv[1], b"new bytes from child")
    """)
    directory = tmp_path / "killed"
    directory.mkdir()
    target = directory / "memo.docx.md"
    proc = subprocess.run(cli_command(target, code=child), capture_output=True, text=True, timeout=60)
    assert proc.returncode == 7, proc.stderr
    assert not target.exists()
    strays = _tmp_names(directory, target)
    assert len(strays) == 1 and re.fullmatch(re.escape(target.name) + r"\.tmp-\d+-\d+", strays[0].name)
    assert strays[0].read_bytes() == b"new bytes from child", "temp was fully written and synced before the kill"
    if os.name == "posix":
        assert _is_private(strays[0])
    assert write.atomic_write(target, b"new bytes from child") is True, "rerun needs no cleanup"
    assert target.read_bytes() == b"new bytes from child"


@pytest.mark.req("REQ-GEN-05")
@pytest.mark.cov("S12", "FM12")
@pytest.mark.fx("FX-16")
def test_T_GEN_11_identical_bytes_leave_target_untouched(tmp_path, gen, monkeypatch):
    target = tmp_path / "memo.docx.md"
    data = gen.docx_like({"image1.png": gen.png_noise(seed=11)})
    assert write.atomic_write(target, data) is True
    long_ago = 1_000_000_000 * 10**9
    os.utime(target, ns=(long_ago, long_ago))
    before = target.stat()

    replaced = []
    real_replace = os.replace
    monkeypatch.setattr(os, "replace", lambda src, dst, *a, **k: (replaced.append(dst), real_replace(src, dst, *a, **k))[1])

    assert write.atomic_write(target, data) is False
    after = target.stat()
    assert replaced == [], "identical bytes: os.replace is not called"
    assert (after.st_mtime_ns, after.st_ino) == (before.st_mtime_ns, before.st_ino)
    assert [p.name for p in tmp_path.iterdir()] == ["memo.docx.md"], "the temp file was deleted"

    assert write.atomic_write(target, data + b"!") is True
    assert len(replaced) == 1 and target.read_bytes() == data + b"!"


@pytest.mark.req("REQ-WRT-01", "REQ-SEC-05")
@pytest.mark.cov("S12", "FM9")
@pytest.mark.fx("FX-02")
def test_T_WRT_01_containment_realpath_and_link_walk(tmp_path, gen, out_dir):
    outside = tmp_path / "outside"
    outside.mkdir()

    done = write.publish_source(out_dir, "sub/a.pdf.md", b"# a\n")
    assert done["ok"] is True and done["written"] == ["sub/a.pdf.md"]
    assert (out_dir / "sub" / "a.pdf.md").read_bytes() == b"# a\n"

    for escape in ("../esc.md", "sub/../../esc2.md"):
        result = write.publish_source(out_dir, escape, b"escaped\n")
        assert result["ok"] is False and [i["code"] for i in result["issues"]] == ["E_OUTPUT_IO"], escape
    assert not (tmp_path / "esc.md").exists() and not (tmp_path / "esc2.md").exists()

    gen.make_dir_link(out_dir / "evil", outside)
    blocked = write.publish_source(out_dir, "evil/b.pdf.md", b"escaped\n")
    assert blocked["ok"] is False and [i["code"] for i in blocked["issues"]] == ["E_OUTPUT_IO"]
    assert list(outside.iterdir()) == [], "nothing written outside out_dir"
    assert str(tmp_path) not in blocked["issues"][0]["message"], "diagnostics carry no absolute paths"

    (out_dir / "sub2").mkdir()
    gen.make_dir_link(out_dir / "sub2" / "media", outside)
    media_source = tmp_path / "m.png"
    media_source.write_bytes(gen.pdf_scan(1))
    linked_media = write.publish_source(out_dir, "sub2/c.pdf.md", b"c\n", {"h.png": media_source})
    assert linked_media["ok"] is False and [i["code"] for i in linked_media["issues"]] == ["E_OUTPUT_IO"]
    assert list(outside.iterdir()) == [] and not (out_dir / "sub2" / "c.pdf.md").exists()

    alias = tmp_path / "alias"
    gen.make_dir_link(alias, out_dir)
    through_alias = write.publish_source(alias, "d/e.pdf.md", b"e\n")
    assert through_alias["ok"] is True, "a linked out_dir itself is the user's choice"
    assert (out_dir / "d" / "e.pdf.md").read_bytes() == b"e\n"


@pytest.mark.req("REQ-WRT-02")
@pytest.mark.cov("S12", "FM5")
@pytest.mark.fx("FX-02", "FX-43")
def test_T_WRT_02_write_failure_is_per_file(tmp_path, gen, out_dir, monkeypatch):
    real_replace, real_open = os.replace, os.open
    (out_dir / "fail-replace.pdf.md").write_bytes(b"previous output")
    (out_dir / "blocker").write_bytes(b"a file where a directory is needed")

    def replace(src, dst, *args, **kwargs):
        if Path(dst).name == "fail-replace.pdf.md":
            raise PermissionError(errno.EACCES, "injected")
        return real_replace(src, dst, *args, **kwargs)

    def open_(path, flags, *args, **kwargs):
        if Path(os.fsdecode(path)).name.startswith("fail-open.pdf.md.tmp-"):
            raise PermissionError(errno.EACCES, "injected")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace)
    monkeypatch.setattr(os, "open", open_)
    results = [
        write.publish_source(out_dir, "fail-replace.pdf.md", gen.pdf_scan(1)),
        write.publish_source(out_dir, "fail-open.pdf.md", gen.pdf_scan(1)),
        write.publish_source(out_dir, "blocker/x.pdf.md", gen.pdf_scan(1)),
        write.publish_source(out_dir, "fine.zip.md", gen.zip_basic()),
    ]

    for result in results[:3]:
        assert result["ok"] is False and [i["code"] for i in result["issues"]] == ["E_OUTPUT_IO"], result
        assert str(tmp_path) not in result["issues"][0]["message"]
    assert contracts.EXIT_CODE_MAP["E_OUTPUT_IO"] == 2
    assert results[3]["ok"] is True and (out_dir / "fine.zip.md").read_bytes() == gen.zip_basic(), "the next file is still written"
    assert (out_dir / "fail-replace.pdf.md").read_bytes() == b"previous output", "a failed replace keeps the old output"
    assert not (out_dir / "fail-open.pdf.md").exists()


@pytest.mark.req("REQ-SNF-01b", "REQ-ASM-02")
@pytest.mark.cov("S12", "FM12")
@pytest.mark.fx("FX-52")
def test_T_WRT_03_output_collision_never_reaches_convert(tmp_path, gen, core_spy, run_temp):
    first_root, second_root = tmp_path / "r1", tmp_path / "r2"
    (first_root / "a").mkdir(parents=True)
    (second_root / "A").mkdir(parents=True)
    (first_root / "a" / "x.pdf").write_bytes(gen.pdf_text(1))
    (second_root / "A" / "x.pdf").write_bytes(gen.pdf_scan(1))

    result = sniff_io.discover([first_root, second_root])

    by_logical = {f["logical"]: f for f in result["files"]}
    assert set(by_logical) == {"a/x.pdf", "A/x.pdf"}, "both are discovered; GEN-07 keeps the second visible"
    assert by_logical["a/x.pdf"]["issues"] == [], "first root wins"
    collided = by_logical["A/x.pdf"]
    assert [i["code"] for i in collided["issues"]] == ["E_OUTPUT_COLLISION"]
    assert str(tmp_path) not in collided["issues"][0]["message"]

    data = Path(collided["path"]).read_bytes()
    sniff_result = gen.fake_sniff(collided["path"], data, fmt="pdf", issues=collided["issues"])
    skipped = convert.convert_source(data, sniff=sniff_result, action="report_only", run_temp=run_temp)
    assert core_spy.calls == [], "a colliding source is report_only and never reaches Convert"
    assert skipped["body"] == ""


@pytest.mark.req("REQ-SEC-09")
@pytest.mark.cov("S7", "FM5")
@pytest.mark.fx("FX-02")
def test_T_SEC_09_cache_files_private_and_cache_clear_empties_dir(tmp_path, gen):
    cache = tmp_path / "cache"
    key_id = "ab" + "0" * 62
    entry = cache / "units" / "ab" / f"{key_id}.json"

    assert write.atomic_write(entry, b'{"v":1}', dir_mode=0o700) is True

    if os.name == "posix":
        assert _is_private(entry), "cache files are 0o600"
        for directory in (cache, cache / "units", cache / "units" / "ab"):
            assert stat.S_IMODE(directory.stat().st_mode) == 0o700, directory
    (cache / "units" / "ab" / f"{key_id}.json.tmp-1-1").write_bytes(b"stale")
    (cache / "base").mkdir()
    (cache / "base" / "abc-0.3.5.md").write_bytes(b"cached body")

    write.clear_cache(cache)

    assert cache.is_dir() and list(cache.iterdir()) == [], "cache clear leaves the directory, empty"
