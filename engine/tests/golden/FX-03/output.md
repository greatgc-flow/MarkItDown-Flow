---
mdflow: 2
source: "reports/q3.pdf"
sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
bytes: 1024
format: "pdf"
route: "NATIVE"
need: "PARTIAL"
label: "M"
triage_decision: "ocr_recommended"
coverage_state: "complete"
units: {total: 2, done: 1, pending: 1, failed: 0}
provider: "openai-compatible"
model: "fixture-model"
prompt_version: "p1"
dpi: 200
tools: {mdflow: "2.0.0", markitdown-gc: "0.3.6", pypdfium2: "fixture", pillow: "fixture"}
generated: "2026-11-09T00:00:00+00:00"
content_sha256: "08fa087d16a3e04c17e41f7d34e5f4fe43c44fc5b18f4cc690873684293ad76e"
---
<!-- mdflow:page 1 -->
Base first page

<!-- mdflow:page 2 -->
<!-- mdflow:ocr unit="p2" key="41a1c2a66238a20c" provider="openai-compatible" model="fixture-model" prompt="p1" dpi="200" at="2026-11-09T00:00:00+00:00" -->
## OCR p2 (openai-compatible, fixture-model, 2026-11-09)
Own OCR text
<!-- /mdflow:ocr -->

<!-- mdflow:page 3 -->
Base third page

<!-- mdflow:page 4 -->
<!-- mdflow:pending unit="p4" reason="no_provider" -->
