# Packaging and release: v2.0.0

Design specification, 2026-11-09. Binding inputs: [brief](00_BRIEF.md), [decisions](01_DECISIONS.md), especially F1 and R8-R14. Requirement IDs below are stable. Local observations identify inspected repository code; external facts have official web citations. Proposed behavior is a requirement, not an assertion that implementation exists. Unconfirmed external claims are marked TODO-VERIFY.

## 1. Reuse audit

| ID | Inspected file | Disposition and reason |
|---|---|---|
| PKG-R01 | `main.ts` | Reuse lifecycle, ribbon, event registration and output-opening patterns. Rewrite startup, settings loading, dependency management and job ownership. Current unload does not cancel children; installation targets `markitdown[all]`. |
| PKG-R02 | `src/types/settings.ts` | Preserve compatible preference/history types through the migration below. Replace wrapper options, dependency status and result types with versioned engine contracts. |
| PKG-R03 | `src/converter/MarkitdownConverter.ts` | Rewrite as engine client. Current one-JSON-result parsing, wrapper flags, Azure fallback options and shell-side output mutation contradict R5-R10. |
| PKG-R04 | `src/services/ConversionService.ts` | Keep UI coordination, history and open-result behavior. Replace option injection and direct conversion with plan/consent/run coordination. |
| PKG-R05 | `src/utils/python.ts` | Keep argument-array spawning and UTF-8 environment setup. Replace global-package preference, unbounded buffering, inherited environment and installer. Add timeout, protocol framing and cancellation. |
| PKG-R06 | `src/utils/bundledScripts.ts` | Replace. Writing only missing scripts retains stale engine code after upgrades. Community distribution uses the explicit engine setup below. |
| PKG-R07 | `src/utils/bundledPythonScripts.generated.ts` | Generated derivative, when present; retire wrapper/router payload generation. Never hand-port generated code. |
| PKG-R08 | `src/utils/paths.ts` | Keep vault adapter discovery and relative-link behavior. Preserve filename tokens; engine owns final output validation and naming. Replace lexical containment with checks that handle symlinks and platform case rules. |
| PKG-R09 | `src/utils/history.ts` | Reuse bounded 100-entry list and display formatting. History remains UI history, never OCR cache evidence. |
| PKG-R10 | `src/utils/postprocess.ts` | Retire shell Markdown rewrites. Engine assembles summary frontmatter and migrated tags once. |
| PKG-R11 | `src/utils/fileTypes.ts` | Rewrite format lists from the engine capability contract. Audio/video must not remain advertised as v2 conversion inputs. |
| PKG-R12 | `src/utils/i18n.ts` | Keep keyed tables and applicable English/Korean strings; replace obsolete fallback/OCR-engine wording. Retain other translations only where unchanged and free, per R9. |
| PKG-R13 | `src/settings/SettingsTab.ts` | Reuse public `Setting` controls and applicable labels. Rewrite dependency/provider controls; remove persisted secrets, arbitrary plugin arguments and image-router tuning. |
| PKG-R14 | `src/settings/PluginArgsEditor.ts` | Drop; arbitrary wrapper arguments have no v2 contract. Do not reinterpret them as trusted commands. |
| PKG-R15 | `src/modals/FileConvertModal.ts` | Keep picker/UI pattern. Replace temp-in-output-folder writes and direct conversion with job staging and Plan display. |
| PKG-R16 | `src/modals/FolderConvertModal.ts` | Keep selection and recursive preference. Engine owns bounded discovery, member routing and scheduling; remove the shell conversion loop. |
| PKG-R17 | `src/modals/UrlConvertModal.ts` | Retire URL/YouTube execution for the file-focused 2.0 scope; keep its command as a compatibility notice. No implicit URL fetch through core. |
| PKG-R18 | `src/modals/SetupModal.ts` | Rewrite as interpreter/engine diagnostics and external setup instructions. Current Python 3.8+ text, global installer and private settings API calls are unsuitable. See PKG-O01. |
| PKG-R19 | `src/modals/SelfTestModal.ts` | Replace with offline engine health/triage check. Current router schema and missing community-install fixture directory are unsuitable. |
| PKG-R20 | `src/modals/BatchProgressModal.ts` | Reuse progress presentation; replace file-loop updates with engine events and actual cancellation. |
| PKG-R21 | `src/modals/HistoryModal.ts` | Reuse bounded history presentation and clear action; apply migration validation/redaction. |
| PKG-R22 | `src/modals/PreviewModal.ts` | Drop unused implementation: no caller found. Plan consent is separate from this post-conversion Save dialog. |
| PKG-R23 | `src/__mocks__/obsidian.ts` | Extend minimal mocks only for tested shell behavior; empty classes do not validate real Obsidian compatibility. |
| PKG-R24 | `src/__tests__/converter/MarkitdownConverter.test.ts` | Preserve secret-not-in-argv and failure-handling intent; replace obsolete wrapper/Azure assertions with protocol tests. |
| PKG-R25 | `src/__tests__/converter/e2e.test.ts` | Replace with packaged-engine integration. Current test returns successfully when engine sources are absent; required tests must fail on missing payloads. |
| PKG-R26 | `src/utils/__tests__/python.test.ts` | Keep spawn/error cases; replace preference for globally installed core with interpreter/venv/handshake cases. |
| PKG-R27 | `src/utils/__tests__/paths.test.ts` | Preserve containment/template cases; extend real-filesystem checks for symlinks, collisions and Windows paths. |
| PKG-R28 | `manifest.json` | Preserve `id=markitdown-flow`, name and author; set version 2.0.0, desktop-only and accurate description. Determine minimum app version by testing. |
| PKG-R29 | `versions.json` | Preserve existing entries; append 2.0.0 mapped to the tested minimum Obsidian version. |
| PKG-R30 | `.github/workflows/release.yml` | Rewrite. Current workflow has tag-only builds, `npm install`, mutable action tags, no test gates and no engine/lock attestation. Retain provenance intent. |
| PKG-R31 | `scripts/generate-bundled-scripts.mjs` | Retire old wrapper embedding; engine wheel/package is the canonical distributable. |
| PKG-R32 | `scripts/verify-roundtrip.mjs` | Replace with package-content/import smoke checks. It references `python/` and four exports, while the generator reads `engine/src/` and five exports. |
| PKG-R33 | `package.json`, `package-lock.json`, `esbuild.config.mjs`, `jest.config.js` | Keep npm lock, TypeScript/esbuild and Jest structure. Remove old generation hooks, pin Obsidian build API, synchronize 2.0.0 and use `npm ci`. Keep bundled CJS compatible with the tested minimum desktop app. |
| PKG-R34 | `styles.css` | Reuse applicable plugin-scoped modal/history styles; remove selectors for retired controls. |

## 2. Settings and command compatibility

**PKG-M01:** Replace `Object.assign(DEFAULT_SETTINGS, loadData())` with a validated, allowlisted migration. Missing `schemaVersion` means v1; write `schemaVersion=2`. Missing keys use v2 defaults; invalid values use safe defaults and a notice. A newer schema is read-only with an incompatibility notice. Migration runs before engine launch or installation.

Each row specifies the complete v1 top-level mapping. Unchanged names intentionally minimize migration work.

| ID | v1 `data.json` key | v2 key/action and user-visible change |
|---|---|---|
| PKG-M02 | `pythonPath` | Same key, bootstrap-interpreter preference only; never the conversion interpreter. Notice that execution uses the dedicated venv. |
| PKG-M03 | `enablePlugins` | Dropped. Notice: third-party core plugin loading is unavailable in 2.0. |
| PKG-M04 | `pluginArgs` | Dropped, including every entry's `key`/`value`. Notice: wrapper arguments were not imported; configure any command provider explicitly. |
| PKG-M05 | `docintelEndpoint` | Dropped. Notice: built-in Azure DocIntel/CU fallback was removed; external command configuration is manual. Never map it to an OCR API base URL. |
| PKG-M06 | `docintelCredential` | Dropped from memory after migration and from persisted state. Notice: set the chosen provider's credential in its documented environment variable. |
| PKG-M07 | `llmApiKey` | Dropped with the same environment-only notice; never silently enable a provider. |
| PKG-M08 | `outputPath` | Same key; empty retains `markitdown-output`. Reject destinations outside the vault with a notice. |
| PKG-M09 | `assetExtractionEnabled` | Same key; controls published media only. Internal extraction for triage/OCR is independent of this preference. |
| PKG-M10 | `assetSubfolderTemplate` | Same key, default `{filename}-assets`; reject unsafe folder names with a notice. |
| PKG-M11 | `inputBasePath` | Same key; preserve source-tree mirroring for valid selected inputs. |
| PKG-M12 | `enableBatchProgress` | Same key; hiding progress never disables consent, errors or cancellation access. |
| PKG-M13 | `enableContextMenu` | Same key. |
| PKG-M14 | `enableRecursiveConversion` | Same key; engine bounds still apply. |
| PKG-M15 | `outputFilenameTemplate` | Same key; retain `{filename}`, `{ext}`, `{date}`, `{datetime}` semantics. Validate final destinations and collisions. |
| PKG-M16 | `enableDragDrop` | Same key; drops enter planning, with no automatic remote OCR. |
| PKG-M17 | `enableAutoFrontmatter` | Dropped. Notice: minimal provenance frontmatter is always generated in v2. Existing notes are untouched. |
| PKG-M18 | `autoTags` | Same comma-separated string; trim/filter into tags at engine assembly. No shell postprocessing. |
| PKG-M19 | `conversionHistory` | Same key; validate and preserve the newest 100 entries in existing order. Nested mapping below. |
| PKG-M20 | `imagePipelineEnabled` | Dropped. Notice: legacy image-router toggles are replaced by per-unit Plans. |
| PKG-M21 | `ocrLang` | Dropped. Notice: Tesseract language codes do not configure the v2 provider; review its transcription settings. |
| PKG-M22 | `imagePipelineAdvancedConfig` | Dropped as a whole, including custom keys. Notice: local OCR ensemble/table/deskew/confidence tuning is unavailable in 2.0. |

**PKG-M23:** For `conversionHistory[]`, preserve `inputFile`, `outputFile`, `timestamp`, `success`, `processingTimeMs`, `assetsExtracted` with type checks. Preserve `error` only after secret redaction; substitute a generic legacy error if safe redaction cannot be established. Invalid entries are skipped with a count notice. Do not infer source hashes, OCR completion or approvals from history.

**PKG-M24:** Explicitly drop these nested advanced-config defaults: `ocr_engines`, `ocr_confidence_threshold`, `enable_ocr_ensemble`, `enable_table_extraction`, `preprocess_deskew`, `deskew_method`, `confidence_weight_engine_conf`, `confidence_weight_agreement`, `confidence_weight_length`, `confidence_weight_cleanliness`, `confidence_weight_stdev_inv`. Unknown top-level and nested fields are dropped with a count notice; never copy arbitrary values into backups or logs.

**PKG-M25:** Before replacing settings, save an allowlisted, sanitized v1 rollback snapshot inside the plugin directory. Omit credential fields and free-form plugin/advanced-config values; redact history errors. Persist the v2 candidate safely before committing migration completion; on failure retain the original and do not launch jobs. Never create an additional raw secret-bearing backup. Consolidate notices by requirement ID, store only their IDs/counts, and keep them visible until acknowledged. Document that existing external backups may still contain old keys.

**PKG-M26:** New defaults are `provider.type=none` and plan-only execution. Never import prior consent or command trust. Migration acceptance covers every row, missing/null/malformed values, interrupted save, repeat migration, unknown keys and downgrade; serialized settings and diagnostics must contain no credential values.

**PKG-M27:** Keep plugin ID and all six local command IDs exactly stable. Obsidian adds the plugin prefix; do not add it to `addCommand.id`. [Official command-ID requirement](https://docs.obsidian.md/community-directory/submission-requirements-for-plugins).

| ID | Existing local command ID | v2 behavior |
|---|---|---|
| PKG-C01 | `convert-file` | File selection, Plan, approved execution. |
| PKG-C02 | `convert-folder` | Bounded folder Plan and execution. |
| PKG-C03 | `convert-url` | Compatibility notice: download the source locally and use file conversion; URL/YouTube import is unavailable in 2.0. |
| PKG-C04 | `view-conversion-history` | Open migrated history. |
| PKG-C05 | `open-log-folder` | Open v2 plugin-local redacted logs; explain that historical `~/omnidata_logs` is retained. |
| PKG-C06 | `run-image-pipeline-selftest` | Run offline engine health/triage check, with a notice explaining the retired router test. No provider call. |

## 3. Engine distribution and compatibility

**PKG-E01:** Community installs retrieve `main.js`, `manifest.json`, and optional `styles.css`; an attached engine ZIP is not automatically installed. Ship `engine.zip` plus `engine.lock` for explicit external setup. ZIP contains the built `mdflow` wheel, the same lock, setup instructions and required license notices, never a relocated venv. [Obsidian installation assets](https://docs.obsidian.md/Plugins/Releasing/Submit%20your%20plugin).

**PKG-E02:** SetupModal diagnoses and displays the exact release's external setup instructions. Bootstrap creates `<plugin-dir>/runtime/<engine-version>-<lock-digest>/venv` at its final location. Community build must not invoke pip, install dependencies or self-update; PKG-O01 objects to that part of R10. Setup network activity is distinct from document-egress consent. [Developer policies](https://docs.obsidian.md/community-directory/developer-policies).

**PKG-E03:** Discovery probes the configured executable first, then `python3`/`python` and versioned executable candidates for 3.14 through 3.10; on Windows also probe installed versions through `py` without installing Python. Try 3.15 only as an explicitly selected experimental candidate. Use argument arrays, a five-second probe timeout, and report `sys.executable`, version and architecture. Reject versions outside `>=3.10,<3.16`, missing venv/pip, and unsupported lock targets. A failed explicit path is shown before offering alternatives. Existing global MarkItDown installations confer no preference.

**PKG-E04:** External bootstrap uses the selected interpreter's `-m venv`, then that venv's absolute `Scripts/python.exe` on Windows or `bin/python` elsewhere. Install the local engine wheel and `markitdown-gc==0.3.5` with the release lock, using `-m pip install --require-hashes -r engine.lock`; no `[all]`, global installation or unpinned upgrade. Lock every transitive dependency and wheel hash, including the engine; use environment markers and hashes for each advertised Python/OS/architecture target. Pip hash mode requires exact requirements and hashes for dependencies. [pip secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/).

**PKG-E05:** Build and validate wheel-only installations per target; never silently compile missing dependencies on an end user's machine. An unavailable wheel is a clear setup error. Python activation is unnecessary; venvs are generally nonportable, so recreate after a vault/plugin path move or missing base interpreter. [Python venv documentation](https://docs.python.org/3/library/venv.html).

**PKG-E06:** Upgrade by creating a new version/lock directory at its final location, installing externally, running `pip check`, handshake and offline smoke conversion, then switching a plugin-local active-runtime pointer atomically. Retain the prior working directory and pointer for rollback. No in-place dependency updates, renaming a completed venv, or replacing a runtime while jobs use it. Setup failure leaves the previous pointer unchanged.

**PKG-E07:** Before accepting jobs, call `<venv-python> -m mdflow --handshake`. One JSON response reports `protocol_version`, `engine_version`, `plugin_version_range`, `core_distribution`, `core_version`, `triage_schema_version`, `lock_digest`, Python version and capabilities. For 2.0.0: protocol 1, triage schema 1, distribution `markitdown-gc`, core 0.3.5, engine 2.0.0 and exact release lock. The plugin checks its own manifest version against the engine range; initial engine range is `>=2.0.0,<2.1.0`. Relaxing accepted engine versions requires passing compatibility evidence, not matching major versions alone.

**PKG-E08:** Invalid handshake, wrong package identity, unexpected core version/schema, missing capability or lock mismatch blocks jobs and opens diagnostics. Never fall back to global Python or upstream `markitdown`. Missing engine prevents conversion but not settings/history access.

**PKG-E09:** Public availability, immutable artifact hashes and wheel coverage for `markitdown-gc` 0.3.5 are TODO-VERIFY. Local metadata reports 0.3.5 and `>=3.10,<3.16`; the supplied local GUIDE/source were inspected. PyPI web verification failed and the connected GitHub file lookup returned 404; neither proves public installation will work. Resolve this before a public release, including the engine's downloadable wheel source. Python 3.11-3.13 install/handshake smoke evidence is required before advertising the full interpreter range.

## 4. Shell and engine boundary

**PKG-S01:** Shell owns Obsidian lifecycle, settings migration, selections, vault UI, Plan presentation, consent response, event display, history and process supervision. Engine owns sniff/triage, classification, bounds, Plan creation, conversion, ledger, rendering, providers, assembly and publication. Shell does not reconstruct unit selection, alter Markdown or call a provider directly.

**PKG-S02:** Spawn the absolute venv interpreter with argument arrays, `shell:false`, hidden Windows subprocess windows, a scrubbed environment and UTF-8. Supply only explicitly selected provider credentials by environment; configuration carries environment-variable names, never key values. No raw stderr or provider exceptions reach notices, history or logs.

**PKG-S03:** Protocol 1 uses UTF-8 JSON-lines on stdout, diagnostics on stderr, and JSON-lines controls on stdin. Event envelope: `{protocol_version, job_id, seq, type, payload}`. Required event types: `plan`, `progress`, `approval_required`, `result`, `error`, `cancelled`. Controls: `approve` with the engine Plan hash, or `cancel`, bound to `job_id`. Buffer across split UTF-8 characters/chunks and CRLF; cap a line at 1 MiB. Unknown required events, malformed/oversized lines or nonmonotonic sequence numbers fail the job. A closed process without one terminal event is failure, never success.

**PKG-S04:** Consent modal shows source identity, selected unit IDs/count, cache hits versus pending sends, provider/model, actual destination, sensitive-glob hits, estimated cost/currency and maximum spend or request bound. Unknown estimates are labeled unknown, never zero. Default action is cancel/keep Plan. Any Plan/source/destination/unit/cap change invalidates approval. Engine revalidates approval before every egress adapter, including trusted commands; shell confirmation alone is insufficient. Threshold >20 units and sensitive hits remain explicit acknowledgments per R6. Cache hits cause no new provider call.

**PKG-S05:** Cancel button, plugin unload and parent-input closure stop scheduling and cancel active requests. Send cooperative cancel, allow five seconds for checkpoint/cleanup, then terminate engine and owned command descendants using tested OS-specific handling. Record unfinished units as retryable and preserve completed cache entries. Cancellation cannot retract an already sent request or guarantee zero charge. Do not equate Node `child.kill()` with descendant cleanup. [Node child-process API](https://nodejs.org/api/child_process.html).

**PKG-S06:** Use per-job staging under the plugin directory, retaining original source path/identity for sensitive matching. Keep output inside the validated vault destination; publish completed artifacts atomically and report collisions. On cancel/failure, remove owned staging after descendants exit; never delete sources or existing outputs. Core URL/audio/plugin paths that could bypass the Plan are disabled in 2.0.

## 5. CI and release jobs

These are required implementation gates; no test results are claimed by this document.

| ID | Job | Required coverage |
|---|---|---|
| PKG-T01 | Jest/build | Windows, Ubuntu, macOS; pinned Node 22 build environment, `npm ci`, typecheck/build and Jest. Test all migration/command rows, chunked JSON-lines, consent changes, redaction and cancellation. |
| PKG-T02 | pytest | Each of Windows/Ubuntu/macOS x Python 3.10/3.14: six required jobs against the release lock. Class routing, real/generated fixtures, protected/malformed/oversize inputs, partial failure, inline ordering and cache invalidation. |
| PKG-T03 | Experimental pytest | Each OS x Python 3.15, `continue-on-error` only for these three jobs. Report failures visibly; exclude them from release readiness claims. |
| PKG-T04 | Core contract | Separate job set over the six required OS/Python cells. Initial declared core range `>=0.3.5,<0.3.6`; test pinned 0.3.5 and the newest published version satisfying that range, deduplicating equal versions. Reject schema !=1; assert candidate IDs, media-byte mapping, PDF per-page behavior, output/error channels and offline operation. Public artifact access is PKG-E09's gate. Expand the range only after evidence. |
| PKG-T05 | Packaged integration | On all required OS/Python cells, bootstrap externally from release-format artifacts into an empty plugin-shaped directory with spaces/non-ASCII path components. No source-tree imports or global core. Check handshake, TXT conversion, mixed-document mock OCR, zero provider calls on rerun, cancellation/restart and runtime rollback. |
| PKG-T06 | Release build | Depends on all required jobs and acceptance evidence. Test/package/attest one candidate from the exact release commit; upload a draft release. Publish those same bytes after review. No live provider key is needed for required CI; optional real-API smoke needs the separately approved key/quota. |

**PKG-T07:** Pin all external actions to reviewed full commit SHAs, including checkout, setup-node, setup-python, artifact upload/download, attestation and release helpers; retain readable version comments. Use read-only default permissions and no release secrets for PR jobs. Grant `id-token:write` and `attestations:write` only to attestation, and `contents:write` only to release publication. Actual action SHAs, runner labels/architectures and exact Node patch are TODO-VERIFY at implementation; no fabricated SHAs. [GitHub action security guidance](https://docs.github.com/en/actions/reference/security/secure-use).

**PKG-T08:** Attest `main.js`, `manifest.json`, `styles.css`, `engine.zip`, `engine.lock` and `SHA256SUMS`. Preserve attestation bundles with the release; verify each subject against this repository and expected workflow/commit before publication. GitHub documents binary provenance and `gh attestation verify`; provenance does not replace tests or attest dependency safety. Repository/plan availability is TODO-VERIFY. [GitHub attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

**PKG-T09:** Release acceptance requires R13's evidence: 100% classification on labeled fixtures, zero unit loss/duplication and zero provider calls on an idempotent rerun. Missing required fixtures/artifacts fail rather than skip. Record evidence under the acceptance checklist; do not assert a numeric score without it.

## 6. Community-directory checklist

| ID | Release checklist item | Official basis |
|---|---|---|
| PKG-OCD01 | Preserve `markitdown-flow`; validate all required manifest fields, `version=2.0.0` and tested `minAppVersion`. | [Manifest schema](https://docs.obsidian.md/Reference/Manifest) |
| PKG-OCD02 | Description <=250 characters, sentence case, period, no emoji/special characters. Proposed: `Convert local documents to Markdown with OCR planning and selective transcription.` Remove old audio/Azure fallback promises. | [Submission requirements](https://docs.obsidian.md/community-directory/submission-requirements-for-plugins) |
| PKG-OCD03 | Preserve local command IDs without adding the plugin ID; remove sample commands/classes and unused sample code. | [Submission requirements](https://docs.obsidian.md/community-directory/submission-requirements-for-plugins) |
| PKG-OCD04 | Keep `isDesktopOnly:true` for Node subprocess/filesystem use; remove mobile claims. | [Submission requirements](https://docs.obsidian.md/community-directory/submission-requirements-for-plugins) |
| PKG-OCD05 | README discloses remote OCR destinations/purpose, selected images leaving the machine, provider account/cost requirements, external file access and explicit external dependency downloads. Explain plan-only defaults, local cache retention and command trust without claiming env vars guarantee secrecy. | [Developer policies](https://docs.obsidian.md/community-directory/developer-policies) |
| PKG-OCD06 | Include root README/LICENSE, source and required dependency notices; remove runtime self-install/update behavior under PKG-O01. | [Developer policies](https://docs.obsidian.md/community-directory/developer-policies) |
| PKG-OCD07 | Release tag exactly `2.0.0`, matching manifest; attach standard assets individually. Additional ZIP/lock are manual setup assets. | [Release/submission guide](https://docs.obsidian.md/Plugins/Releasing/Submit%20your%20plugin) |
| PKG-OCD08 | Treat this as an existing listing update, not a duplicate initial submission. Current initial submissions use the Community site; do not prescribe the obsolete list-PR workflow. Confirm owner access and listing update behavior: TODO-VERIFY. | [Current submission guide](https://docs.obsidian.md/Plugins/Releasing/Submit%20your%20plugin) |

## 7. Release, rollback and cleanup

| ID | Procedure and required evidence |
|---|---|
| PKG-L01 | Resolve PKG-O01 and external TODO-VERIFY gates before release. Link every applicable acceptance criterion to passing evidence; retain offline smoke evidence if live OCR was not authorized. |
| PKG-L02 | Freeze the candidate; synchronize plugin manifest/package and engine version at 2.0.0. Append the tested app minimum to `versions.json`; retain all historical entries. Verify exact core lock and plugin/engine handshake. Keep existing 1.0.8 release/tag; no additional archive tag is necessary. |
| PKG-L03 | Produce draft artifacts, hashes, provenance and migration notes: external setup, removed Azure/router/audio/URL behavior, credential environment setup and retained command aliases. Confirm payloads match the tested candidate and contain no credentials or local cache. |
| PKG-L04 | In isolated desktop vaults on Windows/macOS/Linux, test fresh standard-asset install plus documented external engine bootstrap, then upgrade a representative v1 settings fixture. Check six commands, en/ko UI, Plan cancellation, mock OCR ordering, idempotent rerun, restart and rollback. Test the claimed minimum and current stable Obsidian; versions are TODO-VERIFY until recorded. |
| PKG-L05 | Publish the reviewed 2.0.0 release/tag and matching default-branch metadata through the normal release process. Afterwards install/update through the actual community listing, compare downloaded asset hashes and verify engine setup, handshake, migration, local conversion and zero unexpected egress. Record platform/app/runtime versions and outcomes. |
| PKG-L06 | Runtime rollback: cancel jobs and select the retained compatible runtime; re-handshake before execution. Plugin rollback: disable plugin, preserve current settings/cache, manually restore verified 1.0.8 standard assets and sanitized v1 snapshot, then re-enable. Reconfigure credentials externally as appropriate; snapshot deliberately omits secrets. Never feed v2 settings to v1 or share its global-package environment with v2. For a public defect, retain immutable prior artifacts and publish a corrected higher patch release; do not retag or claim automatic downgrades. |
| PKG-L07 | After verification, remove owned failed staging and obsolete generated wrapper artifacts only within verified plugin-local paths, after processes exit. Retain previous working runtime through the rollback window. Cache contains transcriptions: retain by default for R4, offer explicit clear, and disclose that clearing may require paid retranscription. Do not delete historical logs, old outputs, source files, external backups or rollback material silently. Retain released locks/hashes/attestations and record cleanup completion. |

## Objections

**PKG-O01 - R10 SetupModal installation conflicts with community policy.** Obsidian says plugins must not "Install or update themselves or their dependencies." [Exact policy](https://docs.obsidian.md/community-directory/developer-policies). The text provides no user-click/consent exemption. Proposed resolution: retain the dedicated plugin-local venv and pinned engine, but have users run the documented bootstrap/upgrade externally; SetupModal only diagnoses and guides. A plugin-run installer remains blocked for the community build unless an applicable official clarification establishes permission. This is a reasoned objection to R10, not a claim that R10 has already been amended. All other binding decisions are retained.
