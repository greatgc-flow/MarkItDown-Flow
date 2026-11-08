# Obsidian shell: v2.0.0

Status: R5 revision, 2026-11-09. Binding: [decisions R1-R25](01_DECISIONS.md). Engine authority: [SPEC](10_SPEC.md). Distribution: [25_PACKAGING](25_PACKAGING.md). `SYNC-AFTER-DRAFT-3` marks dependencies on the concurrent SPEC revision, not completed verification. Requirements describe behavior, not passing implementation evidence.

## 1. Clean-room boundary and behavior inventory

REQ-SHL-01 MUST: Write shell, styles and tests from this specification and public Obsidian APIs. **v1 `src/` is NOT read during implementation.** Neither v1 `styles.css` nor v1 tests are implementation references. No copied upstream-derived code or translations. Oracle: source/import and build-input checks reject references to those retired inputs. Those checks do not prove independent authorship: the separate R15 implementer/reviewer attestation and historical MIT credit are release checklist items under [REQ-PKG-15](25_PACKAGING.md#5-release-assets-and-obsidian-checklist).

This is a behavior inventory, not a reuse authorization (14 rows).

| Surface | Required behavior | Requirement / section |
|---|---|---|
| `convert-file` | Select local files, run locally, present any required consent. | REQ-SHL-02; section 4 |
| `convert-folder` | Select local folder; respect recursion preference and engine bounds. | REQ-SHL-02; section 4 |
| `convert-url` | Compatibility notice: save locally, then convert a file. No URL/YouTube fetch. | REQ-SHL-02 |
| `view-conversion-history` | Open history, including migrated entries. | REQ-SHL-02/07 |
| `open-log-folder` | Open plugin-local redacted logs; explain old logs remain at `~/omnidata_logs`. | REQ-SHL-02/18 |
| `run-image-pipeline-selftest` | Explain router retirement; invoke SPEC's offline selftest. | REQ-SHL-02/20 |
| Settings | Validate/migrate all 21 v1 keys; persist schema 2 and no credentials. | REQ-SHL-03..06; section 2 |
| History | At most 100 entries; UI history confers no cache status or authorization. | REQ-SHL-07 |
| Ribbon | One document-conversion icon opens file selection; register/dispose once. | REQ-SHL-08 |
| Context menu | Optional file/folder conversion actions use the same coordinator. | REQ-SHL-08 |
| Drag/drop | Optional local-file drop opens selection confirmation, then the same coordinator. | REQ-SHL-08 |
| Language | Ship complete keyed English/Korean UI; English fallback. | REQ-SHL-19 |
| SetupModal | Diagnose and show external terminal instructions; never install/update. | REQ-SHL-10 |
| Lifecycle/progress | One owned conversion at a time, visible outcome and cancellation. | REQ-SHL-09/13..16 |

REQ-SHL-02 MUST: Register exactly these six local command IDs, without adding `markitdown-flow:`; preserve plugin ID `markitdown-flow`. Unsupported legacy commands remain notices, not missing commands. A single `Platform.isDesktop` entry guard precedes lifecycle registrations and Node API loading/access; mobile returns without registrations or engine work. The manifest's `isDesktopOnly:true` is mandatory under [REQ-PKG-15](25_PACKAGING.md#5-release-assets-and-obsidian-checklist). Oracle: desktop registration snapshot equals the six inventory IDs; simulated mobile registers/spawns nothing and loads no Node API; URL command makes zero engine/network calls; history/log commands work without Python.

README disclosures for outside-vault access, remote services/purpose, no client telemetry and optional account/key/cost requirements live in [REQ-PKG-16 (R16)](25_PACKAGING.md#5-release-assets-and-obsidian-checklist). Shell setup/provider UI links those disclosures; it does not maintain a second policy checklist.

## 2. Settings and migration

REQ-SHL-03 MUST: Missing `schemaVersion` identifies v1. Parse into an allowlisted schema-2 candidate; validate types before use. Missing/invalid fields take the defaults below with one aggregated migration notice listing dropped/reset preferences and counts, never their raw values. Unknown keys are discarded. Newer schemas are read-only and block jobs with an incompatibility notice. Oracle: fixtures for missing, null, malformed, unknown and future fields produce the expected candidate/notices and no launches before success.

Complete v1 top-level migration map (21 keys):

| v1 key | v2 mapping or drop + notice |
|---|---|
| `pythonPath` | Valid executable-path string -> `bootstrapPythonHint`, used only to prefill terminal instructions. Notice: select the venv interpreter as `enginePython`; no automatic execution migration. |
| `enablePlugins` | Drop. Notice: third-party Core plugin loading is unavailable. |
| `pluginArgs` | Drop entire array and nested values. Notice: wrapper arguments were not imported; command providers are CLI-only. |
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

Schema-2 persisted keys are `schemaVersion=2`, `enginePython` (absolute venv interpreter, initially unset), `bootstrapPythonHint` (optional), `outputPath`, the four retained UI booleans above, `conversionHistory=[]`, `locale=auto`, `provider={name:none,model:"",baseUrl:"https://api.openai.com/v1"}`, and nonsecret `runOptions={dpi:200,minPriority:low,maxUnits:200,approveThreshold:20,sensitive:[]}`. `locale` accepts `auto|en|ko`. Bounds/options use SPEC section 10 validation. Shell provider choices are `none|openai-compatible`; `command` remains available through the engine CLI under R7. Cut shell command templates, command environment/trust controls and their persistence/session modes. Reject unsupported persisted provider choices with a notice and reset to `none`; never pass unknown arguments. No other v1 field is retained; never migrate trust or approval.

REQ-SHL-05 MUST: Persist migration atomically before enabling engine jobs. Make `data.v1.json` once as an allowlisted, sanitized rollback snapshot: preserve only mapped v1 preference names and safe history; omit credentials, endpoint, arbitrary plugin arguments and advanced config. Remove known credential values from retained strings; replace legacy history errors with `Legacy conversion failed.` Never back up raw settings. On failure discard raw settings/credential references from working memory, block jobs and show one recovery notice: the original disk file may still contain v1 keys; remove them manually before syncing and retry migration. Preserve that original if writing is impossible; do not overwrite it with a recovery placeholder or create another copy. Do not claim disk sanitization succeeded on a failed save. Oracle: interrupted writes leave valid old or new JSON; repeat migration is idempotent; successful v2/snapshot writes and all notices/logs contain no credential sentinels; a write-denied fixture leaves original bytes unchanged, launches no job and displays the unsanitized-disk warning. External backups are outside migration.

REQ-SHL-06 MUST: Credentials come only from the Obsidian process environment (R8); settings expose variable names/instructions, never a key input. Persist no secrets, approval hashes or completed consent. Scrub the engine environment to the SPEC baseline plus required provider variables and UTF-8 settings; no command-variable forwarding. Setup explains that desktop launches may lack terminal environment variables: fully quit Obsidian, set the variables and launch it from that same terminal using platform-specific instructions under REQ-PKG-05. Display only whether `MDFLOW_API_KEY` is present. If absent, keep provider `none` usable; block remote execution with localized configuration guidance. Redact diagnostics per SPEC section 9. Oracle: absent/present environment fixtures produce the expected state; desktop-launch smoke verifies inherited variables without printing values; keys never appear in argv, persisted state, notices, history or logs. No credential-entry/keychain mode is added.

REQ-SHL-07 MUST: History preserves typed `inputFile`, `outputFile`, `timestamp`, `success`, optional `processingTimeMs`, `assetsExtracted`; discard invalid entries and unknown fields. Paths are display references, not executable input. Stable-sort valid entries by descending timestamp, then original order; cap 100 on migration and insertion. New entries distinguish complete, pending consent, partial failure and cancelled using a nonsecret `outcome`; never infer success from a created file alone. Clear history clears only history. Oracle: 105-entry fixture retains the expected 100; ties are stable; clear leaves cache/outputs unchanged; cancelled and pending runs are visibly distinct from success.

## 3. Engine contract: incorporation only

REQ-SHL-11 MUST: **Incorporate [SPEC section 7.3](10_SPEC.md#73-progress-events-stderr-one-json-object-per-line---progress-jsonl), [section 8.4](10_SPEC.md#84-consent-semantics), and [section 10](10_SPEC.md#10-cli-surface) VERBATIM BY REFERENCE.** They are the sole shell/engine protocol under R19. This document supplies no replacement envelope, handshake command, control channel, staging protocol or altered exit semantics. Plan/report/error data likewise use SPEC sections 7.1/7.4/7.5. Oracle: subprocess contract tests replay engine-produced fixtures through the shell and compare invocations and decoded values with those SPEC sections; an invented command/option fails the test.

REQ-SHL-12 MUST: Spawn the absolute `enginePython` as an executable plus argument array, `shell:false`, hidden subprocess window on Windows; module entry point is `-m mdflow`. Snapshot the original ordered absolute input arguments, working directory, output/cache roots and nonsecret options once. Keep that working directory fixed for the whole job and its replay; let SPEC define logical roots. Pass the actual validated vault destination directly as `-o`, and `<plugin-dir>/cache` as cache. Engine owns discovery, classification, work selection and publication; shell neither renames outputs nor invokes providers. Oracle: spaces, Korean and metacharacters remain single arguments; original and replay input arguments/cwd/output/cache are identical; nested `inputs/sub/a.pdf` retains logical `sub/a.pdf` and the same output path. Warm-success assertions follow SPEC section 10.4, not audit-report write counts. Root/Plan fixture contract: `SYNC-AFTER-DRAFT-3` (SPEC sections 7.1/8.4/10).

REQ-SHL-13 MUST: Frame UTF-8 incrementally across arbitrary chunks/CRLF using SPEC section 7.3's version and byte limit; ignore unknown event names as required. Invalid known events fail visibly without raw-byte display. Consume approval events as summaries, not full unit lists; obtain full Plans from SPEC section 10.1's `plan` output. Cut the full-Plan-on-one-event assumption; add no chunk/reference protocol or Plan truncation. Spool structured stdout to private owned temporary storage with bounded read buffers, validate after exit and remove after consumption/handled failure/cancel; recover only verified owned stale files. This is transport storage, not publication staging. Validate mdflow codes against section 7.5 only in mdflow-owned fields; preserve raw `files[].triage` with its separate Core vocabulary (R5-N08). Oracle: split UTF-8/CRLF, unknown events, malformed/oversized lines and missing reports fail or decode as specified; valid raw triage `corrupt` is retained; a large unit list stays in full Plan output while the event is bounded and no authorization occurs from a truncated Plan. `SYNC-AFTER-DRAFT-3`: sections 7.1/7.3/10 summary/Plan framing (R5-N09).

## 4. Interaction and consent

REQ-SHL-08 MUST: Use the public lifecycle/event APIs; one ribbon registration, conditional context actions and conditional drop listener. A drop accepts local files only, shows selection before work, and never intercepts unrelated text/URL drops. All entry points share output validation, diagnostics, consent and cancellation. Oracle: disabled preferences register no corresponding action; identical selections through all entry points produce identical coordinator requests; reload leaves one listener/icon.

REQ-SHL-09 MUST: Resolve output against the vault, reject absolute/traversing paths and component/symlink escapes using platform-aware real paths, and revalidate immediately before spawn. For a nonexistent destination resolve the nearest existing ancestor. Do not use a bare string-prefix check. Nonrecursive folder selection excludes hidden entries, symlinks, output and cache locations; recursive discovery remains engine-owned. Admit one active conversion per plugin instance; a second request reports busy. Progress details show engine stage, file counts and unit outcomes without inventing completed work. Oracle: sibling-prefix paths, Windows case/separators, symlink escape, nonexistent parent and concurrent launch probes have explicit results and zero unsafe launches.

REQ-SHL-14 MUST: Use one modal for the complete original selection, listing each file's full engine Plan and hash per SPEC sections 7.1/8.4. Show source/root identity, provider/model/destination, selected units, DPI, pending/low-priority and informational cache/send counts, approved request budget and `approved.est_max_cost` in USD or `unknown`, threshold/sensitive hits. Cached status is not an authorization field. Cut token estimation, run-level totals/hash and interruption counters; display the conservative per-file bounds supplied by the engine, without pretending shared Keys are independent charges or guaranteed deduplicated across concurrent jobs. A fixed notice explains interrupted/failed-cache requests may already have been billed and retry can duplicate cost. Render fields as text with scrolling. Default **Keep pending**, Escape/close = no authorization. **Approve this selection** acknowledges threshold/sensitive/unknown-cost notices once for the displayed file scopes. Oracle: 50 files produce one modal, per-file fields match Plans, no invented run/token/interruption fields, HTML stays literal and dismissal yields zero approved launches. `SYNC-AFTER-DRAFT-3`: final approved/status/cost shapes in SPEC sections 7.1/8.4 (R5-N02/N03/N11).

REQ-SHL-15 MUST: Prepare remote work with SPEC `plan` on the original selection. After it exits and the user approves, replay the **exact original batch/root invocation** snapshot as `run`: retain ordered input arguments, cwd, provider/options and output/cache roots; only the documented subcommand/authorization arguments change (SPEC sections 8.4/10). Use existing repeatable `--yes <file-plan-hash>` arguments for the displayed file scopes in one `run`, with `--approved-by plugin:modal`. No run-level hash, shell manifest, bare approval or root-preserving custom flag. `none` runs without a consent modal. Never turn a nested file into a file root or replay per file. Changes to hash-bound source/provider/options discard approval; cache changes follow SPEC's unhashed informational status and do not force a new authorization hash. Engine denial/pending state is displayed for fresh review, never auto-approved/retried. Cancel prevents replay; no authorization survives reload. Oracle: directory/nested-file/multi-root fixtures retain input order/cwd/logical paths, approved hashes and output destinations; 50 files yield one approved run; cache warming leaves the hash stable; changed approved content has no unauthorized egress. `SYNC-AFTER-DRAFT-3`: exact `plan`/`run` options, stable approved object and hash-list semantics in SPEC sections 7.1/8.4/10 (R5-N03/N10).

REQ-SHL-16 MUST: Keep Cancel visible even with progress details hidden. Cancel/unload dismisses consent and prevents launches, then requests R19 cancellation of the owned engine. Allow up to five seconds before force termination. Distinguish tested cooperative shutdown (SPEC exit/report) from forced/native termination (interrupted, report may be absent); never synthesize exit 130 or success. Do not wait for a 120-second provider timeout or retry backoff. Engine owns waits/temporary recovery; shell launches no command provider or process-tree helper. Preserve committed results and disclose possible sent-request cost. Oracle: cancel before launch/in modal/during a blocked mock request/unload prevents replay; cooperative POSIX path produces exit 130; forced POSIX and Windows paths record actual native status, recover on restart and leave no owned live engine/worker in the process inventory. Actual Windows/blocked-request tests are mandatory release gates, not a claimed guarantee. `SYNC-AFTER-DRAFT-3`: SPEC REQ-GEN-09/sections 8.2/10.3 must distinguish cooperative and forced paths (R5-N07).

## 5. Diagnostics-only SetupModal

REQ-SHL-10 MUST: SetupModal displays configured interpreter, Python/engine/Core/renderer versions, probe status and copyable external bootstrap/upgrade instructions from [25_PACKAGING section 2](25_PACKAGING.md#2-user-terminal-bootstrap-and-version-check). Probe `enginePython` first with a five-second timeout and SPEC's version command. If unconfigured, optional `python3`, `python`, or `py -3` version probes only prefill instructions; never become an execution fallback. No interpreter hunt, managed-runtime pointer, pip/venv launch, installer, dependency download or self-update. The user chooses an absolute venv interpreter after external setup. Oracle: mocked spawn/network/filesystem calls from modal open/refresh contain only version probes, zero dependency mutations/network calls; copy buttons only write clipboard text. Missing engine leaves settings/history available.

REQ-SHL-17 MUST: Consume SPEC section 10's complete `version` response using [REQ-PKG-06](25_PACKAGING.md#2-user-terminal-bootstrap-and-version-check): protocol/schema 1, supported Python/engine/Core and release-locked pypdfium2/Pillow compatibility. Missing/malformed required fields, timeout or mismatch blocks jobs and links diagnostics; ignore additional optional fields. Oracle: actual version response and fixtures missing/mismatching each required field produce exact enabled/blocked states with zero conversion after failure. `SYNC-AFTER-DRAFT-3`: regenerate fixtures from SPEC section 10.1; do not retain the former four-field gate (R5-N11).

REQ-SHL-18 MUST: Logs are plugin-local, bounded to five 1 MiB rotated files, and contain timestamp, stage/code/count/status only; no OCR text, source bytes, complete Plan/report, credentials or raw exceptions. Diagnostics copy includes redacted version/probe results and codes only; identify paths relative to vault or redact home prefixes. History/log access does not start conversion. Oracle: injected secrets/document text are absent from all logs/copies; rotation never exceeds the bound; the log command opens only the owned folder.

REQ-SHL-20 MUST: The frozen command runs the version check then SPEC section 10.1's existing `selftest`; no shell-authored fixture or parallel health-test mode. Report its exit/diagnostics through the same localized coordinator. Oracle: spawn snapshot contains only `version`/`selftest`, with zero sockets/provider calls and no shell-created raster. `SYNC-AFTER-DRAFT-3`: package-bundled fixture and selftest oracle must match the final SPEC command.

## 6. Error-code to message tables

REQ-SHL-19 MUST: Key the message table and independently authored `en`/`ko` dictionaries by code. **Generate engine row keys from the active Code-column cells of SPEC section 7.5; the resulting sets must be identical.** Do not scan deleted-code prose, raw Core issue lists or the entire SPEC for codes. Each engine row selects `engine.<CODE>`; local diagnostics select `shell.<NAME>`. Use host language for `locale=auto` (`ko*` -> ko, otherwise en), with explicit override. Interpolate text nodes/fixed parameters, never raw `message`; unknown codes use `engine.UNKNOWN` plus a redacted literal code. Oracle: `JT-SHL-19-01`, tagged `req("REQ-SHL-19")`, parses section 7.5's active table rows, unions E_/W_ literals in their first cells and asserts set-equality with this section's engine-code rows and both dictionaries' engine-code suffixes (excluding fallback `UNKNOWN`). Duplicate rows, a missing/new/deleted code or unequal dictionary sets fail; values must be nonempty and interpolation safe in both languages. A raw triage `issues[].code` is outside this set. Named bilingual meaning review is separately required by REQ-PKG-15; key parity is not translation proof. `SYNC-AFTER-DRAFT-3`: regenerate and rerun this exact assertion after SPEC settles; never keep a second closed-code list.

Generated key snapshot: SPEC DRAFT-3 section 7.5 active Code-column cells; English copy supplies message meaning. This snapshot must pass `JT-SHL-19-01` after DRAFT-3 synchronization. No exit/scoping rules are duplicated here.

| Engine error code | English message / next action |
|---|---|
| `E_USAGE` | Engine arguments are invalid. Review settings/diagnostics. |
| `E_CORE_VERSION` | Unsupported Core version. Open setup diagnostics. |
| `E_PROVIDER_CONFIG` | Provider configuration is invalid. Check settings/environment. |
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
| `E_OUTPUT_IO` | Output could not be written. Check destination/access. |
| `E_OUTPUT_COLLISION` | Sources map to the same output. Rename inputs or change the selection. |
| `E_CACHE_IO` | Cache could not be written. Review diagnostics before retrying. |
| `E_APPROVAL_REQUIRED` | OCR work is pending your approval. Review the Plan. |
| `E_APPROVAL_DENIED` | OCR was not approved. Pending output is retained. |
| `E_PROVIDER_HTTP` | Provider request failed. Review diagnostics before retrying. |
| `E_PROVIDER_TIMEOUT` | Provider request timed out. Review before retrying. |
| `E_PROVIDER_OUTPUT` | Provider returned unusable text. Review before retrying. |

| Engine warning code | English message |
|---|---|
| `W_SKIPPED_HIDDEN` | Hidden entry skipped. |
| `W_SKIPPED_SYMLINK` | Symbolic link skipped. |
| `W_DUPLICATE_INPUT` | Repeated input skipped; its first occurrence is retained. |
| `W_EXT_MISMATCH` | File content differs from its extension. |
| `W_MEDIA_NOT_INSPECTED` | Some media was not inspected. |
| `W_TRIAGE_UNSUPPORTED` | OCR inspection is unavailable for this format. |
| `W_TRIAGE_UNKNOWN` | OCR need remains unknown. |
| `W_TRIAGE_INCONSISTENT` | Inspection evidence is inconsistent; review required. |
| `W_TRIAGE_UNKNOWN_VALUE` | Inspection returned an unknown value; review compatibility. |
| `W_TRIAGE_PARTIAL` | Inspection is incomplete; more OCR work may exist. |
| `W_CORE_DEPENDENCY` | Core inspection dependency is unavailable. Open setup diagnostics. |
| `W_EXTERNAL_MEDIA` | External media was not fetched or inspected. |
| `W_UNRESOLVED_EMBED` | Embedded media could not be resolved. |
| `W_IMAGE_PROBE` | Image inspection failed; OCR eligibility needs review. |
| `W_REVIEW_PRIORITY` | Low-priority OCR candidates need review. |
| `W_MEDIA_UNMAPPED` | OCR media has no inline anchor; review the unmapped appendix. |
| `W_MEDIA_FORMAT` | Media encoding cannot be used for OCR. |
| `W_MEDIA_MULTIFRAME` | Embedded multi-frame media has limited processing; review the report. |
| `W_CACHE_CORRUPT` | Invalid cache entry ignored; work may need repeating. |
| `W_OUTPUT_TRUNCATED` | Provider text exceeded the output limit and was truncated. |
| `W_OUTPUT_EDITED` | Existing output was edited and was preserved. |
| `W_APPROVAL_UNUSED` | An approved hash was unused; the file may already be cached. |

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

REQ-SHL-21 MUST: Tag machine-checkable shell tests with `req("REQ-SHL-xx")` and export registrations/results to R20's generator; reject unknown IDs and zero-test requirements. R15 independent-authorship review, bilingual meaning review and R16 README review are separately named manual gates under REQ-PKG-15/16. Never count an evidence-file-presence assertion as proof of those properties or include a manual gate in automated coverage totals. Oracle: removing a marker/adding an unknown ID fails CI; removing a manual sign-off blocks the release checklist independently; generated automated coverage still reports only executable assertions.

| Review finding | Disposition in this document |
|---|---|
| Fable X-01/X-02/X-03 | Fixed: clean-room inventory, amended R10, one selected interpreter and external setup. |
| Fable X-10/X-11 | Fixed: sole SPEC contract by reference; actual engine output destination, no shell staging. |
| Fable X-12/X-13/X-14 | Fixed: naming/media/tag preferences dropped with notices, no new engine flags. |
| Fable X-18/X-19 | Fixed: engine cost/budget display; SPEC selftest replaces the shell fixture recipe. |
| Fable X-19b/X-25/X-27 | Shell portion fixed: five-second supervision, SPEC protocol, diagnostics-only setup. Engine/acceptance edits remain outside this file. |
| Fable X-31/X-32/X-35 | Shell command controls cut; Azure migration and explicit REQ-PKG-15/16 policy ownership retained. |
| ag orphan AC-014/015/018; R3-26 shell traceability | Fixed here by migration/setup/i18n requirements and executable marker gate. AC-012 also maps to REQ-SHL-06/18; packaging owns AC-023. |
| R5-N07 / SHL-REV-06 | Cooperative versus forced cancellation distinguished; arbitrary command launch cut. Real OS evidence remains a release gate; engine synchronization is pending. |
| R5-N08/N09 | Separate Core/mdflow code validation; cut full-Plan events in favor of bounded summaries and full `plan` output. Final framing fixtures are `SYNC-AFTER-DRAFT-3`. |
| R5-N10 / SHL-REV-05 | One modal, exact original batch/root replay, repeatable file hashes; no root-changing per-file mode or run hash. Final option/Plan fixtures are `SYNC-AFTER-DRAFT-3`. |
| R5-N11 / cc code-table mismatch | Table regenerated from active DRAFT-3 codes; JT-SHL-19-01 requires equality with SPEC and en/ko. Full version gate and approved maximum-cost/status display referenced; final contract-test sync remains pending. |
| SHL-REV-01/02 | Explicit desktop guard plus REQ-PKG-15 `isDesktopOnly`; REQ-PKG-16 R16 README/UI links. |
| SHL-REV-03/04/07/08 | Risk/UX clarified and simpler alternatives selected; requested extra modes, destructive recovery and command removal rejected below. |
| R5 engine-only findings N01..06/N12 and remaining R3 partials | Owned by Fable's SPEC revision; no shell reclassification, cache locking or alternate protocol. Contract checks remain `SYNC-AFTER-DRAFT-3`. |

## Objections / Rejected findings

- The former rejection of protocol/schema/Pillow fields and engine `selftest` is withdrawn: current SPEC section 10 defines them. Consume that authority by reference; do not freeze the earlier four-field schema.
- SHL-REV-01's separate guard around every registration is rejected as redundant. One desktop entry guard precedes all registrations/Node access; REQ-PKG-15 enforces the manifest flag.
- SHL-REV-03's sanitized recovery placeholder is rejected: a failed/denied write cannot promise a successful replacement, and overwriting recoverable preferences adds data loss. Drop raw memory references, block jobs and disclose unsanitized original disk state; successful writes still remove secrets.
- SHL-REV-04's credential-entry/keychain mode is not adopted under the simplification rule. SPEC permits a spawning shell to supply an env value from memory; it does not require another credential UI. Use tested launch-time environment inheritance and keep `none` usable when no key is present.
- SHL-REV-05's shell-authored batch manifest/token estimator is rejected; accept one batch modal using engine Plans and existing authorization only.
- SHL-REV-06's mandatory Job Objects/taskkill subsystem is rejected: remove shell command-provider support, use the SPEC engine lifecycle, distinguish forced native death and require real OS tests. Windows behavior is not declared verified by prose; failed cleanup remains release-blocking.
- SHL-REV-07's removal of R15/manual gates from requirement coverage is rejected where it conflicts with R20/R21. Accept separation: automated REQ-SHL-01/19 checks cover inputs/key parity; independent authorship, meaning and README compliance require separate named release sign-offs, never fake Jest passes.
- SHL-REV-08's removal of `convert-url` is rejected under F1's frozen six command IDs. Keep the compatibility notice and no execution path.
- Fable X-03's suggested in-place upgrade is not prescribed: the user creates/selects another venv externally so rollback can retain the old one. No plugin-managed runtime pointer or installation is introduced.
- Fable section 6's raw `data.json` copy with only credential-key removal is rejected: plugin arguments, advanced config and history errors can also contain secrets. REQ-SHL-05 sanitizes an allowlist before any snapshot.
- Reuse of v1 patterns/code/styles is rejected under R15, even if technically useful. The old PKG-O01 objection is resolved by amended R10 and is not an open objection.

## 8. R5 changelog (including every cut)

| Finding / cut | Change |
|---|---|
| N10 / cut per-file replay | Original ordered batch arguments/cwd/output/cache stay fixed; one replay uses SPEC authorization. |
| SHL-REV-05 / cut per-file modals | One engine-scoped selection approval; no shell manifest or token estimator. |
| SHL-REV-06 / cut shell command provider | `command` is CLI-only; delete shell template/trust/env controls and session configuration mode. |
| N11 / cut duplicate health fixture | Use SPEC `selftest`; no shell PNG creation or parallel health implementation. |
| N11 / cut stale version schema | Delegate complete response/gates to SPEC section 10 and REQ-PKG-06. |
| cc/N11 / cut independent code inventory | Generate/compare active SPEC section 7.5 keys; remove `W_TRIAGE_COVERAGE`, `E_PROVIDER_INTERRUPTED`, `W_STALE_TEMP`; add active `W_APPROVAL_UNUSED`. |
| N07 / cut universal exit-130 promise | Distinguish cooperative cancellation from forced native interruption; require OS evidence. |
| SHL-REV-03 / cut recovery-placeholder mode | Keep one atomic migration; failure blocks jobs, drops raw memory references and warns about original disk secrets. |
| SHL-REV-04 / cut credential UI/keychain proposals | Keep env-only credentials and tested terminal launch guidance. |
| SHL-REV-07 / cut automatic policy-proof claims | Machine input/key tests and named manual release attestations have separate outcomes. |
| N09 / cut full Plan progress payload | Bounded summary events; full Plans only through SPEC `plan` stdout; no chunk/reference protocol. |
| N03/N11 / cut run hash, mutable-cache authorization and extra cost/counter fields | Repeated per-file hashes on the same batch; display only SPEC's approved maximum cost and informational status. |
| Earlier cuts retained | No inherited shell code, URL fetching, output/media templates, tags, old router tuning, auto-installer or runtime pointer. |

Open: `SYNC-AFTER-DRAFT-3` gates cover final same-root/per-file authorization, approved versus informational status, summary/full-Plan framing, cost/pending shape, complete version/code fixtures and cooperative/forced cancellation. The current DRAFT-3 code-row set was regenerated and checked; actual JT/engine/OS/manual evidence remains required. No engine or test implementation was changed in this documentation task.
