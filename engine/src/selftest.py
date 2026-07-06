#!/usr/bin/env python3
"""
selftest.py — UI-callable image pipeline self-test
==========================================================================
Drives SmartImageRouter against a directory of test images and emits a
single-line JSON result on stdout. The Obsidian plugin's SelfTestModal
parses this output and renders a table.

CLI contract (mirrors markitdown_wrapper.py):
    stdout : on success, ONE JSON line
             {
               "ok": true,
               "image_count": N,
               "elapsed_ms": M,
               "deps": { "opencv": true/false, "tesseract": true/false, ... },
               "cases": [
                 { "file": "...", "kind": "...", "confidence": …, "method": "...",
                   "should_escalate_to_ai": …, "elapsed_ms": …,
                   "preprocess": { "skew_angle": …, "ops_applied": [...] },
                   "breakdown": { "engine_conf_mean": …, "cross_engine_agreement": …, … },
                   "engines": { "tesseract": "…", "easyocr": "…" },
                   "text_preview": "…"
                 }, …
               ]
             }
    stderr : on failure, ONE JSON line {"error": "...", "type": "..."}
    exit   : 0 = success, 1 = failure

Usage:
    python selftest.py --image-dir tests/fixtures/images           # default fixtures
    python selftest.py --image-dir /vault/images                   # any folder
    python selftest.py --image-dir tests/fixtures/images \\
                       --cfg '{"ocr_engines":["easyocr"]}'         # override cfg

Image acceptance:
    Any .png/.jpg/.jpeg/.bmp/.tif/.tiff/.webp in the given directory.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Make sibling image_router importable when invoked as a script.
WRAPPER_DIR = os.path.dirname(os.path.abspath(__file__))
if WRAPPER_DIR not in sys.path:
    sys.path.insert(0, WRAPPER_DIR)

# Quieten the engine logger — the UI doesn't want the verbose debug stream.
logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')


# ─────────────────────────────────────────────────────────────────────────
# Defaults — mirror PARAM_SPEC in markitdown_wrapper.py
# ─────────────────────────────────────────────────────────────────────────
DEFAULT_CFG = {
    "ocr_engines": ["tesseract", "easyocr"],
    "ocr_lang": "kor+eng",
    "ocr_confidence_threshold": 70,
    "enable_ocr_ensemble": True,
    "preprocess_deskew": True,
    "enable_table_extraction": True,
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def probe_deps() -> dict:
    """Inventory which optional packages are available — purely for diagnostics."""
    def _ok(modname: str, attr: str = None) -> bool:
        try:
            import importlib
            mod = importlib.import_module(modname)
            if attr:
                getattr(mod, attr)
            return True
        except Exception:
            return False

    deps = {
        "opencv":       _ok("cv2"),
        "pillow":       _ok("PIL"),
        "tesseract":    _ok("pytesseract"),
        "easyocr":      _ok("easyocr"),
        "paddleocr":    _ok("paddleocr"),
        "transformers": _ok("transformers"),
        "torch":        _ok("torch"),
    }
    # tesseract binary is a separate concern from the python binding
    if deps["tesseract"]:
        try:
            import pytesseract  # type: ignore
            pytesseract.get_tesseract_version()
            deps["tesseract_binary"] = True
        except Exception:
            deps["tesseract_binary"] = False
    else:
        deps["tesseract_binary"] = False
    return deps


def find_images(image_dir: Path) -> list:
    if not image_dir.exists():
        return []
    files = sorted(p for p in image_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
    return files


def run_case(router, path: Path) -> dict:
    """Route a single image and shape the result into the UI-friendly dict."""
    t0 = time.time()
    try:
        res = router.route(str(path))
    except Exception as e:
        return {
            "file": path.name,
            "error": str(e),
            "elapsed_ms": int((time.time() - t0) * 1000),
        }
    elapsed = int((time.time() - t0) * 1000)
    details = res.get("details", {}) or {}

    return {
        "file": path.name,
        "kind": details.get("kind"),
        "status": res.get("status"),
        "confidence": res.get("confidence"),
        "method": res.get("method"),
        "should_escalate_to_ai": res.get("should_escalate_to_ai"),
        "elapsed_ms": elapsed,
        "preprocess": details.get("preprocess"),
        "breakdown": details.get("breakdown"),
        "engines": {
            k: {"conf": v.get("conf"), "preview": v.get("text_preview")}
            for k, v in (details.get("engine_results") or {}).items()
        },
        "text_preview": (res.get("content") or "")[:200],
        "table_summary": (
            {
                "grid_cells": len(details.get("table") or []),
                "structure_confidence": details.get("structure_confidence"),
                "column_consistency": details.get("column_consistency"),
                "unified_confidence": details.get("unified_confidence"),
            }
            if "structure_confidence" in details else None
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="SmartImageRouter self-test")
    parser.add_argument("--image-dir", required=True,
                        help="Directory containing the test images (e.g. tests/fixtures/images)")
    parser.add_argument("--cfg", default=None,
                        help="Optional JSON config override; merged on top of DEFAULT_CFG")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    cfg = dict(DEFAULT_CFG)
    if args.cfg:
        try:
            cfg.update(json.loads(args.cfg))
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid --cfg JSON: {e}", "type": "ValueError"}),
                  file=sys.stderr)
            sys.exit(1)

    try:
        from image_router import SmartImageRouter
    except ImportError as e:
        print(json.dumps({"error": f"Could not import image_router: {e}",
                          "type": "ImportError"}), file=sys.stderr)
        sys.exit(1)

    images = find_images(image_dir)
    if not images:
        print(json.dumps({"error": f"No images found in {image_dir}",
                          "type": "ValueError"}), file=sys.stderr)
        sys.exit(1)

    deps = probe_deps()
    router = SmartImageRouter(cfg)

    t0 = time.time()
    cases = [run_case(router, p) for p in images]
    total_elapsed_ms = int((time.time() - t0) * 1000)

    payload = {
        "ok": True,
        "image_count": len(images),
        "elapsed_ms": total_elapsed_ms,
        "image_dir": str(image_dir.resolve()),
        "cfg": cfg,
        "deps": deps,
        "cases": cases,
    }
    # Single line JSON on stdout — UI parses this.
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Defensive: any unhandled crash → structured stderr so the UI can show it.
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        sys.exit(1)
