"""
_make_test_images.py
========================================================================
Synthesises four test images for SmartImageRouter validation.

  case_1_doc_clean.png   — clean Korean+English document scan
  case_2_doc_skewed.png  — case 1 rotated by 7° (deskew should recover)
  case_3_table.png       — ruled table with cells (Hough detects → 'table')
  case_4_photo.png       — gradient continuous-tone (classifier → 'photo')

Output dir: python/_test_images/
Run:        python scripts/_make_test_images.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed — run `pip install Pillow`")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
OUT  = ROOT / "tests" / "fixtures" / "images"
OUT.mkdir(parents=True, exist_ok=True)


def find_korean_font() -> ImageFont.FreeTypeFont:
    """
    Find a Korean-capable TrueType font on the host. Pillow's default bitmap
    font can't render Hangul, so we look for the standard Windows fonts first
    and fall back to a no-op bitmap font (which will just render boxes for
    Korean — still useful for OCR confidence experiments).
    """
    candidates = [
        "C:/Windows/Fonts/malgun.ttf",        # Malgun Gothic — common Windows Korean
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "C:/Windows/Fonts/batang.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, 28)
    print("WARNING: no Korean font found — Hangul will render as boxes.")
    return ImageFont.load_default()


def case_1_doc_clean(font: ImageFont.FreeTypeFont) -> Path:
    """White background, dense Korean+English text. High contrast → document."""
    img = Image.new("RGB", (1200, 900), "white")
    d = ImageDraw.Draw(img)
    lines = [
        "보고서 — 채권 무효화 진행 현황",
        "Project status: 2026 Q2 — Compliance Audit",
        "",
        "본 보고서는 채권 무효화 절차의 진행 상황을 정리합니다.",
        "1. 법무 검토 (Legal review) — 완료",
        "2. 회계 처리 (Accounting) — 진행 중",
        "3. 보고 및 공시 (Reporting) — 예정",
        "",
        "담당자: 김OO  /  연락처: 010-XXXX-XXXX",
        "Status code: ACTIVE-2026-05-27",
        "",
        "다음 단계는 6월 첫 째 주에 진행될 예정입니다.",
        "Next milestone: 2026-06-03",
    ]
    y = 60
    for line in lines:
        d.text((80, y), line, fill="black", font=font)
        y += 50
    out = OUT / "case_1_doc_clean.png"
    img.save(out)
    return out


def case_2_doc_skewed(src: Path) -> Path:
    """case 1 rotated by 7° — should trigger deskew."""
    img = Image.open(src)
    rotated = img.rotate(7, expand=True, fillcolor="white")
    out = OUT / "case_2_doc_skewed.png"
    rotated.save(out)
    return out


def case_3_table(font: ImageFont.FreeTypeFont) -> Path:
    """Ruled grid with cells — Hough should detect horizontal + vertical lines."""
    img = Image.new("RGB", (1200, 700), "white")
    d = ImageDraw.Draw(img)

    rows, cols = 5, 4
    x0, y0, x1, y1 = 80, 60, 1120, 620
    cell_w = (x1 - x0) / cols
    cell_h = (y1 - y0) / rows

    # Grid lines (3 px so Hough finds them robustly)
    for i in range(rows + 1):
        y = int(y0 + i * cell_h)
        d.line([(x0, y), (x1, y)], fill="black", width=3)
    for j in range(cols + 1):
        x = int(x0 + j * cell_w)
        d.line([(x, y0), (x, y1)], fill="black", width=3)

    # Header row
    headers = ["항목", "수량", "단가", "비고"]
    for j, h in enumerate(headers):
        cx = int(x0 + j * cell_w + 20)
        d.text((cx, y0 + 10), h, fill="black", font=font)

    # Body rows — mostly numeric to give column-type consistency a chance
    body = [
        ["볼펜",    "12",   "1500",  "재고 충분"],
        ["A4용지",  "5",    "3500",  "재발주 검토"],
        ["스템플러","2",    "8000",  "신규 입고"],
        ["테이프",  "20",   "1200",  "정상"],
    ]
    for r, row in enumerate(body, start=1):
        for j, val in enumerate(row):
            cx = int(x0 + j * cell_w + 20)
            cy = int(y0 + r * cell_h + 10)
            d.text((cx, cy), val, fill="black", font=font)

    out = OUT / "case_3_table.png"
    img.save(out)
    return out


def case_4_photo() -> Path:
    """
    Continuous-tone gradient (no high-contrast extremes).
    Classifier should label this 'photo' (low extreme-bin ratio, no grid).
    """
    img = Image.new("RGB", (1200, 800))
    px = img.load()
    for y in range(800):
        for x in range(1200):
            # Smooth diagonal gradient — keeps extreme-bin ratio low
            r = int(40 + (x / 1200) * 180)
            g = int(60 + (y / 800) * 150)
            b = int(120 + ((x + y) / 2000) * 100)
            px[x, y] = (r, g, b)
    # A tiny watermark-like text — but in mid-grey, NOT extreme black/white
    d = ImageDraw.Draw(img)
    d.text((40, 720), "synthetic / for classifier test only", fill=(80, 80, 80))
    out = OUT / "case_4_photo.png"
    img.save(out)
    return out


def main():
    font = find_korean_font()
    print(f"Output dir: {OUT}")

    p1 = case_1_doc_clean(font);  print(f"  wrote {p1.name} ({p1.stat().st_size:,} bytes)")
    p2 = case_2_doc_skewed(p1);   print(f"  wrote {p2.name} ({p2.stat().st_size:,} bytes)")
    p3 = case_3_table(font);      print(f"  wrote {p3.name} ({p3.stat().st_size:,} bytes)")
    p4 = case_4_photo();          print(f"  wrote {p4.name} ({p4.stat().st_size:,} bytes)")
    print("OK")


if __name__ == "__main__":
    main()
