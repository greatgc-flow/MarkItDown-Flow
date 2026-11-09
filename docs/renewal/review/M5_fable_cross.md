# M5 cross-cutting MECE audit (Fable)

Reviewer: cc.fable. Date: 2026-11-09. Workspace = repo at `91620a0` (clean tree; branch `renewal/v2-zero-base`, PR #1 open, 3-OS CI in flight). Read-only: file reads, greps, `sha256sum`/`wc -c` on six FX-71 files, and one independent `npx jest --ci` run from `shell/` (**25 suites, 277/277 passed**, 0 failed, 8.9 s). Engine 568 pass and `tsc --noEmit` clean are taken from the orchestrator and commit `8303b03`; tsc/build were not re-run here (sandbox). No code edits, no git.

Inputs read: `M4_fable_cross.md`, `M4_cx_vertical.md`, `M4_SHELL_FIXES.md`, `M4_ENGINE_FIXES.md`, `HANDOFF.md`, `20_SHELL.md`, `90_ACCEPTANCE.md`, `30_TESTPLAN.md` JT rows, `25_PACKAGING.md` section 2, `engine/BOOTSTRAP.md`, `README.md`, `CHANGELOG.md`, `manifest.json`, `versions.json`, `.github/workflows/ci.yml`; `shell/src` (`ui/coordinator.ts`, `ui/progress.ts`, `ui/settings-tab.ts`, `ui/entry-points.ts`, `ui/output-path.ts`, `main.ts`, `process/version-gate.ts`, `process/launcher.ts`, `process/node-apis.ts`, `pure/settings.ts`, `pure/paths.ts`, `pure/i18n.ts` keys), `shell/scripts/publish-fx71.mjs`, `shell/package.json`, `jest.config.js`, `esbuild.config.mjs`, FX-71 `manifest.json` + `version.json`, JT-04/09/16/17 sources, `test/fixtures/plugin-harness.ts`; engine `cli.py` parser, `orchestrate.py` emitters, `openai_compat.canonical_destination`, `tests/packaging/test_pt_release.py::gate`, `tests/packaging/test_m4_docs.py` (T-META-95, T-GEN-96/97), `tests/packaging/_support.py::version_tuple`, `tests/matrix.toml:414`.

MAN-01 note (unchanged): the shell was implemented by this reviewer; every statement cites a file:line or fixture byte a second reader can check. R15 independence remains a named human gate.

Severity as before: BLOCKER = release-blocking MUST violation or user harm; MAJOR = MUST/doc-code mismatch with user-visible effect; MINOR = drift, dead code, UX. Two classes stay strictly apart: **(A) findings fixable in code/docs now** and **(B) external evidence (90_ACCEPTANCE §7 E-01..E-15)**. Class B is tracked separately and never lowers a score here.

---

## 1. Verification of every M4_fable_cross finding

### 1a. Round-4 class-A findings (P-01..P-06, D-01..D-04)

| ID | M4 sev | Status | Evidence at `91620a0` |
|---|---|---|---|
| P-01 (M3-V03) | MINOR | **CLOSED** | `ui/progress.ts:31-43` `emptyProgressSummary`, `:50-80` `applyProgressEvent` in place, `run_start` resets every field before `filesTotal` (`:52-55`); `summarizeProgress` (`:83-87`) is the fold; `JobStatusBar` holds one `summary` (`:112`), `event()` applies then renders (`:148-152`), no array. JT-09 `jt-09-output-busy.test.ts:243-279`: `[...PLAN, ...RUN]` equals Run-only, Plan-only prefix reports `pending 9`/`exit 3`, incremental == whole-stream at every 17th prefix of the FX-71 stream. JT-16 `:247` `Object.keys(bar)` has no `events`. REQ-SHL-09 text (`20_SHELL.md:84`), CHANGELOG `:21-22`. |
| P-02 (M3-V04) | MINOR | **PARTIAL (Q-01)** | `version-gate.ts:107-111` `releaseSegment` = `^(\d+)\.(\d+)(?:\.(\d+))?[A-Za-z0-9.+-]*$`: anchored, rejects `5.15.1???`, whitespace, `v5.15.1`, bare `5` (JT-17 `:121-144`, 7 valid / 11 invalid). But the package gate (`test_pt_release.py:296-304`) applies **two** steps: the regex **and** `packaging.version.Version(text)`. The shell implements only the regex, so any alphabetic/dotted suffix the regex class admits but PEP 440 does not passes the shell and fails the package gate. T-GEN-96's own case `('python', '3.14garbage', False)` (`test_m4_docs.py:28`) is admitted by the shell as `[3,14,0]`. Section 3, Q-01. |
| P-03 (X-11) | MINOR | **CLOSED** | `shell/test/fixtures/fx71/manifest.json:6-9` `recording_host.python = 3.14.10`, `:12` Core `0.3.6`, every recorded `argv` label `python -I -m mdflow` (T-GEN-97); `version.json` = `{"mdflow":"2.0.0","markitdown-gc":"0.3.6","pypdfium2":"5.15.1","pillow":"13.0.0","python":"3.14.10",...}`. Spot-check here: 53 files present; `sha256sum`/`wc -c` of `version.json` (187 B, `4500cc82…`), `approve-required.progress.jsonl` (35944 B, `93061a61…`), `plan-mixed.stdout.json` (8762 B, `208339d8…`), `consent-5-approved.progress.jsonl` (8521 B, `b3e02d36…`), `selftest.json` (14 B, `a279e7d0…`), `usage-error.stderr.json` (110 B, `bf3be571…`) all equal the manifest. No widened policy: JT-10 `:23`, JT-20 `:18`, JT-17 `:32` are `RELEASE_LOCK`; harness `versionWithinPolicy()` returns the recorded `version.json` bytes (`plugin-harness.ts:23-26`); JT-17 `:46-47` asserts python 3.14.x and Core `0.3.6`. `scripts/publish-fx71.mjs` verifies staged + published sets/bytes/sha256 (`:33-51`, `:80-92`); `package.json:15` `fx71:publish`. Only `version.python-3.15.json` still says `3.15.2`: it is the derived **negative** variant (`manifest.json:860-866`), correct. |
| P-04 | MINOR | **CLOSED** | `pure/paths.ts:36-38` single `isAbsolutePath` (POSIX root, drive, UNC) used by `settings.ts:314-315` (`validateV2`: printable **and** absolute, else `enginePython: reset` without the value), `settings-tab.ts:96`, `launcher.ts:88` (`snapshotJob`) and `coordinator.ts:165` (refuses `shell.RUNTIME` before the gate and before any spawn). JT-04 `:246-258` five relative spellings reset, three absolute forms kept; JT-09 `:282-308` `{accepted:false, diagnostic:'shell.RUNTIME'}`, notices exactly `['shell.RUNTIME']`, zero spawns. REQ-SHL-04 (`20_SHELL.md:64`), README `:129-131`. |
| P-05 | MINOR | **CLOSED** | `settings-tab.ts:51-68` `committed(text, persisted, apply)`: refusal -> one `shell.settings.rejected` notice, `inputEl.value` reverted to `persisted()`, baseline reset so the same refused text is reported again; used for interpreter (`:90-99`), output path (`:106-110`), Base URL (`:148-155`), max units (`:171-176`), threshold (`:180-185`). `main.ts:203` supplies `notify`. Keys in en/ko (`i18n.ts:242`, `:368`). 30_TESTPLAN `:393` names the JT-04 whole-plugin oracle; README `:127-130`; CHANGELOG `:31-32`. |
| P-06 (M4-V03, N-07 residual) | MINOR | **CLOSED** | `settings.ts:152` `LOOPBACK_HOSTS = {localhost, 127.0.0.1, [::1]}` = engine `_LOCAL_HOSTS` (`openai_compat.py:25`, bracket form vs `urlsplit.hostname` form, same tokens); `:155-158` `rawAuthority` = `urlsplit` netloc; `:161-168` `rawHost` strips port, keeps brackets; `:181-195`: whitespace/control chars (engine `:34`), WHATWG parse for structure, `?`/`#` in text (engine `:45`), any `@` in the raw authority (engine `:43`), `https` any host, `http` only when the **raw lower-cased host token** is loopback (engine `:47`). Traced spellings: `127.1`, `2130706433`, `0x7f000001`, `0177.0.0.1`, `127.0.0.1.`, `https://@host`, `http://@localhost`, `host@evil` -> both sides refuse; `LOCALHOST`, `[::1]:11434`, `https://0x7f000001` -> both accept. Only divergence is fail-closed: the engine `strip()`s (`:33`) while the shell refuses untrimmed text; the tab trims before the check (`settings-tab.ts:151`), so no accepted value is lost. JT-04 `:202-244`. Engine rule untouched. |
| D-01 (`SYNC-AFTER-DRAFT-3`) | MINOR | **CLOSED for the marker; two stale rows remain (Q-02)** | Grep: the marker appears in 20/25/30/90 only in the historical disposition row `20_SHELL.md:213` ("no sentence remains"); T-META-95 (`test_m4_docs.py:20-22`) asserts absence in 25/30/90. `20_SHELL.md:3` status line and `:247` Open paragraph describe the M4 state. Residual: disposition rows `20_SHELL.md:190` ("engine synchronization is pending") and `:193` ("final contract-test sync remains pending") still assert a pending sync. |
| D-02 (`-I` recipes) | MINOR | **CLOSED** | `engine/BOOTSTRAP.md:26,28,40,41,79` and `25_PACKAGING.md:30,31,41,42` all read `-I -m mdflow selftest\|version`; 0 recipe lines without `-I`; T-META-95 (`test_m4_docs.py:11-15`) enforces it. Equal to SetupModal/README (`README.md:145-157`). |
| D-03 (HANDOFF tsc, CHANGELOG, README) | MINOR | **CLOSED for the three named lines; recurrence (Q-03)** | `HANDOFF.md:18` now "re-run by the orchestrator and is clean at commit 9038074"; `CHANGELOG.md:23-25` Windows forced-only caveat; `README.md:21-23` venv-in-vault cwd "still not on the import path". Recurrence: `HANDOFF.md:36` again says the orchestrator "should re-run `npm run typecheck` before committing" although `8303b03` records tsc clean; `HANDOFF.md:27` "Engine 536 pass … Shell was 266/266" two lines after `:25` "568 passed" without saying it is the pre-fix snapshot. |
| D-04 (matrix comment) | MINOR | **CLOSED (horizontal owner)** | `engine/tests/matrix.toml:414` now "file class x stage (67 cells)" = cx's 67 otherwise-unregistered equivalences; "117" is gone. |

### 1b. Carried M3 rows (N-01..N-12, X-11, S-13, S-16..S-21) re-checked

All remain **CLOSED** with unchanged evidence: N-02 `launcher.ts:24` prefix / `:41-43` cwd / `main.ts:241-244` probe cwd; N-01 `coordinator.ts:97,142-151` reservation; N-03 `:300-304`; N-04 README `:99-105` disclosure plus engine-owned `runtime_temp` recovery (M4_ENGINE_FIXES); N-05/N-06 `main.ts:221-234` picker outcomes; N-07 -> P-06 above; N-08/N-09 `settings-tab.ts:112-118,129`; N-10 `node-apis.ts:62-72` positional `readRange`; N-11 `main.ts:171-173`; N-12 -> D-01; X-11 -> P-03; S-13 -> D-03; S-16 `esbuild.config.mjs` externals = `obsidian`, `electron`, builtins; S-17/S-20 0 matches for `approvableHashes`/`legacyFilePath`/`@electron/remote` in `shell/src`; S-18 `spool.ts` has `finishWith` and `discard` only; S-19 `CoordinatorDeps` (`coordinator.ts:43-65`) has no `locale`; S-21 `ui/output-path.ts` imports from `pure/paths` (`:6`), no re-export.

### 1c. M4_cx_vertical shell handoffs

| Handoff | Status | Evidence |
|---|---|---|
| M4-V01 (MAJOR; Cancel/unload during admission launched anyway) | **CLOSED** | `coordinator.ts:99` `admissionCancelled`, cleared when the reservation is taken (`:145`), set by `cancel()` (`:235`) and therefore by `dispose()` (`:241-244`); `admissionInterrupted()` (`:153-158`, disposed -> `shell.RUNTIME`, cancelled -> `shell.CANCELLED`) re-checked after the gate await (`:168-169`), the destination await (`:174-175`) and the folder listing (`:193-194`); activation (`:212-214`) only afterwards; the reservation is released in `finally` (`:148-150`). JT-16 `jt-16-cancel-ui.test.ts:261-317`: cancel row (0 requests, not active, no Cancel button, no history, later job accepted and spawns once), dispose row (0 requests, later submit `shell.RUNTIME`), control row (exactly one spawn). REQ-SHL-16 text (`20_SHELL.md:90`), 30_TESTPLAN `:405`. |
| M3-V03 (Plan->Run progress) | **CLOSED** | P-01 row. |
| M3-V04 (gate syntax) | **PARTIAL** | P-02 row / Q-01: the renderer case `5.15.1???` cx probed is now blocked on both sides; the engine's new `Version()` step is not mirrored. |
| M4-V03 (URL alias table) | **CLOSED** | P-06 row: cx's four-row table (`127.0.0.1` control, `127.1`, `2130706433`, `0x7f000001`) now agrees on both sides; JT-04 `:225-227,241`. |
| X-11 publication | **CLOSED** | P-03 row. |
| M4-V02, M4-O01 (engine) | **Engine owner reports CLOSED** (M4_ENGINE_FIXES rows 1-2; T-CLS-91, independent `collection-*.json`). Not re-verified here (engine scope); 568 pass per orchestrator. | — |

Round-4 scorecard: 10 class-A items (P-01..P-06, D-01..D-04): 8 CLOSED, 1 PARTIAL (P-02), 1 CLOSED-with-recurrence (D-03). 5 cx shell handoffs: 4 CLOSED, 1 PARTIAL (M3-V04 = P-02). **No BLOCKER or MAJOR is open in shell code.**

---

## 2. Re-audit: shell docs <-> code (20_SHELL REQ-SHL-* vs `shell/src`)

| REQ | Status | Evidence / gap |
|---|---|---|
| SHL-01 | OK | JT-01 scan; esbuild `absWorkingDir: shellDir`, entry `src/main.ts`, bundle to repo-root `main.js`. MAN-01 = E-08 (class B). |
| SHL-02 | OK | Six ids (`main.ts:154-184`), one `Platform.isDesktop` guard (`:72`), `loadNodeApis` after it (`:74`). |
| SHL-03 | OK | Schema-2 allowlist (`settings.ts:95-98`), newer schema -> `jobsBlocked`, read-only tab (`settings-tab.ts:76-82`), refused saves (`main.ts:297-300`). |
| SHL-04 | OK | All 21 rows; absolute-only interpreter in tab **and** on disk (P-04); rejected commits never silent (P-05); raw-text Base URL rule (P-06); reload/drop notes. Text at `:64` matches code. |
| SHL-05 | OK | temp+rename store, allowlisted snapshot, refused later saves (unchanged). |
| SHL-06 | OK | env-only key, presence only, `MDFLOW_BASE_URL` from the setting (`launcher.ts:115-119`), scrubbed child env. |
| SHL-07 | OK | cap/sort/outcome, `historyInputLabel` (`coordinator.ts:88-91`). |
| SHL-08 | OK | DOM picker, four outcomes (`main.ts:221-234`), confirm modal, shared coordinator, drop ignores text/URL (`entry-points.ts:55-69`). |
| SHL-09 | OK | Destination rules (`output-path.ts:33-60`), atomic admission, pre-spawn revalidation (`coordinator.ts:332,343`), per-run incremental presenter (P-01); text at `:84` matches. |
| SHL-10 | OK | probes only, background gate (`main.ts:99`), committed absolute path only, cwd venv root or home (`:241-244`). |
| SHL-11/12 | OK | argv array, `shell:false`, fixed prefix, cwd outside the vault, `-o`/`--cache` direct (`launcher.ts:126-156`). |
| SHL-13 | OK | framing/spool/null-file; ranged reads. |
| SHL-14 | OK | one modal, literal text, Keep pending default. |
| SHL-15 | OK | yes-file of needing-consent hashes only, `--approved-by plugin:modal`, removed in `finally` (`coordinator.ts:325-334,347-351`). |
| SHL-16 | OK | status-bar Cancel; pending-admission refusal (M4-V01); cooperative then forced; Windows forced-only disclosed. Real-OS runs = E-03 (class B). |
| SHL-17 | **1 MINOR (Q-01)** | Complete 8-field gate, blank platform blocked (`version-gate.ts:162`), FX-71 on a supported host against `RELEASE_LOCK`. The sentence "Version strings must have the package gate's full syntax (`test_pt_release.py`: `[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)`, whole string) … so the shell and the package gate agree on every spelling" (`20_SHELL.md:96`) describes only half of the package gate (`:298` regex **plus** `:301` `Version(text)`); `3.14garbage` disagrees. Same overclaim in 30_TESTPLAN `:406` ("version syntax = package gate") and the JT-17 comment (`jt-17-version-gate.test.ts:134`). |
| SHL-18 | OK | five x 1 MiB, allowlisted fields, redaction, mkdir before open. |
| SHL-19 | OK | codes/i18n parity by JT-SHL-19-01; `shell.settings.rejected` present in en/ko. |
| SHL-20 | OK | `version` then `selftest` only, isolated prefix. |
| SHL-21 | OK | `req()` titles -> `build/trace/junit-shell.xml` (`jest.config.js` reporter); `ci.yml:123-125` copies it per OS and reruns JT-SHL-19-01 separately. |

Doc-internal drift: Q-02 (`20_SHELL.md:190,193` "pending" rows vs `:3`/`:247`), Q-03 (`HANDOFF.md:27,36`).

## 3. Shell <-> engine contract

Verified consistent at `91620a0`: `buildSpawnRequest` (`launcher.ts:133-147`) emits only options the parser defines (`cli.py:48-63`: `-o`, `--cache`, `--provider`, `--model`, `--dpi`, `--min-priority`, `--max-units`/`--approve-threshold` from `orchestrate.DEFAULTS`, `--sensitive`, `--progress jsonl`, `--yes-file`, `--approved-by`); never `--report`, `--force`, `--yes`, `--prompt-version` or command-provider flags. Progress events consumed by `applyProgressEvent` match the emitters: `run_start.files` (`orchestrate.py:451`), `file_start.total` (`:455`), `file_end.units` (`:420`), `approve_required` (`:336`), `run_end.exit` (`:502`). Startup error object = `usage-error.stderr.json`; consent predicate `egress && requests_to_send > 0` (`coordinator.ts:83-85`) = `approve.py`; Base URL rule now byte-compatible with `canonical_destination` in the fail-open direction (P-06). FX-71 is the supported-host recording (P-03), so JT-11/13/15/17 replay the real 2.0.0 / Core 0.3.6 engine.

Gap (class A):

- **Q-01 (MINOR, P-02 / M3-V04 residual)** `releaseSegment` (`version-gate.ts:108`) mirrors the package gate's regex but not its second step `packaging.version.Version(text)` (`test_pt_release.py:296-304`). Spellings admitted by the shell and refused by the package gate: `3.14garbage` (T-GEN-96 `test_m4_docs.py:28`, the engine's own python case), `5.15.1abc`, `5.15.1..1`, `5.15.1+` (empty local), `5.15.1a1b2`. Direction: shell more permissive than the package gate, so a malformed `version` response could enable jobs the packaged acceptance would refuse. Fix: after the regex, require the public PEP 440 grammar (release `\d+(?:\.\d+)*`, optional `(a|b|rc)\d*`, `.post\d*`, `.dev\d*`, `+[A-Za-z0-9.]+`, case-insensitive, `-`/`_`/`.` separators as `packaging` normalises them) and keep the first three release parts; add `3.14garbage`, `5.15.1abc`, `5.15.1..1`, `5.15.1+`, `5.15.1a1b2` to the JT-17 bad list and `3.14.0rc1`, `0.3.6rc1`, `13.0.0+local`, `5.15.1-1` to the good list, mirroring all twelve T-GEN-96 parameters per field; reword `20_SHELL.md:96`, `30_TESTPLAN.md:406` and the JT-17 comment to name both steps.

## 4. Security

Re-verified: isolated interpreter and non-vault cwd for every spawn; absolute-only interpreter from the tab, from disk and at admission (P-04); no secret on argv; schema-2 allowlist; child env = SPEC baseline + UTF-8 + `MDFLOW_*` only for `openai-compatible`; logs allowlisted and redacted; yes-file/spool/consent/log dirs 0700, files 0600 (`node-apis.ts:74-79,106-108`); destination containment by real paths with pre-spawn revalidation; atomic single-job admission that a Cancel/unload now invalidates (M4-V01); Base URL refused up front exactly where the engine would refuse (P-06); 0 matches for `innerHTML`, `requestUrl`, `console.`, `eval(`, `new Function`, `electron.remote` in `shell/src`; presenter renders text nodes only (`progress.ts:165-177`); `require('electron')` used only for `shell.openPath`, `clipboard`, `webUtils` (`node-apis.ts:142-176`). NodeFs `list`/`realpath`/`isDirectory`/`isSymlink` swallow errors (`:90-132`), so a folder vanishing between pick and listing yields `shell.DESTINATION`, not an unhandled rejection.

Findings: none. Q-01 is a compatibility-admission mismatch, not a confidentiality/integrity/containment defect. Real-OS forced-cancel/no-live-process evidence is E-03 (class B).

## 5. Obsidian policy and submission rules

| Rule | Result |
|---|---|
| `isDesktopOnly:true`, id `markitdown-flow`, version 2.0.0, `minAppVersion 1.14.4`, `versions.json` entry and prior entries preserved | OK (`manifest.json`, `versions.json`). Obsidian 1.14.4 existence = MAN-04/E-09 (class B). |
| Description <= 250 chars, ends with a period | OK (90 chars). |
| Six command ids, no plugin prefix, sentence case | OK. |
| No self/dependency install; probes only, isolated | OK. |
| No telemetry, no remote fetch | OK. |
| Node/Electron behind the desktop guard; no `electron.remote` | OK. |
| No untrusted code execution path | OK (`-I`, non-vault cwd, absolute interpreter only). |
| `main.js` not committed; LICENSE, README present | OK (`.gitignore` `/main.js`). |
| README R16 disclosures | Present and consistent with code: isolated launch (`:19-26`), Base URL raw rule incl. aliases (`:39-43`), outside-vault access and sync (`:53-70`), telemetry (`:72-78`), key/cost/Cancel/Windows/temp dir (`:80-107`), picker/drop/reload/rejected settings/relative interpreter (`:119-131`), CLI with `-I` (`:145-157`). MAN-02/E-09 named review still owed (class B). |
| Release notes | `CHANGELOG.md:3-52` 2.0.0 entry with per-run progress, Windows caveat, rejected-settings/raw URL/relative interpreter lines. |
| Long work in `onload` | OK (background probe `main.ts:99`). |
| Operational handoff docs | **Q-03 (MINOR)**: `HANDOFF.md:36` still asks the orchestrator to re-run `npm run typecheck` before committing (done in `8303b03`); `:27` "Engine 536 pass … 266/266" after `:25` "568 passed" is the pre-fix snapshot but is not labelled as such; title `:1` still "MECE round 3". |

## 6. User-goal fit (classify -> selective OCR with consent, provenance, no re-transcription, markitdown-gc)

Engine/CLI: fits (Core 0.3.6 reference, unchanged evidence per M4_ENGINE_FIXES).

Plugin at `91620a0`: the `none` and `openai-compatible` paths run with isolated spawn, single-job admission that Cancel/unload can revoke, visible Cancel, per-run progress that never mixes Plan and Run counts, consent only where requests remain, distinguishable picker outcomes, Base URL and interpreter values refused up front with a notice and a reverted field. Remaining class-A gap: Q-01 (a garbage-suffixed `version` field could enable a job the package gate would refuse; no realistic installed engine emits such a string). Real-app behaviour (picker/`webkitdirectory`, drop, Cancel on real Windows) = E-03/E-09 (class B).

## 7. Simplicity (delete or merge)

| ID | Item | Action |
|---|---|---|
| Q-04 | `RECORDING_HOST_POLICY` (`jt-17-version-gate.test.ts:32`), `POLICY` (`jt-10-setup.test.ts:23`, `jt-20-selftest.test.ts:18`) are aliases of `RELEASE_LOCK`; the first name still implies a distinct recording-host policy that no longer exists | Delete the three aliases; use `RELEASE_LOCK` (or the default argument) directly |
| Q-02 | Two disposition rows assert a pending sync that `:3`/`:247` say is settled | Mark historical in one clause each |
| Q-03 | HANDOFF stale typecheck note, unlabelled snapshot line, stale title | Three one-line edits |
| (ok) | `JobStatusBar.events` gone; `isAbsolutePath` single definition; one `committed` contract; `summarizeProgress` is a three-line fold used by JT-09; `publish-fx71.mjs` replaces an undocumented copy | none |

No new dead code or duplicate oracle in `shell/src` in this round.

---

## 8. Consolidated findings

### 8A. Fixable in code/docs now (class A)

| ID | Sev | Owner | Location | Defect | Fix |
|---|---|---|---|---|---|
| Q-01 | MINOR | shell + docs | `process/version-gate.ts:108`; `jt-17-version-gate.test.ts:134-144`; `20_SHELL.md:96`; `30_TESTPLAN.md:406` | Shell mirrors the package gate's regex but not its `packaging.Version()` step; `3.14garbage` (T-GEN-96) and `5.15.1abc`/`5.15.1..1`/`5.15.1+`/`5.15.1a1b2` are admitted by the shell and refused by the package gate; docs claim agreement "on every spelling" (P-02 / M3-V04 residual) | PEP 440 grammar after the regex; JT-17 mirrors all twelve T-GEN-96 cases plus the five above; reword the two sentences and the comment |
| Q-02 | MINOR | docs (shell) | `20_SHELL.md:190,193` | Disposition rows still say engine synchronization / contract-test sync "remains pending", contradicting `:3` and `:247` (D-01 residual) | Add "(settled at DRAFT-3.5 / FX-71 M4)" or move to a historical note |
| Q-03 | MINOR | docs (HANDOFF) | `HANDOFF.md:1,27,36` | Stale "re-run `npm run typecheck` before committing" (done in `8303b03`); unlabelled pre-fix "536 / 266" line beside "568"; title still round 3 (D-03 recurrence) | Three one-line edits |
| Q-04 | MINOR | shell tests | `jt-17:32`, `jt-10:23`, `jt-20:18` | `RECORDING_HOST_POLICY`/`POLICY` aliases of `RELEASE_LOCK` after the widening was removed | Delete the aliases |

No BLOCKER or MAJOR remains open in code. Q-01 is one function plus one JT table; Q-02..Q-04 are text/alias edits.

### 8B. External evidence (class B; tracked in 90_ACCEPTANCE §7, not deducted)

E-01/E-12/E-13 (6 endpoint JUnits, 9 smokes, independent collections), E-02 (3-OS shell `npm ci && typecheck && build && jest`; the local receipt here is one Windows run, 277/277), E-03 (real-process JT-16 incl. Windows forced termination), E-04 (contract-min/max), E-05/E-14 (reference and compatibility installs), E-06/E-15 (tag, attestations, release gate), E-07 (`trace.py score` 100/100), E-08/E-09 (MAN-01..04), E-10 (packaged candidate replay), E-11 (post-deploy). The open PR #1 CI run is the first E-01/E-02/E-04/E-12 attempt; its result is not known at this snapshot and is not scored here.

---

## 9. Scores (0-100 from code/doc facts only; 100 iff no open class-A finding on the axis)

| Axis | M4 | M5 | Driver / exactly what blocks 100 |
|---|---|---|---|
| Shell docs <-> code | 91 | **96** | P-01/P-04/P-05/P-06/M4-V01 closed and documented (REQ-SHL-04/09/16 texts match code). Blocks: Q-01 (REQ-SHL-17 "agree on every spelling" is false for `3.14garbage`-class strings; 30_TESTPLAN `:406` same), Q-02 (`20_SHELL.md:190,193` pending-sync rows). |
| Contract consistency | 93 | **97** | Supported-host FX-71 published and verified; argv/options/events/consent/Base URL identical to the engine. Blocks: Q-01 (version-syntax parity lacks the `Version()` step). |
| Security | 95 | **100** | Absolute-only interpreter at every layer, revocable admission, raw-authority URL rule, no leak/injection/containment defect, 0 forbidden APIs. Nothing open in code or docs on this axis; real-OS cancel evidence is E-03 (class B). |
| Policy compliance | 94 | **98** | Manifest/commands/desktop/no-install/no-telemetry/README/CHANGELOG consistent; recipes isolated everywhere (D-02). Blocks: Q-03 (HANDOFF operational prose stale). MAN-02/04 are class B. |
| Goal fit | 90 | **98** | Per-run progress, revocable admission, early refusal of interpreter/URL values with notice + revert, consent filter, picker outcomes. Blocks: Q-01 (an untested garbage-suffixed interpreter spelling could be admitted where the package gate refuses). |
| Simplicity | 93 | **96** | Event history, five silent callbacks, duplicate `isAbsolutePath`, stale marker sentences and the "117" comment are gone. Blocks: Q-04 (three policy aliases), Q-02/Q-03 (five stale sentences). |

Round-5 exit condition for the shell (class A, all small): add the PEP 440 step to `releaseSegment` and mirror T-GEN-96 in JT-17 (Q-01); mark the two pending-sync rows historical (Q-02); fix the three HANDOFF lines (Q-03); delete the three `RELEASE_LOCK` aliases (Q-04); rerun jest/tsc/build. Everything else that remains is class B: E-01..E-15 (push/CI/MAN-01..04/reference/release).
