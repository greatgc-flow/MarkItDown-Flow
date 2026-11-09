# M3 cross-cutting MECE audit (Fable)

Reviewer: cc.fable. Date: 2026-11-09. Workspace = repo at `8229e4c` (clean tree; one untracked concurrent review file `M3_ag_horizontal.md`, not an input here). Read-only: `git ls-files`, file reads, greps and one independent `npx jest` run (25 suites, 255/255 passed, 3.7 s). Engine 507 pass, tsc clean and build OK are taken from the orchestrator and `M2_ENGINE_FOLLOWUP.md`; not re-run here. No code edits, no git.

Inputs read: all of `shell/src/**` (31 files), `shell/styles.css`, `esbuild.config.mjs`, `jest.config.js`, `package.json`; shell tests JT-01/02r2/09/12/15/16-ui/17 and the FX-71 manifest plus `version*.json`, `consent-4-plan-warm`, `consent-5-approved`, `usage-error`; `20_SHELL.md`, `25_PACKAGING.md` sections 1-2/5, `10_SPEC.md` sections 7.3-10.4 and 12.6, `30_TESTPLAN.md` section 4.3, `90_ACCEPTANCE.md`, `00_BRIEF.md` header, `HANDOFF.md`, `README.md`, `CHANGELOG.md`, `.gitignore`, `manifest.json`, `versions.json`, `engine/BOOTSTRAP.md`, `docs/providers/command.md`, `.github/workflows/*`, `tools/trace.py`; engine `cli.py`, `approve.py`, `providers/__init__.py`, `openai_compat.canonical_destination`, `orchestrate.tools/cancellation/run end`.

MAN-01 note: the shell was implemented by this reviewer. Every statement below cites a file and line or a fixture byte that a second reader can check; nothing relies on memory of intent. The R15 independence attestation remains a separate named human gate.

Severity as in M2: BLOCKER = release-blocking MUST violation or user harm; MAJOR = MUST/doc-code mismatch with user-visible effect; MINOR = drift, dead code, UX.

---

## 1. Verification of every M2_fable_cross finding

| ID | M2 sev | Status | Evidence at `8229e4c` |
|---|---|---|---|
| X-01 | BLOCKER | CLOSED | `ui/progress.ts:91-159` `JobStatusBar` (phase text, optional details, unconditional Cancel button); `main.ts:132-136` binds `onCancel` to `coord.cancel()`; `coordinator.ts:181,185,228,276,309` drive `begin/event/phase/end`; `jt-16-cancel-ui.test.ts` asserts Cancel absent idle, present in run and consent, hidden details keep Cancel, click cancels, whole-plugin status-bar wiring. |
| X-02 | MAJOR | CLOSED | `launcher.ts:90-94` `engineEnvFor` sets `MDFLOW_BASE_URL = snapshot.provider.baseUrl` for `openai-compatible` (setting wins); JT-12 `jt-12-spawn-replay.test.ts:146-162` asserts the override, no argv leak and FX-71 `plan-mixed` destination `<baseUrl>/chat/completions`; README "Network services" and REQ-SHL-06 state it. |
| X-03 | MAJOR | CLOSED | `main.ts:118` `settingsReadOnly = jobsBlocked || result === null`; `main.ts:299-304` `saveSettings` refuses with `shell.SETTINGS`; `settings-tab.ts:63-69` renders only the read-only notice; JT-03/JT-05 (`jt-02-plugin-round2.test.ts:75-115`) prove byte-identical `data.json` after tab display and history clear. |
| X-04 | MAJOR | CLOSED | `settings-tab.ts:42-55` commits on blur/Enter only; `:76-80` requires `isAbsolutePath`; `main.ts:221-229` probes once per committed interpreter change; JT-10 (`jt-02-plugin-round2.test.ts:117-157`) asserts zero spawns while typing, relative value refused, one `version` probe per commit. |
| X-05 | MAJOR | CLOSED (code); MAN-04 open | `process/dom-picker.ts` (`<input type=file>`, `webkitdirectory`), `node-apis.ts:130-153` (`webUtils.getPathForFile` then legacy `File.path`), `main.ts:163-177` notifies `shell.notice.pickerUnavailable`; JT-02 (`:223-239`). No `electron.remote` string in `shell/src` except two comments. Real-app behaviour of the DOM picker is unverified until MAN-04 (see N-05). |
| X-06 | MAJOR | CLOSED | `ui/drop-confirm-modal.ts` (Cancel is `mod-cta` default, Escape/close declines); `entry-points.ts:126` submits only after `confirmSelection`; JT-08 (`jt-02-plugin-round2.test.ts:263-282`). |
| X-07 | MAJOR | CLOSED (text); MAN-02 open | README now says `data.v1.json` (matches `persist.ts:137`); no `MDFLOW_MODEL` anywhere in repo docs; Base URL setting documented with the loopback-http rule (matches `openai_compat.py:47`); cache/spool/consent/logs location and sync disclosure present; CLI usage section added. Named R16 review still required. |
| X-08 | MINOR | CLOSED | `coordinator.ts:84-86` `needsConsent = egress && requests_to_send > 0` (== `approve.py:15`); `consent-modal.ts:69,137` informational marker; JT-15 `:214-242` with FX-71 `consent-4-plan-warm` (file 1: `max_requests 2`, `requests_to_send 0` -> informational; yes-file holds exactly the two hashes that need consent). |
| X-09 | MINOR | CLOSED | SPEC 7.3 line 471 "`file` is a logical string or `null` for a run-level issue"; `framing.ts:49-50,134-139` accept null for `warning`/`error` only. No recorded FX-71 stream contains `"file": null` (0 matches), so coverage is unit-level (JT-13) only; acceptable. |
| X-10 | MINOR | CLOSED | `coordinator.ts:296,307,330-333` revalidate before the `run` spawn and before writing the yes-file; JT-09 in `jt-15-consent-replay.test.ts:244-265` (symlink swap during consent -> `shell.DESTINATION`, no yes-file write). |
| X-11 | MINOR | PARTIAL | FX-71 manifest `engine.mdflow` is now `2.0.0` from the installed wheel (was `2.0.0.dev0`), 25 recorded + 28 derived, `--verify` passes per `M2_ENGINE_FOLLOWUP.md`. **Still recorded on Python `3.15.2`** (`manifest.recording_host`, `version.json`); `RELEASE_LOCK` rejects it, so JT-17 still widens the policy (`jt-17-version-gate.test.ts:29`). Release-host (3.14) re-recording remains open; honestly labelled `version.python-3.15.json`. |
| X-12 | MINOR | CLOSED | `main.ts:205-211` notifies `shell.notice.selftestRouter` before `runSelftest`; en/ko strings exist (`i18n.ts:253,375`); JT-02 (`:241-248`). |
| X-13 | MINOR | CLOSED | `settings-tab.ts:132-163` dpi/minPriority/maxUnits/approveThreshold/sensitive controls with SPEC 10.2 bounds; JT-04 (`jt-02-plugin-round2.test.ts:177-221`). |
| X-14 | MINOR | CLOSED | `cli.py:204-207` dispatches `version` before `_check_core`; `orchestrate.tools()` emits `"unavailable"`; SPEC REQ-GEN-02 and 10.1 line 584 updated; fixture `version.core-unavailable.json` -> gate reason `core` (JT-17 `:91`). |
| X-15 | MINOR | CLOSED | `main.ts:129-130` `void this.refreshGate()`; `currentGate()` awaited by `submit` only; JT-02 (`:250-261`) loads with a hung probe in < 1 s and registers six commands. |
| X-16 | MINOR | MOSTLY CLOSED | 30_TESTPLAN JT-15 row and 90_ACCEPTANCE G-07 now say `--yes-file`; no `tools/mutate.py` reference remains; SPEC 8.2 links the existing `docs/providers/command.md`; README has "Command-line usage". **`HANDOFF.md` is stale again** (states 446 engine tests, lists X-11/X-14/SPEC 7.3/8.2/S-14/S-15 as open) -> folded into S-13 below. |
| X-17 | MINOR | CLOSED | No `electron.remote`/`@electron/remote` import in `shell/src`; `esbuild.config.mjs:25` still lists `@electron/remote` as an external (dead entry, S-16). |
| X-18 | MINOR | CLOSED | `coordinator.ts:89-92` `historyInputLabel` = first path + `(+N)`; JT-07 (`jt-16-cancel-ui.test.ts:211-228`). |
| X-20 | MINOR | CLOSED (disclosure) | README "Outside-vault access" names `cache/`, `spool/`, `consent/`, `logs/` under the plugin folder and the Sync replication risk; relocation not chosen (acceptable, disclosed). |
| S-01..S-03 | MINOR | CLOSED | `pure/argv.ts`, `pure/errors.ts`, `pure/index.ts`, `process/index.ts`, `ui/index.ts` absent from `git ls-files`. |
| S-04 | MINOR | CLOSED | `launcher.ts:42-45` `Authorization` has only `yesFile` + `approvedBy`. |
| S-05 | MINOR | CLOSED | Oracles live in `shell/test/fixtures/protocol.ts`; `pure/protocol.ts` keeps decoders only (but see S-17 for `approvableHashes`). |
| S-06 | MINOR | CLOSED | `history.ts:38-45` `RunFacts` has no `outputsCreated`. |
| S-07 | MINOR | CLOSED | `pure/trace.ts` deleted; `tools/trace.py:299-311` reads `req()` bindings from test sources for registration and `junit-shell-*.xml` for execution (`:426-438`); 20_SHELL REQ-SHL-21 says the same. |
| S-08 | MINOR | CLOSED | `setup.ts:166` `environmentDiagnostics` feeds `providerEnv`; `setup-modal.ts:82-83` renders presence per variable. |
| S-09 | MINOR | CLOSED | `log.ts:6` imports `joinPath` from `pure/paths`. |
| S-10 | MINOR | CLOSED | No `this.load()` in `main.ts`. |
| S-11 | MINOR | CLOSED | `coordinator.submit(selection, entry)` logs `entry` (`:257`); `EngineRun.onEvent` subscribed (`:228`). |
| S-12 | MINOR | CLOSED | `.gitignore` is the v2 set (no `python/__pycache__`, `clean-release/`, `release/`, `test-extract/`). |
| S-13 | MINOR | PARTIAL | `CHANGELOG.md` has a 2.0.0 entry; `00_BRIEF.md` marked SUPERSEDED; **`HANDOFF.md` stale** (see X-16). |
| S-14 | MINOR | CLOSED | `cli._provider_list` absent; `providers.describe()` reads `DEFAULT_META` (`providers/__init__.py:106-112`). |
| S-15 | MINOR | CLOSED | `report.publish(value, *, stdout)` (`report.py:77`); `cli.py:239-247` owns the `--report` copy. |

Round-2 scorecard: 37 items; 33 CLOSED, 2 PARTIAL (X-11 release-host recording, S-13/X-16 HANDOFF), 2 CLOSED-in-code with a named manual gate still owed (X-05 MAN-04, X-07 MAN-02). No M2 finding is open in code except the X-11 recording host.

---

## 2. Re-audit: shell docs <-> code (20_SHELL REQ-SHL-* vs `shell/src`)

| REQ | Status | Evidence / gap |
|---|---|---|
| SHL-01 | OK | JT-01 import/build-input scan; esbuild reads `shell/` only. MAN-01 separate. |
| SHL-02 | OK | Six ids (`ui/commands.ts`), one guard (`main.ts:103`), selftest notice, picker notice. |
| SHL-03/04 | OK | 21-key map, schema-2 allowlist, read-only path, run-option controls, blur/Enter commit. |
| SHL-05 | OK | temp+rename store, allowlisted/scrubbed snapshot, failure keeps bytes, later saves refused. |
| SHL-06 | OK | env-only key, presence only, `MDFLOW_BASE_URL` from setting, scrubbed child env. Settings tab and `pickProvider` accept non-loopback `http://` that the engine refuses at startup (N-07). |
| SHL-07 | OK | cap/sort/outcome, first-path+count label. |
| SHL-08 | OK | DOM picker, confirm modal, shared coordinator. Drop handler intercepts every local-file drop while enabled, including attachment drops into notes (N-08, UX, documented as opt-in default false). Toggle changes take effect only after reload (N-09). |
| SHL-09 | **FAIL (1 MAJOR)** | Destination/symlink/case rules and pre-spawn revalidation OK. **Busy admission is not atomic** (N-01). |
| SHL-10 | OK | probes only, background gate, committed absolute path only. |
| SHL-11/12 | OK (1 BLOCKER) | argv array, `shell:false`, fixed cwd, `-o`/`--cache` direct. **The interpreter is launched without `-I`/`-P`, so the vault root (cwd) is `sys.path[0]`** (N-02). |
| SHL-13 | OK (1 MINOR) | framing/spool/null-file. `DirectorySpoolFs.read` re-reads the whole file per 64 KiB window (N-10). |
| SHL-14 | OK | one modal, literal text, Keep pending default, informational rows. |
| SHL-15 | OK | yes-file of needing-consent hashes only, `--approved-by plugin:modal`, removed in `finally`. |
| SHL-16 | OK | status-bar Cancel for plan/consent/run; cooperative then forced; Windows = forced only (`node-spawner.ts:57-58`), honestly reported; real-OS gate still open per 20_SHELL "Open". |
| SHL-17 | OK (X-11 partial) | complete 8-field gate; `core-unavailable` -> `core`. |
| SHL-18 | OK (1 MINOR) | five x 1 MiB, allowlisted fields, redaction. `open-log-folder` before the first log line targets a directory that does not yet exist (N-11). |
| SHL-19 | OK | codes/i18n parity by JT-SHL-19-01; command names/ribbon tooltip read `locale` once at load (N-09). |
| SHL-20 | OK | `version` then `selftest` only. |
| SHL-21 | OK | `req()` titles -> junit; `trace.py` consumes. |

20_SHELL "Open" line (`:235`) still lists the SPEC cooperative/forced distinction and the bundled selftest fixture as `SYNC-AFTER-DRAFT-3`, but SPEC 10.3 row 130 and `cli._selftest_documents` already satisfy both; only the real-OS cancellation runs remain (N-12, doc drift).

## 3. Shell <-> engine contract (FX-71 re-recorded)

Verified consistent at `8229e4c`: `buildSpawnRequest` emits only options present in `cli.py:_parser` (`-o`, `--cache`, `--provider`, `--model`, `--dpi`, `--min-priority`, `--max-units`, `--approve-threshold`, `--sensitive`, `--progress jsonl`, `--yes-file`, `--approved-by`); FX-71 `consent-3/5` argv carry `--yes-file <file> --approved-by plugin:modal` and `consent-5-approved.stdout.json` records `"by": "plugin:modal"`; `plan` stdout is concatenated pretty JSON (`cli.py:233` -> `parsePlanOutput`); `run_end` fields `exit/files_ok/files_failed/provider_calls` (`orchestrate.py:495-501`) match `framing.ts:55-57`; startup error object matches `usage-error.stderr.json`; `version` keys match `tools()` + `cli.py:205-206`; consent predicate identical on both sides; exit map `outcomeFor` matches SPEC 10.3; shell never passes `--report`, `--force`, `--yes` or command-provider flags.

Gaps:

- **X-11 (PARTIAL, carried)** recording host Python 3.15.2; release-host recording pending (engine owner).
- **N-03 (MINOR)** `coordinator.ts:266-268`: when `plan` ends with a well-formed exit-1 startup error (`E_PROVIDER_CONFIG`, `E_CORE_VERSION`, `E_USAGE`) or a spawn failure, the shell shows the correct code message **and additionally `shell.PROTOCOL`** ("Invalid engine response") because `plan.stdout` is null. A valid startup error is not a protocol violation; the `run` path (`:322`) does not add it. Fix: append `shell.PROTOCOL` only when `plan.stdout?.ok === false` or `plan.invalid.length > 0`.
- **N-04 (MINOR)** Windows cooperative cancel: the engine honours `SIGBREAK` (`orchestrate.py:57`) but Node cannot deliver `CTRL_BREAK_EVENT`, so `requestCooperativeStop` returns false on win32 and every Cancel is `TerminateProcess` with no report and the run temp dir (`mdflow-*` under `%TEMP%`, `orchestrate.py:451`) left behind. Documented as honest forced termination; disclose the temp-dir residue in README "Account, API key and cost" or clean stale `mdflow-*` dirs at next engine start (engine owner).

## 4. Security

Re-verified (unchanged from M2 unless noted): no secret on argv; schema-2 allowlist; child env = SPEC baseline + UTF-8 + four `MDFLOW_*` names only for `openai-compatible`, `MDFLOW_BASE_URL` overwritten by the setting; logs allowlisted and redacted; yes-file/spool/consent/log dirs `0700`/files `0600`, owned names, removed after use; destination containment by real paths; no network API in `shell/src` (0 matches for `fetch(`, `requestUrl`, `XMLHttpRequest`); no `innerHTML`/`console.` in `shell/src`; DOM picker returns only paths, never file contents; engine `canonical_destination` enforces https or loopback-http, no userinfo/query/fragment, no redirects.

Findings:

- **N-02 (BLOCKER, security)** `launcher.ts:108,137` and `setup.ts:114-121` spawn `<python> -m mdflow ...` **without `-I` (or `-P`)**. With `-m`, CPython prepends the current working directory to `sys.path`. The shell fixes `cwd` to the **vault root** for `plan`/`run` (`coordinator.ts:109`) and to the **plugin directory inside the vault** for `version`/`selftest`/bootstrap probes (`main.ts:208,265`). A vault that contains `mdflow.py`, `mdflow/__init__.py`, `PIL/`, `pypdfium2/`, `markitdown_gc/` or any stdlib-shadowing module at its root (shared vault, Obsidian Sync, downloaded vault template) therefore executes attacker-chosen Python with the user's privileges on the next conversion or even on plugin load (background version probe). The project's own tooling already runs `python -I` everywhere (`tools/record_protocol.py`, 25_PACKAGING, CI); the shell does not. Fix: `args = ['-I', '-X', 'utf8', '-m', 'mdflow', ...]` in `buildSpawnRequest` and `buildUtilityRequest` (`-I` implies `-E`, which drops `PYTHONUTF8`/`PYTHONIOENCODING`, hence `-X utf8`; `cli.py:199-201` already reconfigures stdio to UTF-8), keep `cwd` as is, update JT-12 `args.slice(0,3)` assertions and add a JT asserting `-I` precedes `-m` in every spawn (plan, run, version, selftest, bootstrap probes); add the rule to REQ-SHL-12 and BOOTSTRAP/SetupModal recipes (`-I -m mdflow version|selftest`). `-P` alone is insufficient (Python 3.10 lacks it).
- **N-01 (MAJOR)** `coordinator.ts:133-179`: `isActive` is set only after `await gate()`, `await validateDestination`, and the nonrecursive `fs.list` loop. Two submissions that both pass line 134 before either reaches line 179 (realistic: the first job after load awaits a version probe of up to 5 s; a second context-menu click or drop lands in that window) both start, spawn two engines, overwrite `this.job`/`this.engine`, and Cancel then stops only the second. REQ-SHL-09 MUST "one active conversion ... zero unsafe launches"; JT-09 (`jt-09-output-busy.test.ts:140-154`) tests only the sequential case. Fix: set a synchronous `reserved` flag at the top of `submit` (released on every refusal path), add a JT that fires two `submit` calls in the same tick with a pending gate promise and asserts one spawn and one `shell.BUSY`.
- **N-07 (MINOR)** `settings-tab.ts:124-125` and `settings.ts:147-155` accept any `http://` Base URL; the engine refuses non-loopback http at startup (`openai_compat.py:47`), so the user sees `E_PROVIDER_CONFIG` plus the spurious N-03 notice at job time instead of a validation error in the tab. Apply the loopback rule in the tab.
- **N-06 (MINOR)** `dom-picker.ts:80` `input.click()` needs Chromium user activation; a command invoked without it (URI handler, another plugin, future automation) never fires `change`/`cancel`, so the returned promise never settles and the hidden input leaks. Harmless for locks (coordinator not reserved) but silent; add a one-shot timeout or notice.

No secret leak, injection or containment defect found beyond N-02.

## 5. Obsidian policy and submission rules

| Rule | Result |
|---|---|
| `isDesktopOnly:true`, id `markitdown-flow`, version 2.0.0, `minAppVersion 1.14.4` with `versions.json` entry and prior entries preserved | OK. Real existence of Obsidian 1.14.4 is MAN-04 TODO-VERIFY (unchanged). |
| Description <= 250 chars, ends with period, equals REQ-PKG-15 candidate | OK (90 chars). |
| Six command ids, no plugin prefix, names without plugin name, sentence case | OK. Menu item title includes "(MarkItDown Flow)" (`i18n.ts:244`); allowed for menu items, not commands. |
| No self/dependency install, probes only | OK (`setup.ts`, `selftest.ts`). |
| No client telemetry, no remote fetch | OK. |
| Node/Electron use behind a desktop guard; no `electron.remote` | OK; `require('electron')` only for `shell.openPath`, `clipboard`, `webUtils` (`node-apis.ts:129`). |
| `main.js` not committed; LICENSE, README present | OK (`.gitignore:4`). |
| README R16 disclosures | Headings and content present and consistent with code (checked: `data.v1.json`, `~/.mdflow/cache`, `<plugin-dir>/cache`, loopback-http rule, `MDFLOW_TIMEOUT_S`/`MDFLOW_PROXY` from env, CLI targets 3 OS x 3.10/3.14 = `release.yml:113-114`, `--yes HASH` repeatable = `cli.py:54`). Named MAN-02 review still owed. |
| Release notes | `CHANGELOG.md` 2.0.0 entry present and accurate. |
| Long work in `onload` | Fixed (background probe). |

Findings: none new at policy level. N-02 is also a policy concern (developer policy forbids executing untrusted code; a plugin that lets vault content select the Python modules it runs would fail a security review if noticed).

## 6. User-goal fit (classify -> selective OCR with consent, provenance, no re-transcription, markitdown-gc)

Engine/CLI: fits (unchanged evidence: FX-71 `classified` T/S/M labels, candidate-only rendering, per-file plan hash, `consent-6-warm` `provider_calls 0`, Core 0.3.5 gate, `version` usable without Core).

Plugin at `8229e4c`: the end-to-end path now works for `none` and for `openai-compatible` with the configured Base URL, with Cancel and progress visible, consent only where requests remain, pickers and drop confirmation in place. Remaining gaps:

- N-01 (two jobs can run), N-02 (vault-controlled module path), N-03 (misleading second notice on configuration errors), N-07 (late Base URL validation).
- **N-05 (MINOR, MAN-04)** Folder selection via `webkitdirectory` enumerates every file of the chosen tree just to derive one root (`dom-picker.ts:68-77`); an empty folder or a folder of only subfolders resolves to `null` and the command silently does nothing (indistinguishable from cancel). Rehearsal must confirm Electron shows no browser-style "upload" confirmation and that large folders stay responsive; add a notice for the empty case.
- **N-08 (MINOR)** With `enableDragDrop` on, every local-file drop anywhere in the workspace is converted instead of attached (`entry-points.ts:116-128`). Default is off; state the trade-off in the toggle description.
- **N-09 (MINOR)** `enableContextMenu`, `enableDragDrop` and `locale` are read once at load (`main.ts:186-216`); changes apply after reload with no hint. Add "takes effect after reload" to the three descriptions or re-register on save.
- **N-11 (MINOR)** `open-log-folder` on a fresh install calls `shell.openPath` on a not-yet-created `logs/` directory (`log.ts:70-73` creates it lazily); the error string is ignored (`node-apis.ts:144-146`). `mkdir` before opening.

## 7. Simplicity (delete or merge)

| ID | Item | Action |
|---|---|---|
| S-13 (carried) | `docs/renewal/HANDOFF.md` stale (446 tests; lists X-11/X-14/SPEC 7.3/8.2/S-14/S-15 as open) | Refresh to `8229e4c` state or delete; one source of status. |
| S-16 | `esbuild.config.mjs:25` external `@electron/remote` | Remove (nothing imports it). |
| S-17 | `pure/protocol.ts:347-350` `approvableHashes` (comment still says `--yes`; 0 production or test callers) | Delete. |
| S-18 | `pure/spool.ts:42-44` `Spool.finish()` (only `finishWith` is called) | Delete. |
| S-19 | `ui/coordinator.ts:52` `CoordinatorDeps.locale` is never read by the coordinator (modal locales come from `main.ts` closures) | Remove the field and the 15 test sites that fill it. |
| S-20 | `entry-points.ts:55-58` `legacyFilePath` duplicates the fallback branch of `node-apis.ts:137-138` | Make `node-apis.filePath` the single resolver; drop the default parameter. |
| S-21 | `ui/output-path.ts:9` re-exports `pure/paths` helpers | Import from `pure/paths` directly; delete the shim. |
| N-10 | `main.ts:49-53` `DirectorySpoolFs.read` reads the whole spool per call; `Spool.finishWith` then loops in 64 KiB windows, so an N-byte report costs O(N^2/64 KiB) I/O and the "bounded read buffer" claim is nominal | Read once (`readFile`) and decode, or implement a real offset read with `fs.open/read`. |
| N-12 | 20_SHELL `:235` "Open" still names two `SYNC-AFTER-DRAFT-3` items that SPEC 10.3/`cli._selftest_documents` already satisfy | Reword to "real-OS cancel runs (G-09) and MAN-01..04". |

---

## 8. Consolidated findings (new in M3)

| ID | Sev | Location | Defect | Fix |
|---|---|---|---|---|
| N-02 | BLOCKER | `process/launcher.ts:108,137`, `process/setup.ts:114-121`, cwd in `ui/coordinator.ts:109`, `main.ts:208,265` | Python launched without `-I`; vault root / plugin dir become `sys.path[0]`, so vault content can supply `mdflow`, `PIL`, stdlib shadows -> code execution on convert or load | `['-I','-X','utf8','-m','mdflow',...]` everywhere; JT asserting it; REQ-SHL-12 + recipes |
| N-01 | MAJOR | `ui/coordinator.ts:133-179` | Busy admission not atomic across the gate/destination awaits; two concurrent submits start two engines; Cancel covers one | Synchronous reservation flag; concurrent-submit JT |
| N-03 | MINOR | `ui/coordinator.ts:266-268` | Valid exit-1 startup error on `plan` also raises `shell.PROTOCOL` | Add PROTOCOL only on decode/framing failure |
| N-04 | MINOR | `process/node-spawner.ts:57`, README | Windows Cancel is always forced; engine temp dir residue undisclosed | Disclose or clean stale `mdflow-*` at engine start |
| N-05 | MINOR | `process/dom-picker.ts:68-77` | Empty-folder pick is a silent no-op; full-tree enumeration for one root; real Electron behaviour unverified | Notice on empty; MAN-04 check |
| N-06 | MINOR | `process/dom-picker.ts:80` | Picker promise never settles without user activation | Timeout/notice |
| N-07 | MINOR | `ui/settings-tab.ts:124`, `pure/settings.ts:147` | Non-loopback `http://` Base URL accepted, refused later by engine | Loopback rule in tab/migration |
| N-08 | MINOR | `ui/entry-points.ts:116-128` | Drop toggle hijacks attachment drops | Describe trade-off |
| N-09 | MINOR | `main.ts:186-216` | Context-menu/drop/locale changes need reload, unannounced | Note or re-register |
| N-10 | MINOR | `main.ts:49-53`, `pure/spool.ts:47-57` | Quadratic spool read; bounded-buffer claim nominal | Single read or real offset read |
| N-11 | MINOR | `main.ts:201-204`, `process/log.ts:70-73` | Open-logs before first write targets a missing dir | mkdir first |
| N-12 | MINOR | `20_SHELL.md:235` | Stale `SYNC-AFTER-DRAFT-3` items | Reword |
| X-11 | MINOR (carried) | FX-71 manifest | Recording host Python 3.15.2 | Re-record on 3.14 (engine owner) |
| S-13..S-21 | MINOR | section 7 | Stale HANDOFF, dead export/external/field/shim | Delete/merge |

## 9. Scores (0-100; 100 only with no open finding)

| Axis | M2 | M3 | Driver |
|---|---|---|---|
| Shell docs <-> code | 58 | 82 | All M2 MUST gaps closed; N-01 (SHL-09 atomic busy), N-09/N-12 drift |
| Contract consistency | 72 | 88 | argv/events/report/consent identical to FX-71 2.0.0 recordings; X-11 host, N-03 |
| Security | 74 | 60 | No leak/injection; **N-02 vault-controlled `sys.path`** outweighs the M2 fixes; N-07 |
| Policy compliance | 78 | 90 | Manifest/commands/desktop/no-install/no-telemetry/README/CHANGELOG OK; MAN-02/04 owed; N-02 exposure |
| Goal fit | 66 | 84 | Cancel/progress/Base URL/picker/drop/consent-filter done; N-01/03/05/07/08/11 |
| Simplicity | 62 | 86 | 13 of 15 S-items done; 7 small leftovers + N-10 |

Round-3 exit condition for the shell: fix N-02 and N-01 (both are one-function changes plus one JT each), then N-03/N-07 together, refresh HANDOFF, rerun jest/tsc/build, and hand X-11 host re-recording plus N-04 disclosure to the engine owner. MAN-01..04 remain the only non-code gates.
