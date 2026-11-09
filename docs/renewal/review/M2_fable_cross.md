# M2 cross-cutting MECE audit (Fable)

Reviewer: cc.fable. Date: 2026-11-09. Workspace = repo at `f9d3d14` (engine 446 pass, shell 230 jest, tsc clean, build OK as reported by the orchestrator; not re-run here). Read-only: `git ls-files`, `ls`, file reads and greps. No code edits, no git.

Inputs read: `20_SHELL.md`, `25_PACKAGING.md`, `10_SPEC.md` sections 7-10, `01_DECISIONS.md`, `00_BRIEF.md`, `90_ACCEPTANCE.md`, `30_TESTPLAN.md` (fixture/JT rows), `README.md`, `manifest.json`, `versions.json`, `CHANGELOG.md`, `engine/BOOTSTRAP.md`, `PACKAGING_VERIFICATION.md`, `HANDOFF.md`; all of `shell/src/**`; shell tests JT-02/08/14/16/17 and the FX-71 manifest plus recorded `consent-5-approved.*`, `version.json`, `usage-error.stderr.json`; engine `cli.py`, `report.py`, `approve.py`, `redact.py`, `plan.py`, `transcribe.py`, `assemble.py` (escaping/postprocess), `orchestrate.py` (approval, signals, run end), `providers/*`; `.github/workflows/*`, `tools/build_engine.py` subjects, `engine/pyproject.toml`.

Severity: BLOCKER = release-blocking MUST violation or user harm; MAJOR = MUST/doc-code mismatch with user-visible effect; MINOR = drift, dead code, UX.

---

## 1. Shell docs <-> code (20_SHELL REQ-SHL-* vs `shell/src`)

| REQ | Status | Evidence |
|---|---|---|
| SHL-01 clean room | OK | JT-01 input/import checks; esbuild reads only `shell/`. Manual R15 attestation still required (MAN-01). |
| SHL-02 six commands, one desktop guard | OK (1 MINOR) | `ui/commands.ts` ids; `main.ts:96` single guard; JT-02. Row "Explain router retirement" for `run-image-pipeline-selftest` has no notice (X-12). |
| SHL-03/04 migration map | OK | `pure/settings.ts` 21 keys, allowlisted schema 2; JT-03/04. **Newer-schema read-only is broken by `saveSettings`** (X-03). |
| SHL-05 atomic migration, snapshot | OK (1 MAJOR) | `pure/persist.ts`, `ui/data-store.ts` temp+rename. Failure path later overwritten by settings tab (X-03). README names the snapshot `data.v1.json.bak`; code writes `data.v1.json` (X-07). |
| SHL-06 env-only credentials, scrub | PARTIAL | `pure/env.ts` baseline + provider vars + UTF-8; key presence only. **Configured `provider.baseUrl` never reaches the engine** (X-02). |
| SHL-07 history | OK (1 MINOR) | `pure/history.ts` cap/sort/outcome; `inputFile` is a joined list of absolute paths (X-18). |
| SHL-08 entry points | PARTIAL | Ribbon/menu/drop share the coordinator (JT-08). Drop "selection confirmation" is a Notice that always returns true (`main.ts:182-186`) (X-06). |
| SHL-09 destination, busy, progress details | PARTIAL | `ui/output-path.ts` real-path containment, Windows case fold, symlink per component; busy check. No revalidation before the `run` spawn (X-10). **No progress UI exists**; `ui/progress.ts` is only used by JT-09 (X-01). |
| SHL-10 diagnostics-only setup | OK (1 MAJOR) | `process/setup.ts` probes only; instructions rendered. Settings tab probes on every keystroke (X-04). |
| SHL-11/12 SPEC-only protocol, argv array | OK | `process/launcher.ts` `shell:false`, `windowsHide`, cwd fixed, `-o` = validated vault dir, cache `<plugin-dir>/cache`; JT-11/12 replay FX-71. |
| SHL-13 framing, spool | OK | `pure/framing.ts` 64 KiB, CRLF, unknown `ev` ignored, summary-only `approve_required`; `pure/spool.ts` owned nonce names, stale recovery. |
| SHL-14 one modal | OK (1 MINOR) | `ui/consent-modal.ts` literal text, Keep pending default, Escape = none; JT-14 hostile path. Prompts also for fully cached files (X-08). |
| SHL-15 yes-file replay | OK | `coordinator.ts:262-270` writes `<plugin-dir>/consent/yes-*.txt`, `--approved-by plugin:modal`, removed in `finally`; JT-15. |
| SHL-16 Cancel visible, 5 s grace | **FAIL** | `EngineRun.cancel` and JT-16 are correct, but nothing in the UI calls `coordinator.cancel()` except `onunload`. The user cannot cancel a running conversion (X-01). |
| SHL-17 version gate | OK (1 MINOR) | `process/version-gate.ts` complete field set, ranges; the "actual" FX-71 response is from Python 3.15 and is blocked by `RELEASE_LOCK` (X-11). |
| SHL-18 logs | OK | `process/log.ts` five x 1 MiB, allowlisted fields, home/vault redaction. |
| SHL-19 i18n | OK | `pure/codes.ts` + `pure/i18n.ts`; JT-SHL-19-01 set equality. |
| SHL-20 selftest | OK | `process/selftest.ts` spawns exactly `version` then `selftest`. |
| SHL-21 traceability | OK (1 MINOR) | `tools/trace.py` parses `req()` from test files directly; `pure/trace.ts` export is unused in production (S-07). |

## 2. Shell <-> engine contract (argv/flags/events vs `cli.py`/`report.py`, FX-71)

Verified consistent: subcommands `plan|run|version|selftest`; options emitted by `buildSpawnRequest` all exist in `cli.py:_parser`; `--yes-file` parse rules (`approve.parse_yes_lines` == `launcher.parseYesFile`); `--approved-by plugin:modal` recorded in `files[].consent.by` (fixture `consent-5-approved.stdout.json`); progress event names/fields in `framing.ts` match SPEC 7.3 and the recorded `consent-5-approved.progress.jsonl`; `run_end` fields match `cli.py:261-265`; exit map `outcomeFor` matches SPEC 10.3; startup error object `{"error":{"code","message"}}` matches `cli.py:_error` and `usage-error.stderr.json`; `version` keys match `orchestrate.tools()` + `cli.py:219`; report decoder tolerates extra fields (`key_id` in issues, top-level `issues`).

Gaps:

- **X-02 (MAJOR)** `settings.provider.baseUrl` is persisted, editable in the settings tab and copied into the job snapshot (`launcher.ts:96`) but never passed to the engine. The engine reads only `MDFLOW_BASE_URL` (`providers/__init__.py:84`), which the shell forwards from the host environment. A user who sets a proxy/Ollama base URL in settings sends rasters to `https://api.openai.com/v1` (or whatever the host env says). SPEC REQ-SEC-01 explicitly allows persisted `base_url`. Fix: in `buildSpawnRequest`, for `openai-compatible` set `env.MDFLOW_BASE_URL = snapshot.provider.baseUrl` (settings win; do not forward the host value), add a JT-12 assertion that the Plan `destination` equals the canonical form of the configured URL, and state this in README and REQ-SHL-06.
- **X-08 (MINOR)** `coordinator.ts:248` prompts when `approved.max_requests > 0`; the engine requires consent only when `requests_to_send > 0` (`approve.py:15`, SPEC 8.4). FX-71 `consent-4-plan-warm` file 1 has `max_requests 2, requests_to_send 0`: the modal appears for a fully cached file and the approved hash is reported `W_APPROVAL_UNUSED`. Fix: filter on `approved.provider.egress && status.requests_to_send > 0`; list the rest as informational.
- **X-09 (MINOR)** The engine emits `warning`/`error` events with `file: null` for run-level issues (`orchestrate.py:482,489`, `cli.py:260`); `framing.ts:135` requires a string, so a valid run ends with `shell.PROTOCOL`. SPEC 7.3 shows only string examples. Fix: SPEC 7.3 `file: string|null` for run-level issues; shell accepts null.
- **X-11 (MINOR)** FX-71 was recorded from `mdflow 2.0.0.dev0` on Python 3.15.2 (manifest). `version.json` is blocked by `RELEASE_LOCK`; JT-17 widens the policy to pass. Re-record from the built 2.0.0 wheel on Python 3.14 before release (REQ-PKG-09 "final fixtures"); keep the 3.15 file as a derived variant.
- **X-14 (MINOR)** `cli.py:215` runs `_check_core` before dispatch, so `version` exits 1 with `E_CORE_VERSION` when Core is missing; the shell then reports `blocked (exit)` instead of `core`. Let `version` print JSON with `"markitdown-gc": "unavailable"` (already produced by `tools()`), and gate only `run/plan/selftest`.

## 3. Security

Verified: no secret on argv (`buildSpawnRequest` emits model, globs, paths only); no key field in schema 2 (`pickProvider` allowlists `name/model/baseUrl`; JT-04/06 sentinels); child env is the SPEC 8.2 allowlist plus `PYTHONUTF8/PYTHONIOENCODING` plus the four `MDFLOW_*` names only for `openai-compatible` (`PYTHONPATH` excluded); logs carry `ts/stage/code/count/status` only; diagnostics copy redacts home/vault; migration snapshot allowlists and scrubs credential values and legacy error text; `data.json` writes go through temp+rename; yes-file and spool are owned, mode 0600/0700, removed in `finally`; destination validation uses real paths, per-component symlink checks, Windows case folding, rejects absolute/`..`/dot segments; nonrecursive selection skips hidden/symlink/dir entries. Engine: `redact.py` masks `*KEY*/*TOKEN*/*SECRET*/*PASSWORD*` values and `Authorization`, truncates to 500; `_Parser.error` never echoes argv; `openai_compat.canonical_destination` enforces https (loopback http only), rejects userinfo/query/fragment, disables redirects, single explicit proxy; prompt `p1` is constant and tells the model the image is data (`transcribe.py:63-66`); provider output goes through `postprocess_text` (fence strip, 200k cap) and `esc_text/esc_attr/esc_head` so `<!--`/`-->` cannot close provenance comments; command provider requires `--trust-command`, `--command-egress`, `--model`, uses `shell=False`, argument-wise substitution, allowlisted env, 4 MiB cap, kill on timeout. No telemetry: no `fetch`/`requestUrl`/`XMLHttpRequest` in `shell/src`.

Findings:

- **X-04 (MAJOR)** `ui/settings-tab.ts:32-37` saves `enginePython` on every keystroke and `main.ts:195-197` spawns `<typed prefix> -m mdflow version` each time. Partial paths are executed as programs (e.g. `C:\tools\rm` while typing `C:\tools\rmdir-tool\python.exe`). REQ-SHL-10 allows probing only the configured interpreter. Fix: accept the value on blur/Enter, require `isAbsolutePath`, probe once; same debounce for `outputPath`.
- **X-10 (MINOR)** REQ-SHL-09 requires revalidating the destination immediately before spawn. `submit` validates once; the `plan` + modal can take minutes before `run` spawns (`coordinator.ts:281`). Fix: re-run `resolveDestination` in `runJob` before `execute('report')` and refuse on mismatch with `snapshot.outDir`.
- **X-02** above is also a security finding: the displayed destination comes from the engine Plan, so the modal is honest, but the user's configured endpoint is silently ignored.
- **X-20 (MINOR)** `cache/`, `spool/`, `consent/` and `logs/` live under `<vault>/.obsidian/plugins/markitdown-flow/`; Obsidian Sync with "installed community plugins" enabled, or a cloud-synced vault, replicates transcriptions and temporary reports. Disclose in README (ties to X-07) or move cache/spool under the OS temp/app-data directory.

No BLOCKER-level secret leak, injection or containment defect found.

## 4. Obsidian policy and submission rules

| Rule | Result |
|---|---|
| `isDesktopOnly: true`, id `markitdown-flow`, version 2.0.0, `minAppVersion` 1.14.4 with `versions.json` entry | OK (`manifest.json`, `versions.json`). |
| Description <= 250 chars, ends with period, no slogans | OK (90 chars, equals REQ-PKG-15 candidate). |
| Six frozen command IDs, no `markitdown-flow:` prefix, names without plugin name | OK (`ui/commands.ts`, `i18n.ts` command strings). |
| No self/dependency install or update | OK (`process/setup.ts` renders text; only `--version`/`version`/`selftest` spawns). |
| No client telemetry | OK (no network API in `shell/src`; engine REQ-SEC-08). |
| README R16 disclosures present | Headings present (network/purpose, outside-vault, telemetry, account/key/cost, migration). **Content errors** (X-07). |
| MIT credit for historical contributors and Microsoft MarkItDown | OK (README last section, LICENSE). |
| Release notes | `CHANGELOG.md` still describes v1 0.1.0 only (X-16). |
| Electron usage | `node-apis.ts:125-127` uses `electron.remote` / `@electron/remote` for file dialogs (X-05, X-17). |
| Long work in `onload` | `main.ts:121` awaits a version probe up to 5 s before registering commands (X-15). |

Findings:

- **X-07 (MAJOR, R16 accuracy)** README: (a) "sanitized rollback snapshot `data.v1.json.bak`" but the shell writes `data.v1.json` (`persist.ts:137`, 20_SHELL REQ-SHL-05, REQ-PKG-20); (b) "using `MDFLOW_MODEL` and `MDFLOW_API_KEY`": no `MDFLOW_MODEL` exists; the model is the settings value passed as `--model`; (c) the Base URL setting is undocumented and currently inert (X-02); (d) the plugin cache is described under "Outside-vault access" but is inside the vault's plugin folder and may be synced (X-20). A named R16 reviewer "matches configured behavior" would fail today.
- **X-05 (MAJOR)** `pickFiles/pickFolder` return `null` when no dialog is available; `convert-file`, `convert-folder` and the ribbon then do nothing without any notice (`main.ts:151-156`). JT-02/08 inject fake pickers, so this is untested against the real app. Fix: fall back to a hidden `<input type="file" multiple>` / `webkitdirectory` element (public DOM API; Electron exposes `File.path`), and notify when neither picker is available. Add to MAN-04 rehearsal.
- **X-17 (MINOR)** `electron.remote` is removed upstream since Electron 14 and only works because Obsidian re-exposes it; a reviewer may flag it. Same fix as X-05 removes the dependency.
- **X-15 (MINOR)** Do not await `refreshGate()` in `onload`; probe lazily on first submit or in the background.

## 5. User-goal fit (classify -> selective OCR with consent, provenance, no re-transcription, markitdown-gc)

Engine/CLI: fits. T/S/M labels from Core triage (`classified` events in FX-71: `memo.txt` T/convert_only, `sub/a.pdf` M, `3분기 결산.pdf` S); only candidate units are rendered and sent (`sub/a.pdf` 4 pages, units p2/p4, 1 request); consent is per-file plan hash with `plan` -> `--yes-file` replay; provenance in frontmatter plus `## OCR pN (provider, model, date)` blocks; warm rerun shows `cached` units and `provider_calls 0` (`consent-6-warm`); `markitdown-gc` 0.3.5 range gated at startup and in `version`.

Plugin: the path works for `none` and for `openai-compatible` when the host env already carries the right `MDFLOW_*` variables, with these gaps:

- **X-01 (BLOCKER)** No Cancel control and no progress display. REQ-SHL-16 ("Keep Cancel visible even with progress details hidden") and REQ-SHL-09 ("Progress details show engine stage, file counts and unit outcomes") are MUST. `coordinator.cancel()` is reachable only through `onunload`; `EngineRun.onEvent` has no subscriber; `ui/progress.ts` and the `enableBatchProgress` setting are dead in production. A user who approves a 200-page remote OCR cannot stop it without disabling the plugin. Fix: a status-bar item or small modal created by the coordinator on `submit` showing `summarizeProgress(events)` (details only when `enableBatchProgress`), always with a Cancel button bound to `coordinator.cancel()`; add a JT asserting the button exists while a job is active and that clicking it calls cancel before launch, in modal and during run.
- **X-02** (above): configured endpoint ignored.
- **X-05** (above): picker may silently do nothing.
- **X-06 (MAJOR)** Drop confirmation is a Notice (`main.ts:182-186`), not a confirmation; REQ-SHL-08 requires showing the selection before work. Fix: a small modal listing the dropped paths with Convert/Cancel; `FilePicker.confirmSelection` already has the right shape and JT-08 already exercises it.
- **X-03 (MAJOR)** REQ-SHL-03 says newer schemas are read-only and REQ-SHL-05 says a failed migration must leave the original file untouched. `main.ts:109` falls back to `defaultSettings()` in memory and `saveSettings` (`main.ts:249-258`) writes them to `data.json` on any settings-tab change, overwriting a newer schema or the unparseable original. Fix: when `outcome.jobsBlocked` or `outcome.result === null`, make `saveSettings` refuse with `shell.SETTINGS` and do not register the settings tab writers (or render it read-only).
- **X-13 (MINOR)** `runOptions` (dpi, min priority, max units, approve threshold, sensitive globs) have no settings UI; R6/D4 "user sensitive globs" are reachable only by hand-editing `data.json`. Add controls or document the limitation.
- **X-12 (MINOR)** `run-image-pipeline-selftest` shows only pass/RUNTIME; REQ-SHL-02 row promises a router-retirement explanation.
- **X-16 (MINOR, docs)** 30_TESTPLAN JT-15 and 90_ACCEPTANCE G-07 still say "repeated `--yes`" (code and 20_SHELL use `--yes-file`); 30_TESTPLAN FX-60 cites `tools/mutate.py`, which does not exist; SPEC 8.2 cites `docs/providers/*.md` (absent; the R7 `command` recipe for `markitdown-gc -d`/peerhub is undocumented); README has no CLI usage section (`run/plan/--yes-file/classify`), so CLI users must read the SPEC; `HANDOFF.md` is stale (227/229 jest, 7 tsc errors).

## 6. Simplicity (VerySimpleGuide): delete or merge

| ID | Item | Action |
|---|---|---|
| S-01 | `shell/src/pure/argv.ts` duplicates `launcher.buildSpawnRequest` and still emits only repeated `--yes` | Delete; point JT-04 at `buildSpawnRequest`. |
| S-02 | `shell/src/pure/errors.ts` (`NotImplementedError`, red-phase marker) | Delete (unused). |
| S-03 | Barrels `pure/index.ts`, `process/index.ts`, `ui/index.ts` | Delete (no importer in src or tests). |
| S-04 | `launcher.Authorization` `yes` variant and the `--yes` branch of `approvedHashesIn`; REQ-SHL-15 says the shell uses only `--yes-file` | Remove the variant. |
| S-05 | Test oracles in production source: `invocationViolations`, `replayInvariantArgs`, `approvedHashesIn`, `parseYesFile`, `SPEC_OPTIONS` (includes command-provider flags the shell never emits) | Move to `shell/test/fixtures/protocol.ts`. |
| S-06 | `history.RunFacts.outputsCreated` always 0 | Remove field. |
| S-07 | `pure/trace.ts` `buildTraceExport` used only by JT-21; `tools/trace.py` reads `req()` from test files | Delete or make `trace.py` consume the export (pick one). |
| S-08 | `env.environmentDiagnostics` unused in production | Use it in SetupModal (presence of all four `MDFLOW_*` names) or delete. |
| S-09 | `log.ts` private `joinPath` duplicates `ui/output-path.joinPath` | Reuse the platform-aware one. |
| S-10 | `main.ts:207` `this.load()` inside `onload` (test convenience) | Remove; tests call `plugin.load()`. |
| S-11 | `coordinator.submit(_entry)` unused parameter; `EngineRun.onEvent` unused until X-01 is fixed | Drop or wire. |
| S-12 | `.gitignore` v1 remnants (`python/__pycache__/`, `src/utils/bundledPythonScripts.generated.ts`, `clean-release/`, `release/`, `test-extract/`, duplicate `main.js`, scrambled comments) | Rewrite to the v2 set. |
| S-13 | `CHANGELOG.md` v1-only; `HANDOFF.md` stale; `00_BRIEF.md` still "DRAFT-1 not approved" | Add 2.0.0 entry; delete or refresh HANDOFF; mark BRIEF superseded by 01_DECISIONS. |
| S-14 | `cli._provider_list` hard-codes `openai-compatible` destination and retries separately from `providers/*` meta | Derive from provider classes (static meta) to keep one source. |
| S-15 | `report.publish(report_path=...)` parameter unused (`cli.py` writes the report itself) | Remove parameter. |

Engine code otherwise reads as single-purpose modules; no duplicated classification or hashing logic found across `plan.py`/`ledger.py`/`approve.py`.

---

## 7. Consolidated findings

| ID | Sev | Location | Defect | Fix |
|---|---|---|---|---|
| X-01 | BLOCKER | `shell/src/main.ts`, `ui/coordinator.ts`, `ui/progress.ts` | No Cancel control or progress UI; REQ-SHL-09/16 MUST unmet; `enableBatchProgress` dead | Status-bar/modal with Cancel bound to `coordinator.cancel()`, progress from `summarizeProgress`; new JT |
| X-02 | MAJOR | `process/launcher.ts:137`, `pure/env.ts:76-78` | `provider.baseUrl` never reaches engine; host `MDFLOW_BASE_URL` or default wins | Set `MDFLOW_BASE_URL` from settings for `openai-compatible`; assert Plan destination; README/REQ-SHL-06 |
| X-03 | MAJOR | `main.ts:109,249-258` | Newer schema / failed migration overwritten by settings-tab saves | Refuse `saveSettings` when `jobsBlocked`/`result===null`; read-only tab |
| X-04 | MAJOR | `ui/settings-tab.ts:32-37`, `main.ts:195-197` | Per-keystroke save and spawn of partial interpreter paths | Commit on blur/Enter, require absolute path, probe once |
| X-05 | MAJOR | `process/node-apis.ts:125-131`, `main.ts:151-156` | File/folder pickers depend on `electron.remote`; silent no-op if absent; untested in real app | DOM `<input type=file>` fallback + notice; MAN-04 check |
| X-06 | MAJOR | `main.ts:182-186` | Drop "confirmation" is a Notice returning true | Confirmation modal with Convert/Cancel |
| X-07 | MAJOR | `README.md` | R16 inaccuracies: `data.v1.json.bak`, `MDFLOW_MODEL`, undocumented/inert Base URL, cache location/sync | Correct text; add CLI usage; re-review MAN-02 |
| X-08 | MINOR | `ui/coordinator.ts:248` | Consent prompt keyed on `max_requests` instead of `requests_to_send` | Filter on egress and `requests_to_send > 0` |
| X-09 | MINOR | `orchestrate.py:482,489`, `cli.py:260`, `framing.ts:135`, SPEC 7.3 | Run-level events carry `file: null`; shell rejects | Allow null in SPEC and decoder |
| X-10 | MINOR | `ui/coordinator.ts:281` | Destination not revalidated before `run` spawn | Re-run `resolveDestination` before replay |
| X-11 | MINOR | `shell/test/fixtures/fx71/*`, JT-17 | Recordings from 2.0.0.dev0 on Python 3.15; "actual response" blocked by release policy | Re-record on 3.14 from the 2.0.0 wheel |
| X-12 | MINOR | `main.ts:166-170`, 20_SHELL row | Selftest lacks router-retirement explanation | Add notice or amend row |
| X-13 | MINOR | `ui/settings-tab.ts` | No UI for `runOptions`/sensitive globs | Add controls or document |
| X-14 | MINOR | `cli.py:215-221` | `version` fails with exit 1 when Core missing; gate reason `exit` | Emit JSON with `unavailable`; gate Core in shell |
| X-15 | MINOR | `main.ts:121` | `onload` awaits a 5 s probe | Probe lazily |
| X-16 | MINOR | 30_TESTPLAN, 90_ACCEPTANCE G-07, SPEC 8.2, HANDOFF, README | `--yes` vs `--yes-file`; `tools/mutate.py` and `docs/providers/*.md` missing; stale handoff; no CLI docs | Sync docs; add provider recipe or drop reference |
| X-17 | MINOR | `process/node-apis.ts` | Deprecated `electron.remote` | Covered by X-05 fix |
| X-18 | MINOR | `ui/coordinator.ts:217` | History `inputFile` = joined absolute paths | Store count + first path |
| X-20 | MINOR | README, plugin-dir layout | Cache/spool/consent/logs inside vault may be synced | Disclose or relocate |
| S-01..S-15 | MINOR | see section 6 | Dead/duplicated code and stale docs | Delete/merge as listed |

## 8. Scores (0-100; 100 only with no open finding)

| Axis | Score | Driver |
|---|---|---|
| Shell docs <-> code | 58 | X-01 BLOCKER; X-03/04/06 MAJOR; X-08/10/12/13/15 |
| Contract consistency | 72 | X-02; X-08/09/11/14; events/argv/report otherwise match FX-71 |
| Security | 74 | No leak/injection found; X-04 partial-path execution, X-02 destination, X-10 TOCTOU, X-20 sync |
| Policy compliance | 78 | Manifest/commands/desktop/no-install/no-telemetry OK; X-07 README accuracy, X-17, stale CHANGELOG |
| Goal fit | 66 | Engine/CLI fit; plugin lacks Cancel/progress, ignores Base URL, picker risk, drop confirm |
| Simplicity | 62 | 15 deletions/merges, 5 stale docs |

Round-2 exit condition for the shell: fix X-01..X-07, re-record FX-71 (X-11), sync the four doc drifts (X-16), then rerun jest/tsc/build and the R16 review.
