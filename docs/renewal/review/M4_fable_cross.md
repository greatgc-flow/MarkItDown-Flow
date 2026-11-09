# M4 cross-cutting MECE audit (Fable)

Reviewer: cc.fable. Date: 2026-11-09. Workspace = repo at `cadfe1f` (clean tree). Read-only: file reads, greps and one independent `npx jest --json` run from `shell/` (25 suites, **266/266 passed**, 0 failed). Engine 536 pass, `tsc --noEmit` clean and `npm run build` OK are taken from the orchestrator and `M3_ENGINE_FIXES.md`; tsc/build were not re-run here (sandbox). No code edits, no git.

Inputs read: all of `shell/src/**` after the M3 fix commit `9038074` (launcher, setup, coordinator, main, dom-picker, node-apis, node-spawner, spool-fs, spool, settings, settings-tab, entry-points, log, progress, version-gate, paths, env, engine-process, output-path, types), `esbuild.config.mjs`, `package.json`, FX-71 manifest and `version*.json`, JT-09/12/17 test sources, `20_SHELL.md`, `25_PACKAGING.md` sections 2-3, `HANDOFF.md`, `README.md`, `CHANGELOG.md`, `PACKAGING_VERIFICATION.md`, `engine/BOOTSTRAP.md`, `.github/workflows/ci.yml` jest job, engine `cli.py` parser, `orchestrate.py` run_end/temp dir/signals, `openai_compat.canonical_destination`, `tests/packaging/test_pt_release.py::gate`, `tests/matrix.toml` heading, the staged recording `build/trace/redgreen/m3-fx71-py314/manifest.json`, and the three M3 review files.

MAN-01 note (unchanged): the shell was implemented by this reviewer; every statement cites a file:line or fixture byte a second reader can check. R15 independence remains a named human gate.

Severity as before: BLOCKER = release-blocking MUST violation or user harm; MAJOR = MUST/doc-code mismatch with user-visible effect; MINOR = drift, dead code, UX. Two classes are kept strictly apart in this report: **(A) findings fixable in code/docs now** and **(B) items only human/CI evidence can close**. Class B never lowers a code score.

---

## 1. Verification of every M3_fable_cross finding

| ID | M3 sev | Status | Evidence at `cadfe1f` |
|---|---|---|---|
| N-02 | BLOCKER | **CLOSED** | `launcher.ts:24` `ENGINE_ARGV_PREFIX = ['-I','-X','utf8','-m','mdflow']` used by `buildSpawnRequest` (`:138`) and `buildUtilityRequest` (`:167`); `engineWorkingDirectory` (`:41-43`) = venv root; `coordinator.ts:110` cwd from it, `main.ts:240-243` probe cwd = venv root or home, `main.ts:261` version probe likewise; bootstrap probes `-I --version` (`setup.ts:13-17`); recipe `-I -m mdflow version|selftest` (`setup.ts:92-93,101-102`). JT-12 `jt-12-spawn-replay.test.ts:191,212` assert `argv[0..2]`, `-I` before `-m` and cwd outside the vault for coordinator, version probe, selftest and setup diagnostics. `cli.py:200-201` reconfigures stdio to UTF-8, so `-I` (implies `-E`) is safe. README `:19-24` and REQ-SHL-12 (`20_SHELL.md:76`) state the rule. |
| N-01 | MAJOR | **CLOSED** | `coordinator.ts:96-97,138-146` synchronous `reserved` flag taken before the first await, released in `finally`; JT-09 `jt-09-output-busy.test.ts:158-203` same-tick double submit with pending gate: one spawn, exactly one `shell.BUSY`; refusal releases. REQ-SHL-09 text (`20_SHELL.md:84`). |
| N-03 | MINOR | **CLOSED** | `coordinator.ts:279-287` notifies `plan.diagnostics` (EngineRun already maps startup errors to `engine.<CODE>` at `engine-process.ts:256`) and adds `shell.PROTOCOL` only when no diagnostic was produced. |
| N-04 | MINOR | **CLOSED (disclosure)** | README `:95-101` states Windows Cancel is always forced and names the `mdflow-*` temp-dir residue (`orchestrate.py:451`). Engine-side stale-dir cleanup was offered as optional in HANDOFF `:21`; `M3_ENGINE_FIXES.md` does not implement it. Acceptable as disclosed; no further action required for release. |
| N-05 | MINOR (MAN-04) | **CLOSED (code)**; MAN-04 open | `dom-picker.ts:33-41` `PickOutcome` `selected|cancelled|empty|blocked`; `:75,91-96` empty folder / unresolvable paths -> `empty`; `main.ts:219-233` notifies `shell.notice.pickerEmpty` (`i18n.ts:257,382`). Real Electron behaviour of `webkitdirectory` on large trees still needs the MAN-04 rehearsal (class B). |
| N-06 | MINOR | **CLOSED** | `dom-picker.ts:61` returns `blocked` when `navigator.userActivation.isActive` is false (`node-apis.ts:156-160`); `main.ts:227-229` notifies `pickerUnavailable`; no promise is left unsettled. |
| N-07 | MINOR | **CLOSED (residual P-06)** | `settings.ts:147-167` `isAcceptableBaseUrl` (https, or http for `localhost`/`127.0.0.1`/`[::1]`; no userinfo/query/fragment; control chars) applied in the tab (`settings-tab.ts:129-131`) and in `pickProvider` migration (`:224`); JT-04. Residual canonicalisation divergence vs the engine's raw check: P-06 below. |
| N-08 | MINOR | **CLOSED** | `settings-tab.ts:97` drop toggle carries `shell.settings.enableDragDropNote` (`i18n.ts:234,359`); README `:117-120`. |
| N-09 | MINOR | **CLOSED** | `settings-tab.ts:95,97,108` context-menu, drop and locale carry `shell.settings.reloadNote` (`i18n.ts:233,358`); README `:120-121`. |
| N-10 | MINOR | **CLOSED** | `FileSystemOps.readRange` (`types.ts:57-61`), `NodeFs.readRange` positional `fs.open/read` (`node-apis.ts:62-72`), `DirectorySpoolFs.read` delegates (`spool-fs.ts:27-29`); `Spool.finishWith` drains in 64 KiB windows with O(N) I/O (`spool.ts:50-55`). REQ-SHL-13 text (`20_SHELL.md:78`). |
| N-11 | MINOR | **CLOSED** | `main.ts:169-174` `mkdir(log.directory)` (0700, `node-apis.ts:106-108`) before `openFolder`; REQ-SHL-18 (`20_SHELL.md:98`). |
| N-12 | MINOR | **PARTIAL** | `20_SHELL.md:239` Open line reworded ("no `SYNC-AFTER-DRAFT-3` item remains"). But the marker is still asserted as pending in normative text: `20_SHELL.md:3` (status line), `:90` (REQ-SHL-16 "SPEC must distinguish..."), `:100` (REQ-SHL-20 "must match the final SPEC command"); `25_PACKAGING.md:3,61,63,184`; `30_TESTPLAN.md:525` ("JT-12..17 stay unverified until then"); `90_ACCEPTANCE.md:67`. SPEC 10.3 and `cli._selftest_documents` already satisfy these and FX-71 is a 2.0.0 recording, so the sentences contradict `20_SHELL.md:239`. D-01 below. |
| X-11 | MINOR (carried) | **OPEN, now shell-fixable (P-03)** | Engine owner staged a supported-host recording: `build/trace/redgreen/m3-fx71-py314/manifest.json` `recording_host.python = 3.14.10`, Core 0.3.6, 53 files verify (`M3_ENGINE_FIXES.md` X-11 row). The shell fixture is unchanged: `shell/test/fixtures/fx71/manifest.json:6-9` still `3.15.2`, `:12` Core `0.3.5`; `jt-17-version-gate.test.ts:29` still widens the policy to admit 3.15. Publication is a plain fixture swap plus deletion of `RECORDING_HOST_POLICY`; it is class A, not human evidence. (Cosmetic: the staged manifest's `argv` labels still read `python -m mdflow` without `-I`; the recorder itself runs `-I` per `T-GEN-92`.) |
| S-13 | MINOR | **CLOSED (one nit, D-03)** | `HANDOFF.md` rewritten for round 3 (`:1-21`), links the repair reports, lists owner handoffs. Nit: `:18` still says `tsc --noEmit` "must be re-run by the orchestrator before commit"; commit `9038074` reports tsc clean. |
| S-16 | MINOR | **CLOSED** | `esbuild.config.mjs:25` externals are `obsidian`, `electron`, builtins only. |
| S-17 | MINOR | **CLOSED** | 0 matches for `approvableHashes` in `shell/`. |
| S-18 | MINOR | **CLOSED** | `spool.ts` has `finishWith` and `discard` only. |
| S-19 | MINOR | **CLOSED** | `CoordinatorDeps` (`coordinator.ts:43-65`) has no `locale`. |
| S-20 | MINOR | **CLOSED** | `entry-points.ts:22-23` single `pathOf` resolver = `node-apis.filePath` (`node-apis.ts:143-152`); 0 matches for `legacyFilePath`. |
| S-21 | MINOR | **CLOSED** | `ui/output-path.ts:6` imports from `pure/paths`; no re-export. |

Round-3 scorecard: 20 items; 17 CLOSED, 1 PARTIAL (N-12 doc drift), 1 OPEN but shell-fixable now (X-11 publication), 1 CLOSED-in-code with a named manual gate (N-05/MAN-04). **No M3 finding is open in shell code.**

### 1b. cx -> shell handoffs listed in `M3_ENGINE_FIXES.md`

| Handoff | Status | Evidence |
|---|---|---|
| M3-V03 (Plan progress survives into Run; quadratic re-render) | **OPEN, shell** | `coordinator.ts:194` calls `progress.begin()` once per job; `:241` forwards every event of both the `plan` and the `run` process to the same sink; `progress.ts:128-132` appends to one array and `:143-158` re-reduces the whole history on every event; `phase()` (`:122-126`) changes the label only. Plan `file_end` units therefore add to Run counts and `filesEnded` can exceed `filesTotal`. P-01 below. |
| M3-V04 shell half (`5.15.1???` admitted) | **OPEN, shell** | `version-gate.ts:100-104` `releaseSegment` regex `^\s*(\d+)\.(\d+)(?:\.(\d+))?` is unanchored at the end and tolerates leading whitespace; package gate `test_pt_release.py:303` uses `re.fullmatch(r"[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)")`. Engine half (blank platform) is done on both sides (`version-gate.ts:155`, `test_pt_release.py:290-291`). P-02 below. |
| X-11 publication | **OPEN, shell** | See X-11 row; P-03. |
| M3-D01 matrix comment (`117 cells`) | **OPEN, horizontal owner** | `engine/tests/matrix.toml:414` still says "117 cells"; M3_cx counted 77 expanded declarations. Protected file; D-04 below (not a shell score driver). |
| `-I` in `BOOTSTRAP.md` / 25_PACKAGING recipes (shell -> engine/docs) | **OPEN, docs owner** | `engine/BOOTSTRAP.md:26-28,40-41` and `25_PACKAGING.md:30-31,41-42,79` still show `-m mdflow selftest|version` without `-I`, while the SetupModal recipe (`setup.ts:92-93,101-102`) and README `:145-148` show `-I`. REQ-PKG-05 requires `BOOTSTRAP.md` and SetupModal to show the same commands. D-02 below. |

---

## 2. Re-audit: shell docs <-> code (20_SHELL REQ-SHL-* vs `shell/src`)

| REQ | Status | Evidence / gap |
|---|---|---|
| SHL-01 | OK | JT-01 import/build-input scan; esbuild `absWorkingDir: shellDir`, entry `src/main.ts`. MAN-01 separate (class B). |
| SHL-02 | OK | Six ids, one `Platform.isDesktop` guard (`main.ts:72`), lazy `loadNodeApis` after it (`:74`). |
| SHL-03 | OK | Schema-2 allowlist, read-only path (`main.ts:87,295-300`), newer schema blocks. |
| SHL-04 | **1 MINOR (P-04)** | Text says "`enginePython` accepts only an absolute path" (`20_SHELL.md:64`). The tab enforces it (`settings-tab.ts:79`), but `validateV2` (`settings.ts:284`) accepts any printable string from disk, so a hand-edited or synced `data.json` with a relative interpreter survives migration; `snapshotJob` then throws and the user sees the unrelated `shell.DESTINATION` (`coordinator.ts:186-190`), and `engineWorkingDirectory('venv/bin/python')` yields the relative `venv`. Base URL rule, run-option bounds, reload/drop notes: OK. |
| SHL-05 | OK | temp+rename store, allowlisted snapshot, refused later saves (unchanged since M2). |
| SHL-06 | OK | env-only key, presence only, `MDFLOW_BASE_URL` from setting (`launcher.ts:120-124`), scrubbed child env (`env.ts:67-80`). |
| SHL-07 | OK | cap/sort/outcome, `historyInputLabel` (`coordinator.ts:88-91`). |
| SHL-08 | OK | DOM picker with four distinguishable outcomes, confirm modal, shared coordinator, drop never intercepts text/URL (`entry-points.ts:55-69`). |
| SHL-09 | **OK (1 MINOR, P-01)** | Destination/symlink/case rules, atomic admission (N-01), pre-spawn revalidation. "Progress details ... without inventing completed work": the presenter sums Plan and Run `file_end` units into one display (M3-V03), which overstates completed work for `openai-compatible` jobs. |
| SHL-10 | OK | probes only, background gate, committed absolute path only, cwd venv root or home. |
| SHL-11/12 | OK | argv array, `shell:false`, fixed `-I -X utf8 -m mdflow` prefix, cwd outside the vault, `-o`/`--cache` direct. |
| SHL-13 | OK | framing/spool/null-file; ranged reads (N-10). |
| SHL-14 | OK | one modal, literal text, Keep pending default, informational rows. |
| SHL-15 | OK | yes-file of needing-consent hashes only, `--approved-by plugin:modal`, removed in `finally` (`coordinator.ts:304-313,328-330`). |
| SHL-16 | OK | status-bar Cancel for plan/consent/run; cooperative then forced; Windows forced-only, disclosed. Real-OS runs: class B. |
| SHL-17 | **OK (1 MINOR, P-02)** | Complete 8-field gate; blank platform blocked (`version-gate.ts:155`). Version-syntax rule looser than the package gate (M3-V04 shell half). FX-71 host still 3.15 (P-03). |
| SHL-18 | OK | five x 1 MiB, allowlisted fields, redaction, mkdir before open. |
| SHL-19 | OK | codes/i18n parity by JT-SHL-19-01; new keys present in en/ko (`i18n.ts:232-234,256-257,357-359,381-382`). |
| SHL-20 | OK | `version` then `selftest` only, both with the isolated prefix. |
| SHL-21 | OK | `req()` titles -> junit; `trace.py` consumes. |

Doc-internal drift (D-01): normative sentences in `20_SHELL.md:3,90,100` still frame `SYNC-AFTER-DRAFT-3` as pending, contradicting `:239`.

## 3. Shell <-> engine contract

Verified consistent at `cadfe1f`: `buildSpawnRequest` emits only options present in `cli.py:48-63` (`-o`, `--cache`, `--provider`, `--model`, `--dpi`, `--min-priority`, `--max-units`, `--approve-threshold`, `--sensitive`, `--progress jsonl`, `--yes-file`, `--approved-by`); the shell never passes `--report`, `--force`, `--yes`, `--prompt-version` or command-provider flags; `run_end` keys `exit/files_ok/files_failed/provider_calls` (`orchestrate.py:501`) match `framing.ts`; startup error object matches `usage-error.stderr.json` and `engine-process.ts:185-203`; consent predicate `egress && requests_to_send > 0` identical on both sides; `-I` is compatible with the engine (`cli.py:200-201` UTF-8 reconfigure, no `PYTHON*` dependence); cooperative stop remains SIGTERM on POSIX and unavailable on Windows (`node-spawner.ts:57-58`, `orchestrate.py:57`).

Gaps (all class A):

- **P-03 (MINOR, carried X-11)** FX-71 in `shell/test/fixtures/fx71` is the Python 3.15.2 / Core 0.3.5 recording; the 3.14.10 / Core 0.3.6 recording is staged under `build/trace/` (gitignored). Publish the 53 files, delete `RECORDING_HOST_POLICY` (`jt-17-version-gate.test.ts:29`) so JT-17 runs against `RELEASE_LOCK`, and re-run JT-11..17.
- **P-02 (MINOR, carried M3-V04)** Version-syntax parity: anchor `releaseSegment` (`version-gate.ts:101`) to `^(\d+)\.(\d+)(?:\.(\d+))?(?:[A-Za-z0-9.+-]*)$` and reject leading whitespace, matching `test_pt_release.py:303`; add `5.15.1???` and `' 5.15.1'` to the JT-17 bad list and keep `5.15.1rc1`/`5.15.1.post1` admitted on both sides.
- **P-06 (MINOR, N-07 residual)** `isAcceptableBaseUrl` validates the WHATWG-normalised URL while `canonical_destination` (`openai_compat.py:33-48`) validates the raw text: `https://@api.openai.com/v1` (empty userinfo; engine rejects any `@` in netloc, `:43`), `http://0x7f000001/v1` and `http://127.1/v1` (WHATWG normalises to `127.0.0.1`; engine compares the literal host) pass the tab and fail at job time with `E_PROVIDER_CONFIG`. Fix: reject `@` anywhere in the authority and compare the raw host token (not `url.hostname`) against the loopback set; add these three to the JT-04 negative list.

## 4. Security

Re-verified: isolated interpreter and non-vault cwd for every spawn (N-02 closed); no secret on argv; schema-2 allowlist; child env = SPEC baseline + UTF-8 + four `MDFLOW_*` names only for `openai-compatible`; logs allowlisted and redacted; yes-file/spool/consent/log dirs 0700, files 0600; destination containment by real paths with pre-spawn revalidation; atomic single-job admission; no network API, `innerHTML` or `console.` in `shell/src` (0 matches; the only `innerHTML`/`requestUrl` hits are the test mock that forbids them); DOM picker returns paths only; `require('electron')` used only for `shell.openPath`, `clipboard`, `webUtils`.

Findings: no BLOCKER or MAJOR. Hardening only: **P-04** (accept only absolute `enginePython` from disk, consistent with the tab; a relative value is resolved against the child cwd by the OS, which is user-owned but not what REQ-SHL-04 promises). The engine `cwd` claim "never the vault" (README `:20-21`) is literally false when the user created the venv inside the vault; harmless under `-I`, see D-03.

## 5. Obsidian policy and submission rules

| Rule | Result |
|---|---|
| `isDesktopOnly:true`, id `markitdown-flow`, version 2.0.0, `minAppVersion 1.14.4`, `versions.json` entry and prior entries preserved | OK (unchanged). Existence of Obsidian 1.14.4 = MAN-04 TODO-VERIFY (class B). |
| Description <= 250 chars, ends with a period | OK (90 chars). |
| Six command ids, no plugin prefix, sentence case | OK. |
| No self/dependency install; probes only, isolated | OK (`setup.ts`, `selftest.ts`, `-I --version`). |
| No telemetry, no remote fetch | OK. |
| Node/Electron behind the desktop guard; no `electron.remote` | OK. |
| No untrusted code execution path | OK now: vault content cannot reach `sys.path` (N-02). |
| `main.js` not committed; LICENSE, README present | OK. |
| README R16 disclosures | Present and consistent with code: isolated launch (`:19-24`), Base URL rule (`:36-40`), outside-vault access and sync (`:49-66`), telemetry (`:68-74`), key/cost/Cancel/Windows/temp dir (`:76-103`), picker/drop/reload (`:115-121`), CLI with `-I` (`:137-158`). Named MAN-02 review still owed (class B). |
| Release notes | `CHANGELOG.md` 2.0.0 entry present. Nit (D-03): `:21-22` says "cooperative stop, forced after 5 s" without the Windows forced-only caveat the README states. |
| Long work in `onload` | OK (background probe). |

No policy finding beyond the D-03 nit.

## 6. User-goal fit (classify -> selective OCR with consent, provenance, no re-transcription, markitdown-gc)

Engine/CLI: fits (unchanged evidence; Core 0.3.6 reference with byte-identical triage per `M3_ENGINE_FIXES.md`).

Plugin at `cadfe1f`: end-to-end path for `none` and `openai-compatible` works with isolated spawn, single-job admission, visible Cancel/progress, consent only where requests remain, distinguishable picker outcomes, validated Base URL, reload notes. Remaining gaps (class A):

- **P-01 (MINOR, carried M3-V03)** Progress details mix Plan and Run counts (section 1b). Fix: reset the presenter's summary on each `run_start` (keep phase and Cancel), and maintain an incremental `ProgressSummary` instead of re-reducing the array; JT: Plan->consent->Run sequence with independently expected strings and a linear-work check.
- **P-05 (MINOR, new)** Rejected commits are silent: a non-absolute interpreter (`settings-tab.ts:76-80`), an unsafe output path (`:87-89`), a refused Base URL (`:129-131`) and a non-integer bound (`:148,155`) are dropped with no notice while the field keeps showing the rejected text, so the user believes the value was saved. Fix: one `shell.settings.rejected` notice (en/ko) and revert `inputEl.value` to the persisted value; JT-04 asserts both.
- **P-06** (section 3): a Base URL the tab accepts but the engine refuses.
- N-05 real-app behaviour (large `webkitdirectory` trees, Electron activation semantics) stays MAN-04 (class B).

## 7. Simplicity (delete or merge)

| ID | Item | Action |
|---|---|---|
| P-01 | `progress.ts:92,128-158` whole-history array + full re-reduce per event | Incremental summary; delete the array |
| D-01 | `SYNC-AFTER-DRAFT-3` asserted pending in 9 places across four docs while `20_SHELL.md:239` says none remains | Delete the sentences or mark them historical; one status statement |
| D-03 | `HANDOFF.md:18` tsc note; CHANGELOG missing Windows caveat; README "never the vault" cwd wording | Three one-line edits |
| D-04 | `engine/tests/matrix.toml:414` "117 cells" (actual 77) | Horizontal owner |
| (ok) | S-16..S-21 all deleted; `DirectorySpoolFs` in its own module; no dead export found in this pass | none |

No new dead code or duplicate oracle was found in `shell/src` in this round.

---

## 8. Consolidated findings

### 8A. Fixable in code/docs now

| ID | Sev | Owner | Location | Defect | Fix |
|---|---|---|---|---|---|
| P-01 | MINOR | shell | `ui/progress.ts:128-158`, `ui/coordinator.ts:194,241` | Plan and Run events share one summary; quadratic re-render (M3-V03) | Reset on `run_start`, incremental summary, Plan->Run JT |
| P-02 | MINOR | shell | `process/version-gate.ts:100-104` | `releaseSegment` admits `5.15.1???` / leading space; package gate rejects (M3-V04) | Anchored regex matching `test_pt_release.py:303`; JT-17 cases |
| P-03 | MINOR | shell | `shell/test/fixtures/fx71/*`, `jt-17-version-gate.test.ts:29` | FX-71 still recorded on Python 3.15.2 / Core 0.3.5 although a 3.14.10 / 0.3.6 recording is staged (X-11) | Publish the 53 staged files; drop `RECORDING_HOST_POLICY`; rerun JT-11..17 |
| P-04 | MINOR | shell | `pure/settings.ts:284`, `ui/coordinator.ts:186-190` | Relative `enginePython` accepted from disk against REQ-SHL-04; failure surfaces as `shell.DESTINATION` | `isAbsolutePath` in `validateV2` (reset + notice); map interpreter snapshot failure to `shell.RUNTIME`; JT-03/04 |
| P-05 | MINOR | shell | `ui/settings-tab.ts:76-80,87-89,129-131,148,155` | Rejected commits are silent and the field keeps the rejected text | Notice + revert; JT-04 |
| P-06 | MINOR | shell | `pure/settings.ts:155-167` | Base URL check on the normalised URL diverges from the engine's raw check (`https://@host`, `http://0x7f000001`, `http://127.1`) | Reject `@` in authority; compare raw host token; JT-04 negatives |
| D-01 | MINOR | docs (shell/pkg/testplan/acceptance) | `20_SHELL.md:3,90,100`; `25_PACKAGING.md:3,61,63,184`; `30_TESTPLAN.md:525`; `90_ACCEPTANCE.md:67` | `SYNC-AFTER-DRAFT-3` still asserted pending; contradicts `20_SHELL.md:239` and the 2.0.0 FX-71 recording (N-12 residual) | Remove or mark historical |
| D-02 | MINOR | docs (engine/pkg) | `engine/BOOTSTRAP.md:26-28,40-41`; `25_PACKAGING.md:30-31,41-42,79` | Recipes lack `-I` while SetupModal/README show it; REQ-PKG-05 requires equality | Add `-I` to the five lines |
| D-03 | MINOR | docs | `HANDOFF.md:18`; `CHANGELOG.md:21-22`; `README.md:20-21` | Stale tsc note; missing Windows forced-cancel caveat; "never the vault" overclaim when the venv lives inside the vault | Three one-line edits ("not on the import path") |
| D-04 | MINOR | horizontal owner | `engine/tests/matrix.toml:414` | "117 cells" stale (77) | Correct the comment |

No BLOCKER or MAJOR remains open in code. P-01..P-06 are each a one-function change plus one JT case; D-01..D-04 are text edits.

### 8B. Closable only by human or CI evidence (do not lower code scores)

| Gate | What it needs | Why local work cannot close it |
|---|---|---|
| MAN-01 (R15 clean-room) | Named implementer and a different named reviewer; `trace.py attest MAN-01` | Independence is a human attestation; JT-01 is supportive only |
| MAN-02 (R16 README) | Named reviewer citing README anchors against configured behaviour | Disclosure accuracy is a human judgement; this audit's section 5 is not that sign-off |
| MAN-03 (en/ko meaning) | Named bilingual reviewer | Key parity (JT-SHL-19-01) is not meaning |
| MAN-04 (release rehearsal) | 3 OS x Obsidian min/current: picker/`webkitdirectory` under real Electron activation, drop, Cancel incl. real Windows forced termination, 1.0.8 upgrade/rollback, terminal env launch | Requires the real app and OS; Jest fakes the DOM and spawner |
| 3-OS CI | A push that runs `ci.yml` jest job (`:102-130`: windows-2022/ubuntu-24.04/macos-15-intel, Node 24.22.2, `npm ci`, typecheck, build, 266 jest, JT-SHL-19-01) and the engine matrix | Local Windows receipts (266 jest here; 536 pytest per cx) are single-host |
| Reference install / release | Linux x64 / Python 3.14 Core 0.3.6 hash-mode reference, six endpoint receipts, provenance, tag, `versions.json` agreement, published assets | Release pipeline and remote hosts |

---

## 9. Scores (0-100; 100 only with no open class-A finding)

| Axis | M3 | M4 | Driver / exactly what blocks 100 |
|---|---|---|---|
| Shell docs <-> code | 82 | **91** | All N-01..N-11 closed and documented. Blocks: P-04 (REQ-SHL-04 absolute-only not enforced on disk values), P-01 (REQ-SHL-09 "without inventing completed work"), D-01 (`SYNC-AFTER-DRAFT-3` contradictions in 20_SHELL). |
| Contract consistency | 88 | **93** | argv prefix/cwd/options/events/consent/exit identical to engine. Blocks: P-03 (fixture host 3.15 / Core 0.3.5), P-02 (version-syntax parity), P-06 (Base URL parity). |
| Security | 60 | **95** | N-02 and N-01 closed with asserting JTs; no leak, injection or containment defect. Blocks: P-04 (relative interpreter accepted from disk). Real-OS cancel/no-live-process evidence is class B and does not count here. |
| Policy compliance | 90 | **94** | Manifest/commands/desktop/no-install/no-telemetry/README consistent; vault content can no longer select executed code. Blocks: D-03 (CHANGELOG lacks the Windows caveat; README cwd wording), D-02 (BOOTSTRAP recipe differs from SetupModal, REQ-PKG-05). MAN-02/04 are class B. |
| Goal fit | 84 | **90** | Isolated spawn, single job, Cancel/progress, consent filter, picker outcomes, Base URL validation. Blocks: P-01 (progress counts), P-05 (silent rejected settings), P-06 (late Base URL failure). |
| Simplicity | 86 | **93** | S-16..S-21 done; one status source in HANDOFF. Blocks: P-01 (whole-history presenter), D-01/D-03 (nine stale sync sentences, three nits), D-04 (matrix comment, other owner). |

Round-4 exit condition for the shell (class A, all small): publish the staged FX-71 and drop the widened JT-17 policy (P-03); make the progress presenter per-run and incremental (P-01); anchor `releaseSegment` (P-02); enforce absolute `enginePython` in `validateV2` and notify/revert rejected settings commits (P-04, P-05); tighten `isAcceptableBaseUrl` to the engine's raw rule (P-06); then delete the stale `SYNC-AFTER-DRAFT-3` sentences and add `-I` to the two recipes (D-01, D-02, D-03). Rerun jest/tsc/build. Everything else that remains is class B: MAN-01..04, the 3-OS CI run, the reference install and the release itself.
