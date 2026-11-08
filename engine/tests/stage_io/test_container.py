"""T-CTR-01..04 (TESTPLAN step 5): zip containers. RED: stubs raise NotImplementedError."""

import hashlib
import os
from pathlib import Path

import pytest

from mdflow import sniff_io


def _put(directory, name, data):
    path = Path(directory) / name
    path.write_bytes(data)
    return path


def _codes(sniff_result):
    return {issue["code"] for issue in sniff_result["issues"]}


@pytest.mark.req("REQ-CTR-01")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-44")
def test_T_CTR_01_unsafe_member_names_flagged_and_siblings_continue(tmp_path, gen):
    work = tmp_path / "work"
    work.mkdir()
    bundle = _put(work, "slip.zip", gen.zip_slip())
    before = sorted(os.listdir(work)), sorted(os.listdir(tmp_path))

    container = sniff_io.expand_container(bundle, logical="slip.zip")

    members = {m["member"]: m for m in container["members"]}
    assert set(members) == {"ok.txt", "A.txt", "a.txt", "../x", "C:\\x", "a\\b", "/abs.txt"}
    for name in ("../x", "C:\\x", "a\\b", "/abs.txt", "a.txt"):
        assert "E_ZIP_PATH" in _codes(members[name]["sniff"]), name
    for name in ("ok.txt", "A.txt"):
        assert _codes(members[name]["sniff"]) == set(), name
        assert members[name]["data"] == f"payload of {name}".encode()
    assert members["ok.txt"]["logical"] == "slip.zip/ok.txt"
    assert members["../x"]["logical"] == "slip.zip/../x", "member ids are verbatim, never normalised"
    assert (sorted(os.listdir(work)), sorted(os.listdir(tmp_path))) == before, "members are never extracted by name"
    assert not (tmp_path / "x").exists() and not (work / "x").exists()


@pytest.mark.req("REQ-CTR-02")
@pytest.mark.cov("S1", "FM3")
@pytest.mark.fx("FX-45", "FX-47", "FX-50")
def test_T_CTR_02_depth_entries_total_and_bomb_bounds(tmp_path, gen):
    nest = _put(tmp_path, "nest.zip", gen.zip_depth4())
    container = sniff_io.expand_container(nest, logical="nest.zip")
    by_logical = {m["logical"]: m for m in container["members"]}
    assert container["issues"] == []
    assert set(by_logical) == {
        "nest.zip/top.txt", "nest.zip/l2.zip", "nest.zip/l2.zip/l2.txt", "nest.zip/l2.zip/l3.zip",
        "nest.zip/l2.zip/l3.zip/l3.txt", "nest.zip/l2.zip/l3.zip/l4.zip",
    }, "top-level zip is depth 1; the depth-4 archive is listed but not expanded"
    assert "E_ZIP_DEPTH" in _codes(by_logical["nest.zip/l2.zip/l3.zip/l4.zip"]["sniff"])
    assert by_logical["nest.zip/l2.zip"]["sniff"]["route"] == "CONTAINER"
    assert _codes(by_logical["nest.zip/l2.zip"]["sniff"]) == set()
    assert _codes(by_logical["nest.zip/top.txt"]["sniff"]) == set()

    shallow = sniff_io.expand_container(nest, logical="nest.zip", zip_depth=1)
    shallow_members = {m["logical"]: m for m in shallow["members"]}
    assert "E_ZIP_DEPTH" in _codes(shallow_members["nest.zip/l2.zip"]["sniff"])
    assert not any(name.startswith("nest.zip/l2.zip/") for name in shallow_members)

    many = _put(tmp_path, "many.zip", gen.zip_n_files(1001))
    over = sniff_io.expand_container(many, logical="many.zip", zip_entries=1000)
    assert "E_ZIP_ENTRIES" in {i["code"] for i in over["issues"]}
    assert over["members"] == [], "bounds are evaluated before any member is processed"
    exact = sniff_io.expand_container(many, logical="many.zip", zip_entries=1001)
    assert exact["issues"] == [] and len(exact["members"]) == 1001

    cumulative_entries = _put(tmp_path, "cum-entries.zip", gen.zip_cumulative_entries())
    cum = sniff_io.expand_container(cumulative_entries, logical="cum-entries.zip", zip_entries=1000)
    assert "E_ZIP_ENTRIES" in {i["code"] for i in cum["issues"]}, "entries are cumulative over nested archives"

    cumulative_total = _put(tmp_path, "cum-total.zip", gen.zip_cumulative_total())
    single = sniff_io.sniff(cumulative_total, logical="cum-total.zip", zip_total_bytes=2500)
    assert "E_ZIP_TOTAL" not in _codes(single), "each archive alone is under the bound"
    total = sniff_io.expand_container(cumulative_total, logical="cum-total.zip", zip_total_bytes=2500)
    assert "E_ZIP_TOTAL" in {i["code"] for i in total["issues"]}
    assert {m['logical'] for m in total['members']} == {
        'cum-total.zip/middle.zip', 'cum-total.zip/middle.zip/inner.zip'}
    assert all('E_ZIP_TOTAL' in _codes(m['sniff']) for m in total['members']), \
        'a later bound failure preserves discovered members as report-only evidence'

    bomb = _put(tmp_path, "bomb.zip", gen.zip_bomb("a"))
    bombed = sniff_io.expand_container(bomb, logical="bomb.zip")
    assert "E_ZIP_BOMB" in {i["code"] for i in bombed["issues"]}


@pytest.mark.req("REQ-CTR-03")
@pytest.mark.cov("S1", "FM0")
@pytest.mark.fx("FX-43")
def test_T_CTR_03_members_sniffed_independently(tmp_path, gen):
    members_in = {
        "docs/report.pdf": gen.pdf_text(1),
        "notes.txt": gen.txt_utf8(),
        "files/memo.docx": gen.docx_like({"i.png": gen.png_noise(seed=43)}),
    }
    bundle = _put(tmp_path, "pack.zip", gen.make_zip(members_in))

    container = sniff_io.expand_container(bundle, logical="pack.zip")

    assert container["logical"] == "pack.zip" and container["issues"] == []
    by_member = {m["member"]: m for m in container["members"]}
    assert set(by_member) == set(members_in)
    expected_format = {"docs/report.pdf": "pdf", "notes.txt": "txt", "files/memo.docx": "docx"}
    for name, data in members_in.items():
        member = by_member[name]
        assert member["logical"] == f"pack.zip/{name}"
        assert member["data"] == data
        assert member["sniff"]["sha256"] == hashlib.sha256(data).hexdigest(), "member sha256 is of the member bytes"
        assert member["sniff"]["bytes"] == len(data)
        assert member["sniff"]["format"] == expected_format[name]
        assert member["sniff"]["route"] == "NATIVE"
        assert member["sniff"]["path"] == f"pack.zip/{name}"


@pytest.mark.req("REQ-CTR-04")
@pytest.mark.cov("S1", "FM4")
@pytest.mark.fx("FX-16", "FX-23", "FX-33", "FX-35", "FX-43")
def test_T_CTR_04_office_family_zips_are_never_containers(tmp_path, gen):
    packages = {
        "memo.docx": (gen.docx_like({"i.png": gen.png_noise(seed=1)}), "docx", "NATIVE"),
        "korean.hwpx": (gen.hwpx_like(), "hwpx", "NATIVE"),
        "book.epub": (gen.epub_like(), "epub", "NATIVE"),
        "letter.odt": (gen.odt_like(), "odt", "LEGACY"),
    }
    for name, (data, fmt, route) in packages.items():
        path = _put(tmp_path, name, data)
        alone = sniff_io.sniff(path, logical=name)
        assert (alone["format"], alone["route"]) == (fmt, route), name
        tight = sniff_io.sniff(path, logical=name, zip_entries=1)
        assert "E_ZIP_ENTRIES" in _codes(tight), f"{name}: Office-family zips still get the archive preflight"
        assert tight["route"] == route and tight["route"] != "CONTAINER"

    outer = _put(tmp_path, "outer.zip", gen.make_zip({name: data for name, (data, _, _) in packages.items()} | {"inner.zip": gen.make_zip({"a.txt": b"a"})}))
    container = sniff_io.expand_container(outer, logical="outer.zip")
    by_member = {m["member"]: m for m in container["members"]}
    for name, (_, fmt, route) in packages.items():
        assert by_member[name]["sniff"]["format"] == fmt, name
        assert by_member[name]["sniff"]["route"] == route, name
    assert by_member["inner.zip"]["sniff"]["route"] == "CONTAINER"
    assert not any(m["logical"].startswith(f"outer.zip/{name}/") for m in container["members"] for name in packages), \
        "package internals are not listed as members"
