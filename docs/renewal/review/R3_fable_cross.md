# R3 cross-audit (Fable): 20_PACKAGING_RELEASE.md + 90_ACCEPTANCE.md vs 10_SPEC.md, 01_DECISIONS.md (R1-R18)

Reviewer: cc.fable. Date: 2026-11-09. Inputs read in full: 00, 01 (incl. R15-R18), 10, 20, 90, ref/ocr_triage_0.3.5.py.txt, ref/GUIDE grep. Method: every AC and PKG requirement checked against the REQ it claims to cover; fixture expectations re-derived from Core source, not from the fixture table.

Naming: SPEC = 10_SPEC.md, PKG = 20_PACKAGING_RELEASE.md, ACC = 90_ACCEPTANCE.md. Stage numbers below are SPEC §4 (1 Sniff .. 12 Report); ACC's 0..10 numbering is wrong and is itself a finding (X-30).

Severity: BLOCKER = TDD cannot start / release gate false; MAJOR = contradiction or uncovered MUST; MINOR = text fix.

---

## 1. Vertical MECE: stage x failure mode (cells lacking a real AC/test)

ACC §3 vertical matrix fills 88 cells; I accepted a cell only if the cited AC's *pass criterion text* actually tests that cell. Result: 14 cells genuinely covered, 31 legitimately N/A, 43 GAP or mis-cited. Failure modes used: FM-1 corrupt, FM-2 encrypted, FM-3 bounds, FM-4 path/naming, FM-5 schema/dep drift, FM-6 provider/network, FM-7 consent, FM-8 cache/partial state, plus two modes ACC omits: FM-9 secret/prompt-injection, FM-10 cancellation. Stage 11 Write is absent from ACC entirely.

| Stage | FM | SPEC REQ | ACC cites | Status | Needed test |
|---|---|---|---|---|---|
| 1 Sniff | FM-1 | REQ-SNF-05 (E_CORRUPT: pdf non-password error, BadZipFile, unreadable CFB) | AC-001 "flags invalid magic" | GAP (AC-001 is classification; detection untested; FX-028/029 have wrong labels, §5) | T-SNF-05 x3 corrupt fixtures |
| 1 Sniff | FM-2 | REQ-SNF-04 (4 detectors: pdf, zip flag_bits, CFB+ooxml ext, HWP5 header bit) | AC-001 | GAP: only pdf+zip fixtures exist; CFB-OOXML and HWP5 untested | T-SNF-04 x4 |
| 1 Sniff | FM-3 | REQ-SNF-02 (`--max-bytes` 200 MiB, member uncompressed size) | AC-002 | MIS-CITED: AC-002 says 100 MB, Plan stage, page ceiling (X-20) | T-SNF-02 (flag lowered) |
| 1 Sniff | FM-4 | REQ-SNF-01 hidden/symlink skip; REQ-SNF-03 W_EXT_MISMATCH | AC-001 "sanitizes input path" | GAP (no such AC text) | T-SNF-01, T-SNF-03 |
| 1 Sniff | FM-5 | REQ-GEN-02 E_CORE_VERSION exit 1 | none | GAP | T-GEN-02 (monkeypatch version) |
| 2 Triage | FM-1 | REQ-TRI-02 E_TRIAGE_FAIL -> U, convert_only | AC-003 | GAP (AC-003 covers schema only) | T-TRI-02 (mock raise) |
| 2 Triage | FM-2 | n/a (row 2 precedes triage) | AC-001/AC-003 "detects crypto" | WRONG N/A claim; delete | - |
| 2 Triage | FM-3 | Core MAX_PAGES=1000 -> `coverage.state=partial` -> row 22 U | AC-002 "bounded triage" | GAP | T-CLS-22 (mock report) |
| 2 Triage | FM-5 | REQ-TRI-03 schema; rows 22/23 vocab drift | AC-003, AC-019 | OK for schema; GAP for vocab rows (Phase IV text exists, no AC) | T-CLS-23, CT-01..05 |
| 2 Triage | side effect | REQ-TRI-05 sha before==after | AC-003 "without side effects" | OK (make explicit) | CT-06 |
| 3 Classify | all | REQ-CLS-01 total, REQ-CLS-05 100% | AC-001/021 | PARTIAL: 9 of 23 rows have no fixture (§5) | T-CLS-01..23 |
| 4 Plan | FM-3 | REQ-PLN-04 E_PLAN_OVERSIZE: output still assembled, pending `oversize` | AC-002 "without running conversion" | CONTRADICTS SPEC (X-20) | T-PLN-04 |
| 4 Plan | FM-7 | REQ-PLN-02 plan_hash canonical; §10.4 cross-OS stable | AC-011 "hash verified" | GAP (determinism untested) | T-PLN-02 golden hash per fixture |
| 4 Plan | FM-4 | REQ-PLN-06 sensitive glob, case-insens. on Windows | AC-011 | PARTIAL (no Windows case test) | T-PLN-06 |
| 4 Plan | priority | REQ-PLN-03 `--min-priority normal` skip | none | GAP | T-PLN-03 |
| 5 Convert | FM-1 | REQ-CNV-01 E_CONVERT_FAIL -> base "", OCR continues | AC-004 "catches core crash" | GAP (not in AC-004 text) | T-CNV-01 |
| 5 Convert | FM-4 | REQ-CNV-03 media dir `<out parent>/media`; SEC-05 containment | AC-004 "safe media extract paths" | GAP | T-CNV-03, T-SEC-05 |
| 5 Convert | FM-8 | REQ-CNV-04 base cache keyed by core_version (invalidation, R12) | none | GAP | T-CNV-04 |
| 5 Convert | per page | REQ-CNV-02 one-page PDF via pypdfium2 import_pages | AC-005 | PARTIAL (AC-005 is Render) | T-CNV-02 |
| 6 Render | FM-1 | REQ-RND-04 E_RENDER_FAIL per unit, others continue | AC-005 "fails page render safely" | GAP (not in AC-005) | T-RND-04 |
| 6 Render | FM-5 | REQ-RND-01 byte-stable PNG (no tIME) | AC-005 | GAP | T-RND-01 render twice, bytes equal |
| 6 Render | FM-3 | REQ-RND-03 EMF/WMF -> W_MEDIA_FORMAT pending | none | GAP | T-RND-03 |
| 6 Render | FM-4 | REQ-RND-05 rasters never under out dir | none | GAP | T-RND-05 |
| 7 Lookup | FM-8 | REQ-LKP-02 failed=miss, REQ-LKP-03 `--force`, REQ-LKP-04 W_CACHE_CORRUPT | AC-007 "corrupt cache discarded" | GAP (AC-007 text has none of these) | T-LKP-02..04 |
| 8 Approve | FM-7 | REQ-APR-02 bare `--yes` refused when threshold/sensitive; APR-04 denied; APR-05 consent in ledger; APR-06 never persisted | AC-011 | PARTIAL: AC-011 misstates gate (X-23); APR-04/05/06 untested | T-APR-02..06 |
| 9 Transcribe | FM-6 | REQ-TRX-03 per-unit failed, exit 4; §8.2 retries 2x (2 s, 8 s) on 429/5xx | AC-022 "retry with exp backoff" | CONTRADICTS (ACC Phase II demands exponential jittered backoff + Retry-After; SPEC fixed 2/8 s) | T-TRX-03 mock server |
| 9 Transcribe | FM-8 | REQ-TRX-02 ledger write per unit before next batch | AC-007 | GAP | T-TRX-02 kill after unit 2 |
| 9 Transcribe | FM-9 | SEC-06 prompt constant; TRX-04 fence strip only | none | GAP | T-SEC-06 |
| 9 Transcribe | FM-3 | SEC-07 200k truncation marker | none | GAP | T-SEC-07 |
| 9 Transcribe | network | SEC-08 no sockets except base_url; provider none = 0 sockets | AC-008 (rerun only) | GAP for first run | T-SEC-08 socket guard |
| 10 Assemble | FM-1 | provider text containing `<!-- /mdflow:ocr -->` | AC-009 "validates text markers" | GAP, and SPEC gap: §6.5 has no escaping rule (X-40) | T-ASM-06 |
| 10 Assemble | FM-4 | ASM-P3 no abs paths/usernames; §6.5 `"`->`_` in unit id | AC-010 "anchor sanitization" | GAP | T-ASM-P3 |
| 10 Assemble | FM-7 | §6.6 pending reasons (8 values) | AC-013 (no_provider only) | GAP for 7 reasons | T-ASM-66 parametrised |
| 10 Assemble | schema | §6.4 key order, REQ-ASM-08 content_sha256 | none | GAP | T-ASM-03/08 golden frontmatter |
| 11 Write | FM-8 | REQ-GEN-05 atomic `.tmp-<pid>` + os.replace; REQ-ASM-09 no rewrite | AC-007 (cache only), AC-008 (calls only) | GAP for outputs; "zero files rewritten" (REQ-GEN-06) absent from AC-008 | T-GEN-05, T-ASM-09 mtime unchanged |
| 11 Write | FM-4 | SEC-05 realpath containment; R17 `.pdf.md`; Windows reserved names | none | GAP; SPEC silent on `CON.txt` member -> `CON.txt.md` (X-41) | T-SEC-05, T-ASM-02 |
| 11 Write | FM-1 | E_OUTPUT_IO exit 2 | none | GAP | T-RPT-03 |
| 12 Report | all | REQ-GEN-07 every path exactly once; §7.4 schema; §10.3 exit codes incl. precedence and 130 | AC-004/AC-016 | GAP: no AC tests any exit code or the report schema | T-RPT-01..03, T-GEN-07 |
| any | FM-10 | REQ-GEN-09 SIGINT/SIGTERM -> 130, outputs old-or-new | AC-016 (1500 ms, "lockfiles") | MIS-SPEC'd (X-25) | T-GEN-09 |
| any | PURE | REQ-GEN-04 Classify/Plan/Approve/Assemble: no IO/clock | AC-004 "functional" | GAP | T-GEN-04 (monkeypatch open/time -> raise) |

## 2. Horizontal MECE: label x stage (cells lacking AC/test)

ACC uses labels T S M C L P U A. SPEC labels are T S M C L P X U where U = NATIVE+UNKNOWN (rows 10, 11, 14, 15, 16, 20, 22, 23) and X = UNSUPPORTED. ACC has no row for SPEC-U at all, calls UNSUPPORTED "U", and invents "A" (SPEC: media is X with reason). Gaps per SPEC label:

| Label | Stage | SPEC | Gap |
|---|---|---|---|
| T (pdf) | Convert/Assemble | REQ-CNV-02 per-page; REQ-ASM-04 anchor for every page even with 0 units | No AC (AC-009 is OCR-only). FX-002 should assert 5 anchors, 0 blocks. |
| T (docx/pptx/xlsx) | Convert | REQ-CNV-03 extract-media always -> `media/` published even when Need=NONE | No AC; conflicts PKG-M09 (X-14) |
| T (G2) | Triage | REQ-TRI-01 `not_run` synthesised | No AC; FX-033/034 should assert `triage_decision: not_run` |
| S | Assemble | REQ-ASM-07 empty base body, identical structure; provider none -> pending `no_provider` | AC-004 "base empty" cite is wrong; needs T-ASM-07 |
| S (image) | Render | REQ-RND-02 PNG/JPEG passthrough, else re-encode, dpi=0 | AC-005 "zero byte alteration" contradicts re-encode (X-22) |
| S (multi-frame TIFF) | all | Core emits `f1..fN` (verified ocr_triage.py L439); SPEC MAP-02 only maps `image` | SPEC gap + FX-018 wrong (X-42) |
| M (pdf) | Plan | K<P only -> FX-005 valid; FX-006 single page can only be S (X-50) | fixture fix |
| M (office) | Assemble | §6.3 unmapped appendix (MAP-04), MAP-05 hwp/hwpx all unmapped, MAP-07 duplicate raster = 2 anchors 1 entry | No AC; AC-010 "zero orphan at footer" contradicts §6.3 (X-24) |
| M (office) | Render | REQ-RND-03 EMF/WMF pending | No AC/FX |
| C | Assemble/Write | REQ-ASM-02 member path `<zip>.md` index + `<zip>/<member>.md`; §6.4 index table | "Evaluated per member" x5 cells, no AC |
| C | Sniff | REQ-CTR-03 member sha256 = member bytes; REQ-CTR-01 E_ZIP_PATH per member, others continue | No AC; SPEC row 8 contradicts REQ-CTR-01 (X-43) |
| C | Plan | REQ-CTR-02 depth/entries/total/bomb | Only bomb fixture (FX-024); AC-002 text has no zip bounds |
| L | Report | row 6 hint text, exit 2 | AC-017 ok except `.xls` (X-26) |
| P | Sniff/Report | row 2 E_ENCRYPTED, exit 2; label P | FX-025/026 say label U (X-51) |
| X | Classify | rows 4/5 two reasons | FX-035 label A (X-52); no row-5 fixture |
| U | everything | rows 10, 11, 14, 15, 16, 20, 22, 23 -> convert_only or report_only | Zero coverage: no ACC row, no fixture except accidental FX-019 (X-53) |
| all | CLI | §10.1 `plan` writes nothing, `classify`, `providers`, `cache stats|clear`, `version`; E_USAGE | No AC |

## 3. Contradictions

### 3.1 PKG vs decisions (R10, R15)

- **X-01 BLOCKER** PKG §1 (PKG-R01..R34) vs R15. Reuse table says "Reuse lifecycle, ribbon..." (R01), "Keep argument-array spawning" (R05), "Reuse bounded 100-entry list" (R09), "Keep keyed tables" (R12), "Reuse `Setting` controls" (R13), "Keep picker/UI pattern" (R15), "Reuse progress presentation" (R20), "Preserve containment/template cases" (R27), "Reuse ... styles" (R34). R15: shell is CLEAN-ROOM, "no copied code", and explicitly supersedes "preserve useful shell code". Fix: delete §1. Replace with "Behaviour inventory" (<=15 rows: command IDs, settings keys, history cap 100, ribbon, context menu, drag-drop, en/ko) with column "re-specified in 20_SHELL.md §". Add sentence: "v1 `src/`, `styles.css` and `src/__tests__` are not read during v2 implementation; tests are written from 20_SHELL.md." Add evidence item for R15 in ACC (AC-R15: reviewer attestation + optional similarity script).
- **X-02 MAJOR** PKG-O01, PKG-E02 ("PKG-O01 objects to that part of R10"), PKG-OCD06 ("under PKG-O01"), PKG-M01 ("before engine launch or installation"), PKG-E02 "Setup network activity is distinct from document-egress consent". R10 was amended r2 to exactly PKG-O01's position; the objection is stale and the "or installation"/"setup network activity" phrases imply plugin-side installs. Fix: delete PKG-O01; replace references with "per R10 (amended)"; PKG-M01 "before engine launch"; delete the setup-network sentence (plugin performs no setup network activity).
- **X-03 MAJOR** PKG-E06 "Upgrade by creating a new version/lock directory ... running `pip check`, handshake ... switching a plugin-local active-runtime pointer atomically. Retain prior directory for rollback." Under R10 the plugin runs nothing but handshake; a runtime-pointer scheme with `pip check` is plugin-managed dependency lifecycle in all but name. Fix (also §6 cut): one setting `enginePython` (absolute path). SetupModal: probe -> handshake -> on failure show the exact two commands (`<python> -m venv <path>`; `<path>/bin/python -m pip install --require-hashes -r engine.lock`) with suggested path `<plugin-dir>/venv`. Upgrade = user re-runs pip with the new lock; rollback = user points `enginePython` at the old venv. Delete PKG-E06 and the probing list in PKG-E03 beyond `python3|python|py -3` used only to pre-fill the suggested command.

### 3.2 PKG vs SPEC

- **X-10 BLOCKER** PKG-S03 protocol vs SPEC §7.3/§10.3/REQ-GEN-09/§8.4. PKG: stdout JSON-lines events `{protocol_version, job_id, seq, type, payload}`, types `plan|progress|approval_required|result|error|cancelled`, stdin controls `approve|cancel`, 1 MiB line cap, seq monotonic. SPEC: progress on **stderr** (`--progress jsonl`), run report on **stdout**, events `{v, ev, ts, ...}` with 10 `ev` names, **"No stdin protocol"**, consent = rerun with `--yes <plan_hash> --approved-by plugin:modal`, cancel = signal. ACC AC-016 has a third protocol (X-25). Fix: delete PKG-S03; add PKG-S03' = "Shell consumes SPEC §7.3 verbatim; consent flow per SPEC §8.4 (modal on `approve_required` + exit 3, rerun with hash); cancel = `child.kill('SIGTERM')` (TerminateProcess on Windows), expect exit 130; ignore unknown `ev`; 1 MiB line guard consumer-side." Record as R19 in 01_DECISIONS.
- **X-11 BLOCKER** PKG-S06 per-job staging under plugin dir then "publish completed artifacts atomically ... report collisions" vs REQ-ASM-02 (fixed `<out>/<rel>.ext.md`, collision-free by R17), REQ-ASM-09/REQ-GEN-06 (no rewrite when existing output unchanged; needs the real output dir), PKG-T05 "zero provider calls on rerun" still holds but "0 files rewritten" cannot. Fix: delete staging; shell passes `-o <vault>/<outputPath>` and validates it is inside the vault; engine atomicity (REQ-GEN-05) is the publish step.
- **X-12 MAJOR** PKG-M15 `outputFilenameTemplate` `{filename}{ext}{date}{datetime}` and PKG-M10 `assetSubfolderTemplate` `{filename}-assets` vs R17 + REQ-ASM-02 + REQ-CNV-03 (`media/<h12>.<ext>`, links relative). Shell renames break REQ-ASM-09 and media links. Fix: PKG-M15/M10 -> "Dropped. Notice: outputs are `<name>.<ext>.md`, media in `media/` beside the output."
- **X-13 MAJOR** PKG-M18 `autoTags` "into tags at engine assembly" vs REQ-ASM-03 (§6.4 keys exactly, no others). Fix (pick one, recommend a): (a) SPEC adds `--tag TEXT` (repeatable) and optional §6.4 key `tags: [..]` after `label`; (b) drop with notice. Record choice in 01.
- **X-14 MAJOR** PKG-M09 `assetExtractionEnabled` "controls published media only" vs REQ-CNV-03 (extract-media always for docx/pptx/xlsx; links depend on it). Fix: drop with notice "media files are always written to `media/`" or SPEC adds `--no-media` (then all office candidates become MAP-04 unmapped). Recommend drop.
- **X-15 MAJOR** PKG-T04 core range `>=0.3.5,<0.3.6` vs REQ-GEN-02 `>=0.3.5,<0.4`. Fix: SPEC wins; PKG-T04 tests 0.3.5 and newest `<0.4`.
- **X-16 MAJOR** PKG-E07 `-m mdflow --handshake` with `protocol_version, plugin_version_range, lock_digest, capabilities` vs SPEC §10.1 (`mdflow version` -> mdflow, markitdown-gc, pypdfium2, python). Fix: SPEC `mdflow version` adds `protocol: 1`, `triage_schema: 1`, `platform`; drop the rest; plugin requires engine `>=2.0.0,<2.1`. Delete PKG-E08 "lock mismatch blocks jobs" (plugin cannot know the lock without owning installs).
- **X-17 MAJOR** PKG-E04 lock = `markitdown-gc==0.3.5` (no extras) vs FX-019/FX-020 (HWP5/HWPX classified T/M). Core `_hwp` raises `missing_dependency` without `markitdown-gc[hwp]` (ocr_triage.py L908-914) -> decision `unknown` -> SPEC row 15 -> label U. Fix: decide: lock includes `[hwp]` extra (then REQ-GEN-01 lists it) **or** HWP5 is documented U with W_TRIAGE_UNKNOWN and FX-019 expects U. Recommend extra in lock if it is pure-Python with wheels (TODO-VERIFY alongside PKG-E09).
- **X-18 MINOR** PKG-S04 "maximum spend or request bound", "currency" — SPEC Plan has `est_cost` (USD, may be null) only. Fix: "est_cost (USD) or 'unknown'"; drop cap.
- **X-19 MINOR** PKG-C06 "offline engine health/triage check" has no engine command. Fix: SPEC adds `mdflow selftest` (classify a package-bundled 1-page PDF and PNG, provider none, exit 0) or shell runs `mdflow version` + `mdflow classify` on a generated PNG.
- **X-19b MINOR** PKG-S05 5 s cooperative grace vs AC-016 1500 ms. Pick 5 s (SPEC silent); put the number in SPEC REQ-GEN-09.

### 3.3 ACC vs SPEC / decisions

- **X-20 BLOCKER** AC-002: "byte ceiling default 100MB", "page ceiling default 500 pages", "blocked at Plan stage as OVERSIZE ... without running conversion", "500MB sparse". SPEC: `--max-bytes` 200 MiB at **Sniff** (E_TOO_LARGE, report_only); `--max-units` 200 at Plan (E_PLAN_OVERSIZE, **output still assembled** with pending `oversize`); no page ceiling. Fix text: "REQ-SNF-02: file > `--max-bytes` -> E_TOO_LARGE, report_only, exit 2 (test with `--max-bytes 1024`). REQ-PLN-04: units_total > `--max-units` -> E_PLAN_OVERSIZE, 0 provider calls, output written with `oversize` pending markers for every unit (test with `--max-units 2` on FX-004)."
- **X-21 BLOCKER** AC-006 and FX-007 "(300 DPI)": CJK auto-escalation (>30% code points / >40% glyph area). R17: "dpi is an explicit option, no auto-CJK rule"; REQ-RND-01 `--dpi 200|300`. Fix: delete AC-006; replace with AC-RND: "`--dpi 300` changes Key (dpi field), renders at 300, frontmatter `dpi: 300`; default 200; `--dpi 150` -> E_USAGE." Weight 4 -> move to new AC for exit codes/report schema.
- **X-22 MAJOR** AC-005 "Zero byte alteration of extracted raster assets" vs REQ-RND-02/03 (GIF/BMP/TIFF/WebP re-encoded to PNG; PNG/JPEG passthrough). Fix: "PNG/JPEG units: raster bytes == member/file bytes; others: PNG re-encode, byte-stable across two renders (REQ-RND-01)."
- **X-23 MAJOR** AC-011 "halts with status APPROVAL_REQUIRED unless `--yes`"; "Gate triggered unconditionally if units > 20 or sensitive". SPEC: gate is **always** on for egress providers with units_to_send > 0; threshold/sensitive only change the accepted consent form (bare `--yes` refused, `--yes <plan_hash>` required, REQ-APR-02); exit 3; outputs still written with `approval_required` markers; threshold compares `units_to_send` (after cache hits). Fix text accordingly + add APR-04 denied, APR-05 consent in ledger entries, APR-06 not persisted.
- **X-24 MAJOR** AC-010 "Zero orphan transcriptions at document footer" vs §6.3 unmapped appendix (MAP-04, MAP-05 hwp/hwpx always unmapped). Fix: "Mapped units: block immediately after the link line (link kept). Unmapped units (W_MEDIA_UNMAPPED, all hwp/hwpx): under `## OCR media (unmapped)` in source_id order; nowhere else."
- **X-25 BLOCKER** AC-016 protocol `{type: progress|unit_complete|error|result}`, "bidirectional", "SIGINT/SIGTERM ... within 1500ms ... orphan lockfiles". Contradicts SPEC §7.3 (names), REQ-GEN-09 (no stdin), PKG-S05 (5 s), and SPEC has no lockfiles. Fix: "Progress events validate against §7.3 schema (golden JSON-schema); SIGTERM during Transcribe -> exit 130 within 5 s, every output file is either absent or complete, every ledger entry parses, rerun needs no cleanup."
- **X-26 MAJOR** AC-017 `.xls` -> LEGACY vs SPEC table 3.1A (CFB + ext xls -> NATIVE, G2 convert_only). Fix: remove `.xls`; add `.rtf`, `.odt`. Add FX for xls as T.
- **X-27 MAJOR** AC-015 (SetupModal creates venv, installs wheels, `<plugin-dir>/.venv`) vs R10 amended, PKG-E02. Fix: "SetupModal performs only probe + handshake and displays the bootstrap/upgrade commands for the exact release lock; jest asserts no `spawn` with `pip`/`venv` args from plugin code (grep + spawn mock)."
- **X-28 MAJOR** AC-003 "Unrecognized schemas fail fast with a fatal diagnostic" vs REQ-TRI-03 (per-file report_only, E_TRIAGE_SCHEMA, run continues, exit 2); ACC Phase IV `IncompatibleCoreSchemaError` is not a SPEC code. Fix: use E_TRIAGE_SCHEMA, exit 2, other files processed.
- **X-29 MAJOR** AC-007 key `sha256:provider:model:prompt_version:dpi` vs SPEC §5.1 `|` separator; "`.tmp` renamed to `.json`" vs `<target>.tmp-<pid>`; cache dir "strictly `~/.mdflow/cache`" vs `--cache DIR`. Fix text to SPEC literals; add REQ-LKP-02..04.
- **X-30 MINOR** AC-004 stage list 0..10 with Convert->Lookup->Approve->Render vs SPEC §4 1..12 with Render **before** Lookup (R3 keys need rasters) and a Write stage. Fix: cite SPEC §4 order; replace "idempotent, functional" with T-GEN-04 (PURE stages raise on IO/clock) and §10.4 determinism.
- **X-31 MINOR** AC-013 "env secret interpolation" vs SEC-03 (no interpolation; secrets passed as env names via `--command-env`); missing `--command-egress` (required, no default) and `--trust-command`. Fix text.
- **X-32 MINOR** AC-014 "pointing to ... openai-compatible vision endpoints" vs PKG-M05 "Never map it to an OCR API base URL" — align on PKG-M05 wording; AC-014 is shell-only (engine reads no config, SPEC §10.2) -> evidence jest only.
- **X-33 MINOR** AC-021 partial rubric "deduct 1 pt per misclassified" and every other "Partial Rubric" contradict Scoring Rule 3 (single failure blocks) and R13 (100% exact). Fix: delete the Partial Rubric column.
- **X-34 MINOR** AC-020 pins "Windows Server 2022, Ubuntu 22.04, macOS 14" while PKG-T07 says runner labels TODO-VERIFY. Fix: "latest stable runner per OS, recorded in CI log".
- **X-35 MAJOR** Decision coverage: ACC maps R1-R14; R15 (clean-room), R16 (README disclosures), R17 (`.ext.md`, explicit dpi), R18 (CT vocab pinning) have no AC. AC-023 omits attestations, engine.zip+lock assets, versions.json, isDesktopOnly (R14, PKG-T08, PKG-OCD04). Fix: add AC-R15, AC-R16, fold R17 into AC-ASM, R18 into AC-019 with CT-IDs; extend AC-023.

### 3.4 SPEC defects surfaced by the cross-check (not my file; needed for FX/AC correctness)

- **X-40 MAJOR** §6.5/6.6: no escaping rule when provider text contains `<!-- /mdflow:ocr -->` or `<!-- mdflow:`. Fix: REQ-TRX-04 adds "replace `<!--` with `<!-​-` (zero-width) ... " or simpler: "any line matching `^<!--\s*/?mdflow:` in provider text is prefixed with a space". Test T-ASM-06b.
- **X-41 MAJOR** Windows reserved names (FX-023 `CON.txt`): writing `CON.txt.md` fails on Windows. SPEC silent. Fix: REQ-ASM-02 adds "basename stem in {CON, PRN, AUX, NUL, COM1-9, LPT1-9} (case-insens.) -> prefix `_`"; or E_OUTPUT_IO documented. Pick prefix.
- **X-42 MAJOR** Multi-frame TIFF/GIF: Core candidate ids `f1..fN`, kind `image` (ocr_triage.py L437-454). SPEC MAP-02/REQ-RND-02 only know `image`. Fix: MAP-02' "candidate `fN` -> page unit N, raster = frame N re-encoded PNG, P = n_frames, anchors per page"; row 17 unchanged.
- **X-43 MAJOR** Row 8 "any E_ZIP_*" -> container report_only vs REQ-CTR-01 (E_ZIP_PATH is per member, others continue). Fix: row 8 = `E_ZIP_DEPTH|ENTRIES|TOTAL|BOMB`; E_ZIP_PATH -> member row with report_only.
- **X-44 MAJOR** Rows 13 and 14 test `coverage.state == media_not_inspected|unsupported_format`; in Core these are **issue codes** (L169, L188, L649), never states (states: `none|partial|complete|not_applicable`). Both rows are dead (G2 formats are never triaged, containers never triaged). Fix: delete rows 13-14; row 15 (`decision == unknown`) already catches fatal Core issues; copy `triage.issues[].code` into `reasons`. Add CT-02 pinning the state vocabulary.
- **X-45 MINOR** REQ-SNF-03 "at most the first 8 bytes" but WEBP magic needs bytes 8-11 and Core reads 16. Fix: 16 bytes.
- **X-46 MINOR** Zero-byte file: no rule (no magic -> ext -> "any other" -> E_UNSUPPORTED; `empty.pdf` would be X). Core calls it `corrupt`. Fix: REQ-SNF-05 adds "bytes == 0 -> E_CORRUPT".
- **X-47 MINOR** Sniff detects hwpx via `mimetype` member; Core via `Contents/content.hpf` (L640). Use Core's marker to avoid disagreement.
- **X-48 MINOR** Ledger entry `v: 1` but no rule for `v != 1` on read. Fix: REQ-LKP-04 includes `v != 1`.

## 4. Measurability / self-assertion audit of ACC

Not objectively checkable as written (fix = concrete oracle):
- AC-004 "idempotent, functional, independently testable" -> T-GEN-04 + §10.4 golden outputs.
- AC-005 "Zero byte alteration" -> see X-22.
- AC-012 "all ambient cloud/API credentials" -> "child env == allowlist §8.2 + `--command-env` names (assert exact set)"; "error stack traces" -> T-SEC-02 regex on every stderr/stdout/report/cache byte for the injected key.
- AC-016 "cleanly flush open ledger writes" -> "every file under cache parses as JSON; no `*.tmp-*` older than run start".
- AC-018 "All dynamic parameter insertions sanitized" -> undefined; replace with "every key in `en` exists in `ko` (jest snapshot); engine `message` is English only, shell localizes by `code`".
- AC-019 "validates triage output structure" -> enumerate CT-01..CT-08 (below).
- AC-022 "orphan dropped blocks" -> "for every planned unit exactly one provenance block or pending marker with that `unit=` id; count(blocks) == units_total" (property test over all fixtures).
- AC-023 "static asset manifest accurate", "clean npm audit" -> "`npm audit --audit-level=high` exit 0" or drop; "manifest fields validated by JSON schema".
- §3 matrices: every cell asserts coverage by citation; 43 are false (§1). Self-asserted. Replace with generated matrix (§7).
- §4 Phase I "line ending integrity" is unrelated to product acceptance; Phase II backoff rule contradicts SPEC; Phase III is good and should become tests T-GEN-06a (mtime touch) and JT-05 (vault scan); Phase IV good -> T-CLS-22/23, CT-01.
- Scoring: weights sum to 100 (verified) but partial rubrics make the sum meaningless under Rule 3.

## 5. Fixture corpus (FX-*) vs SPEC table 3.2 (23 rows)

Expectations re-derived from Core source; wrong rows:

| FX | Defect | Fix |
|---|---|---|
| FX-006 | 1 page with candidate p1 -> K==P -> **S**, not M; small inline figure likely yields no candidate at all | 2 pages: p1 text-only, p2 text + large raster -> `["p2"]`, M. Expected ids must come from pinned golden triage, not hand-written |
| FX-007 | Born-digital CJK vector text -> `no_candidates` -> **T**; "300 DPI" has no trigger (R17) | Rasterised Korean page, run with `--dpi 300` -> S, 1 unit, key dpi=300 |
| FX-011 | "logo" is likely small (<24 px side or <15000 px^2, L880) -> not a candidate -> 2 ids not 3 | Make all images >= 200x200 |
| FX-013 | OK label M (SPEC row 21: office is always PARTIAL). Note priority will be `high` (scan_like) | add assertion decision `ocr_recommended` |
| FX-018 | ids `p1..p3` wrong; Core gives `f1,f2,f3` | `["f1","f2","f3"]` after X-42 |
| FX-019 | T only if `[hwp]` extra installed; otherwise U (X-17) | decide; also "programmatic minimal OLE" needs the HWP5 FileHeader stream or Core reports corrupt |
| FX-021 | Need NONE ok; add expected outputs: `x.zip.md` index + 2 member files | add |
| FX-022 | Need `FULL` for a container is wrong (row 7: NONE) | NONE; leaf FX-003 member has 1 unit |
| FX-023 | E_ZIP_PATH is per member (X-43); `CON.txt` is a Write issue (X-41) | container C/NONE/recurse; member `../../etc/passwd` -> E_ZIP_PATH report_only; `CON.txt` -> `_CON.txt.md` |
| FX-024 | 42KB->10GB needs 1 GiB default total; fine. Add `--zip-total-bytes` lowered variant for speed | - |
| FX-025 | label **P** not U; issue E_ENCRYPTED | fix; `pikepdf` is a dev dep (declare) |
| FX-026 | label **P**; route PROTECTED ok | fix |
| FX-027 | 0 bytes: SPEC gives X/E_UNSUPPORTED today (X-46 -> E_CORRUPT); reason `empty_file` does not exist | X, E_CORRUPT |
| FX-028 | Truncated PDF has `%PDF` magic -> route NATIVE, E_CORRUPT -> label **U**, not UNSUPPORTED; reason `corrupt_header` not a code | U / E_CORRUPT |
| FX-029 | Random bytes + `.docx`: no zip magic -> X/E_UNSUPPORTED, **not** corrupt. To hit E_CORRUPT zip: `PK\x03\x04` + garbage | split into FX-029a (X) and FX-029b (U, E_CORRUPT) |
| FX-030 | 150 MB < 200 MiB default -> passes; label T/NONE wrong (row 1: U, report_only) | 2 MiB file + `--max-bytes 1048576` -> U, E_TOO_LARGE |
| FX-035 | label **X**, not A | fix; add FX mp4 |

Missing fixtures (row / REQ -> add):
- Row 5 other unsupported: `data.bin`, unknown CFB (`FX-036/037`).
- Row 6: `.rtf` (magic `{\rtf`, trivially generated), `.odt`.
- Row 9: `xls` (CFB, NATIVE G2 — resolves X-26), `csv`, `html`, `epub`.
- Rows 10, 11, 16, 20, 22, 23: mocked triage reports as JSON fixtures `GT-*` (golden) — ACC Phase IV lists them but no IDs.
- Row 2: CFB-wrapped encrypted `.docx`; encrypted HWP5.
- REQ-SNF-01 hidden file, symlink; REQ-SNF-03 `W_EXT_MISMATCH` (PDF bytes named `.docx`; magic wins).
- REQ-CTR-02 depth 4 nesting, entries 1001 (with `--zip-entries 10`), E_ZIP_TOTAL.
- REQ-RND-02/03: standalone `bmp`, `webp` (re-encode); docx with EMF (W_MEDIA_FORMAT); docx image never referenced (W_MEDIA_UNMAPPED); same image twice (MAP-07: 2 anchors, 1 entry, 1 call).
- REQ-PLN: 21-unit scan PDF or `--approve-threshold 2` on FX-004; sensitive glob hit; low-priority-only docx with `--min-priority normal`.
- Paths: non-ASCII (한국어, emoji), spaces, 200-char path (ACC Phase I has no fixture).
- Provider mocks: 429x3, 500, timeout, empty content, non-string content, fenced output, 250k-char output, output containing `<!-- /mdflow:ocr -->`, command exit 7.
- Cache: corrupt entry, `v:2` entry, failed entry then success, `--force`.
- Golden triage JSON pinned per fixture (`tests/golden/triage/FX-nnn.json`) with CT asserting equality against installed Core — this is the only honest source for "Expected Candidate IDs" (R12 "golden triage reports pinned").

## 6. Over-engineering to cut (VerySimpleGuide)

PKG: §1 reuse audit (34 rows -> 0, X-01); PKG-E03 interpreter hunt (keep 3 names); PKG-E06 runtime pointer/rollback (X-03); PKG-E07/E08 handshake fields (X-16); PKG-S03 framed protocol (X-10); PKG-S05 descendant-tree kill (engine kills its own `command` child on SIGTERM; shell sends one SIGTERM, waits 5 s, kills); PKG-S06 staging (X-11); PKG-M10/M15 templates (X-12); PKG-M25 notice-ID persistence + rollback snapshot machinery -> "copy `data.json` to `data.v1.json` with credential keys removed; one aggregated notice"; PKG-L06 plugin rollback procedure -> 3 lines.
ACC: §4 mermaid + "three recursive rounds" + WARN_DISPOSITIONS.csv + Phase I (process, not acceptance) -> delete, keep Phase III/IV as tests; Partial Rubric column; LaTeX math; AC-006; runner pins; §3 hand-written matrices -> generated.
SPEC (for the record): rows 13-14 dead (X-44); REQ-CNV-04 SHOULD base cache is fine to keep.

## 7. Proposed doc set for TDD kickoff

```
docs/renewal/
  00_BRIEF.md                 frozen
  01_DECISIONS.md             + R19 protocol = SPEC §7.3/§8.4 (no stdin), R20 tags/media/output ownership (X-13/14), R21 HWP extra (X-17)
  10_SPEC.md                  engine; amendments X-40..48 applied in place, "SPEC-2"
  20_SHELL.md                 NEW, clean-room shell spec: settings migration (PKG §2 moves here), commands PKG-C*, SetupModal (diagnose only), consent modal, process supervision, i18n, disclosures (R16). Consumes only SPEC §7, §10.
  25_PACKAGING_RELEASE.md     renamed from 20_: keep §3 (E01, E02', E04, E05, E09), §5, §6, §7; drop §1, §2, §4
  30_TESTPLAN.md              NEW (structure below)
  90_ACCEPTANCE.md            <= 1 page: AC table only (ID, decision/REQ area, test-ID set, weight, evidence URL column). No matrices, no process, no rubrics.
  review/                     peer reviews
```

### 30_TESTPLAN.md structure

1. **ID scheme.** `T-<AREA>-<NN>[a-z]` engine unit/property tests, AREA = SPEC REQ area (GEN SNF TRI CLS PLN CNV LKP APR RND TRX ASM RPT CTR SEC CLI); `CT-NN` contract tests against the installed Core (pin vocab per R18); `GT-NN` golden triage reports (mocked rows); `IT-NN` packaged integration (PKG-T05); `JT-NN` jest shell tests; `RT-NN` release checks (PKG-T06..T08, OCD). One REQ -> >=1 test; one test -> exactly one AC.
2. **Traceability table** (the single source of truth; everything else is generated from it):

| Test ID | REQ | AC | FX / GT | Stage | FM | Labels | Kind | Oracle |
|---|---|---|---|---|---|---|---|---|
| T-SNF-04b | REQ-SNF-04 | AC-SNF | FX-038 (CFB docx) | 1 | FM-2 | P | unit | route==PROTECTED, issue E_ENCRYPTED, exit 2 |
| T-CLS-19 | REQ-CLS-01 row 19 | AC-CLS | FX-005, GT-19 | 3 | - | M | golden | classification JSON == golden |
| T-APR-02b | REQ-APR-02 | AC-APR | FX-004 + `--approve-threshold 2 --yes` | 8 | FM-7 | S | e2e | exit 3, E_APPROVAL_REQUIRED, 0 sockets, 3 pending markers `approval_required` |
| ... | | | | | | | | |

3. **Fixture corpus** FX table (corrected per §5) + `tests/golden/triage/FX-nnn.json`; generator `tests/tools/generate_fixtures.py`; binary-frozen list with licence note (FX-031/032 real `.doc/.ppt` must be self-authored).
4. **Contract tests CT-01..08**: schema_version==1; `coverage.state` in {none, partial, complete, not_applicable}; `candidates[].kind` in {page, image}; `priority` in {high, low}; ids `pN|image|fN|<member path>`; `decision` in {unknown, ocr_recommended, review, no_candidates}; `reasons` vocab (R18 list); extract-media filename == sha256(member)[:12]; triage leaves file sha unchanged; HWPX marker.
5. **Generated MECE matrices.** pytest markers `@req("REQ-..")`, `@stage(n)`, `@fm("FM-k")`, `@label("P")`; `tests/tools/trace.py` emits stage x FM and label x stage tables into `30_TESTPLAN.md` §6 and **fails CI if any non-N/A cell is empty or any MUST REQ has no test**. N/A cells are declared once in `tests/trace_na.toml` with a one-line reason. This replaces ACC §3 and makes "MECE" a check, not a claim.
6. **Acceptance mapping.** ACC AC rows become ~15 area gates (AC-GEN, AC-SNF, AC-CLS, AC-PLN, AC-CNV/RND, AC-LKP/TRX, AC-APR, AC-ASM, AC-RPT/CLI, AC-CTR, AC-SEC, AC-CT, AC-SHELL, AC-RELEASE, AC-POLICY[R15/R16]); weights sum 100, binary; evidence = CI run URL + `trace.py` report.
7. **TDD order.** CLS (pure, golden) -> SNF -> PLN -> ASM (pure, golden markdown) -> RND/LKP -> APR -> TRX (mock server) -> CTR -> CLI/RPT -> SEC -> CT -> IT -> JT.

## 8. Verdict

**Overall: REJECT** (both documents; neither can serve as the TDD/100-100 gate as written).

| Area | Score | Justification |
|---|---|---|
| PKG §3/§5/§6/§7 (distribution, CI, directory, release) | 70 | Lock/hash/attestation/community checklist sound and cited; TODO-VERIFY honest. Loses on E06/E07/E08 over-build and core-range mismatch (X-03, X-15, X-16). |
| PKG §1 reuse audit | 0 | Directly contradicts R15 (X-01). |
| PKG §2 settings/commands | 55 | Row-complete v1 mapping is good; M09/M10/M15/M18 contradict SPEC (X-12..14); belongs in 20_SHELL. |
| PKG §4 shell/engine boundary | 25 | S03 protocol and S06 staging contradict SPEC (X-10, X-11); S01/S02/S04 largely fine. |
| ACC §1 AC table | 30 | Weights sum 100, but 5 BLOCKER contradictions (X-20, 21, 25, 27 + X-23/24 MAJOR), 7 ACs unmeasurable, R15-R18 absent, no exit-code/report/CLI AC. |
| ACC §2 fixtures | 35 | 35 rows is the right scale; 15 rows have wrong labels/ids against Core source; 9 decision rows and most REQ-level negatives have no fixture. |
| ACC §3 matrices | 10 | 43 of 57 non-N/A cells cite an AC that does not test the cell; stage Write and label U missing. |
| ACC §4 protocol | 40 | Phases III/IV are real tests; rest is process text; backoff rule contradicts SPEC. |
| SPEC consistency with Core ref (incidental) | 80 | Total decision table is right in shape; rows 13-14 dead, fN/TIFF, escaping, reserved names, zero-byte, row 8 need amendments (X-40..48). |

Minimum to flip to APPROVE-WITH-CHANGES: X-01, X-10, X-11, X-20, X-21, X-25, X-27 fixed; ACC §3 replaced by generated matrices; FX table re-derived from pinned golden triage.
