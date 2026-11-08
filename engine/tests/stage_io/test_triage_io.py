"""T-TRI-01..06 (TESTPLAN step 5): Triage wrapper over a fake Core. RED: stubs raise NotImplementedError.

Sniff results are SniffResult-shaped literals (gen.fake_sniff) so the wrapper is tested in isolation;
the reports are minimal envelopes -- the wrapper checks only the envelope and never reads other fields.
"""

import copy
import hashlib
from pathlib import Path

import pytest

from mdflow import triage


def _put(directory, name, data):
    path = Path(directory) / name
    path.write_bytes(data)
    return path


def _codes(outcome):
    return [issue["code"] for issue in outcome["issues"]]


@pytest.mark.req("REQ-TRI-01")
@pytest.mark.cov("S2", "FM0")
@pytest.mark.fx("FX-28", "FX-30", "FX-05")
def test_T_TRI_01_runs_for_every_native_source_and_nothing_else(tmp_path, gen, fake_core):
    native = [("notes.txt", gen.txt_utf8(), "txt"), ("table.csv", b"a,b\n1,2\n", "csv"),
              ("page.html", b"<html><img src='x.png'></html>", "html"), ("doc.md", b"# t\n", "md"),
              ("clean.pdf", gen.pdf_text(1), "pdf")]
    other = [("locked.pdf", gen.pdf_encrypt_trailer(), "pdf", "PROTECTED"), ("old.doc", gen.cfb_legacy("doc"), "doc", "LEGACY"),
             ("song.mp3", b"ID3" + gen.rng_bytes(32, 38), "mp3", "UNSUPPORTED"), ("pack.zip", gen.zip_basic(), "zip", "CONTAINER")]

    for name, data, fmt in native:
        path = _put(tmp_path, name, data)
        before = len(fake_core.triage_calls)
        outcome = triage.run_triage(path, gen.fake_sniff(path, fmt=fmt))
        assert outcome["ran"] is True, name
        assert len(fake_core.triage_calls) == before + 1, f"{name}: exactly one Core call"
        args, kwargs = fake_core.triage_calls[-1]
        assert Path(args[0]) == path and kwargs == {}, "Core is called as triage(path) with default options"

    for name, data, fmt, route in other:
        path = _put(tmp_path, name, data)
        before = len(fake_core.triage_calls)
        outcome = triage.run_triage(path, gen.fake_sniff(path, fmt=fmt, route=route))
        assert len(fake_core.triage_calls) == before, f"{name}: Core must not run for route {route}"
        assert outcome["ran"] is False and outcome["report"] is None and outcome["issues"] == []


@pytest.mark.req("REQ-TRI-02")
@pytest.mark.cov("S2", "FM1")
@pytest.mark.fx("FX-02", "FX-30")
def test_T_TRI_02_exception_becomes_triage_fail(tmp_path, gen, fake_core):
    def explode(*args, **kwargs):
        raise RuntimeError(f"boom while reading {args[0]}")

    fake_core.triage_impl = explode
    for name, data, fmt in (("table.csv", b"a,b\n", "csv"), ("scan.pdf", gen.pdf_scan(3), "pdf")):
        path = _put(tmp_path, name, data)
        outcome = triage.run_triage(path, gen.fake_sniff(path, fmt=fmt))
        assert _codes(outcome) == ["E_TRIAGE_FAIL"], name
        assert outcome["ran"] is True and outcome["report"] is None
        assert outcome["coverage_state"] == "not_run"
        assert str(tmp_path) not in outcome["issues"][0]["message"], "no absolute path in the diagnostic"


@pytest.mark.req("REQ-TRI-03")
@pytest.mark.cov("S2", "FM10")
@pytest.mark.fx("FX-60", "FX-02", "FX-30")
def test_T_TRI_03_envelope_check_before_any_field(tmp_path, gen, fake_core):
    cases = [("scan.pdf", gen.pdf_scan(1), "pdf"), ("doc.md", b"# t\n", "md")]
    bad_reports = [
        {"schema_version": 2, "decision": "no_candidates"},
        {"schema_version": 0}, {"schema_version": True}, {"schema_version": "1"}, {"decision": "no_candidates"},
        [], None, "not a report",
    ]
    for name, data, fmt in cases:
        path = _put(tmp_path, name, data)
        sniff_result = gen.fake_sniff(path, fmt=fmt)
        for report in bad_reports:
            fake_core.triage_impl = lambda *a, _r=report, **k: _r
            outcome = triage.run_triage(path, sniff_result)
            assert _codes(outcome) == ["E_TRIAGE_SCHEMA"], (name, report)
        fake_core.triage_impl = lambda *a, **k: {"schema_version": 1, "rules_version": "1", "decision": "no_candidates"}
        assert _codes(triage.run_triage(path, sniff_result)) == [], name


@pytest.mark.req("REQ-TRI-04")
@pytest.mark.cov("S2", "FM0")
@pytest.mark.fx("FX-03")
def test_T_TRI_04_report_returned_verbatim(tmp_path, gen, fake_core):
    report = {
        "schema_version": 1, "rules_version": "1", "decision": "ocr_recommended",
        "coverage": {"state": "complete", "pages_total": 4, "pages_inspected": 4},
        "candidates": [{"id": "p2", "kind": "page", "page": 2, "priority": "high", "reasons": ["scan_like"]}],
        "issues": [{"code": "frame_cap", "detail": "free text"}],
        "pages": [{"n": 1, "chars": 12}], "unknown_future_key": {"nested": [1, 2, {"x": None}]},
    }
    snapshot = copy.deepcopy(report)
    fake_core.triage_impl = lambda *a, **k: report
    path = _put(tmp_path, "mixed.pdf", gen.pdf_mixed())

    outcome = triage.run_triage(path, gen.fake_sniff(path, fmt="pdf"))

    assert outcome["report"] == snapshot, "the stored report equals what Core returned"
    assert report == snapshot, "the report object was not modified in place"
    assert outcome["coverage_state"] == "complete"
    assert outcome["issues"] == []


@pytest.mark.req("REQ-TRI-05")
@pytest.mark.cov("S2", "FM0")
@pytest.mark.fx("all")
def test_T_TRI_05_triage_does_not_touch_the_file(tmp_path, gen, fake_core):
    for name, path in gen.sample_files(tmp_path).items():
        if name == "empty.pdf":
            continue
        data = path.read_bytes()
        stat = path.stat()
        listing = sorted(p.name for p in tmp_path.iterdir())
        sniff_result = gen.fake_sniff(path, fmt=path.suffix.lstrip("."), route="NATIVE")
        triage.run_triage(path, sniff_result)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(data).hexdigest(), name
        assert path.stat().st_mtime_ns == stat.st_mtime_ns and path.stat().st_size == stat.st_size, name
        assert sorted(p.name for p in tmp_path.iterdir()) == listing, f"{name}: no sidecar files next to the source"


@pytest.mark.req("REQ-TRI-01")
@pytest.mark.cov("S2", "FM4")
@pytest.mark.fx("FX-30", "FX-33")
def test_T_TRI_06_not_run_when_core_returns_no_state(tmp_path, gen, fake_core):
    envelope = {"schema_version": 1, "rules_version": "1", "decision": "unknown", "candidates": []}
    reports = [
        ("table.csv", b"a,b\n", "csv", {**envelope, "issues": [{"code": "unsupported_format", "detail": "csv"}]}, "not_run"),
        ("page.html", b"<html/>", "html", {**envelope, "coverage": {}, "issues": [{"code": "media_not_inspected"}]}, "not_run"),
        ("book.xls", gen.cfb_legacy("xls"), "xls", {**envelope, "coverage": {"reason": "not inspected"}}, "not_run"),
        ("doc.md", b"# t\n", "md", {**envelope, "coverage": {"state": "none", "reason": "media_not_inspected"}}, "none"),
        ("notes.txt", gen.txt_utf8(), "txt", {**envelope, "decision": "no_candidates", "coverage": {"state": "not_applicable"}}, "not_applicable"),
    ]
    for name, data, fmt, report, expected in reports:
        path = _put(tmp_path, name, data)
        fake_core.triage_impl = lambda *a, _r=report, **k: _r
        outcome = triage.run_triage(path, gen.fake_sniff(path, fmt=fmt))
        assert outcome["coverage_state"] == expected, name
        assert outcome["report"] == report, name
