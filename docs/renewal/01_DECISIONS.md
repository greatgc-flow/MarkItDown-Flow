# Decision Log (ADR-lite). Source: peer round 1 (cx.effort REJECT-until-fixed, ag.effort & cc.fable APPROVE-WITH-CHANGES) + orchestrator probes 2026-11-09.

## Verified facts that shape the design
- F1 Published: `markitdown-flow` 1.0.8 is in the Obsidian community directory (~1k downloads) -> plugin `id` and v1 command IDs are frozen; v1 `data.json` settings MUST migrate (tested). Desktop-only stays; mobile claim is dropped.
- F2 Core PDF conversion emits NO page markers; scanned page -> empty text. Per-page conversion works (pypdfium2 split -> markitdown per page); pypdfium2 ships with pdfplumber (render needs no new dep).
- F3 DOCX/PPTX/XLSX: `--extract-media DIR` links `![..](media/<sha256[:12]>.<ext>)`; triage media candidate id = zip member path (e.g. `word/media/rId10.png`). Mapping rule: sha256(member bytes)[:12] == media filename => in-situ replacement anchor.
- F4 Triage: standalone image => id `image`; PDF => `pN`; DOCX embedded image => `review`/low; `.txt/.log` => not_applicable. `no_candidates` != born-digital proof.
- F5 Upstream `markitdown-ocr` (LLM-vision plugin, needs upstream markitdown >=0.1.8) exists but targets upstream package, not the gc fork, and OCRs inline w/o consent/ledger -> not used.

## Resolutions
| ID | Resolution | Basis |
|---|---|---|
| R1 Taxonomy | Two independent axes. Route = {NATIVE, CONTAINER, LEGACY, PROTECTED, UNSUPPORTED} (media/audio -> UNSUPPORTED reason `media_out_of_scope`); Need = {NONE, PARTIAL, FULL, UNKNOWN}. User-facing labels: T(text)=NATIVE+NONE, S(scan)=NATIVE+FULL, M(mixed)=NATIVE+PARTIAL. Need rule is deterministic from triage (see SPEC). OVERSIZE is a Plan bound, not a class. | cx#1, fable#1 |
| R2 Pipeline | Sniff(magic+encryption+container only) -> Triage(core) -> Classify -> Plan -> Convert(core) -> Lookup(ledger) -> Approve -> Render -> Transcribe -> Assemble -> Report. Verify/Reconcile deferred (v2.1): no auto-merge ever. | all |
| R3 OCR unit | Executable unit = {kind: page|media, source_id, raster bytes sha256, dpi}. Page ids render via pypdfium2 (200dpi; 300 for dense CJK); media units use extracted bytes. | cx#2, fable#2 |
| R4 Ledger | Single source of truth: content-addressed cache (CLI `~/.mdflow/cache`, plugin `<plugin-dir>/cache`), key=sha256(raster)+provider+model+prompt_version+dpi. No sidecar in vault (rename-proof, no pollution). Frontmatter = summary only (sha256, class, counts, versions). Failed/partial units stay retryable; atomic writes. | ag#2, cx#3, fable#3 |
| R5 Placement | Inline: PDF assembled per page with `<!-- mdflow:page N -->` anchors, OCR block in page order; Office: OCR text replaces/follows the image link at its in-situ position. Provenance heading/comment keeps provider, model, date, key. | all 3 (D6 CHANGE) |
| R6 Egress/consent | Providers declare `egress: bool`, `cost_hint`, `max_batch`. Approve stage gates ANY egress provider on a concrete Plan (destination, N units, est. cost cap, sensitive-glob hits); approval hash recorded; default=plan-only. Thresholds configurable (default >20 units). Applies to every adapter incl. `command`. | cx#4, fable#4 |
| R7 Providers v2.0 | `none` (default; emits plan + pending markers), `openai-compatible` (single stdlib-HTTP adapter: OpenAI/Azure OpenAI/Gemini-compat/Anthropic-compat/Ollama via base_url), `command` (template, secrets via env, explicit trust flag). Azure DocIntel/CU removed from 2.0 (whole-document, not unit-level) -> migration notice; `command` can wrap `markitdown-gc -d`. peerhub = dev tool + documented `command` recipe, NOT a dependency (D3 KEEP, unanimous). | cx/fable |
| R8 Secrets | Env only; scrub child env; redact logs/progress/exceptions; no keys in persisted provider config. | cx#7 |
| R9 i18n | en + ko shipped, key-based table-driven; other 6 languages = v1 strings kept only if migrating is free, else deferred (not scaffolded). | cx, fable, ag |
| R10 Runtime/distribution | Engine = pure-Python package `mdflow` + pinned lock; plugin SetupModal creates a dedicated venv in plugin dir and installs pinned `markitdown-gc`; user Python only used to bootstrap. Versioned JSON-lines progress/error protocol with cancellation. | ag#3, fable D1, cx D1/D10 |
| R11 LibreOffice | Dropped from 2.0 (LEGACY -> report with reason + hint). Revisit 2.1 with original+derived provenance. | ag, fable, cx(bounded) |
| R12 Tests | pytest (engine; programmatic + small real fixtures; malformed/encrypted/oversize/partial-failure/cache-invalidation) + jest (shell) + contract tests pinned to markitdown-gc version range, fail loud on schema_version!=1. CI: win+ubuntu+macos; py3.10 and 3.14 required, 3.15 allowed-failure. | fable D9, cx D9 |
| R13 Quality bar | "100/100" = every checklist item in 90_ACCEPTANCE.md PASS with evidence (tests green + measurable thresholds: classification accuracy 100% on labelled fixtures, 0 unit loss/duplication, idempotent rerun = 0 provider calls). Scores are per-criterion and evidence-linked, never self-asserted. | cx#5, fable |
| R14 Release | 2.0.0 semver-major; tag == manifest version; assets main.js, manifest.json, styles.css (+ engine zip + lock); attestations kept; Obsidian submission rules (description <=250 chars, no plugin id in command ids, sample code removed). | web research |

## Open questions for the user (batched, ask once)
Q1 Is dropping Azure DocIntel/CU from the built-in set acceptable (kept only via `command`)? Q2 Default OCR provider when user configures none: `none` (plan only) - confirm. Q3 Sensitive-glob defaults. Q4 Real-API OCR smoke test needs a key/quota approval (offline mocks used otherwise).
