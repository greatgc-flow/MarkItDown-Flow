"""
_smartimage_demo.py
========================================================================
Drives SmartImageRouter against the four synthetic test images produced by
scripts/_make_test_images.py and prints a structured report:

  - per-case: kind / confidence / method / escalation decision
  - per-case: preprocess info (skew_angle, ops_applied)
  - per-case: ensemble breakdown (engine_conf, agreement, length, …)
  - text preview (first 80 chars) of OCR output

Engines tried: tesseract + easyocr. Each engine gracefully no-ops when not
installed, so the run still produces useful output even with only one engine
available (we expect tesseract to be skipped on this host because the
binary is not on PATH).

Run:
    python scripts/_smartimage_demo.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "python"))

# Bring the wrapper's logger up so we see DEBUG output from the router on stderr.
import logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logging.getLogger("OmniDataEngine").setLevel(logging.INFO)

from image_router import SmartImageRouter  # noqa: E402

IMG_DIR = ROOT / "tests" / "fixtures" / "images"

CFG = {
    # OCR
    "ocr_engines": ["tesseract", "easyocr"],
    "ocr_lang": "kor+eng",
    "ocr_confidence_threshold": 70,
    "enable_ocr_ensemble": True,
    # Preprocess
    "preprocess_deskew": True,
    # Table
    "enable_table_extraction": True,
    # No AI in this demo — we want to observe the escalation gate, not exercise it
    "llm_prompt": None,
}

CASES = [
    ("case_1_doc_clean.png",  "document",  "Expected: kind=document, confidence>=70, NO escalation"),
    ("case_2_doc_skewed.png", "document",  "Expected: kind=document/diagram, deskew applied (~7°)"),
    ("case_3_table.png",      "table",     "Expected: kind=table (classifier Hough); extractor skipped if no transformers"),
    ("case_4_photo.png",      "photo",     "Expected: kind=photo, OCR skipped, NO escalation (no llm_prompt)"),
]


def _short(v, n=80):
    if v is None: return "<None>"
    s = str(v)
    return s[:n].replace("\n", " ") + ("…" if len(s) > n else "")


def run_case(filename: str, expected_kind: str, hint: str) -> dict:
    path = IMG_DIR / filename
    print(f"\n{'=' * 80}")
    print(f"CASE   {filename}")
    print(f"HINT   {hint}")
    print(f"PATH   {path}")
    if not path.exists():
        print(f"  ! image missing — skipped")
        return {"file": filename, "missing": True}

    router = SmartImageRouter(CFG)
    t0 = time.time()
    res = router.route(str(path))
    elapsed = time.time() - t0

    details = res.get("details", {}) or {}
    kind = details.get("kind")
    classified_ok = (kind == expected_kind) or (
        # for skewed scan, both document and diagram are acceptable depending on edge density
        expected_kind == "document" and kind in ("document", "diagram")
    )

    print(f"  kind            : {kind}  ({'OK' if classified_ok else f'expected {expected_kind}'})")
    print(f"  status          : {res.get('status')}")
    print(f"  confidence      : {res.get('confidence')}")
    print(f"  method          : {res.get('method')}")
    print(f"  should_escalate : {res.get('should_escalate_to_ai')}")
    print(f"  elapsed         : {elapsed:.2f}s")

    if "preprocess" in details:
        pre = details["preprocess"] or {}
        print(f"  preprocess      : skew={pre.get('skew_angle'):.2f}°  ops={pre.get('ops_applied')}  upscaled={pre.get('was_upscaled')}")

    if "breakdown" in details:
        b = details["breakdown"] or {}
        print(f"  ocr breakdown   : eng_conf={b.get('engine_conf')} agree={b.get('agreement')} len={b.get('length')} clean={b.get('cleanliness')} stdev_inv={b.get('stdev_inv')}")

    if "engine_results" in details:
        for eng, info in (details["engine_results"] or {}).items():
            print(f"    {eng:9s}    conf={info.get('conf')}  text={_short(info.get('text_preview'))}")

    if "table" in details:
        table_grid = details.get("table") or []
        struct = details.get("structure_confidence")
        col = details.get("column_consistency")
        print(f"  table extractor : grid_cells={len(table_grid)}  structure_conf={struct}  col_consistency={col}")
        if "reason" in details:
            print(f"  reason          : {details['reason']}")

    if res.get("content"):
        print(f"  content preview : {_short(res['content'], 120)}")

    return {
        "file": filename,
        "expected_kind": expected_kind,
        "kind": kind,
        "classified_ok": classified_ok,
        "confidence": res.get("confidence"),
        "should_escalate": res.get("should_escalate_to_ai"),
        "elapsed_s": round(elapsed, 2),
        "status": res.get("status"),
        "method": res.get("method"),
    }


def main():
    print(f"SmartImageRouter demo — cfg: {json.dumps(CFG, ensure_ascii=False, indent=2)}")
    summary = []
    for filename, expected_kind, hint in CASES:
        summary.append(run_case(filename, expected_kind, hint))

    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    header = ["file", "expected", "kind", "ok?", "conf", "esc", "elapsed", "status"]
    print(f"{header[0]:<25} {header[1]:<10} {header[2]:<10} {header[3]:<5} {header[4]:>7} {header[5]:>6} {header[6]:>9} {header[7]}")
    for s in summary:
        if s.get("missing"):
            print(f"{s['file']:<25} (missing)")
            continue
        print(
            f"{s['file']:<25} "
            f"{s['expected_kind']:<10} "
            f"{str(s['kind']):<10} "
            f"{('Y' if s['classified_ok'] else 'N'):<5} "
            f"{(s['confidence'] if s['confidence'] is not None else 0):>7.1f} "
            f"{str(s['should_escalate']):>6} "
            f"{s['elapsed_s']:>8.2f}s "
            f"{s['status']}"
        )


if __name__ == "__main__":
    main()
