"""Probe the pixel distribution of each fixture vs the classifier thresholds."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "python"))

from PIL import Image
import numpy as np
import cv2

from image_router import ImageClassifier

IMG_DIR = ROOT / "tests" / "fixtures" / "images"

print(f"{'file':30s} {'white>245':>10s} {'black<10':>10s} {'extreme':>10s} {'max/tot':>10s} {'edge%':>10s}  kind")
print(f"{'-'*30:30s} {'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s} {'-'*10:>10s}  ----")
for path in sorted(IMG_DIR.glob("*.png")):
    img = Image.open(path)
    arr = np.array(img.convert("L"))
    total = arr.size
    white = int((arr > 245).sum())
    black = int((arr < 10).sum())
    extreme = (white + black) / total
    max_extreme = max(white, black) / total

    edges = cv2.Canny(arr, 100, 200)
    edge_ratio = float((edges > 0).sum()) / total

    kind = ImageClassifier.classify(img)
    print(f"{path.name:30s} {white/total:>9.3%} {black/total:>9.3%} {extreme:>9.3%} {max_extreme:>9.3%} {edge_ratio:>9.3%}  {kind}")

print()
print(f"BLANK_RATIO threshold        = {ImageClassifier.BLANK_RATIO:.3f}")
print(f"DOC_EXTREME_RATIO threshold  = {ImageClassifier.DOC_EXTREME_RATIO:.3f}")
print(f"DIAGRAM_EDGE_DENSITY thresh  = {ImageClassifier.DIAGRAM_EDGE_DENSITY:.3f}")
