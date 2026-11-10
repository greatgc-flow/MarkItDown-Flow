"""Step 2: independent byte/hash oracles and mutations of pinned Core reports."""
from copy import deepcopy
from hashlib import sha256
import math
import random

import pytest


def signature(c):
    return tuple(c[k] for k in ("route", "need", "label", "action"))


def issue_codes(c):
    return {i["code"] for i in c["issues"]}


@pytest.mark.req("REQ-SNF-03")
@pytest.mark.cov("S1", "FM0")
@pytest.mark.fx("FX-13", "FX-40", "FX-41")
def test_T_SNF_11_pure_magic_precedence_and_empty(core_api, core_data):
    detect = core_api.sniff_pure.detect_format
    for header, ext, expected in ((b"%PDF-1.4\n", "docx", "pdf"),
        (b"RIFF\x08\0\0\0WEBP", "bin", "webp"), (b"II+\0", "bin", "tiff"),
        (b"MM\0+", "bin", "tiff"), (b"\x89PNG\r\n\x1a\n", "png", "png")):
        result = detect(header, ext)
        assert result["format"] == expected and result["route"] == "NATIVE"
    assert "W_EXT_MISMATCH" in issue_codes(detect(b"%PDF-1.4", "docx"))
    assert "E_CORRUPT" in issue_codes(detect(b"", "pdf"))
    for member, ext, fmt, route in (("word/document.xml", "zip", "docx", "NATIVE"),
        ("ppt/presentation.xml", "zip", "pptx", "NATIVE"),
        ("xl/workbook.xml", "zip", "xlsx", "NATIVE"),
        ("Contents/content.hpf", "zip", "hwpx", "NATIVE"),
        ("META-INF/container.xml", "epub", "epub", "NATIVE"),
        ("META-INF/manifest.xml", "odt", "odt", "LEGACY")):
        assert (lambda r: (r["format"], r["route"]))(detect(b"PK\x03\x04", ext, members=(member,))) == (fmt, route)
    assert detect(b"PK\x03\x04", "zip", encrypted=True)["route"] == "PROTECTED"
    for ext, route in (("txt", "NATIVE"), ("csv", "NATIVE"), ("pages", "LEGACY"),
                       ("mp3", "UNSUPPORTED"), ("xyz", "UNSUPPORTED")):
        assert detect(b"unrecognised", ext)["route"] == route


@pytest.mark.req("REQ-SNF-06")
@pytest.mark.cov("S1", "FM0")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_SNF_12_pure_result_and_canonical_hashes(core_api, core_data):
    value = {"z": [None, True, 3], "가": "é\n", "a": {"b": 2}}
    expected = core_data.canonical(value)
    assert core_api.hashing.canonical_json(value) == expected
    assert core_api.hashing.sha256(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    for invalid in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            core_api.hashing.canonical_json({"bad": invalid})
    data = "Own UTF-8 fixture. 한국어\n".encode()
    detection = dict(ext="txt", magic="unknown", format="txt", route="NATIVE", reasons=[], issues=[])
    result = core_api.sniff_pure.sniff_result(data, "docs/a.txt", ".", detection)
    assert set(result) == {"path", "root", "bytes", "sha256", "ext", "magic", "format", "route", "reasons", "issues"}
    assert result["sha256"] == sha256(data).hexdigest() and result["bytes"] == len(data)
    assert result["path"] == "docs/a.txt" and result["format"] == "txt"


@pytest.mark.req("REQ-CLS-01")
@pytest.mark.cov("S3", "FM0")
@pytest.mark.fx("FX-60")
def test_T_CLS_01_totality_with_unknown_values(core_api, core_fx):
    base = core_fx.report("FX-03")
    sniff = core_fx.sniff()
    rng = random.Random(43)
    inputs = [None, [], "not an object", {}, base]
    for _ in range(40):
        report = deepcopy(base)
        field = rng.choice(("decision", "state", "priority", "kind"))
        unknown = "future_" + str(rng.getrandbits(64))
        if field == "decision":
            report[field] = unknown
        elif field == "state":
            report["coverage"]["state"] = unknown
        else:
            report["candidates"][0][field] = unknown
        inputs.append(report)
    before = deepcopy(inputs)
    for report in inputs:
        result = core_api.classify.classify(sniff, report)
        assert result["route"] in {"NATIVE", "UNSUPPORTED", "CONTAINER", "LEGACY", "PROTECTED"}
        assert result["need"] in {"NONE", "PARTIAL", "FULL", "UNKNOWN"}
        assert result["action"] in {"convert_only", "convert_and_ocr", "report_only", "recurse"}
        assert len(result) == 10
    assert inputs == before


@pytest.mark.req("REQ-CLS-02")
@pytest.mark.cov("S3", "FM0")
@pytest.mark.fx("FX-03", "FX-16", "FX-17")
@pytest.mark.parametrize("fx,fmt", (("FX-03", "pdf"), ("FX-16", "docx"), ("FX-17", "docx")))
def test_T_CLS_02_schema_refs_and_reason_copy(core_api, core_fx, fx, fmt):
    report = core_fx.report(fx)
    result = core_api.classify.classify(core_fx.sniff(fx, format=fmt), report)
    assert set(result) == {"route", "need", "label", "action", "decision", "coverage_state",
                           "candidates_unique", "uninspected_pages", "reasons", "issues"}
    ids = list(dict.fromkeys(c["id"] for c in report["candidates"]))
    assert [c["id"] for c in result["candidates_unique"]] == ids
    for candidate in result["candidates_unique"]:
        assert set(candidate) == {"id", "kind", "page", "priority", "priority_core", "refs"}
        assert candidate["refs"] == sum(c["id"] == candidate["id"] for c in report["candidates"])
    assert {"core:" + i["code"] for i in report["issues"]} <= set(result["reasons"])
    assert {"cand:" + r for c in report["candidates"] for r in c["reasons"]} <= set(result["reasons"])
    assert result["uninspected_pages"] == (report["coverage"]["pages_total"] - report["coverage"]["pages_inspected"] if fmt == "pdf" else 0)


@pytest.mark.req("REQ-CLS-03")
@pytest.mark.cov("S3", "FM0")
@pytest.mark.fx("FX-02", "FX-03")
def test_T_CLS_03_s_and_m_select_the_same_units(core_api, core_fx, core_data):
    report = core_fx.report("FX-03")
    mixed = core_api.classify.classify(core_fx.sniff(), report)
    assert mixed["label"] == "M"
    scanned = core_data.Cases(".").classification()
    scanned.update(deepcopy(mixed), need="FULL", label="S")
    assert core_api.select.select(scanned, core_data.options()) == core_api.select.select(mixed, core_data.options())


@pytest.mark.req("REQ-CLS-04")
@pytest.mark.cov("S3", "FM10")
@pytest.mark.fx("FX-19", "FX-60")
def test_T_CLS_04_priorities_unknown_reasons_and_issue_codes(core_api, core_fx):
    sniff, report = core_fx.sniff(), core_fx.report("FX-03")
    baseline = core_api.classify.classify(sniff, report)
    assert all(c["priority"] == "normal" for c in baseline["candidates_unique"] if c["priority_core"] == "high")
    low = deepcopy(report)
    low["decision"] = "review"
    for c in low["candidates"]:
        c["priority"] = "low"
    result = core_api.classify.classify(sniff, low)
    assert all(c["priority"] == "low" for c in result["candidates_unique"])
    assert "W_REVIEW_PRIORITY" in issue_codes(result)
    for mutate in (lambda r: r["candidates"][0].update(priority="medium"),
                   lambda r: r["issues"].append(dict(code="future_issue", detail="fixture"))):
        changed = deepcopy(report)
        mutate(changed)
        c = core_api.classify.classify(sniff, changed)
        assert signature(c) == ("NATIVE", "UNKNOWN", "U", "convert_only")
        assert "W_TRIAGE_UNKNOWN_VALUE" in issue_codes(c)
    changed = deepcopy(report)
    changed["candidates"][0]["reasons"].append("future_reason")
    c = core_api.classify.classify(sniff, changed)
    assert signature(c) == signature(baseline)
    assert "cand:future_reason" in c["reasons"] and "W_TRIAGE_UNKNOWN_VALUE" in issue_codes(c)


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S3", "FM0")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_CLS_05_every_golden_matches_named_review(core_api, core_fx, repo_root):
    root = repo_root / "engine/tests/golden"
    reports = sorted(root.glob("FX-*/triage.json"))
    assert reports, "Orchestrator-generated golden corpus pending"
    for path in reports:
        expected_path = path.with_name("classification.json")
        review_path = path.with_name("classification.review.json")
        assert expected_path.is_file() and review_path.is_file(), f"Named classification review pending: {path.parent.name}"
        import json
        review = json.loads(review_path.read_text(encoding="utf-8"))
        assert review["reviewer"] and review["verdict"] == "PASS"
        # The sniff oracle is independent reviewed data, not inferred from Core.
        assert "sniff" in review
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert core_api.classify.classify(review["sniff"], core_fx.report(path.parent.name)) == expected


@pytest.mark.req("REQ-CLS-06")
@pytest.mark.cov("S3", "FM11")
@pytest.mark.fx("FX-07", "FX-60")
@pytest.mark.parametrize("state", ("partial", "none"))
def test_T_CLS_06_partial_never_full_or_partial(core_api, core_fx, state):
    report = deepcopy(core_fx.report("FX-07"))
    assert report["coverage"]["pages_total"] == 1001
    assert report["coverage"]["pages_inspected"] == 1000
    report["coverage"]["state"] = state
    result = core_api.classify.classify(core_fx.sniff("FX-07"), report)
    assert signature(result) == ("NATIVE", "UNKNOWN", "U", "convert_and_ocr")
    assert result["candidates_unique"] and result["uninspected_pages"] == 1
    assert "W_TRIAGE_PARTIAL" in issue_codes(result)


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S3", "FM10")
@pytest.mark.fx("FX-60")
@pytest.mark.parametrize("code", "corrupt encrypted external_media frame_cap image_probe_failed media_not_inspected missing_dependency page_cap too_large unresolved_embed unsupported_compression unsupported_format unsupported_media zip_limit".split())
def test_T_CLS_07_every_core_issue_policy(core_api, core_fx, code):
    report = deepcopy(core_fx.report("FX-03"))
    sniff = core_fx.sniff()
    report["issues"] = [dict(code=code, detail="fixture mutation")]
    if code == "media_not_inspected":
        sniff["format"] = "html"
        report["file"]["format"] = "unknown"
        report["decision"], report["candidates"] = "unknown", []
    elif code in {"too_large", "unsupported_format"}:
        report["decision"], report["candidates"] = "unknown", []
        report["coverage"]["state"] = "none"
    elif code in {"page_cap", "frame_cap", "zip_limit", "unsupported_compression", "external_media", "unresolved_embed"}:
        report["coverage"]["state"] = "partial"
    elif code in {"missing_dependency", "corrupt"}:
        report["decision"] = "unknown"
    result = core_api.classify.classify(sniff, report)
    assert "core:" + code in result["reasons"]
    expected = {
        'corrupt': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_TRIAGE_UNKNOWN'}),
        'encrypted': (('PROTECTED','UNKNOWN','P','report_only'), {'E_ENCRYPTED'}),
        'external_media': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_EXTERNAL_MEDIA','W_TRIAGE_PARTIAL'}),
        'frame_cap': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_TRIAGE_PARTIAL'}),
        'image_probe_failed': (('NATIVE','PARTIAL','M','convert_and_ocr'), {'W_IMAGE_PROBE'}),
        'media_not_inspected': (('NATIVE','NONE','T','convert_only'), {'W_MEDIA_NOT_INSPECTED'}),  # R33 html
        'missing_dependency': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_CORE_DEPENDENCY','W_TRIAGE_UNKNOWN'}),
        'page_cap': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_TRIAGE_PARTIAL'}),
        'too_large': (('NATIVE','UNKNOWN','U','convert_only'), {'W_TRIAGE_UNKNOWN'}),
        'unresolved_embed': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_UNRESOLVED_EMBED','W_TRIAGE_PARTIAL'}),
        'unsupported_compression': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_TRIAGE_PARTIAL'}),
        'unsupported_format': (('NATIVE','UNKNOWN','U','convert_only'), {'W_TRIAGE_UNKNOWN','W_TRIAGE_UNSUPPORTED'}),
        'unsupported_media': (('NATIVE','PARTIAL','M','convert_and_ocr'), set()),
        'zip_limit': (('NATIVE','UNKNOWN','U','convert_and_ocr'), {'W_TRIAGE_PARTIAL'}),
    }
    expected_signature, expected_codes = expected[code]
    assert signature(result) == expected_signature
    assert issue_codes(result) == expected_codes
    assert [c['id'] for c in result['candidates_unique']] == ([] if code == 'encrypted' else [c['id'] for c in report['candidates']])
    # Positive/fallback rows complement the error and validation row tables.
    for fx, fmt, expected in (("FX-01", "pdf", ("NATIVE", "NONE", "T", "convert_only")),
        ("FX-02", "pdf", ("NATIVE", "FULL", "S", "convert_and_ocr")),
        ("FX-03", "pdf", ("NATIVE", "PARTIAL", "M", "convert_and_ocr")),
        ("FX-09", "png", ("NATIVE", "FULL", "S", "convert_and_ocr")),
        ("FX-16", "docx", ("NATIVE", "PARTIAL", "M", "convert_and_ocr"))):
        assert signature(core_api.classify.classify(core_fx.sniff(fx, format=fmt), core_fx.report(fx))) == expected
    for retained in (False, True):
        unknown = deepcopy(core_fx.report("FX-03"))
        unknown["decision"] = "unknown"
        if not retained:
            unknown["candidates"] = []
        c = core_api.classify.classify(core_fx.sniff(), unknown)
        assert signature(c) == ("NATIVE", "UNKNOWN", "U", "convert_and_ocr" if retained else "convert_only")
        assert "W_TRIAGE_UNKNOWN" in issue_codes(c)


@pytest.mark.req("REQ-CLS-05", "REQ-CLS-06")
@pytest.mark.cov("S3", "FM1")
@pytest.mark.fx("FX-60")
@pytest.mark.parametrize("mutation,warning", [
    ("missing", "W_TRIAGE_UNKNOWN_VALUE"), ("medium", "W_TRIAGE_UNKNOWN_VALUE"),
    ("state", "W_TRIAGE_UNKNOWN_VALUE"), ("kind", "W_TRIAGE_UNKNOWN_VALUE"),
    ("out_of_range", "W_TRIAGE_INCONSISTENT"), ("wrong_page", "W_TRIAGE_INCONSISTENT"),
    ("no_candidates_with_candidates", "W_TRIAGE_INCONSISTENT"),
    ("review_with_high", "W_TRIAGE_INCONSISTENT"), ("recommended_empty", "W_TRIAGE_INCONSISTENT"),
    ("wrong_format", "W_TRIAGE_INCONSISTENT"), ("candidate_type", "W_TRIAGE_UNKNOWN_VALUE"),
    ("coverage_type", "W_TRIAGE_UNKNOWN_VALUE"), ("issues_type", "W_TRIAGE_UNKNOWN_VALUE"),
    ("txt_v1", "W_TRIAGE_UNKNOWN_VALUE"), ("csv_v2", "W_TRIAGE_UNKNOWN_VALUE"),
    ("raster_v3", "W_TRIAGE_INCONSISTENT"), ("office_v3", "W_TRIAGE_INCONSISTENT")])
def test_T_CLS_08_v1_v4_precede_positive_rows(core_api, core_fx, mutation, warning):
    report = deepcopy(core_fx.report("FX-03"))
    sniff = core_fx.sniff()
    if mutation == "missing":
        del report["coverage"]
    elif mutation == "medium":
        report["candidates"][0]["priority"] = "medium"
    elif mutation == "state":
        report["coverage"]["state"] = "bogus"
    elif mutation == "kind":
        report["candidates"][0]["kind"] = "bogus"
    elif mutation == "out_of_range":
        report["candidates"][0].update(id="p99999", page=99999)
    elif mutation == "wrong_page":
        report["candidates"][0]["page"] += 1
    elif mutation == "no_candidates_with_candidates":
        report["decision"] = "no_candidates"
    elif mutation == "review_with_high":
        report["decision"] = "review"
    elif mutation == "recommended_empty":
        report["candidates"] = []
    elif mutation == "wrong_format":
        report["file"]["format"] = "docx"
    elif mutation == "candidate_type":
        report["candidates"][0]["reasons"] = 123
    elif mutation == "coverage_type":
        report["coverage"] = []
    elif mutation == "issues_type":
        report["issues"] = "not a list"
    elif mutation == "txt_v1":
        sniff = core_fx.sniff("FX-28", format="txt")
        report = deepcopy(core_fx.report("FX-28"))
        del report["candidates"]
    elif mutation == "csv_v2":
        sniff = core_fx.sniff("FX-30", format="csv")
        report = deepcopy(core_fx.report("FX-30"))
        report["decision"] = "future_decision"
    elif mutation == "raster_v3":
        sniff = core_fx.sniff("FX-11", format="tiff")
        report = deepcopy(core_fx.report("FX-11"))
        report["candidates"][0]["id"] = "f999"
    elif mutation == "office_v3":
        sniff = core_fx.sniff("FX-16", format="docx")
        report = deepcopy(core_fx.report("FX-16"))
        report["candidates"][0]["page"] = 1
    result = core_api.classify.classify(sniff, report)
    assert signature(result) == ("NATIVE", "UNKNOWN", "U", "convert_only")
    assert warning in issue_codes(result)


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S3", "FM4")
@pytest.mark.fx("FX-28", "FX-29", "FX-30", "FX-31", "FX-35", "FX-36", "FX-37", "FX-38", "FX-39")
@pytest.mark.parametrize("fx,fmt,route,expected", [
    ("FX-28", "txt", "NATIVE", ("NATIVE", "NONE", "T", "convert_only")),
    ("FX-29", "txt", "NATIVE", ("NATIVE", "NONE", "T", "convert_only")),
    ("FX-30", "csv", "NATIVE", ("NATIVE", "NONE", "T", "convert_only")),
    ("FX-31", "html", "NATIVE", ("NATIVE", "NONE", "T", "convert_only")),
    ("FX-35", "doc", "LEGACY", ("LEGACY", "UNKNOWN", "L", "report_only")),
    ("FX-36", "rtf", "LEGACY", ("LEGACY", "UNKNOWN", "L", "report_only")),
    ("FX-37", "odt", "LEGACY", ("LEGACY", "UNKNOWN", "L", "report_only")),
    ("FX-38", "mp3", "UNSUPPORTED", ("UNSUPPORTED", "UNKNOWN", "X", "report_only")),
    ("FX-39", "xyz", "UNSUPPORTED", ("UNSUPPORTED", "UNKNOWN", "X", "report_only"))])
def test_T_CLS_09_non_g1_rows(core_api, core_fx, fx, fmt, route, expected):
    sniff = core_fx.sniff(fx, format=fmt, route=route)
    if fmt == "mp3":
        sniff["reasons"] = ["media_out_of_scope"]
    result = core_api.classify.classify(sniff, core_fx.report(fx) if route == "NATIVE" else None)
    assert signature(result) == expected
    if fmt == "html":
        assert "W_MEDIA_NOT_INSPECTED" in issue_codes(result)
    if fmt == "mp3":
        assert "E_MEDIA_OUT_OF_SCOPE" in issue_codes(result)


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S3", "FM2")
@pytest.mark.fx("FX-05", "FX-25", "FX-26", "FX-27")
def test_T_CLS_10_protected_and_core_encrypted_precedence(core_api, core_fx):
    for fx, fmt in (("FX-05", "pdf"), ("FX-25", "docx"), ("FX-26", "zip"), ("FX-27", "hwp")):
        result = core_api.classify.classify(core_fx.sniff(fx, format=fmt, route="PROTECTED"), None)
        assert signature(result) == ("PROTECTED", "UNKNOWN", "P", "report_only")
        assert "E_ENCRYPTED" in issue_codes(result)
    report = deepcopy(core_fx.report("FX-03"))
    report["issues"].append(dict(code="encrypted", detail="fixture"))
    assert signature(core_api.classify.classify(core_fx.sniff(), report)) == ("PROTECTED", "UNKNOWN", "P", "report_only")


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S3", "FM3")
@pytest.mark.fx("FX-42", "FX-06", "FX-48", "FX-43", "FX-45")
@pytest.mark.parametrize("route,codes,expected", [
    ("NATIVE", ("E_TOO_LARGE", "E_CORRUPT"), ("NATIVE", "UNKNOWN", "U", "report_only")),
    ("NATIVE", ("E_CORRUPT",), ("NATIVE", "UNKNOWN", "U", "report_only")),
    ("NATIVE", ("E_ZIP_ENTRIES",), ("NATIVE", "UNKNOWN", "U", "report_only")),
    ("CONTAINER", (), ("CONTAINER", "NONE", "C", "recurse")),
    ("CONTAINER", ("E_ZIP_DEPTH",), ("CONTAINER", "UNKNOWN", "C", "report_only")),
    ("NATIVE", ("E_SNIFF_IO", "E_TOO_LARGE"), ("UNSUPPORTED", "UNKNOWN", "X", "report_only")),
    ("NATIVE", ("E_ZIP_PATH",), ("NATIVE", "UNKNOWN", "U", "report_only")),
    ("NATIVE", ("E_TRIAGE_SCHEMA",), ("NATIVE", "UNKNOWN", "U", "report_only")),
    ("NATIVE", ("E_TRIAGE_FAIL",), ("NATIVE", "UNKNOWN", "U", "convert_only"))])
def test_T_CLS_11_error_and_container_rows(core_api, core_fx, route, codes, expected):
    result = core_api.classify.classify(core_fx.sniff(route=route, issues=codes), None)
    assert signature(result) == expected
    assert set(codes[:1]) <= issue_codes(result)


@pytest.mark.req("REQ-CLS-02", "REQ-MAP-08")
@pytest.mark.cov("S3", "FM12")
@pytest.mark.fx("FX-17")
def test_T_CLS_12_duplicate_candidate_ids_one_unit(core_api, core_fx):
    report = core_fx.report("FX-17")
    assert len(report["candidates"]) == 2 and len({c["id"] for c in report["candidates"]}) == 1
    result = core_api.classify.classify(core_fx.sniff("FX-17", format="docx"), report)
    assert len(result["candidates_unique"]) == 1 and result["candidates_unique"][0]["refs"] == 2


@pytest.mark.req("REQ-CLS-05", "REQ-SNF-01b")
@pytest.mark.cov("S3", "FM12")
@pytest.mark.fx("FX-52")
def test_T_CLS_13_collision_row_precedes_triage(core_api, core_fx):
    result = core_api.classify.classify(core_fx.sniff(issues=("E_OUTPUT_COLLISION",)), core_fx.report("FX-03"))
    assert signature(result) == ("NATIVE", "UNKNOWN", "U", "report_only")
    assert "E_OUTPUT_COLLISION" in issue_codes(result)
