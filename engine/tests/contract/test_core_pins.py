"""Pins execute the INSTALLED markitdown-gc, never a replacement Core stub."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import ast
import importlib.metadata
import importlib.util
import inspect
import json
import re
import zipfile

import pytest


CORPUS = ("FX-01", "FX-02", "FX-03", "FX-04", "FX-06", "FX-07", "FX-09", "FX-11",
          "FX-12", "FX-15", "FX-16", "FX-17", "FX-19", "FX-23", "FX-28", "FX-30", "FX-31")


@pytest.mark.req("REQ-GEN-02", "REQ-TRI-03")
@pytest.mark.cov("S2", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
@pytest.mark.parametrize("fx", CORPUS)
def test_CT_01_schema_rules_and_v1_types(installed_core, contract_fx, fx):
    report = installed_core[2](contract_fx.path(fx))
    assert type(report) is dict
    assert type(report["schema_version"]) is int and report["schema_version"] == 1
    assert report["rules_version"] == "1"
    assert isinstance(report["decision"], str)
    assert isinstance(report["coverage"], dict)
    assert type(report["coverage"]["pages_inspected"]) is int
    assert report["coverage"]["pages_total"] is None or type(report["coverage"]["pages_total"]) is int
    for field in ("candidates", "issues", "pages", "rasters"):
        assert isinstance(report[field], list)
    assert set(report["file"]) == {"sha256", "bytes", "format"}


@pytest.mark.req("REQ-CLS-05", "REQ-CLS-06")
@pytest.mark.cov("S3", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_CT_02_decision_and_state_vocabularies(installed_core, contract_fx):
    reports = [installed_core[2](contract_fx.path(fx)) for fx in CORPUS]
    assert {r["decision"] for r in reports} == {"ocr_recommended", "review", "no_candidates", "unknown"}
    assert {r["coverage"]["state"] for r in reports} == {"complete", "partial", "none", "not_applicable"}


@pytest.mark.req("REQ-CLS-05", "REQ-GEN-10", "REQ-TRI-04")
@pytest.mark.cov("S2", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_CT_03_closed_vocabulary_and_regenerated_goldens(installed_core, contract_fx, contract_data, repo_root, tmp_path):
    # Supplement exercised reports with the installed module's literal emissions;
    # rarely reached bound/dependency paths still participate in vocabulary drift.
    import markitdown.ocr_triage as core_triage
    tree = ast.parse(inspect.getsource(core_triage))
    codes, reasons = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            expression = None
            if isinstance(node.func, ast.Name) and node.func.id == "_issue":
                expression = node.args[1]
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "issue":
                expression = node.args[0]
            if expression is not None:
                codes.update(n.value for n in ast.walk(expression) if isinstance(n, ast.Constant) and isinstance(n.value, str))
            if isinstance(node.func, ast.Name) and node.func.id == "_candidate":
                reasons.update(n.value for n in ast.walk(node.args[5]) if isinstance(n, ast.Constant) and isinstance(n.value, str))
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "reasons" and node.func.attr == "append":
                reasons.add(ast.literal_eval(node.args[0]))
    assert codes == contract_data.CORE_CODES
    assert reasons == contract_data.CORE_REASONS
    path = repo_root / "tools/golden.py"
    spec = importlib.util.spec_from_file_location("golden_contract_tool", path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    lock = tool.verify(repo_root)
    for fx in lock["sources"]:
        source = contract_fx.path("FX-17", variant="b") if fx == "FX-17b" else contract_fx.path("FX-02", pages=12) if fx == "FX-02-12p" else contract_fx.path(fx)
        report = installed_core[2](source)
        relative = {"FX-17b": "FX-17/triage-b.json", "FX-02-12p": "FX-02/triage-12p.json"}.get(fx, f"{fx}/triage.json")
        golden = repo_root / "engine/tests/golden" / relative
        assert report == json.loads(golden.read_text(encoding="utf-8")), fx
        assert {i["code"] for i in report["issues"]} <= contract_data.CORE_CODES
        assert {reason for c in report["candidates"] for reason in c["reasons"]} <= contract_data.CORE_REASONS
        assert contract_data.digest(source.read_bytes()) == lock["sources"][fx]["sha256"]
    assert len(contract_data.CORE_CODES) == 14
    # Verification must detect tampering, not merely parse a lock file.
    import shutil
    golden_copy = tmp_path / "engine/tests/golden"
    shutil.copytree(repo_root / "engine/tests/golden", golden_copy)
    first = next(golden_copy.glob("FX-*/triage.json"))
    original_bytes = first.read_bytes()
    first.write_bytes(original_bytes + b" ")
    with pytest.raises(AssertionError, match="golden"):
        tool.verify(tmp_path)
    first.write_bytes(original_bytes)
    copied_lock = golden_copy / "GOLDEN.lock"
    original_lock = copied_lock.read_bytes()
    wrong_version = json.loads(original_lock)
    wrong_version["core_version"] = "0.0.0"
    copied_lock.write_text(json.dumps(wrong_version), encoding="utf-8")
    with pytest.raises(AssertionError, match="Core version"):
        tool.verify(tmp_path)
    copied_lock.write_bytes(original_lock)
    first.unlink()
    with pytest.raises(AssertionError, match="golden"):
        tool.verify(tmp_path)


@pytest.mark.req("REQ-MAP-01", "REQ-MAP-02", "REQ-MAP-08", "REQ-CLS-02")
@pytest.mark.cov("S3", "FM12")
@pytest.mark.fx("FX-03", "FX-11", "FX-17")
def test_CT_04_candidate_shapes_and_repeated_ids(installed_core, contract_fx):
    pdf = installed_core[2](contract_fx.path("FX-03"))
    assert pdf["candidates"], "Mixed fixture must contain scanned pages"
    for c in pdf["candidates"]:
        assert c["id"] == f"p{c['page']}" and c["kind"] == "page"
        assert 1 <= c["page"] <= pdf["coverage"]["pages_total"]
    raster = installed_core[2](contract_fx.path("FX-11"))
    assert [(c["id"], c["kind"], c["page"]) for c in raster["candidates"]] == [(f"f{n}", "image", None) for n in (1, 2, 3)]
    office = installed_core[2](contract_fx.path("FX-17"))
    ids = [c["id"] for c in office["candidates"]]
    assert len(ids) == 2 and len(set(ids)) == 1
    assert all(c["kind"] == "image" and c["page"] is None and c["id"].startswith("word/media/") for c in office["candidates"])


@pytest.mark.req("REQ-CNV-02")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-03")
def test_CT_05_one_page_pdf_conversion_has_no_anchors(installed_core, contract_fx):
    import pypdfium2 as pdfium
    core = installed_core[0](enable_plugins=False)
    bodies = []
    with pdfium.PdfDocument(contract_fx.path("FX-03").read_bytes()) as pdf:
        assert len(pdf) == 4
        for number in range(len(pdf)):
            with pdfium.PdfDocument.new() as one:
                one.import_pages(pdf, [number])
                stream = BytesIO()
                one.save(stream)
                stream.seek(0)
                bodies.append(core.convert_stream(stream, file_extension=".pdf").text_content)
    assert bodies[0].strip() and bodies[2].strip()
    assert not bodies[1].strip() and not bodies[3].strip()
    assert all("mdflow:page" not in body for body in bodies)


@pytest.mark.req("REQ-TRI-05")
@pytest.mark.cov("S2", "FM0")
@pytest.mark.fx("FX-01", "FX-03", "FX-16")
@pytest.mark.parametrize("fx", ("FX-01", "FX-03", "FX-16"))
def test_CT_06_triage_preserves_input_bytes_and_stream_position(installed_core, contract_fx, fx):
    path = contract_fx.path(fx)
    before = path.read_bytes()
    installed_core[2](path)
    assert path.read_bytes() == before
    stream = BytesIO(before)
    stream.seek(7)
    installed_core[2](stream)
    assert stream.tell() == 7 and stream.getvalue() == before


@pytest.mark.req("REQ-RND-02", "REQ-MAP-02")
@pytest.mark.cov("S6", "FM11")
@pytest.mark.fx("FX-11", "FX-12", "FX-15")
def test_CT_07_frames_cap_probe_failure_and_no_total(installed_core, contract_fx, contract_data, tmp_path):
    for fx, count in (("FX-11", 3), ("FX-12", 2)):
        report = installed_core[2](contract_fx.path(fx))
        assert [c["id"] for c in report["candidates"]] == [f"f{n}" for n in range(1, count + 1)]
        assert all(c["page"] is None for c in report["candidates"])
        assert "frames_total" not in json.dumps(report)
    capped = tmp_path / "101frames.tiff"
    capped.write_bytes(contract_data.image_bytes("TIFF", frames=101, size=(24, 24)))
    report = installed_core[2](capped)
    assert len(report["rasters"]) == 100 and report["coverage"]["state"] == "partial"
    assert "frame_cap" in {i["code"] for i in report["issues"]}
    failed = installed_core[2](contract_fx.path("FX-15"))
    assert "image_probe_failed" in {i["code"] for i in failed["issues"]}
    assert [(c["id"], c["page"]) for c in failed["candidates"]] == [("image", None)]


@pytest.mark.req("REQ-CNV-03", "REQ-MAP-03")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-16", "FX-21", "FX-22", "FX-23")
@pytest.mark.parametrize("fx,ext", (("FX-16", "docx"), ("FX-21", "pptx"), ("FX-22", "xlsx"), ("FX-23", "hwpx")))
def test_CT_08_extracted_media_name_is_member_hash(installed_core, contract_fx, tmp_path, fx, ext):
    source = contract_fx.path(fx)
    media = tmp_path / "media"
    result = installed_core[0](enable_plugins=False).convert_stream(BytesIO(source.read_bytes()),
        file_extension="." + ext, extract_media=str(media), media_base_dir=str(tmp_path))
    with zipfile.ZipFile(source) as archive:
        hashes = {sha256(archive.read(n)).hexdigest()[:12] for n in archive.namelist() if "/media/" in n or n.startswith("BinData/")}
    assert hashes, "Fixture must have media members"
    assert media.is_dir() and list(media.iterdir()), "Core extraction produced no files"
    assert all(p.stem in hashes and sha256(p.read_bytes()).hexdigest()[:12] == p.stem for p in media.iterdir())
    if ext in {"docx", "pptx", "hwpx"}:
        assert "media/" in result.text_content


@pytest.mark.req("REQ-MAP-05")
@pytest.mark.cov("S5", "FM0")
@pytest.mark.fx("FX-24")
def test_CT_09_hwp_payload_hash_and_stored_stream(installed_core, contract_fx, contract_data, tmp_path):
    path = contract_fx.path("FX-24")
    assert path.stat().st_size < 8192
    provenance = contract_data.ROOT / "engine/tests/fixtures/README.md"
    assert provenance.is_file(), "FX-24 own-work provenance README pending"
    assert "FX-24" in provenance.read_text(encoding="utf-8")
    report = installed_core[2](path)
    assert report.get("media"), "FX-24 must exercise HWP5 payload mapping"
    assert any(m["payload_kind"] == "stored_ole_stream" for m in report["media"]), "FX-24 needs an unsupported stored-stream case"
    media = tmp_path / "media"
    installed_core[0](enable_plugins=False).convert_stream(BytesIO(path.read_bytes()), file_extension=".hwp",
        extract_media=str(media), media_base_dir=str(tmp_path))
    for row in report["media"]:
        assert row["payload_kind"] in {"parser_image_payload", "stored_ole_stream"}
        assert re.fullmatch(r"[0-9a-f]{64}", row["payload_sha256"])
        if row["payload_kind"] == "parser_image_payload":
            matches = list(media.glob(row["payload_sha256"][:12] + ".*"))
            assert len(matches) == 1 and sha256(matches[0].read_bytes()).hexdigest() == row["payload_sha256"]


@pytest.mark.req("REQ-GEN-01")
@pytest.mark.cov("S2", "FM10")
@pytest.mark.fx("FX-23", "FX-24")
@pytest.mark.parametrize("fx", ("FX-23", "FX-24"))
def test_CT_10_hwp_no_missing_dependency(installed_core, contract_fx, fx):
    report = installed_core[2](contract_fx.path(fx))
    assert "missing_dependency" not in {i["code"] for i in report["issues"]}
    assert report["file"]["format"] == ("hwp" if fx == "FX-24" else "hwpx")


@pytest.mark.req("REQ-CNV-05")
@pytest.mark.cov("S5", "FM9")
@pytest.mark.fx("FX-28", "FX-38")
def test_CT_11_core_offline_bytes_and_uri_filename(installed_core, contract_fx, socket_guard):
    core = installed_core[0](enable_plugins=False, llm_client=None, docintel_endpoint=None)
    stream_info = installed_core[1](extension=".txt", filename="https://example.invalid/secret.txt")
    result = core.convert_stream(BytesIO(contract_fx.path("FX-28").read_bytes()), stream_info=stream_info)
    assert "Own UTF-8 fixture" in result.text_content
    assert not socket_guard.attempts


@pytest.mark.req("REQ-TRI-01")
@pytest.mark.cov("S2", "FM4")
@pytest.mark.fx("FX-28", "FX-30", "FX-31")
def test_CT_12_text_html_csv_verdicts(installed_core, contract_fx):
    txt = installed_core[2](contract_fx.path("FX-28"))
    assert txt["coverage"]["state"] == "not_applicable" and txt["decision"] == "no_candidates"
    for fx, code in (("FX-31", "media_not_inspected"), ("FX-30", "unsupported_format")):
        report = installed_core[2](contract_fx.path(fx))
        assert code in {i["code"] for i in report["issues"]}


@pytest.mark.req("REQ-GEN-02", "REQ-PKG-03")
@pytest.mark.cov("S0", "FM10")
def test_CT_13_installed_version_and_startup_range_gate(repo_root):
    from packaging.version import Version
    installed = Version(importlib.metadata.version("markitdown-gc"))
    assert Version("0.3.5") <= installed < Version("0.4")
    spec = importlib.util.spec_from_file_location("core_version_red", repo_root / "engine/src/mdflow/hashing.py")
    hashing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hashing)
    for value, expected in (("0.3.4", False), ("0.3.5", True), ("0.3.99", True), ("0.4.0", False), ("1.0.0", False)):
        assert hashing.core_version_supported(value) is expected


@pytest.mark.req("REQ-ASM-P3", "REQ-SEC-02", "REQ-TRI-04")
@pytest.mark.cov("S2", "FM9")
@pytest.mark.fx("FX-06")
def test_CT_14_report_has_no_absolute_path_or_exception_text(installed_core, contract_fx, tmp_path):
    sentinel = "SECRET_EXCEPTION_AND_USERNAME_9c36"
    class HostileStream(BytesIO):
        def read(self, *args):
            raise OSError(str(tmp_path) + "/" + sentinel)
    report = installed_core[2](HostileStream(b"%PDF-1.4"))
    original = deepcopy(report)
    encoded = json.dumps(report)
    assert sentinel not in encoded and str(tmp_path) not in encoded
    assert "corrupt" in {i["code"] for i in report["issues"]}
    assert report == original
