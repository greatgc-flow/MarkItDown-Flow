# Obsidian shell: v2.0.0

Status: implementation specification, 2026-11-09. Binding: [R1-R23](01_DECISIONS.md). Engine authority: [SPEC](10_SPEC.md). Distribution: [25_PACKAGING](25_PACKAGING.md). Requirements describe required behavior; they do not claim passing implementation evidence.

## 1. Clean-room boundary and behavior inventory

REQ-SHL-01 MUST: Write the shell, styles and tests from this specification and public Obsidian APIs. **v1 `src/` is NOT read during implementation.** Neither v1 `styles.css` nor v1 tests are implementation references. No copied upstream-derived code or translations. Compatibility facts below come from the superseded design's inventory. Retain historical MIT attribution in README/LICENSE per R15. Oracle: named implementer/reviewer attestation records inputs used; source review confirms no ported modules. Similarity checks may support, but cannot replace, that attestation.

This is a behavior inventory, not a reuse authorization (14 rows).

| Surface | Required behavior | Requirement / section |
|---|---|---|
| `convert-file` | Select local files, run locally, present any required consent. | REQ-SHL-02; section 4 |
| `convert-folder` | Select local folder; respect recursion preference and engine bounds. | REQ-SHL-02; section 4 |
| `convert-url` | Compatibility notice: save locally, then convert a file. No URL/YouTube fetch. | REQ-SHL-02 |
| `view-conversion-history` | Open history, including migrated entries. | REQ-SHL-02/07 |
| `open-log-folder` | Open plugin-local redacted logs; explain old logs remain at `~/omnidata_logs`. | REQ-SHL-02/18 |
| `run-image-pipeline-selftest` | Explain router retirement; run version check and offline classification of a new test PNG. | REQ-SHL-02/20 |
| Settings | Validate/migrate all 21 v1 keys; persist schema 2 and no credentials. | REQ-SHL-03..06; section 2 |
| History | At most 100 entries; UI history confers no cache status or authorization. | REQ-SHL-07 |
| Ribbon | One document-conversion icon opens file selection; register/dispose once. | REQ-SHL-08 |
| Context menu | Optional file/folder conversion actions use the same coordinator. | REQ-SHL-08 |
| Drag/drop | Optional local-file drop opens selection confirmation, then the same coordinator. | REQ-SHL-08 |
| Language | Ship complete keyed English/Korean UI; English fallback. | REQ-SHL-19 |
| SetupModal | Diagnose and show external terminal instructions; never install/update. | REQ-SHL-10 |
| Lifecycle/progress | One owned conversion at a time, visible outcome and cancellation. | REQ-SHL-09/13..16 |

REQ-SHL-02 MUST: Register exactly these six local command IDs, without adding `markitdown-flow:`; preserve plugin ID `markitdown-flow`. Unsupported legacy commands remain notices, not missing commands. Oracle: registration snapshot equals the six inventory IDs; URL command produces zero engine/network calls; history/log commands work without Python.

## 2. Settings and migration

REQ-SHL-03 MUST: Missing `schemaVersion` identifies v1. Parse into an allowlisted schema-2 candidate; validate types before use. Missing/invalid fields take the defaults below with one aggregated migration notice listing dropped/reset preferences and counts, never their raw values. Unknown keys are discarded. Newer schemas are read-only and block jobs with an incompatibility notice. Oracle: fixtures for missing, null, malformed, unknown and future fields produce the expected candidate/notices and no launches before success.

Complete v1 top-level migration map (21 keys):

| v1 key | v2 mapping or drop + notice |
|---|---|
| `pythonPath` | Valid executable-path string -> `bootstrapPythonHint`, used only to prefill terminal instructions. Notice: select the venv interpreter as `enginePython`; no automatic execution migration. |
| `enablePlugins` | Drop. Notice: third-party Core plugin loading is unavailable. |
| `pluginArgs` | Drop entire array and nested values. Notice: wrapper arguments were not imported; command configuration requires explicit trust. |
| `docintelEndpoint` | Drop. Notice: built-in Azure DocIntel/CU removed; external command recipe is available. Never reinterpret as a compatible OCR endpoint. |
| `docintelCredential` | Drop credential from `data.json` and migration memory. Notice: use the selected provider's environment variable. |
| `llmApiKey` | Drop credential identically; provider remains `none`. |
| `outputPath` | Preserve valid vault-relative directory; empty -> `markitdown-output`. Unsafe value -> default + notice. |
| `assetExtractionEnabled` | Drop. Notice: engine-required media publication is always enabled. |
| `assetSubfolderTemplate` | Drop. Notice: engine writes linked media in `media/` beside output. |
| `inputBasePath` | Drop. Notice: selected inputs define engine roots; old mirroring preference is unavailable. |
| `enableBatchProgress` | Preserve boolean; default true. Hiding details never hides consent, errors or Cancel. |
| `enableContextMenu` | Preserve boolean; default true. |
| `enableRecursiveConversion` | Preserve boolean; default true. False selects only immediate regular files; true submits the directory for engine discovery. |
| `outputFilenameTemplate` | Drop. Notice: engine names outputs `<original-name>.<ext>.md`; no shell rename. |
| `enableDragDrop` | Preserve boolean; default false. |
| `enableAutoFrontmatter` | Drop. Notice: minimal engine provenance is mandatory; existing notes are untouched. |
| `autoTags` | Drop. Notice: v2 has no tag option; tags were not added to output. |
| `conversionHistory` | Preserve validated entries, newest first, max 100; invalid entries skipped with count notice. See below. |
| `imagePipelineEnabled` | Drop. Notice: per-unit Plans replace the old image router. |
| `ocrLang` | Drop. Notice: Tesseract language codes do not configure the v2 provider. |
| `imagePipelineAdvancedConfig` | Drop whole object, including unknown keys. Notice: old ensemble, confidence, table and deskew tuning is unavailable. |

REQ-SHL-04 MUST: Implement every row; never pass removed settings as engine flags or modify engine output to emulate them. Drop all nested advanced defaults: `ocr_engines`, `ocr_confidence_threshold`, `enable_ocr_ensemble`, `enable_table_extraction`, `preprocess_deskew`, `deskew_method`, `confidence_weight_engine_conf`, `confidence_weight_agreement`, `confidence_weight_length`, `confidence_weight_cleanliness`, `confidence_weight_stdev_inv`. Oracle: a fixture containing all 21 keys and all nested defaults yields the exact allowlisted result; snapshots of argv/output show no template, tag or media-toggle effects.

Schema-2 persisted keys are `schemaVersion=2`, `enginePython` (absolute venv interpreter, initially unset), `bootstrapPythonHint` (optional), `outputPath`, the four retained UI booleans above, `conversionHistory=[]`, `locale=auto`, `provider={name:none,model:"",baseUrl:"https://api.openai.com/v1"}`, and nonsecret `runOptions={dpi:200,minPriority:low,maxUnits:200,approveThreshold:20,sensitive:[]}`. `locale` accepts `auto|en|ko`. Bounds/options use SPEC section 10 validation. No other v1 field is retained. Command template, environment-name list, egress declaration and explicit trust are session-only in 2.0; labels warn that commands execute with the user's privileges. Never migrate trust or approval.

REQ-SHL-05 MUST: Persist migration atomically before enabling engine jobs. Make `data.v1.json` once as an allowlisted, sanitized rollback snapshot: preserve only mapped v1 preference names and safe history; omit credentials, endpoint, arbitrary plugin arguments and advanced config. Remove known credential values from retained strings; replace legacy history errors with `Legacy conversion failed.` rather than copying free-form errors. Never back up raw settings. If migration/save fails, leave original settings readable, block jobs and show recovery instructions; retry deterministically. Oracle: interrupted writes leave valid old or new JSON; repeat migration is idempotent; injected credential sentinels are absent from saved v2 data, sanitized snapshot, notices and logs. Existing external backups are outside migration and disclosed as potentially containing old keys.

REQ-SHL-06 MUST: Credentials come only from the Obsidian process environment; settings expose variable names/instructions, never a key input. Persist no secrets, approval hashes or completed consent. Scrub the engine environment to the SPEC section 8.2 baseline plus required provider variables and explicitly named command variables; include UTF-8 settings. Redact diagnostics per SPEC section 9 before display/storage. Oracle: environment and serialized-artifact snapshots contain only the permitted variables/fields; injected keys never appear in argv, notices, history or logs. A restarted app needs fresh consent.

REQ-SHL-07 MUST: History preserves typed `inputFile`, `outputFile`, `timestamp`, `success`, optional `processingTimeMs`, `assetsExtracted`; discard invalid entries and unknown fields. Paths are display references, not executable input. Stable-sort valid entries by descending timestamp, then original order; cap 100 on migration and insertion. New entries distinguish complete, pending consent, partial failure and cancelled using a nonsecret `outcome`; never infer success from a created file alone. Clear history clears only history. Oracle: 105-entry fixture retains the expected 100; ties are stable; clear leaves cache/outputs unchanged; cancelled and pending runs are visibly distinct from success.

## 3. Engine contract: incorporation only

REQ-SHL-11 MUST: **Incorporate [SPEC section 7.3](10_SPEC.md#73-progress-events-stderr-one-json-object-per-line---progress-jsonl), [section 8.4](10_SPEC.md#84-consent-semantics), and [section 10](10_SPEC.md#10-cli-surface) VERBATIM BY REFERENCE.** They are the sole shell/engine protocol under R19. This document supplies no replacement envelope, handshake command, control channel, staging protocol or altered exit semantics. Plan/report/error data likewise use SPEC sections 7.1/7.4/7.5. Oracle: subprocess contract tests replay engine-produced fixtures through the shell and compare invocations and decoded values with those SPEC sections; an invented command/option fails the test.

REQ-SHL-12 MUST: Spawn the absolute `enginePython` as an executable plus argument array, `shell:false`, hidden subprocess window on Windows; module entry point is `-m mdflow`. Do not interpolate selections into a shell command. Set engine working directory to the selected input root. Pass the actual validated vault destination directly as `-o`, and `<plugin-dir>/cache` as the cache directory. Engine owns discovery, classification, work selection, conversion, publication and output names. Shell never stages or rewrites Markdown/media and never invokes a provider directly. Oracle: paths containing spaces, Korean characters and shell metacharacters arrive as single arguments; published paths are engine-reported paths; successful warm rerun changes no output bytes/mtimes.

REQ-SHL-13 MUST: Frame UTF-8 incrementally across arbitrary chunks/CRLF, independently for the SPEC streams. Consumer limits: progress line <=1 MiB; parse completed lines, ignore unknown event names as SPEC requires. Unsupported event version or malformed known event fails visibly with a shell diagnostic; never expose raw bytes. Spool the potentially large run report to a private owned temporary file with bounded read buffers, then validate it on process exit. Remove that file after consumption or handled failure/cancellation; recover only verified owned stale files after forced termination. The temp is transport storage, never an output staging area. Do not truncate a report and declare success; an IO/capacity failure is explicit. Oracle: split multibyte text, multiple events/chunk, unknown events, oversized/malformed lines, invalid report and process exit without report are exercised; handled exits leave no transport file. No raw stderr is treated as a Notice or success.

## 4. Interaction and consent

REQ-SHL-08 MUST: Use the public lifecycle/event APIs; one ribbon registration, conditional context actions and conditional drop listener. A drop accepts local files only, shows selection before work, and never intercepts unrelated text/URL drops. All entry points share output validation, diagnostics, consent and cancellation. Oracle: disabled preferences register no corresponding action; identical selections through all entry points produce identical coordinator requests; reload leaves one listener/icon.

REQ-SHL-09 MUST: Resolve output against the vault, reject absolute/traversing paths and component/symlink escapes using platform-aware real paths, and revalidate immediately before spawn. For a nonexistent destination resolve the nearest existing ancestor. Do not use a bare string-prefix check. Nonrecursive folder selection excludes hidden entries, symlinks, output and cache locations; recursive discovery remains engine-owned. Admit one active conversion per plugin instance; a second request reports busy. Progress details show engine stage, file counts and unit outcomes without inventing completed work. Oracle: sibling-prefix paths, Windows case/separators, symlink escape, nonexistent parent and concurrent launch probes have explicit results and zero unsafe launches.

REQ-SHL-14 MUST: Present the engine's concrete Plan in a modal: source identity/hash, provider/model, declared destination/egress, selected unit IDs, total/cache/send/low-priority counts, explicit DPI, estimate in USD or `unknown`, threshold flag and sensitive-glob hits. Label the estimate as an estimate; do not invent a hard spend cap. Long lists scroll without hiding totals. Render all dynamic fields as text, never HTML. Default focus/action is **Keep pending**; Escape/close dismisses without authorization. **Approve this Plan** requires deliberate action; threshold/sensitive/unknown-cost notices require acknowledgment. Apply SPEC section 8.4 to that displayed Plan only. Oracle: engine Plan fixtures exactly match visible values; closing/dismissing produces zero approved launches/provider calls; injected HTML renders literally.

REQ-SHL-15 MUST: After the first process exits, approval replays that file's immutable invocation snapshot according to SPEC section 8.4; batch Plans are approved/replayed one file at a time. Never submit several per-file hashes through an invented batch flag. Changes to selected file bytes, provider, endpoint, command template/trust, options or displayed Plan invalidate the pending approval and require fresh planning. Cancellation during/after the modal prevents replay. No remembered approval across jobs or reloads. Oracle: mutate each dependency while modal is open; stale approval never executes; a multi-file consent run pairs each replay with its own engine hash. Engine revalidation remains mandatory; shell checks cannot repair an engine hash defect.

REQ-SHL-16 MUST: Keep Cancel available even when detailed progress is hidden. Cancel/unload dismisses pending consent, prevents new launches and sends the R19 cancellation signal to the owned engine. Wait up to five seconds, then force-terminate that process if still alive. This is a shell supervision deadline, not a redefinition of SPEC exit behavior. Engine owns its command descendants and temporary-file recovery. Preserve committed cache/output; never delete user sources to cancel. A signal death or missing terminal report is shown as interrupted, never successful. Oracle: cancellation before launch, during planning/provider work and on unload yields no subsequent replay; cooperative engine result is SPEC exit 130 and published files remain parseable/complete. Exercise actual OS processes, including command-child cleanup. Windows signal/exit behavior and descendant cleanup are TODO-VERIFY until those integration runs pass; do not fake exit 130 from an arbitrary native status. Explain that cancellation cannot retract a sent request and retry may incur cost.

## 5. Diagnostics-only SetupModal

REQ-SHL-10 MUST: SetupModal displays configured interpreter, Python/engine/Core/renderer versions, probe status and copyable external bootstrap/upgrade instructions from [25_PACKAGING section 2](25_PACKAGING.md#2-user-terminal-bootstrap-and-version-check). Probe `enginePython` first with a five-second timeout and SPEC's version command. If unconfigured, optional `python3`, `python`, or `py -3` version probes only prefill instructions; never become an execution fallback. No interpreter hunt, managed-runtime pointer, pip/venv launch, installer, dependency download or self-update. The user chooses an absolute venv interpreter after external setup. Oracle: mocked spawn/network/filesystem calls from modal open/refresh contain only version probes, zero dependency mutations/network calls; copy buttons only write clipboard text. Missing engine leaves settings/history available.

REQ-SHL-17 MUST: Use the version response defined in SPEC section 10, with compatibility policy from 25_PACKAGING. Missing/malformed fields, timeout, unavailable interpreter or unsupported engine/Core version block conversions and link diagnostics. Do not require fields absent from SPEC. Oracle: supported and rejected version fixtures yield exact enabled/blocked states; no conversion is launched after a failed check.

REQ-SHL-18 MUST: Logs are plugin-local, bounded to five 1 MiB rotated files, and contain timestamp, stage/code/count/status only; no OCR text, source bytes, complete Plan/report, credentials or raw exceptions. Diagnostics copy includes redacted version/probe results and codes only; identify paths relative to vault or redact home prefixes. History/log access does not start conversion. Oracle: injected secrets/document text are absent from all logs/copies; rotation never exceeds the bound; the log command opens only the owned folder.

REQ-SHL-20 MUST: The frozen selftest command performs the version check then `classify` on a shell-owned, newly authored PNG fixture in private temporary storage; networking/provider invocation forbidden. Report health or a localized code; remove that fixture after exit. Do not add `selftest` to the engine API. Oracle: spawn snapshot contains only SPEC commands, network guard records zero sockets and temp fixture is removed on success/failure/cancel.

## 6. Error-code to message tables

REQ-SHL-19 MUST: Every table code selects `engine.<CODE>` in independently authored `en`/`ko` dictionaries; local diagnostics select `shell.<NAME>`. Use host language for `locale=auto` (`ko*` -> ko, otherwise en), with explicit override. Interpolation uses text nodes and fixed parameters, never raw engine `message`. English copy below is normative meaning; Korean must convey the same meaning. Unknown codes use `engine.UNKNOWN` plus the literal code and redacted details in diagnostics. Oracle: exact dictionary-key parity, nonempty values and interpolation tests in both languages; code-set comparison against SPEC section 7.5 is exhaustive; named bilingual review attests meaning. Engine text stays English in engine artifacts.

| Engine error code | English message / next action |
|---|---|
| `E_CORE_VERSION` | Unsupported Core version. Open setup diagnostics. |
| `E_SNIFF_IO` | Cannot read this source. Check access. |
| `E_TOO_LARGE` | Source exceeds the byte limit. Review limits. |
| `E_ENCRYPTED` | Source is protected. Export an unprotected copy. |
| `E_CORRUPT` | Source could not be parsed. Check the original. |
| `E_UNSUPPORTED` | This format is unsupported. Export a supported format. |
| `E_MEDIA_OUT_OF_SCOPE` | Audio/video conversion is unavailable in 2.0. |
| `E_LEGACY` | Legacy format requires external export to a supported format. |
| `E_ZIP_PATH` | Unsafe archive-member path was refused. |
| `E_ZIP_DEPTH` | Archive nesting exceeds the limit. |
| `E_ZIP_ENTRIES` | Archive entry count exceeds the limit. |
| `E_ZIP_TOTAL` | Expanded archive size exceeds the limit. |
| `E_ZIP_BOMB` | Unsafe archive expansion was refused. |
| `E_TRIAGE_FAIL` | OCR inspection failed. Review the conversion report. |
| `E_TRIAGE_SCHEMA` | Unsupported inspection schema. Check engine/Core compatibility. |
| `E_CONVERT_FAIL` | Base conversion failed. Other reported results may remain usable. |
| `E_RENDER_FAIL` | An OCR unit could not be rendered. Review pending work. |
| `E_PLAN_OVERSIZE` | OCR work exceeds the unit limit. Review the pending Plan. |
| `E_APPROVAL_REQUIRED` | OCR work is pending your approval. Review the Plan. |
| `E_APPROVAL_DENIED` | OCR was not approved. Pending output is retained. |
| `E_PROVIDER_CONFIG` | Provider configuration is invalid. Check settings/environment. |
| `E_PROVIDER_HTTP` | Provider request failed. Review diagnostics before retrying. |
| `E_PROVIDER_TIMEOUT` | Provider request timed out. Review before retrying. |
| `E_PROVIDER_OUTPUT` | Provider returned unusable text. Review before retrying. |
| `E_OUTPUT_IO` | Output could not be written. Check destination/access. |
| `E_USAGE` | Engine arguments are invalid. Review settings/diagnostics. |

| Engine warning code | English message |
|---|---|
| `W_SKIPPED_HIDDEN` | Hidden entry skipped. |
| `W_SKIPPED_SYMLINK` | Symbolic link skipped. |
| `W_EXT_MISMATCH` | File content differs from its extension. |
| `W_MEDIA_NOT_INSPECTED` | Some media was not inspected. |
| `W_TRIAGE_UNSUPPORTED` | OCR inspection is unavailable for this format. |
| `W_TRIAGE_UNKNOWN` | OCR need remains unknown. |
| `W_TRIAGE_INCONSISTENT` | Inspection evidence is inconsistent; review required. |
| `W_TRIAGE_COVERAGE` | Inspection is incomplete; more OCR work may exist. |
| `W_TRIAGE_UNKNOWN_VALUE` | Inspection returned an unknown value; review compatibility. |
| `W_REVIEW_PRIORITY` | Low-priority OCR candidates need review. |
| `W_MEDIA_UNMAPPED` | OCR media has no inline anchor; review the unmapped appendix. |
| `W_MEDIA_FORMAT` | Media encoding cannot be used for OCR. |
| `W_CACHE_CORRUPT` | Invalid cache entry ignored; work may need repeating. |

| Shell diagnostic key | English message |
|---|---|
| `shell.SETTINGS` | Settings could not be migrated/saved; conversion is blocked. |
| `shell.RUNTIME` | Engine unavailable or incompatible. Open setup diagnostics. |
| `shell.PROTOCOL` | Invalid engine response; this run did not complete successfully. |
| `shell.DESTINATION` | Choose an output directory inside this vault. |
| `shell.BUSY` | A conversion is already active. |
| `shell.CANCELLED` | Conversion interrupted; review results before retrying. |
| `shell.LEGACY_URL` | URL import is unavailable; save locally and convert the file. |
| `engine.UNKNOWN` | Unrecognized engine diagnostic. Review compatibility. |

Shell diagnostics are UI keys, never new engine error codes. Exit interpretation is exclusively SPEC section 10.3; show file/unit issues and pending work even when the exit code alone is insufficient. Do not map existence of output or a warning to success.

## 7. Traceability and review disposition

REQ-SHL-21 MUST: Every shell requirement above has tests tagged with `req("REQ-SHL-xx")` (Jest registration helper equivalent to engine `@req(...)`). Export executable test registrations/results to R20's generator; reject unknown IDs and zero-test requirements. Section 1's clean-room review and bilingual review are named manual attestations linked alongside automated evidence. Oracle: removing a marker or adding an unknown ID fails CI; generated coverage links each ID to actual test results. No hand-written coverage matrix or claimed score substitutes for that result.

| Review finding | Disposition in this document |
|---|---|
| Fable X-01/X-02/X-03 | Fixed: clean-room inventory, amended R10, one selected interpreter and external setup. |
| Fable X-10/X-11 | Fixed: sole SPEC contract by reference; actual engine output destination, no shell staging. |
| Fable X-12/X-13/X-14 | Fixed: naming/media/tag preferences dropped with notices, no new engine flags. |
| Fable X-18/X-19 | Fixed: estimate/unknown display; selftest uses existing commands. |
| Fable X-19b/X-25/X-27 | Shell portion fixed: five-second supervision, SPEC protocol, diagnostics-only setup. Engine/acceptance edits remain outside this file. |
| Fable X-31/X-32/X-35 | Shell portion fixed: explicit command trust/env names, Azure migration, R15/R16 ownership. |
| ag orphan AC-014/015/018; R3-26 shell traceability | Fixed here by migration/setup/i18n requirements and executable marker gate. AC-012 also maps to REQ-SHL-06/18; packaging owns AC-023. |
| cx R3-01..10 | Open in the engine specification: Core vocabulary, raster/frame/occurrence handling, capped inspection and classification. Required package contract tests must expose these defects; the shell consumes engine results. |
| cx R3-11..26 and Fable engine/acceptance findings | Open in their owning files; shell must not reclassify, invent fields or silently repair protocol/schema defects. |

## Objections / Rejected findings

- Fable X-16's proposed extra version fields and X-19's proposed engine `selftest` command are rejected for this shell: R19 incorporates SPEC section 10 unchanged. Existing version/classify commands suffice; compatibility checks use only published fields.
- Fable X-03's suggested in-place upgrade is not prescribed: the user creates/selects another venv externally so rollback can retain the old one. No plugin-managed runtime pointer or installation is introduced.
- Fable section 6's raw `data.json` copy with only credential-key removal is rejected: plugin arguments, advanced config and history errors can also contain secrets. REQ-SHL-05 sanitizes an allowlist before any snapshot.
- Reuse of v1 patterns/code/styles is rejected under R15, even if technically useful. The old PKG-O01 objection is resolved by amended R10 and is not an open objection.

Open dependency: R23/cx consent binding, final Plan construction, request budgets, report schemas, cross-platform cancellation and endpoint/config identity need engine-owner resolution and contract evidence. Keep these release-blocking; this document does not assert they are already fixed.
