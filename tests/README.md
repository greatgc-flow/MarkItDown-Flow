# tests/

All non-unit-test resources used to verify MarkItDown-Flow live here.

```
tests/
├── README.md                       ← you are here
├── fixtures/
│   └── images/                     ← synthetic test images
│       ├── case_1_doc_clean.png      clean Korean+English document scan
│       ├── case_2_doc_skewed.png     case 1 rotated by 7°
│       ├── case_3_table.png          ruled table (5 rows × 4 cols)
│       └── case_4_photo.png          continuous-tone gradient ("photo")
└── scripts/
    ├── make_test_images.py         regenerate the four fixtures above (Pillow only)
    └── smartimage_demo.py          drive SmartImageRouter against the fixtures and print a report
```

Jest unit tests live separately under `src/utils/__tests__/`.

## Run the SmartImageRouter demo (CLI)

```bash
# from project root
python tests/scripts/smartimage_demo.py
```

Requirements: `opencv-python` for the classifier and preprocessing, plus at
least one OCR engine (`pytesseract` + Tesseract binary, or `easyocr`, or
`paddleocr`). Missing engines no-op gracefully — the report still shows the
classification + preprocessing path even with no OCR engines installed.

## Run the self-test from inside Obsidian (UI)

The same checks are wired into the plugin UI:

- **Command palette → "MarkItDown Flow: Run image pipeline self-test"**
- **Settings → MarkItDown Flow → Image pipeline → "Run self-test" button**
  (visible when the Image Pipeline section is enabled)

The modal launches `python/selftest.py`, parses the result, and renders a
per-case table. Re-runnable at any time without leaving Obsidian.

## Regenerate the fixtures

If you change the test image set, edit `scripts/make_test_images.py` and run:

```bash
python tests/scripts/make_test_images.py
```

The script needs only Pillow (already a core requirement of `markitdown`).

## Naming convention

- `case_<N>_<kind>_<variant>.png` — `kind` is the classifier label we expect
  (`doc`, `table`, `photo`), `variant` is any modifier (`clean`, `skewed`).
- Fixtures stay small (PNG, ~20–80 KB) so they fit in git without LFS.
