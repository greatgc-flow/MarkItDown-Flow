"""PURE ordered classification boundary (SPEC 3.2)."""
import re
from .contracts import FRAME_ID
from .hashing import SHA256_HEX
from .sniff_pure import RASTERS, OFFICE, G2A, G2B


def classify_derived(sniff: dict, outcome: dict) -> dict:
    """Classify Core's derived Markdown and independently inspected extracted media.

    Core does not expose the intermediate Office container. Candidate ids name
    extracted assets rather than inventing original Office member identities.
    """
    result = classify(dict(sniff, issues=[*sniff['issues'], *outcome['issues']]), outcome['report'])
    if outcome['derived_media']:
        result['coverage_state'] = 'complete'  # scope is the extracted media, not private Office layout
    for asset in outcome['derived_media']:
        evidence = asset['outcome']
        decision = classify(dict(asset['sniff'], issues=[*asset['sniff']['issues'], *evidence['issues']]), evidence['report'])
        if decision['action'] == 'report_only':
            result['issues'].append(dict(code='W_MEDIA_FORMAT', message='Extracted media could not be inspected.'))
        else:
            result['issues'].extend(decision['issues'])
        if decision['candidates_unique'] or decision['action'] == 'report_only':
            result['candidates_unique'].append(dict(id=asset['id'], kind='image', page=None,
                                                    priority='low', priority_core='low', refs=1))
        if decision['need'] == 'UNKNOWN' or decision['action'] == 'report_only':
            result['coverage_state'] = 'partial'
    if result['candidates_unique']:
        result.update(need='UNKNOWN' if result['coverage_state'] == 'partial' else 'PARTIAL',
                      label='U' if result['coverage_state'] == 'partial' else 'M',
                      action='convert_and_ocr', decision='review')
    elif result['coverage_state'] == 'partial':
        result.update(need='UNKNOWN', label='U')
    return result

CORE_CODES = frozenset("corrupt encrypted external_media frame_cap image_probe_failed media_not_inspected missing_dependency page_cap too_large unresolved_embed unsupported_compression unsupported_format unsupported_media zip_limit".split())
CORE_REASONS = frozenset("scan_like suspect_text_layer low_text_nonblank image_with_text_layer standalone_image embedded_image decor_media".split())
DECISIONS = frozenset(("ocr_recommended", "review", "no_candidates", "unknown"))
STATES = frozenset(("complete", "partial", "none", "not_applicable"))


def _matches(value, spec) -> bool:
    """A V1 type spec is a predicate, a one-item list (every item matches it) or a dict of fields.

    A field must be present and match; a '?key' may be absent. Only `_null` admits None.
    Records are open: unlisted keys are ignored.
    """
    if callable(spec):
        return spec(value)
    if isinstance(spec, list):
        return isinstance(value, list) and all(_matches(item, spec[0]) for item in value)
    if not isinstance(value, dict):
        return False
    for key, field in spec.items():
        name = key.removeprefix('?')
        if name in value:
            if not _matches(value[name], field):
                return False
        elif name == key:
            return False
    return True


def _str(v): return isinstance(v, str)
def _int(v): return type(v) is int  # bool is not an int here
def _bool(v): return type(v) is bool
def _num(v): return type(v) in (int, float)
def _vec(n): return lambda v: isinstance(v, list) and len(v) == n and all(map(_num, v))
def _null(spec): return lambda v: v is None or _matches(v, spec)
def _hex64(v): return isinstance(v, str) and SHA256_HEX.fullmatch(v) is not None
def _payload_kind(v): return isinstance(v, str) and v in {'parser_image_payload', 'stored_ole_stream'}  # str first: [] is unhashable
def _filter(v): return isinstance(v, str) or _matches(v, [_str])
def _where(v): return isinstance(v, dict) and all(k == 'slide' and _int(n) for k, n in v.items())

_IMAGE = dict(name=_str, bbox_pt=_vec(4), px=_vec(2), bits=_null(_int), colorspace=[_str], filter=_null(_filter),
              dpi_xy=_null(_vec(2)), imagemask=_bool, area_ratio=_num)
_PAGE = {**dict.fromkeys(('n', 'rotation', 'chars', 'nonspace_chars', 'cid_count', 'replacement_count',
                          'private_use_count', 'vector_objects', 'image_count'), _int),
         'bbox_pt': _vec(4), 'unresolved_glyph_share': _num, 'image_area_ratio': _num,
         'images_truncated': _bool, 'images': [_IMAGE], '?text_sample': _str}
_RASTER = dict(id=_str, frame=_null(_int), px=_null(_vec(2)), mode=_null(_str), dpi_tag=_null(_vec(2)),
               exif_orientation=_null(_int), bytes=_null(_int))
_MEDIA = dict(id=_str, where=_null(_where), px=_null(_vec(2)), bytes=_null(_int), ext=_str, decor=_bool,
              references=[dict(part=_str, id=_str)])  # Office formats only
_HWP_MEDIA = dict(_MEDIA, stored_bytes=_null(_int), stored_sha256=_null(_hex64), payload_sha256=_hex64,
                  payload_kind=_payload_kind)
_COVERAGE = {'?reason': _str, 'pages_total': _null(_int), 'pages_inspected': _int}
_V1 = dict(decision=_str, rules_version=_str, options=dict(samples=_bool),
           summary={**dict.fromkeys(('candidates_high', 'candidates_low', 'image_occurrences', 'nonspace_chars',
                                     'pages_with_text'), _int), 'scope': _str, '?media_small': _int},
           pages=[_PAGE], rasters=[_RASTER], coverage=dict(_COVERAGE, state=_str),
           file=dict(sha256=_null(_str), bytes=_int, format=_str),
           candidates=[{'id': _str, 'kind': _str, 'priority': _str, 'page': _null(_int), 'reasons': [_str],
                        '?decor': _bool}],
           issues=[dict(code=_str, detail=_str)])


def _well_typed(report: dict, fmt: str) -> bool:
    spec = dict(_V1)
    if fmt in G2A | G2B:  # text formats may omit coverage.state
        spec['coverage'] = {**_COVERAGE, '?state': _str}
    if fmt in OFFICE:
        spec['media'] = [_HWP_MEDIA if fmt == 'hwp' else _MEDIA]
    return _matches(report, spec)


def _consistent(report: dict, fmt: str) -> bool:
    candidates, coverage = report["candidates"], report["coverage"]
    def index(text, maximum):
        # V3 rejects invalid identities, including Python's bounded decimal conversion.
        try:
            if maximum < 1 or len(text) > len(str(maximum)):
                return 0
            return int(text)
        except ValueError:
            return 0
    for c in candidates:
        if fmt == "pdf":
            match = re.fullmatch(r"p([1-9]\d*)", c["id"])
            if not match or c["kind"] != "page" or type(coverage["pages_total"]) is not int:
                return False
            number = index(match[1], coverage['pages_total'])
            if not 1 <= number <= coverage["pages_total"] or c["page"] != number:
                return False
        else:
            if c["kind"] != "image" or c["page"] is not None or not c["id"]:
                return False
            if fmt in RASTERS:
                match = FRAME_ID.fullmatch(c["id"])
                if c["id"] != "image" and not match:
                    return False
                if not 1 <= (index(match[1], len(report['rasters'])) if match else 1) <= len(report["rasters"]):
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
        if 'E_PRECONVERT' in sniff_codes:
            return finish('E_PRECONVERT')
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
        if result["coverage_state"] == "not_applicable":
            return finish(need="NONE", action="convert_only")
        if core_codes == {"unsupported_format"} and "legacy_text" in result["reasons"]:
            return finish(need="NONE", action="convert_only")  # row 9d (R30): legacy-encoded text Core cannot validate
        return finish("E_UNSUPPORTED", new_route="UNSUPPORTED")
    if fmt not in G2A | G2B and "encrypted" in core_codes:
        return finish("E_ENCRYPTED", new_route="PROTECTED")
    if fmt in G2B:
        if fmt in {'csv', 'tsv', 'json'}:
            return finish(need='NONE', action='convert_only')
        if fmt in {'md', 'markdown', 'html', 'htm', 'xml', 'epub'}:
            return finish('W_MEDIA_NOT_INSPECTED', need='NONE', action='convert_only')
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
