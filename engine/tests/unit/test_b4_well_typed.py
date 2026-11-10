"""B4: the declarative V1 type check equals the pre-refactor checker on every golden mutation.

`_legacy_well_typed` is the imperative `classify._well_typed` as of d3df252, copied verbatim.
It is kept only as the oracle for this equivalence test.
"""
from copy import deepcopy
from itertools import chain
import json
import re

import pytest


def _legacy_well_typed(report: dict, fmt: str, OFFICE, G2A, G2B) -> bool:
    if not all(isinstance(report.get(k), v) for k, v in
               (("decision", str), ("coverage", dict), ("file", dict),
                ("candidates", list), ("issues", list), ("pages", list),
                ("rasters", list), ("summary", dict), ("options", dict))):
        return False
    if not isinstance(report.get("rules_version"), str):
        return False
    if type(report['options'].get('samples')) is not bool:
        return False
    summary = report['summary']
    for name in ('candidates_high', 'candidates_low', 'image_occurrences', 'nonspace_chars', 'pages_with_text'):
        if type(summary.get(name)) is not int:
            return False
    if not isinstance(summary.get('scope'), str) or 'media_small' in summary and type(summary['media_small']) is not int:
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
        for image in page['images']:
            if not all(k in image for k in ('name', 'bbox_pt', 'px', 'bits', 'colorspace', 'filter', 'dpi_xy', 'imagemask', 'area_ratio')):
                return False
            if not isinstance(image['name'], str) or not vector(image['bbox_pt'], 4) or not vector(image['px'], 2):
                return False
            if image['bits'] is not None and type(image['bits']) is not int:
                return False
            if image['dpi_xy'] is not None and not vector(image['dpi_xy'], 2):
                return False
            if type(image['imagemask']) is not bool or not number(image['area_ratio']):
                return False
            if not isinstance(image['colorspace'], list) or not all(isinstance(v, str) for v in image['colorspace']):
                return False
            if image['filter'] is not None and not isinstance(image['filter'], (str, list)):
                return False
            if isinstance(image['filter'], list) and any(not isinstance(v, str) for v in image['filter']):
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
        if raster['dpi_tag'] is not None and not vector(raster['dpi_tag'], 2):
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
            if m['where'] is not None and (not isinstance(m['where'], dict) or
                    any(k != 'slide' or type(v) is not int for k, v in m['where'].items())):
                return False
            if any(not isinstance(ref.get('part'), str) or not isinstance(ref.get('id'), str) for ref in m['references']):
                return False
            if m['bytes'] is not None and type(m['bytes']) is not int:
                return False
            if m['px'] is not None and not vector(m['px'], 2):
                return False
            if fmt == 'hwp' and (not {'stored_bytes', 'stored_sha256'} <= m.keys() or
                    m['stored_bytes'] is not None and type(m['stored_bytes']) is not int or
                    m['stored_sha256'] is not None and (not isinstance(m['stored_sha256'], str) or
                        not re.fullmatch('[0-9a-f]{64}', m['stored_sha256']))):
                return False
        if fmt == 'hwp' and any(
            not isinstance(m.get('payload_sha256'), str) or
            not re.fullmatch('[0-9a-f]{64}', m['payload_sha256']) or
            not isinstance(m.get('payload_kind'), str) or
            m.get('payload_kind') not in {'parser_image_payload', 'stored_ole_stream'} for m in media):
            return False
    cov, file = report["coverage"], report["file"]
    if 'reason' in cov and not isinstance(cov['reason'], str):
        return False
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
        if 'decor' in c and type(c['decor']) is not bool:
            return False
    return all(isinstance(i, dict) and isinstance(i.get("code"), str) and isinstance(i.get("detail"), str)
               for i in report["issues"])


SUBSTITUTES = (None, True, 1, 1.5, "x", [], {})
# One format per V1 format gate: none, Office without HWP, HWP, and text (G2A | G2B, may omit coverage.state).
FORMAT_GATES = ("pdf", "docx", "hwp", "txt")


def _shape(node):
    """Structural signature: key paths and value types, with list lengths (vectors are length-checked)."""
    if isinstance(node, dict):
        return ("{}", *sorted((key, _shape(value)) for key, value in node.items()))
    if isinstance(node, list):
        return ("[]", len(node), *sorted({_shape(item) for item in node}, key=repr))
    return type(node).__name__


def _thin(node):
    """Copy of `node` whose record lists keep the first item of each distinct shape.

    Every (key path, value type) of the original survives, and so does well-typedness, because each
    kept item is an original item; FX-07's 1,000 identical pages and candidates shrink to one each.
    """
    if isinstance(node, dict):
        return {key: _thin(value) for key, value in node.items()}
    if not isinstance(node, list):
        return node
    items = [_thin(item) for item in node]
    if not all(isinstance(item, dict) for item in items):
        return items  # scalar vectors keep every element
    unique = {}
    for item in items:
        unique.setdefault(_shape(item), item)
    return list(unique.values())


def _variants(node, path, fresh):
    """Mutate `node` in place: drop each key, swap each value; yield (path, mutation) and restore after resuming.

    `path` names list positions "[]", so a mutation is identified by (path, original type, mutation)
    wherever it occurs; `fresh` says whether that identity is still untested, and only then is it applied.
    """
    if isinstance(node, dict):
        slots, record = list(node.items()), True
    elif isinstance(node, list):
        slots, record = list(enumerate(node)), False
    else:
        return
    for key, value in slots:
        where = (*path, key if record else "[]")
        kind = type(value).__name__
        if record and fresh((where, kind, "drop")):
            del node[key]
            yield where, "drop"
            node[key] = value
        for substitute in SUBSTITUTES:
            if fresh((where, kind, repr(substitute))):
                node[key] = substitute  # never mutated, so shared [] and {} are safe
                yield where, repr(substitute)
                node[key] = value
        yield from _variants(value, where, fresh)


def _enriched(goldens):
    """Golden copies that also carry the optional or nullable V1 forms no golden report contains."""
    pdf, raster, hwp = (deepcopy(goldens[fx][1]) for fx in ("FX-03", "FX-09", "FX-24"))
    pdf["coverage"]["reason"] = "page_cap"
    pdf["file"]["sha256"] = None
    pdf["pages"][0]["text_sample"] = "sample"
    image = pdf["pages"][1]["images"][0]
    pdf["pages"][1]["images"] += [dict(image, filter="DCTDecode", bits=None, dpi_xy=None),
                                  dict(image, filter=["FlateDecode", "DCTDecode"], colorspace=[])]
    raster["rasters"].append(dict(raster["rasters"][0], frame=None, px=None, mode="RGB", dpi_tag=[72, 72.5],
                                  exif_orientation=None, bytes=None))
    del hwp["summary"]["media_small"], hwp["candidates"][0]["decor"]
    hwp["media"][0].update(where={"slide": 2}, references=[{"part": "ppt/slides/slide2.xml", "id": "rId3"}])
    hwp["media"][1].update(where={}, stored_bytes=None, stored_sha256=None, bytes=None)
    return {"FX-03+": ("pdf", pdf), "FX-09+": ("png", raster), "FX-24+": ("hwp", hwp)}


def _outcome(check, *args):
    try:
        return bool(check(*args))
    except Exception as error:  # an exception is an outcome too, and must match
        return type(error).__name__


@pytest.mark.req("REQ-CLS-01")
@pytest.mark.cov("S3", "FM9")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_CLS_94_declarative_v1_type_check_equals_legacy_on_every_golden_mutation(core_api, repo_root):
    pure = core_api.sniff_pure
    def legacy(report, fmt):
        return _legacy_well_typed(report, fmt, pure.OFFICE, pure.G2A, pure.G2B)
    def gate(fmt):
        return fmt in pure.OFFICE, fmt == "hwp", fmt in pure.G2A | pure.G2B
    goldens = {}
    for path in sorted((repo_root / "engine/tests/golden").glob("FX-*/triage.json")):
        review = json.loads((path.parent / "classification.review.json").read_text(encoding="utf-8"))
        goldens[path.parent.name] = (review["sniff"]["format"], json.loads(path.read_text(encoding="utf-8")))
    assert len(goldens) >= 48 and all(isinstance(report, dict) for _, report in goldens.values())
    assert len({gate(f) for f in FORMAT_GATES}) == len(FORMAT_GATES)
    seeds = dict(goldens, **_enriched(goldens))
    for name in ("FX-03+", "FX-09+", "FX-24+"):
        fmt, report = seeds[name]
        assert legacy(report, fmt) is True, name  # every enrichment is itself well-typed
    mismatches, checked, verdicts, seen = [], 0, set(), set()
    def compare(name, report, fmt, case):
        nonlocal checked
        old = _outcome(legacy, report, fmt)
        new = _outcome(core_api.classify._well_typed, report, fmt)
        checked += 1
        verdicts.add(old)
        if old != new and len(mismatches) < 20:
            mismatches.append((name, fmt, case, old, new))
        return old
    for name, (own, full) in seeds.items():
        formats = [own, *(f for f in FORMAT_GATES if gate(f) != gate(own))]  # own + one per other gate
        report = _thin(full)
        for fmt in formats:  # the unmutated full report once, and thinning keeps its verdict
            assert compare(name, full, fmt, "full") == _outcome(legacy, report, fmt), (name, fmt)
        def fresh(case, shape=gate(own)):  # a mutation is tested once per format gate of its seed
            case = (shape, case)
            return case not in seen and not seen.add(case)
        for case in chain([None], _variants(report, (), fresh)):  # each variant is undone before the next
            for fmt in formats:
                compare(name, report, fmt, case)
    assert mismatches == []
    # Deduplicated: about 2,000 distinct (gate, path, type, mutation) cases, each under 4 formats.
    assert {True, False} <= verdicts and len(seen) > 1_000 and checked >= 4 * len(seen), (verdicts, len(seen), checked)
