"""PURE ordered classification boundary (SPEC 3.2)."""
import re
from .sniff_pure import RASTERS, OFFICE, G2A, G2B

CORE_CODES = frozenset("corrupt encrypted external_media frame_cap image_probe_failed media_not_inspected missing_dependency page_cap too_large unresolved_embed unsupported_compression unsupported_format unsupported_media zip_limit".split())
CORE_REASONS = frozenset("scan_like suspect_text_layer low_text_nonblank image_with_text_layer standalone_image embedded_image decor_media".split())
DECISIONS = frozenset(("ocr_recommended", "review", "no_candidates", "unknown"))
STATES = frozenset(("complete", "partial", "none", "not_applicable"))


def _well_typed(report: dict, fmt: str) -> bool:
    if not all(isinstance(report.get(k), v) for k, v in
               (("decision", str), ("coverage", dict), ("file", dict),
                ("candidates", list), ("issues", list), ("pages", list),
                ("rasters", list), ("summary", dict), ("options", dict))):
        return False
    if not isinstance(report.get("rules_version"), str):
        return False
    for name in ('pages', 'rasters'):
        if any(not isinstance(item, dict) for item in report[name]):
            return False
    def number(value):
        return type(value) in (int, float)
    def vector(value, length):
        return isinstance(value, list) and len(value) == length and all(number(v) for v in value)
    for page in report['pages']:
        integers = ('n', 'rotation', 'chars', 'nonspace_chars', 'cid_count', 'replacement_count',
                    'private_use_count', 'vector_objects', 'image_count')
        if not all(type(page.get(k)) is int for k in integers):
            return False
        if not vector(page.get('bbox_pt'), 4) or not all(number(page.get(k)) for k in ('unresolved_glyph_share', 'image_area_ratio')):
            return False
        if type(page.get('images_truncated')) is not bool or not isinstance(page.get('images'), list) or any(not isinstance(v, dict) for v in page['images']):
            return False
        if 'text_sample' in page and not isinstance(page['text_sample'], str):
            return False
    for raster in report['rasters']:
        if not isinstance(raster.get('id'), str) or not {'frame', 'px', 'mode', 'dpi_tag', 'exif_orientation', 'bytes'} <= raster.keys():
            return False
        if any(raster[k] is not None and type(raster[k]) is not int for k in ('frame', 'exif_orientation', 'bytes')):
            return False
        if raster['px'] is not None and not vector(raster['px'], 2):
            return False
        if raster['mode'] is not None and not isinstance(raster['mode'], str):
            return False
    if fmt in OFFICE:
        media = report.get('media')
        if not isinstance(media, list) or any(not isinstance(m, dict) or not isinstance(m.get('id'), str) for m in media):
            return False
        for m in media:
            if not {'where', 'px', 'bytes', 'ext', 'decor', 'references'} <= m.keys():
                return False
            if not isinstance(m['ext'], str) or type(m['decor']) is not bool or not isinstance(m['references'], list):
                return False
            if any(not isinstance(ref, dict) for ref in m['references']):
                return False
            if m['bytes'] is not None and type(m['bytes']) is not int:
                return False
            if m['px'] is not None and not vector(m['px'], 2):
                return False
        if fmt == 'hwp' and any(
            not isinstance(m.get('payload_sha256'), str) or
            not re.fullmatch('[0-9a-f]{64}', m['payload_sha256']) or
            m.get('payload_kind') not in {'parser_image_payload', 'stored_ole_stream'} for m in media):
            return False
    cov, file = report["coverage"], report["file"]
    if not {"pages_total", "pages_inspected"} <= cov.keys() or not {"sha256", "bytes", "format"} <= file.keys():
        return False
    if not isinstance(cov.get("state"), str) and not ("state" not in cov and fmt in G2A | G2B):
        return False
    if cov.get("pages_total") is not None and type(cov["pages_total"]) is not int:
        return False
    if type(cov.get("pages_inspected")) is not int:
        return False
    if not isinstance(file.get("format"), str) or type(file.get("bytes")) is not int:
        return False
    if file.get("sha256") is not None and not isinstance(file["sha256"], str):
        return False
    for c in report["candidates"]:
        if not isinstance(c, dict) or not all(isinstance(c.get(k), str) for k in ("id", "kind", "priority")):
            return False
        if "page" not in c or c["page"] is not None and type(c["page"]) is not int:
            return False
        if not isinstance(c.get("reasons"), list) or not all(isinstance(r, str) for r in c["reasons"]):
            return False
    return all(isinstance(i, dict) and isinstance(i.get("code"), str) and isinstance(i.get("detail"), str)
               for i in report["issues"])


def _consistent(report: dict, fmt: str) -> bool:
    candidates, coverage = report["candidates"], report["coverage"]
    for c in candidates:
        if fmt == "pdf":
            match = re.fullmatch(r"p([1-9]\d*)", c["id"])
            if not match or c["kind"] != "page" or type(coverage["pages_total"]) is not int:
                return False
            if not 1 <= int(match[1]) <= coverage["pages_total"] or c["page"] != int(match[1]):
                return False
        else:
            if c["kind"] != "image" or c["page"] is not None or not c["id"]:
                return False
            if fmt in RASTERS:
                match = re.fullmatch(r"f([1-9]\d*)", c["id"])
                if c["id"] != "image" and not match:
                    return False
                if not 1 <= (int(match[1]) if match else 1) <= len(report["rasters"]):
                    return False
    priorities = {c["priority"] for c in candidates}
    if report["decision"] == "no_candidates" and (candidates or coverage.get("state") not in {"complete", "not_applicable"}):
        return False
    if report["decision"] == "ocr_recommended" and "high" not in priorities:
        return False
    if report["decision"] == "review" and ("high" in priorities or "low" not in priorities):
        return False
    core_format = report["file"]["format"]
    return core_format == ("image" if fmt in RASTERS else fmt) or core_format == "unknown" and fmt in G2A | G2B


def classify(sniff: dict, triage: object) -> dict:
    sniff = sniff if isinstance(sniff, dict) else {}
    fmt, route = sniff.get("format", "unknown"), sniff.get("route", "UNSUPPORTED")
    if not isinstance(fmt, str):
        fmt = "unknown"
    if not isinstance(route, str) or route not in {"NATIVE", "CONTAINER", "LEGACY", "PROTECTED", "UNSUPPORTED"}:
        route = "UNSUPPORTED"
    source_issues = sniff.get("issues", [])
    source_reasons = sniff.get("reasons", [])
    issues = [dict(i) for i in source_issues if isinstance(i, dict) and isinstance(i.get("code"), str)] if isinstance(source_issues, (list, tuple)) else []
    sniff_codes = {i.get("code") for i in issues}
    result = dict(route=route, need="UNKNOWN", label={"NATIVE": "U", "CONTAINER": "C", "LEGACY": "L", "PROTECTED": "P", "UNSUPPORTED": "X"}[route],
                  action="report_only", decision="not_run", coverage_state="not_run",
                  candidates_unique=[], uninspected_pages=0, reasons=[r for r in source_reasons if isinstance(r, str)] if isinstance(source_reasons, (list, tuple)) else [], issues=issues)

    def issue(code: str) -> None:
        if code not in {i.get("code") for i in issues}:
            message = "Convert with LibreOffice to a supported format and rerun." if code == "E_LEGACY" else code.replace("_", " ").capitalize() + "."
            issues.append(dict(code=code, message=message))

    def finish(code=None, *, need=None, action=None, new_route=None):
        if new_route:
            result["route"] = new_route
        if need:
            result["need"] = need
        if action:
            result["action"] = action
        result["label"] = ({"NONE": "T", "FULL": "S", "PARTIAL": "M", "UNKNOWN": "U"}[result["need"]]
                           if result["route"] == "NATIVE" else {"CONTAINER": "C", "LEGACY": "L", "PROTECTED": "P", "UNSUPPORTED": "X"}[result["route"]])
        if code:
            issue(code)
        if result['action'] == 'report_only':
            result['candidates_unique'] = []
        return result

    # Preflight conditions precede all access to the Core envelope.
    for code in ("E_SNIFF_IO", "E_ZIP_PATH", "E_OUTPUT_COLLISION", "E_TOO_LARGE"):
        if code in sniff_codes:
            return finish(code, new_route="UNSUPPORTED" if code == "E_SNIFF_IO" else None)
    if route == "PROTECTED":
        return finish("E_ENCRYPTED")
    if "E_CORRUPT" in sniff_codes:
        return finish("E_CORRUPT")
    bounds = ("E_ZIP_DEPTH", "E_ZIP_ENTRIES", "E_ZIP_TOTAL", "E_ZIP_BOMB")
    if route != "CONTAINER":
        for code in bounds[1:]:
            if code in sniff_codes:
                return finish(code)
    if route == "UNSUPPORTED":
        return finish("E_MEDIA_OUT_OF_SCOPE" if "media_out_of_scope" in result["reasons"] else "E_UNSUPPORTED")
    if route == "LEGACY":
        return finish("E_LEGACY")
    if route == "CONTAINER":
        for code in bounds:
            if code in sniff_codes:
                return finish(code)
        return finish(need="NONE", action="recurse")
    if "E_TRIAGE_SCHEMA" in sniff_codes:
        return finish("E_TRIAGE_SCHEMA")
    if "E_TRIAGE_FAIL" in sniff_codes:
        return finish("E_TRIAGE_FAIL", action="convert_only")
    if not isinstance(triage, dict) or type(triage.get("schema_version")) is not int or triage["schema_version"] != 1:
        return finish("E_TRIAGE_SCHEMA")
    if not _well_typed(triage, fmt):
        return finish("W_TRIAGE_UNKNOWN_VALUE", action="convert_only")
    result.update(decision=triage["decision"], coverage_state=triage["coverage"].get("state", "not_run"))
    candidates = triage["candidates"]
    core_codes = {i["code"] for i in triage["issues"]}
    result["reasons"].extend("core:" + i["code"] for i in triage["issues"])
    result["reasons"].extend("cand:" + reason for c in candidates for reason in c["reasons"])
    if triage["rules_version"] != "1" or triage["decision"] not in DECISIONS or result["coverage_state"] not in STATES | ({"not_run"} if fmt in G2A | G2B else set()) or not core_codes <= CORE_CODES or any(c["kind"] not in {"page", "image"} or c["priority"] not in {"high", "low"} for c in candidates):
        return finish("W_TRIAGE_UNKNOWN_VALUE", action="convert_only")
    if not _consistent(triage, fmt):
        return finish("W_TRIAGE_INCONSISTENT", action="convert_only")
    unique = {}
    for c in candidates:
        if c["id"] not in unique:
            unique[c["id"]] = dict(id=c["id"], kind=c["kind"], page=c["page"],
                priority="normal" if c["priority"] == "high" else "low", priority_core=c["priority"], refs=0)
        unique[c["id"]]["refs"] += 1
        if any(reason not in CORE_REASONS for reason in c["reasons"]):
            issue("W_TRIAGE_UNKNOWN_VALUE")
    result["candidates_unique"] = list(unique.values())
    cov = triage["coverage"]
    if fmt == "pdf" and type(cov["pages_total"]) is int:
        result["uninspected_pages"] = max(0, cov["pages_total"] - cov["pages_inspected"])
    for core_code, warning in (("missing_dependency", "W_CORE_DEPENDENCY"), ("external_media", "W_EXTERNAL_MEDIA"),
            ("unresolved_embed", "W_UNRESOLVED_EMBED"), ("image_probe_failed", "W_IMAGE_PROBE")):
        if core_code in core_codes:
            issue(warning)
    if result["decision"] == "review":
        issue("W_REVIEW_PRIORITY")
    if fmt in G2A:
        return finish(need="NONE", action="convert_only") if result["coverage_state"] == "not_applicable" else finish("E_UNSUPPORTED", new_route="UNSUPPORTED")
    if fmt not in G2A | G2B and "encrypted" in core_codes:
        return finish("E_ENCRYPTED", new_route="PROTECTED")
    if fmt in G2B:
        return finish("W_MEDIA_NOT_INSPECTED", action="convert_only")
    if result["decision"] == "no_candidates":
        return finish(need="NONE", action="convert_only")
    if "unsupported_format" in core_codes:
        issue("W_TRIAGE_UNSUPPORTED")
    if result["decision"] == "unknown":
        return finish("W_TRIAGE_UNKNOWN", action="convert_and_ocr" if candidates else "convert_only")
    if result["coverage_state"] in {"partial", "none"}:
        return finish("W_TRIAGE_PARTIAL", action="convert_and_ocr")
    if result["coverage_state"] == "complete":
        if fmt in RASTERS:
            return finish(need="FULL", action="convert_and_ocr")
        if fmt == "pdf":
            k = len({c["page"] for c in candidates})
            if k:
                return finish(need="FULL" if k == cov["pages_total"] else "PARTIAL", action="convert_and_ocr")
        if fmt in OFFICE and candidates:
            return finish(need="PARTIAL", action="convert_and_ocr")
    return finish("W_TRIAGE_UNKNOWN_VALUE", action="convert_only")
