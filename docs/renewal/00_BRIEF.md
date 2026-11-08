# MarkItDown-Flow v2 - Zero-base Renewal Brief (DRAFT for peer deliberation)

Status: DRAFT-1 (orchestrator: cc). Not approved. Goal: analysis/design to TDD-ready, then TDD, cross-MECE audit, 100/100, release.

## 1. Facts (verified 2026-11-09)
- v1.0.8: Obsidian plugin (TS ~3.7k LOC) + Python engine `markitdown_wrapper.py` (1141 LOC, 4 phases: offline -> AI vision -> Azure DocIntel -> Azure CU). Tags 1.0.0-1.0.8. No issues/PRs.
- Core to use: `markitdown-gc` 0.3.5 (fork of microsoft/markitdown; Python 3.10-3.15). It ships `markitdown.ocr_triage.triage()` / `markitdown-gc FILE --ocr-report` (deterministic, local, never OCRs): JSON {decision: ocr_recommended|review|no_candidates|unknown, coverage.state, summary, candidates[{id,kind,page,priority,reasons}], issues[], file{sha256,bytes,format}, pages[], rasters[], schema_version=1}. Supports PDF, raster, DOCX, PPTX, XLSX, HWP5, HWPX. `.txt/.log` -> not_applicable; md/html/xml/rtf -> media_not_inspected; others -> unsupported_format.
- markitdown-gc converts (text only) PDF/DOCX/PPTX/XLSX/XLS/CSV/HWP/HWPX/HTML/EPUB/IPYNB/ZIP/MSG/audio; `--extract-media DIR`; NOT: .doc/.ppt/.rtf. It never OCRs; its guide prescribes: triage -> render pages (200/300 dpi) -> peer OCR (<=3 pages/ask) -> verify by 2nd peer -> assemble `## OCR p3 (peer, model, date)`; approval needed for sensitive docs or >20 pages.
- Local tools present: LibreOffice(soffice), pandoc, exiftool; absent: tesseract, ffmpeg.

## 2. Problem statement
Today every file goes through the same fallback chain; OCR/AI cost is decided late and implicitly. v2 must first CLASSIFY each input, then transcribe selectively, with provenance and no re-transcription.

## 3. Proposed taxonomy (class = f(format, triage report))
| Class | Meaning | Action |
|---|---|---|
| T  TEXT      | born-digital, no OCR candidates (decision no_candidates, coverage complete/not_applicable) | convert only |
| S  SCAN      | all/most pages or the standalone image need OCR | convert (gets empty/placeholder) + OCR all candidates |
| M  MIXED     | some pages/embedded images need OCR (decision ocr_recommended/review with text present) | convert + OCR only candidate ids |
| C  CONTAINER | zip/archive | recurse; each member classified independently; depth+size bounds |
| L  LEGACY    | .doc/.ppt/.rtf/.xls-old etc. unsupported by core | optional pre-convert (LibreOffice) then re-classify; else report |
| A  MEDIA     | audio/video | out of v2.0 OCR scope; core audio transcription only on explicit opt-in |
| U  UNKNOWN   | triage unknown/unsupported/corrupt/too_large | report issue, never silently drop |

## 4. Proposed pipeline (each stage independent, idempotent, individually testable)
0 Sniff -> 1 Triage (core) -> 2 Classify (pure fn) -> 3 Plan (which ids get OCR, provider, cost/page count, approval need) -> 4 Convert (core) -> 5 Transcribe (provider, only planned ids) -> 6 Verify (optional 2nd provider, digits/dates exact) -> 7 Assemble (md + frontmatter + ledger) -> 8 Report.
Default mode = plan-only/dry-run for anything leaving the machine.

## 5. Decision proposals (to be attacked)
- D1 Runtime: Python package `mdflow` (stdlib + markitdown-gc; providers optional) with CLI + JSON-lines progress; Obsidian TS plugin is a thin desktop-only shell (mobile impossible: needs Python subprocess - state it plainly).
- D2 No pipeline phases "Azure CU / DocIntel" as separate hard-coded phases; instead a single OCR-provider interface: `none`(default), `llm` (OpenAI/Anthropic/Gemini via env keys), `docintel` (via core -d), `command` (generic external command template).
- D3 peerhub: NOT a runtime dependency of the plugin. It remains (a) our dev/review/orchestration tool, (b) one documented example of a `command` provider. Core guide's peer-OCR recipe is reproduced as a provider recipe, not coupled code.
- D4 Approval gate: transcription that sends data off-machine requires explicit consent (UI modal in plugin / `--yes` in CLI), mandatory above 20 pages/images or when path matches user "sensitive" globs.
- D5 Never retranscribe: key = sha256(file)+page/image id+provider+model+prompt_version; ledger sidecar `<out>.mdflow.json` (also summarized in frontmatter). Re-run = no-op unless `--force`.
- D6 Output contract: one .md per source, YAML frontmatter (source, sha256, class, triage decision, pages/ocr ledger, tool versions, timestamps tz-aware), then converted body, then `## OCR pN (provider, model, date)` sections; for sources without base text, an empty base body so format is uniform.
- D7 Secrets only via env vars; never argv, never logs.
- D8 i18n: UI en (default)+ko required; remaining 6 languages table-driven, community-extensible; output markup language-neutral.
- D9 Tests: pytest (engine, fixtures generated programmatically, golden triage reports pinned to schema_version=1) + jest (TS shell); contract test against installed markitdown-gc; CI matrix py3.11/3.14 x win/ubuntu.
- D10 Release 2.0.0 (breaking); assets main.js, manifest.json, styles.css, engine zip; attestations kept; pinned action SHAs.
- D11 Keep from v1 only what survives MECE review (Obsidian shell patterns, settings persistence, history); everything else rewritten. Old engine archived under tag `v1-final` (existing tag 1.0.8).
- D12 LEGACY pre-convert via LibreOffice: optional, off by default, detected at runtime.

## 6. Open questions for user (batched later, not now)
OCR provider default; sensitive-glob defaults; whether audio/video is in scope; whether mobile claim should be dropped.
