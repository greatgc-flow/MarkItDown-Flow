#!/usr/bin/env python3
"""
SmartImageRouter — Offline-First Image & Table Processing for MarkItDown-Flow
================================================================================
Routes images through type classification → preprocessing → OCR ensemble → table
extraction, and only escalates to AI when the unified offline confidence falls
below the configured threshold.

[Design Principles]
  1. Offline-first. AI is the last resort (cost / privacy / speed all benefit).
  2. Ensemble-based confidence — never trust a single OCR engine's self-reported score.
  3. Type-based routing — photo / document / table / diagram / blank each take a
     different path.
  4. Structural confidence is computed separately from OCR confidence for tables
     (grid integrity, not character score).
  5. Lazy imports — missing deps degrade gracefully; the host never crashes.

[Installation]
  pip install markitdown Pillow geopy             # core (already used by wrapper)
  pip install opencv-python numpy                 # preprocessing (P0)
  pip install pytesseract                         # OCR engine #1 (P0)
  pip install easyocr                             # OCR engine #2 (P0)
  pip install paddlepaddle paddleocr              # OCR engine #3 (P2, optional)
  pip install img2table                           # Table extraction   (P1, optional, fast)

Notes:
  - Tesseract requires the tesseract binary at OS level. Korean traineddata
    must be installed for `kor` (Linux: tesseract-ocr-kor; Windows: ship with the
    UB-Mannheim installer).
  - EasyOCR / PaddleOCR auto-download model weights to ~/.EasyOCR / ~/.paddleocr
    on first run.
  - Table Transformer downloads ~120 MB on first run.

[API Console Links — same as the wrapper]
  OpenAI         : https://platform.openai.com/api-keys
  Anthropic      : https://console.anthropic.com/settings/keys
  Google Gemini  : https://aistudio.google.com/app/apikey
  Azure DocIntel : https://portal.azure.com/
"""

from __future__ import annotations

import logging
import os
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from typing import Any, Optional

# The wrapper sets up the "OmniDataEngine" logger; we attach the same.
logger = logging.getLogger("OmniDataEngine")


def _configure_tesseract() -> None:
    """
    Auto-detect and configure Tesseract on Windows (UB-Mannheim install).
    Sets:
      - pytesseract.tesseract_cmd  → binary path
      - TESSDATA_PREFIX             → user tessdata dir (if it has more lang files)
    Safe to call multiple times (idempotent).
    """
    if os.name != 'nt':
        return
    bin_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if not os.path.exists(bin_path):
        return

    # pytesseract: point at the binary
    try:
        import pytesseract  # type: ignore
        pytesseract.pytesseract.tesseract_cmd = bin_path
    except ImportError:
        pass

    # TESSDATA_PREFIX: prefer user dir (~/.tessdata) if it has kor.traineddata
    user_tessdata = os.path.join(os.path.expanduser('~'), '.tessdata')
    if os.path.isfile(os.path.join(user_tessdata, 'kor.traineddata')):
        os.environ.setdefault('TESSDATA_PREFIX', user_tessdata)
        logger.debug(f"[Tesseract] TESSDATA_PREFIX → {user_tessdata}")


_configure_tesseract()


# ─────────────────────────────────────────────────────────────────────────────
# Lazy-import helpers. Every heavy dependency is imported inside the function
# that needs it, so an environment with only Pillow + cv2 still gives us
# classify + deskew + Tesseract-only OCR.
# ─────────────────────────────────────────────────────────────────────────────

def _try_import_cv2():
    """Returns (cv2, numpy) or (None, None) if either is missing."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        return cv2, np
    except ImportError:
        return None, None


def _try_import_pil():
    """Returns the Pillow Image module or None."""
    try:
        from PIL import Image  # type: ignore
        return Image
    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 0. ConfidenceMatrix — configurable weighted aggregation of sub-metrics
# ─────────────────────────────────────────────────────────────────────────────

class ConfidenceMatrix:
    """
    Named, weighted aggregation of confidence sub-metrics that collapses
    to a single 0..100 score.

    Each metric key maps to a weight. Weights are automatically normalized
    to sum to 1.0, so disabling one metric (weight=0) or adjusting any
    weight never requires touching the others.

    Default weights replicate the original hand-tuned constants:
      engine_conf  0.30  — mean engine self-reported confidence
      agreement    0.35  — cross-engine text similarity (SequenceMatcher)
      length       0.15  — inter-engine output-length consistency
      cleanliness  0.10  — fraction of non-garbage characters
      stdev_inv    0.10  — inverse of inter-engine confidence spread

    Caller may pass any subset of overrides; unspecified keys keep defaults.
    All values are clamped to [0, ∞) before normalization (negatives ignored).
    """

    DEFAULT_WEIGHTS: dict = {
        "engine_conf": 0.30,
        "agreement":   0.35,
        "length":      0.15,
        "cleanliness": 0.10,
        "stdev_inv":   0.10,
    }

    def __init__(self, weights: Optional[dict] = None):
        merged = {
            k: max(0.0, float(weights.get(k, v)))
            for k, v in self.DEFAULT_WEIGHTS.items()
        } if weights else dict(self.DEFAULT_WEIGHTS)
        total = sum(merged.values()) or 1.0
        self._w = {k: v / total for k, v in merged.items()}

    def compute(self, scores: dict) -> float:
        """Weighted sum; scores are expected in [0, 100]."""
        return sum(scores.get(k, 0.0) * w for k, w in self._w.items())

    def breakdown(self, scores: dict) -> dict:
        """Return per-metric values rounded to 3dp (for diagnostics)."""
        return {k: round(scores.get(k, 0.0), 3) for k in self._w}

    @property
    def weights(self) -> dict:
        return dict(self._w)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ImageClassifier — offline heuristic type detection
# ─────────────────────────────────────────────────────────────────────────────

class ImageClassifier:
    """
    Classifies an image into one of:
      'blank'    near-uniform white or black (>= 95% pixels in extreme bin)
      'table'    Hough lines detect >=4 strong horizontal AND >=3 vertical lines
      'document' high-contrast B/W (text-like), >60% pixels at extremes
      'diagram'  high edge density but low extreme-pixel ratio (line art)
      'photo'    continuous-tone, none of the above

    Order is intentional: table is checked before document because tables are
    also high-contrast and would otherwise be labelled 'document'.

    Tunable class-level constants make behaviour testable without subclassing.
    """

    # Empirically tuned to call only TRULY empty pages 'blank'. A page with even
    # ~3% non-extreme pixels (i.e. with any meaningful text) is no longer
    # 'blank'. We used to use 0.95 here but that misclassified low-density
    # documents (~5-7% text coverage) — see tests/fixtures and the diagnostic
    # in CHANGELOG 0.1.0 "Self-test" entry.
    BLANK_RATIO = 0.99          # min fraction of pixels in extreme bin to call blank
    DOC_EXTREME_RATIO = 0.60    # min fraction at extremes to call document
    DIAGRAM_EDGE_DENSITY = 0.04 # min fraction of edge pixels to call diagram
    TABLE_MIN_HLINES = 4
    TABLE_MIN_VLINES = 3

    @classmethod
    def classify(cls, pil_image) -> str:
        cv2, np = _try_import_cv2()
        if cv2 is None:
            logger.warning("[Classifier] opencv-python/numpy not installed — defaulting to 'photo'.")
            return 'photo'

        try:
            arr = np.array(pil_image.convert("L"))
            total = arr.size

            white = int((arr > 245).sum())
            black = int((arr < 10).sum())
            extreme_ratio = (white + black) / total

            if max(white, black) / total >= cls.BLANK_RATIO:
                logger.debug("[Classifier] kind=blank (extreme-bin dominance)")
                return 'blank'

            # Table check BEFORE document — tables are also high-contrast.
            try:
                edges = cv2.Canny(arr, 50, 150)
                lines = cv2.HoughLinesP(
                    edges, 1, np.pi / 180,
                    threshold=100,
                    minLineLength=max(30, arr.shape[1] // 4),
                    maxLineGap=10,
                )
                h_cnt = v_cnt = 0
                if lines is not None:
                    for line in lines:
                        x1, y1, x2, y2 = line[0]
                        dx, dy = abs(x2 - x1), abs(y2 - y1)
                        if dy < 5 and dx > 30:
                            h_cnt += 1
                        elif dx < 5 and dy > 30:
                            v_cnt += 1
                if h_cnt >= cls.TABLE_MIN_HLINES and v_cnt >= cls.TABLE_MIN_VLINES:
                    logger.debug(f"[Classifier] kind=table (h={h_cnt}, v={v_cnt})")
                    return 'table'
            except Exception as e:
                logger.debug(f"[Classifier] Hough table check failed: {e}")

            if extreme_ratio >= cls.DOC_EXTREME_RATIO:
                logger.debug(f"[Classifier] kind=document (extreme_ratio={extreme_ratio:.2f})")
                return 'document'

            # diagram vs photo
            try:
                edges = cv2.Canny(arr, 100, 200)
                edge_ratio = float((edges > 0).sum()) / total
                if edge_ratio >= cls.DIAGRAM_EDGE_DENSITY:
                    logger.debug(f"[Classifier] kind=diagram (edge_ratio={edge_ratio:.3f})")
                    return 'diagram'
            except Exception as e:
                logger.debug(f"[Classifier] edge density check failed: {e}")

            logger.debug("[Classifier] kind=photo (fallback)")
            return 'photo'
        except Exception as e:
            logger.warning(f"[Classifier] classification failed: {e}. Falling back to 'photo'.")
            return 'photo'


# ─────────────────────────────────────────────────────────────────────────────
# 2. ImagePreprocessor — deskew, denoise, binarize, (optional) super-resolution
# ─────────────────────────────────────────────────────────────────────────────

class ImagePreprocessor:
    """
    Standard scan-cleanup pipeline. Every step is independently toggleable via
    the corresponding `enable_*` argument. Returns (processed_pil, info_dict)
    where info_dict carries diagnostics consumed by downstream confidence
    discounting (notably `skew_angle`).
    """

    DESKEW_MIN_ANGLE_DEG = 0.3   # don't bother rotating below this

    @classmethod
    def preprocess(
        cls,
        pil_image,
        enable_deskew: bool = True,
        deskew_method: str = 'auto',
        enable_denoise: bool = True,
        enable_binarize: bool = True,
    ):
        """
        deskew_method:
          'auto'       — Hough lines first, projection-profile fallback (default)
          'hough'      — Hough only; returns 0° if no long lines detected
          'projection' — Projection-profile only (brute-force angle search)
        """
        info: dict = {"skew_angle": 0.0, "ops_applied": []}
        cv2, np = _try_import_cv2()
        Image = _try_import_pil()
        if cv2 is None or Image is None:
            logger.warning("[Preprocess] opencv-python or Pillow missing — returning original.")
            return pil_image, info

        try:
            arr = np.array(pil_image.convert("L"))

            if enable_deskew:
                angle = cls._detect_skew(arr, cv2, np, method=deskew_method)
                if abs(angle) > cls.DESKEW_MIN_ANGLE_DEG:
                    arr = cls._rotate(arr, angle, cv2)
                    info["skew_angle"] = angle
                    info["ops_applied"].append("deskew")
                    logger.debug(f"[Preprocess] deskew applied: angle={angle:.2f}°")

            if enable_denoise:
                try:
                    arr = cv2.fastNlMeansDenoising(arr, h=10)
                    info["ops_applied"].append("denoise")
                except Exception as e:
                    logger.debug(f"[Preprocess] denoise skipped: {e}")

            if enable_binarize:
                try:
                    arr = cv2.adaptiveThreshold(
                        arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY, 31, 10,
                    )
                    info["ops_applied"].append("binarize")
                except Exception as e:
                    logger.debug(f"[Preprocess] binarize skipped: {e}")

            return Image.fromarray(arr), info
        except Exception as e:
            logger.warning(f"[Preprocess] pipeline failed: {e}. Returning original.")
            return pil_image, info

    @staticmethod
    def _detect_skew(arr, cv2, np, method: str = 'auto') -> float:
        """
        method='hough'      — Hough long-line median only.
        method='projection' — Projection-profile brute-force only.
        method='auto'       — Hough first; projection fallback when no lines found.
        """
        if method == 'projection':
            return ImagePreprocessor._detect_skew_projection(arr, cv2, np)

        # Hough stage (shared by 'hough' and 'auto')
        edges = cv2.Canny(arr, 50, 200, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=100,
            minLineLength=max(30, arr.shape[1] // 3),
            maxLineGap=10,
        )
        if lines is not None:
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 != x1:
                    a = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                    if -45 < a < 45:
                        angles.append(a)
            if angles:
                return float(np.median(angles))

        if method == 'hough':
            return 0.0  # no fallback requested

        return ImagePreprocessor._detect_skew_projection(arr, cv2, np)

    @staticmethod
    def _detect_skew_projection(arr, cv2, np) -> float:
        """
        Two-pass projection-profile skew detection for text-only pages.

        Pass 1 — coarse scan at 1° steps over [-10°, +10°].
        Pass 2 — fine scan at 0.1° steps in [best-1°, best+1°].

        At the correct angle, text baselines are horizontal and produce sharp
        density peaks in the row-sum histogram (high variance). A flat histogram
        means the image has no discernible text rows and we return 0°.
        """
        try:
            _, binary = cv2.threshold(
                arr, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU,
            )
            h, w = binary.shape
            cx, cy = w / 2, h / 2

            def _best_angle(angles):
                best_a, best_v = 0.0, -1.0
                for a in angles:
                    M = cv2.getRotationMatrix2D((cx, cy), float(a), 1.0)
                    rot = cv2.warpAffine(
                        binary, M, (w, h),
                        flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT,
                    )
                    v = float(np.var(np.sum(rot, axis=1)))
                    if v > best_v:
                        best_v, best_a = v, float(a)
                return best_a, best_v

            coarse_best, coarse_var = _best_angle(np.arange(-10.0, 11.0, 1.0))
            # A flat projection (very low variance) means no meaningful text rows.
            if coarse_var < 1e4:
                return 0.0

            fine_best, _ = _best_angle(
                np.arange(coarse_best - 1.0, coarse_best + 1.05, 0.1),
            )
            return fine_best if abs(fine_best) > 0.3 else 0.0
        except Exception as e:
            logger.debug(f"[Preprocess/projection-deskew] failed: {e}")
            return 0.0

    @staticmethod
    def _rotate(arr, angle: float, cv2):
        h, w = arr.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(
            arr, M, (w, h),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. OCREnsemble — Tesseract + EasyOCR (+ PaddleOCR) with unified confidence
# ─────────────────────────────────────────────────────────────────────────────

class OCREnsemble:
    """
    Runs configured OCR engines, computes a unified confidence score, and
    decides whether to escalate to AI.

    Unified confidence (0..100) — weighted sum:
        0.30 × engine_conf_mean       (each engine's own avg confidence)
        0.35 × cross_engine_agreement (mean pairwise SequenceMatcher × 100)
        0.15 × length_consistency     ((1 − CV of text lengths) × 100)
        0.10 × cleanliness            ((1 − garbage_char_ratio) × 100)
        0.10 × conf_stdev_inverse     (max(0, 1 − stdev/30) × 100)

    The escalation gate (`should_escalate_to_ai = True`) fires when:
      - no engine returned usable text, OR
      - inter-engine agreement is below MIN_AGREEMENT_FOR_PICK, OR
      - final unified confidence is below the configured threshold.
    """

    # Anything not in this character class is treated as garbage by the
    # cleanliness sub-metric. Korean range 가-힣 included for the RAG target.
    GARBAGE_PATTERN = re.compile(r'[^\w\s가-힣.,!?;:\-/()]')
    MIN_AGREEMENT_FOR_PICK = 0.70   # below this we refuse to pick any single engine's text
    DEFAULT_AI_THRESHOLD = 70       # unified confidence below which we escalate

    # Keyed by (langs_tuple, gpu_bool) — avoids 5-10s model reload per image.
    _reader_cache: dict = {}

    @classmethod
    def run(
        cls,
        pil_image,
        lang: str = 'kor+eng',
        engines: Optional[list] = None,
        ai_threshold: int = DEFAULT_AI_THRESHOLD,
        metric_weights: Optional[dict] = None,
    ) -> dict:
        """
        Run configured OCR engines (in parallel when >1) and aggregate results
        through a ConfidenceMatrix into a single 0..100 unified score.

        Parameters
        ----------
        metric_weights : optional dict
            Per-metric weight overrides, e.g. {"agreement": 0.5, "length": 0.1}.
            Unspecified keys keep ConfidenceMatrix.DEFAULT_WEIGHTS.
        """
        engines = engines or ['tesseract', 'easyocr', 'paddleocr']
        matrix = ConfidenceMatrix(metric_weights)

        engine_fns = {
            'tesseract': cls._run_tesseract,
            'easyocr':   cls._run_easyocr,
            'paddleocr': cls._run_paddleocr,
        }
        valid = [e for e in engines if e in engine_fns]

        results: dict[str, dict] = {}
        if len(valid) > 1:
            with ThreadPoolExecutor(max_workers=len(valid)) as pool:
                futures = {
                    pool.submit(engine_fns[e], pil_image, lang): e
                    for e in valid
                }
                for fut in as_completed(futures):
                    eng = futures[fut]
                    try:
                        r = fut.result()
                        if r is not None:
                            results[eng] = r
                    except Exception as exc:
                        logger.warning(f"[OCREnsemble] {eng} raised: {exc}")
        else:
            for e in valid:
                r = engine_fns[e](pil_image, lang)
                if r is not None:
                    results[e] = r

        if not results:
            return {
                'text': None,
                'confidence': 0.0,
                'breakdown': {},
                'engine_results': {},
                'should_escalate_to_ai': True,
                'reason': 'No OCR engine available or all failed.',
            }

        texts = [r['text'] for r in results.values() if r.get('text') is not None]
        confs = [r['confidence'] for r in results.values() if r.get('confidence') is not None]

        engine_conf_mean = (sum(confs) / len(confs)) if confs else 0.0
        agreement        = cls._cross_engine_agreement(texts)
        length_consist   = cls._length_consistency(texts)
        cleanliness      = cls._cleanliness(texts)
        stdev_inv        = cls._conf_stdev_inverse(confs)

        scores = {
            "engine_conf": engine_conf_mean,
            "agreement":   agreement * 100,
            "length":      length_consist * 100,
            "cleanliness": cleanliness * 100,
            "stdev_inv":   stdev_inv,
        }
        unified = matrix.compute(scores)

        # Pick best engine's text only when agreement is high enough.
        chosen_text: Optional[str] = None
        chosen_engine: Optional[str] = None
        if agreement >= cls.MIN_AGREEMENT_FOR_PICK and confs:
            chosen_engine = max(results, key=lambda k: results[k].get('confidence', 0))
            chosen_text = results[chosen_engine].get('text')

        logger.debug(
            f"[OCREnsemble] engines={list(results)} parallel={len(valid)>1} "
            f"unified={unified:.1f} agreement={agreement:.2f} chosen={chosen_engine}"
        )

        return {
            'text': chosen_text,
            'confidence': round(unified, 2),
            'breakdown': matrix.breakdown(scores),
            'matrix_weights': {k: round(v, 3) for k, v in matrix.weights.items()},
            'engine_results': {
                k: {'conf': round(v.get('confidence', 0.0), 2),
                    'text_preview': (v.get('text') or '')[:80]}
                for k, v in results.items()
            },
            'chosen_engine': chosen_engine,
            'should_escalate_to_ai': (chosen_text is None) or (unified < ai_threshold),
        }

    # ── Engine adapters ──────────────────────────────────────────────────────

    @staticmethod
    def _run_tesseract(pil_image, lang: str) -> Optional[dict]:
        try:
            import pytesseract  # type: ignore
            data = pytesseract.image_to_data(
                pil_image, lang=lang,
                output_type=pytesseract.Output.DICT,
            )
            confs = [
                int(c) for c in data.get('conf', [])
                if str(c).lstrip('-').isdigit() and int(c) >= 0
            ]
            texts = [t for t in data.get('text', []) if t and t.strip()]
            if not texts:
                return {'text': '', 'confidence': 0.0}
            return {
                'text': ' '.join(texts),
                'confidence': (sum(confs) / len(confs)) if confs else 50.0,
            }
        except ImportError:
            logger.debug("[OCR/tesseract] pytesseract not installed — skipped.")
        except Exception as e:
            logger.warning(f"[OCR/tesseract] failed: {e}")
        return None

    @staticmethod
    def _run_easyocr(pil_image, lang: str) -> Optional[dict]:
        try:
            import easyocr  # type: ignore
            cv2, np = _try_import_cv2()
            if np is None:
                logger.debug("[OCR/easyocr] numpy missing — skipped.")
                return None
            # Tesseract uses 'kor+eng'; EasyOCR uses ISO codes ['ko','en'].
            iso_map = {'kor': 'ko', 'eng': 'en', 'jpn': 'ja', 'chi_sim': 'ch_sim'}
            langs = [iso_map.get(p, p) for p in lang.split('+')]
            cache_key = (tuple(langs), False)
            reader = OCREnsemble._reader_cache.get(cache_key)
            if reader is None:
                logger.debug(f"[OCR/easyocr] loading Reader for langs={langs}")
                reader = easyocr.Reader(langs, gpu=False, verbose=False)
                OCREnsemble._reader_cache[cache_key] = reader
            arr = np.array(pil_image.convert("RGB"))
            results = reader.readtext(arr)  # [(bbox, text, conf), ...]
            if not results:
                return {'text': '', 'confidence': 0.0}
            texts = [r[1] for r in results]
            confs = [float(r[2]) for r in results]
            return {
                'text': ' '.join(texts),
                'confidence': (sum(confs) / len(confs)) * 100 if confs else 0.0,
            }
        except ImportError:
            logger.debug("[OCR/easyocr] easyocr not installed — skipped.")
        except Exception as e:
            logger.warning(f"[OCR/easyocr] failed: {e}")
        return None

    # Keyed by paddle_lang string.
    _paddle_cache: dict = {}

    @staticmethod
    def _run_paddleocr(pil_image, lang: str) -> Optional[dict]:
        try:
            from paddleocr import PaddleOCR  # type: ignore
            cv2, np = _try_import_cv2()
            if np is None:
                logger.debug("[OCR/paddleocr] numpy missing — skipped.")
                return None
            # Paddle codes: 'korean','en','japan','ch','chinese_cht'
            paddle_lang = 'korean' if 'kor' in lang else 'en'
            ocr = OCREnsemble._paddle_cache.get(paddle_lang)
            if ocr is None:
                logger.debug(f"[OCR/paddleocr] loading PaddleOCR for lang={paddle_lang}")
                ocr = PaddleOCR(use_angle_cls=True, lang=paddle_lang, show_log=False)
                OCREnsemble._paddle_cache[paddle_lang] = ocr
            arr = np.array(pil_image.convert("RGB"))
            result = ocr.ocr(arr, cls=True)
            if not result or not result[0]:
                return {'text': '', 'confidence': 0.0}
            texts, confs = [], []
            for line in result[0]:
                if len(line) >= 2 and line[1]:
                    texts.append(line[1][0])
                    confs.append(float(line[1][1]))
            return {
                'text': ' '.join(texts),
                'confidence': (sum(confs) / len(confs)) * 100 if confs else 0.0,
            }
        except ImportError:
            logger.debug("[OCR/paddleocr] paddleocr not installed — skipped.")
        except Exception as e:
            logger.warning(f"[OCR/paddleocr] failed: {e}")
        return None

    # ── Confidence sub-metrics ──────────────────────────────────────────────

    @staticmethod
    def _cross_engine_agreement(texts: list) -> float:
        non_empty = [t for t in texts if t]
        if len(non_empty) < 2:
            return 1.0
        scores = []
        for i in range(len(non_empty)):
            for j in range(i + 1, len(non_empty)):
                scores.append(SequenceMatcher(None, non_empty[i], non_empty[j]).ratio())
        return (sum(scores) / len(scores)) if scores else 0.0

    @staticmethod
    def _length_consistency(texts: list) -> float:
        lens = [len(t) for t in texts if t]
        if len(lens) < 2:
            return 1.0
        mean_len = sum(lens) / len(lens)
        if mean_len == 0:
            return 0.0
        cv = statistics.pstdev(lens) / mean_len
        return max(0.0, 1.0 - cv)

    @classmethod
    def _cleanliness(cls, texts: list) -> float:
        ratios = []
        for t in texts:
            if not t:
                continue
            ratios.append(len(cls.GARBAGE_PATTERN.findall(t)) / max(1, len(t)))
        if not ratios:
            return 1.0
        return max(0.0, 1.0 - (sum(ratios) / len(ratios)))

    @staticmethod
    def _conf_stdev_inverse(confs: list) -> float:
        if len(confs) < 2:
            return 100.0
        return max(0.0, (1.0 - statistics.pstdev(confs) / 30.0) * 100)



# ─────────────────────────────────────────────────────────────────────────────
# 5. SmartImageRouter — orchestrates classify → preprocess → OCR/Table → escalate
# ─────────────────────────────────────────────────────────────────────────────

class SmartImageRouter:
    """
    Decision tree:

        load → classify
          ├─ blank      → skip
          ├─ photo      → metadata only; escalate to AI iff llm_prompt provided
          ├─ table      → img2table fast extraction → fallback to OCREnsemble
          └─ document /
              diagram   → ImagePreprocessor.preprocess → OCREnsemble.run

    Return shape is intentionally compatible with the wrapper's phase dicts
    (`content`, `status`) plus extra keys (`confidence`, `method`,
    `should_escalate_to_ai`, `details`) consumed by MarkItDownEngine.
    """

    AI_ESCALATION_THRESHOLD_DEFAULT = 70   # 0..100
    SKEW_DISCOUNT_ANGLE_DEG = 5
    SKEW_DISCOUNT_FACTOR = 0.9

    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or {}

    # ─── Public API ─────────────────────────────────────────────────────────

    def route(self, image_source) -> dict:
        Image = _try_import_pil()
        if Image is None:
            return self._fail("Pillow not installed")

        try:
            if isinstance(image_source, str):
                pil = Image.open(image_source)
                pil.load()
            else:
                pil = image_source
        except Exception as e:
            return self._fail(f"Could not open image: {e}")

        kind = ImageClassifier.classify(pil)
        logger.info(f"[SmartImageRouter] classified as: {kind}")

        if kind == 'blank':
            return self._make_result(
                content="", status="Skipped (blank)",
                confidence=100.0, method="classify",
                escalate=False, details={"kind": kind},
            )

        if kind == 'photo':
            # No OCR/table work; let upstream AI phase handle if a prompt is set.
            has_prompt = bool(self.cfg.get('llm_prompt'))
            return self._make_result(
                content="", status="Skipped (photo — no text expected)",
                confidence=0.0, method="classify",
                escalate=has_prompt,
                details={"kind": kind, "reason_for_escalation":
                          "llm_prompt present" if has_prompt else "no llm_prompt"},
            )

        if kind == 'table' and self.cfg.get('enable_table_extraction', True):
            return self._route_table(pil, kind)

        return self._route_textual(pil, kind)

    # ─── Internal ───────────────────────────────────────────────────────────

    def _route_textual(self, pil, kind: str) -> dict:
        proc_pil, info = ImagePreprocessor.preprocess(
            pil,
            enable_deskew=self.cfg.get('preprocess_deskew', True),
            deskew_method=self.cfg.get('deskew_method', 'auto'),
            enable_denoise=True,
            enable_binarize=True,
        )

        engines = self.cfg.get('ocr_engines') or ['tesseract', 'easyocr']
        if not self.cfg.get('enable_ocr_ensemble', True):
            engines = ['tesseract']

        threshold = int(self.cfg.get(
            'ocr_confidence_threshold', self.AI_ESCALATION_THRESHOLD_DEFAULT,
        ))
        # Build ConfidenceMatrix weight overrides from individual cfg keys.
        # Any key absent from cfg keeps the ConfidenceMatrix default weight.
        weight_map = {
            "engine_conf": "confidence_weight_engine_conf",
            "agreement":   "confidence_weight_agreement",
            "length":      "confidence_weight_length",
            "cleanliness": "confidence_weight_cleanliness",
            "stdev_inv":   "confidence_weight_stdev_inv",
        }
        metric_weights = {
            metric: self.cfg[cfg_key]
            for metric, cfg_key in weight_map.items()
            if cfg_key in self.cfg
        } or None

        ocr_res = OCREnsemble.run(
            proc_pil,
            lang=self.cfg.get('ocr_lang', 'kor+eng'),
            engines=engines,
            ai_threshold=threshold,
            metric_weights=metric_weights,
        )

        conf = float(ocr_res.get("confidence") or 0.0)
        # No skew discount when deskew was applied — the image fed to OCR is
        # already corrected, so penalising it further would be counterproductive.
        # Only apply the discount when the image arrives pre-skewed and we didn't
        # correct it (angle within DESKEW_MIN_ANGLE_DEG or deskew disabled).
        deskew_applied = "deskew" in info.get("ops_applied", [])
        skew_angle = info.get("skew_angle", 0.0)
        if not deskew_applied and abs(skew_angle) > self.SKEW_DISCOUNT_ANGLE_DEG:
            conf *= self.SKEW_DISCOUNT_FACTOR
            ocr_res["confidence_after_skew_discount"] = round(conf, 2)

        escalate = (ocr_res.get("text") is None) or (conf < threshold)

        logger.debug(
            f"[SmartImageRouter] kind={kind} conf={conf:.1f} "
            f"threshold={threshold} escalate={escalate}"
        )

        return self._make_result(
            content=ocr_res.get("text") or "",
            status=f"OCREnsemble ({kind})",
            confidence=round(conf, 2),
            method=f"classify+preprocess+ensemble({','.join(engines)})",
            escalate=escalate,
            details={"kind": kind, "preprocess": info, **ocr_res},
        )

    # Tesseract→EasyOCR language code map for img2table.
    _TESS_TO_EASYOCR: dict = {
        'kor': 'ko', 'eng': 'en', 'jpn': 'ja',
        'chi_sim': 'ch_sim', 'chi_tra': 'ch_tra',
        'fra': 'fr', 'spa': 'es', 'ara': 'ar', 'hin': 'hi',
        'deu': 'de', 'por': 'pt', 'rus': 'ru', 'ita': 'it',
    }

    @classmethod
    def _tess_lang_to_easyocr(cls, tess_lang: str) -> list:
        """Convert 'kor+eng' Tesseract code to ['ko','en'] EasyOCR list."""
        codes = []
        for part in tess_lang.split('+'):
            code = cls._TESS_TO_EASYOCR.get(part.strip().lower())
            if code:
                codes.append(code)
        return codes or ['en']

    def _route_table(self, pil, kind: str) -> dict:
        """
        Fast table extraction via img2table (OpenCV line detection).
        OCR priority: EasyOCR (always available) → Tesseract (if binary found).
        Falls back to OCREnsemble when img2table finds no table structure.
        """
        try:
            import io
            from img2table.document import Image as Img2Image  # type: ignore

            lang_tess = self.cfg.get('ocr_lang', 'kor+eng')
            buf = io.BytesIO()
            pil.save(buf, format='PNG')
            buf.seek(0)
            img_doc = Img2Image(src=buf)

            ocr = self._build_img2table_ocr(lang_tess)
            if ocr is None:
                logger.debug("[SmartImageRouter] no OCR engine for img2table — falling back")
                return self._route_textual(pil, kind)

            tables = img_doc.extract_tables(ocr=ocr, implicit_rows=True, borderless_tables=False)

            if tables:
                md_parts = [self._df_to_markdown(t.df) for t in tables if t.df is not None]
                md = "\n\n".join(p for p in md_parts if p)
                if md:
                    logger.debug(f"[SmartImageRouter] img2table found {len(tables)} table(s)")
                    return self._make_result(
                        content=md, status="img2table",
                        confidence=90.0, method="img2table + EasyOCR",
                        escalate=False, details={"kind": kind, "table_count": len(tables)},
                    )
        except ImportError:
            logger.debug("[SmartImageRouter] img2table not installed — falling back to OCREnsemble")
        except Exception as e:
            logger.warning(f"[SmartImageRouter] img2table failed: {e} — falling back to OCREnsemble")

        return self._route_textual(pil, kind)

    @classmethod
    def _build_img2table_ocr(cls, tess_lang: str):
        """
        Build the best available img2table OCR engine.
        Tries EasyOCR first (no binary needed), then Tesseract.
        Returns None if neither is available.
        """
        # Try EasyOCR (preferred — already installed in most envs)
        try:
            from img2table.ocr import EasyOCR as Img2EasyOCR  # type: ignore
            lang_list = cls._tess_lang_to_easyocr(tess_lang)
            return Img2EasyOCR(lang=lang_list)
        except Exception as e:
            logger.debug(f"[img2table] EasyOCR unavailable: {e}")

        # Fallback: Tesseract binary (if installed)
        try:
            from img2table.ocr import TesseractOCR  # type: ignore
            return TesseractOCR(lang=tess_lang)
        except Exception as e:
            logger.debug(f"[img2table] TesseractOCR unavailable: {e}")

        return None

    # ─── Builders ───────────────────────────────────────────────────────────

    @staticmethod
    def _make_result(*, content: str, status: str, confidence: float,
                     method: str, escalate: bool, details: dict) -> dict:
        return {
            "content": content,
            "status": status,
            "confidence": confidence,
            "method": method,
            "should_escalate_to_ai": escalate,
            "details": details,
        }

    @staticmethod
    def _fail(reason: str) -> dict:
        return SmartImageRouter._make_result(
            content="", status=f"Failed ({reason})",
            confidence=0.0, method="n/a",
            escalate=True, details={"reason": reason},
        )

    @staticmethod
    def _df_to_markdown(df) -> str:
        """Convert an img2table DataFrame to a GitHub-flavoured Markdown table."""
        if df is None:
            return ""
        try:
            rows = df.values.tolist()
            ncols = len(df.columns)
            if not rows or ncols == 0:
                return ""
            lines = []
            for i, row in enumerate(rows):
                cells = [str(c).replace("|", "\\|") if c is not None else "" for c in row]
                lines.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    lines.append("|" + "|".join(["---"] * ncols) + "|")
            return "\n".join(lines)
        except Exception:
            return ""


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience facade (matches what MarkItDownEngine imports)
# ─────────────────────────────────────────────────────────────────────────────

def route_image(image_source: Any, cfg: Optional[dict] = None) -> dict:
    """Top-level convenience: instantiate a router with the given cfg and run it."""
    return SmartImageRouter(cfg or {}).route(image_source)
