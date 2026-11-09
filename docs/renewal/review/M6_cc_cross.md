# M6 cross-cutting MECE audit (cc)

Reviewer: cc. Date: 2026-11-09. Workspace = repo, branch `feat/r34-gc-0.3.7` (HEAD `7a80669`, clean at start). Read-only: file reads, greps, `sha256sum`/`wc -c` on four FX-71 version files, and one `npx jest --ci --reporters=default` from `shell/` (**27 suites, 296/296 passed**, 5.0 s; default reporter only, so no receipt XML was rewritten). Engine 667 pass, `tsc` clean and 3-OS CI green are taken from the orchestrator; tsc and the build were not re-run here (sandbox). No code edits, no git. The only file written is this one.

Inputs: `M5_fable_cross.md`, `M5_cx_vertical.md`, `M6_ag_horizontal.md`, `20_SHELL.md`, `HANDOFF.md`, `README.md`, `CHANGELOG.md`, `manifest.json`, `30_TESTPLAN.md` JT rows, `90_ACCEPTANCE.md` (greps), SPEC 10.1/CNV-06/CNV-07 lines; `shell/src` (`process/version-gate.ts`, `launcher.ts`, `setup.ts`, `ui/coordinator.ts`, `settings-tab.ts`, `setup-modal.ts`, `results-modal.ts`, `progress.ts`, `main.ts`, `pure/env.ts`, `pure/settings.ts`, `pure/i18n.ts`), FX-71 `version*.json` + `manifest.json`, `publish-fx71.mjs`, JT-17/JT-R32/JT-R33 sources, engine `cli.py`, `convert.py`, `exiftool.py`, `ci.yml`.

Two classes stay apart: **(A)** findings fixable in code/docs now, **(B)** external evidence E-01..E-15 (tracked in 90_ACCEPTANCE §7, never deducted). Severity: BLOCKER = release-blocking MUST violation or user harm; MAJOR = MUST/doc-code mismatch or contract risk with user-visible effect; MINOR = drift, dead code, UX.

---

## 1. Verification of every M5_fable_cross finding

| ID | M5 sev | Status | Evidence at HEAD |
|---|---|---|---|
| Q-01 (gate parity with `packaging.Version`) | MINOR | **CLOSED** | `version-gate.ts:136` charset step, `:146` PEP 440 public grammar (pre `a/b/c/rc/alpha/beta/pre/preview`, post `-N`/`post/rev/r`, dev, local; case-insensitive), `:156-163` `releaseSegment` applies both steps and keeps three release parts. Compared by hand with `packaging`'s `VERSION_PATTERN`: the only parts it omits (epoch, `v`, `_`, whitespace) are already excluded by step one. JT-17 `:117-171`: 16 valid, 12 charset-bad, 11 PEP-440-bad spellings, the twelve T-GEN-96 cases per field with the field's blocked reason, plus five negative and five positive cross-field cases. REQ-SHL-17 (`20_SHELL.md:96`), `30_TESTPLAN.md:415`, `CHANGELOG.md:42-43`, row `20_SHELL.md:218` name both steps. |
| Q-02 (pending-sync rows) | MINOR | **CLOSED** | `20_SHELL.md:190` now "Engine/acceptance edits remain outside this file"; `:193` "engine synchronization is complete; actual OS receipts remain external". `:3` and `:254` agree. |
| Q-03 (HANDOFF) | MINOR | **CLOSED for the three named lines** | Title `HANDOFF.md:1` "rounds 3-5 and owner directives R29-R34"; `:27` labelled "Pre-fix round-4 snapshot (historical; superseded…)"; `:36` says the orchestrator re-ran `npm run typecheck`, clean at `8303b03`. Residual stale sentences elsewhere in the same file: M6-06. |
| Q-04 (`RECORDING_HOST_POLICY`/`POLICY` aliases) | MINOR | **CLOSED** | 0 matches in `shell/` for either name. JT-10/12/17/20 use `RELEASE_LOCK` or the default argument. |
| P-02, D-01, D-03, Q-01..Q-04 chain | - | closed as above | The M5 residual list (Q-01..Q-04) is empty. |

Carried rows re-checked, no regression: P-01 (`progress.ts` per-run summary, one `JobStatusBar.summary`), P-03 (`version.json` 354 B, sha `c4c0d295…`, equals manifest `:782-783`; `core-out-of-range` 383 B `5c66762c…`, `core-unavailable` 389 B `13c93bed…`, `python-3.15` 382 B `512e6293…`, all equal their manifest rows), P-04 (`coordinator.ts:168` absolute-only interpreter before the gate), P-05 (`settings-tab.ts:72-89` `committed`), P-06 (JT-04 green), M4-V01 (`coordinator.ts:146-161,170-199` admission re-checks; JT-16 green). Whole shell suite 296/296.

## 2. Shell parts of R32 / R33 / R34

| Item | Status | Evidence |
|---|---|---|
| R32 settings tab in five headed sections | **CLOSED** | `settings-tab.ts:42,109-110,123-235` (Engine, Conversion, OCR provider, Consent & privacy, Advanced; every `runOptions` field exposed; no LLM settings); JT-04 `jt-r32:76`. |
| R32 consent summary table, Keep pending default | **CLOSED** | JT-14 `jt-r32:123`; REQ-SHL-14 text (`20_SHELL.md:86`) agrees (Keep pending default, Approve secondary row `:216`). |
| R32 status-bar Cancel accessible label | **CLOSED** | `progress.ts:137-141`, `aria-label` + `title`. |
| R32 ResultsModal from decoded report only | **CLOSED** | `results-modal.ts:40-58` projection, `coordinator.ts:364` only when `run.stdout?.ok`; JT-09 `jt-r32:208,258` (cancelled/report-less run shows nothing). Never inferred from created files. |
| R32 history table, styles | **CLOSED** | JT-07 `jt-r32:271`, JT-01 `jt-r32:400` (CSS variables only, `:focus-visible`). |
| R33 `enableLegacyPreconvert` (schema 2, off, non-boolean resets with notice) | **CLOSED** | `settings.ts:49,102,114`; JT-04 `jt-r33:74`; REQ-SHL-04 text `20_SHELL.md:64`. |
| R33 `--preconvert-legacy` on `plan`/`run` only when on, no timeout flag | **CLOSED** | `launcher.ts:21,153`; engine parser accepts it on both (`cli.py:62-63`); JT-12 `jt-r33:149`. |
| R33 `EXIFTOOL_PATH`/`SOFFICE_PATH` forwarded for every provider; presence-only display | **CLOSED** | `env.ts:38,81,98-101`; JT-06 `jt-r33:170`; REQ-SHL-06 text `20_SHELL.md:68`. |
| R33 tool status lines (SetupModal, settings tab), `"unavailable"` = missing | **CLOSED** | `setup-modal.ts:18-30,129-130`, `settings-tab.ts:21-26`, `version-gate.ts:209-219`; JT-10/JT-17 `jt-r33:186,266`. |
| R33c co-install guard: exit-1 `E_CORE_CONFLICT` -> `core_conflict`, fix command shown, never executed | **CLOSED** | `version-gate.ts:233-246,335-337`, `setup.ts:118-121,177-187`, `setup-modal.ts:110-116`; stderr shape equals engine `cli.py:101-104,329-330`; JT-17 `jt-r33:221,423`, JT-10 `:302`. |
| R33 derived result marking (`W_PRECONVERTED{tool,version}`, `fidelity: DERIVED`) | **CLOSED** | `results-modal.ts:45-54,98-103`; engine shape `convert.py:126-128`; JT-09 `jt-r33:350`; en/ko codes JT-SHL-19-01 `jt-r33:413`. |
| R34 Core admission `>=0.3.7,<0.4` and bootstrap text | **CLOSED** | `version-gate.ts:95-96`, `setup.ts:39`, `engine/BOOTSTRAP.md:22,38`, `25_PACKAGING.md:13,28,39`, `engine/pyproject.toml:11`, `cli.py:85-93`. |
| R34 FX-71 version stream refreshed | **CLOSED (bytes)**, drift in prose | Manifest `:12` `markitdown-gc 0.3.7`, `version.json` real isolated probe with libreoffice fields, per-file note `:785`. Prose drift: M6-05. |
| M5 cx carried shell items | M5-V01 **CLOSED** (= Q-01); M5-D01 **CLOSED** (= Q-02); M5-D02 **PARTIAL** (normative text fixed, comments and HANDOFF not: M6-06/M6-07); M5-S01 **OPEN** (M6-04); M5-O01 (trace consumer) not re-verified here (tools owner; `tools/trace.py:359,495` now has `collect_shell`/`shell_rows_passed`). |

## 3. New defects (class A)

### M6-01 MAJOR (contract / goal fit): the `version` gate probe can time out on a healthy engine because the engine's optional-tool probes are not inside its 5 s budget, and a blocked gate is cached

- The shell gives the whole `version` command **5 000 ms** (`version-gate.ts:249`, REQ-SHL-10 "five-second timeout"). Since R31/R33 the engine's `version` runs two optional probes before it prints: `exiftool.detect()` with `_TIMEOUT_S = 15` (`exiftool.py:26,36`) and the LibreOffice probe with `timeout_s=5` (`cli.py:224`, SPEC 10.1 `10_SPEC.md:593` "five-second deadline"), after Python start and the Core import. Worst case is therefore above 20 s; one cold `soffice --version` (profile creation, antivirus scan on Windows) of 3-5 s on top of start-up already approaches the shell's whole budget. SPEC says the probes "never change the compatibility gate", but their latency does.
- Failure path: `probeVersion` -> `blocked('timeout')` (`version-gate.ts:333`); `main.ts:266-270` stores the blocked gate; `currentGate()` returns any truthy cached gate (`main.ts:250-254`); `coordinator.ts:173` refuses every job as `shell.RUNTIME` until the user changes the interpreter or opens the Setup modal and refreshes. There is no automatic retry for `timeout`/`spawn_failed`.
- Status: derived from the code bounds above, **not measured** (no real LibreOffice here). No test models a slow optional probe; the 5 s timeout tests use a silent child (JT-17 `probe(...)` helpers).
- Fix (small): keep optional-tool probing out of the gating latency, either by giving the shell's `version` probe a budget that exceeds the engine's worst case (or the engine bounding the total below 5 s), and do not cache `timeout`/`spawn_failed` gates (re-probe on the next job). Add a JT-17 case: a child that answers after the first deadline then succeeds on the second job.

### M6-02 MINOR (goal fit): the migrated `pythonPath` hint is rendered unquoted in the copyable recipe

`setup.ts:165` takes `deps.bootstrapPythonHint` verbatim as `bootstrapPython`; `renderBootstrapInstructions` puts it unquoted at `:96` (`${paths.bootstrapPython} -m venv …`) and `:105`. The hint is any printable string up to 4 096 characters (`settings.ts:143-145`, `:301-304,326`). A real v1 value such as `C:\Program Files\Python312\python.exe` (spaces) yields a Windows block that fails in PowerShell, and a synced/hand-edited hint is pasted as shell text. Probe candidates like `py -3` legitimately need to stay a command plus arguments, so the hint needs its own rendering (quote it as an executable path, `& 'path'` on Windows). Not a new trust boundary (a writer of `data.json` already controls `enginePython`), so not charged to Security. Untested: JT-10 `:101,110` only render `py -3.14` / `python3.14`.

### M6-03 MINOR (docs <-> code): POSIX commands use PowerShell quote escaping

`setup.ts:83-85` `quote()` doubles single quotes (PowerShell). The same function builds the POSIX lines (`:102-109`) and the POSIX uninstall command (`:118-121`). In `sh`, `'/Users/o''brien/venv/bin/python'` is `/Users/obrien/venv/bin/python`: the apostrophe is dropped and the copied command points at a different path. Quotes always balance, so no injection, only a wrong command. No test uses an apostrophe. Fix: a POSIX quoter (`'\''`) for the posix lines and the POSIX uninstall command; add one apostrophe case to JT-10 and JT-R33.

### M6-04 MINOR (simplicity / lifetime), carried from cx M5-S01, still open

`coordinator.ts:254-259` `cancelSignal()` appends a resolver to `cancelWaiters` for every consent race (`:317`); only `cancel()`/`dispose()` drains it (`:240`), and the job finalizer (`:218-222`) does not. One resolver closure stays alive per completed consent job for the plugin's lifetime. No wrong authorization or process leak. Fix: remove the waiter when the race settles (return an unsubscribe) and add a three-job lifecycle assertion (retained waiters 0 after normal approve/dismiss).

### M6-05 MINOR (docs <-> code): stale statements about LibreOffice reporting and the recording's Core version

- `20_SHELL.md:220` still says "`version` does not report LibreOffice in SPEC 10.1 yet … shows 'not reported' until the engine emits them (handoff to cx)". SPEC 10.1 now defines the fields (`10_SPEC.md:587,593`), the engine emits them (`cli.py:208-230,276`), and FX-71 `version.json` carries them. "Not reported" remains only for older engines.
- `90_ACCEPTANCE.md:67` and `20_SHELL.md:254` describe the published recording as "Python 3.14.10, Core 0.3.6", while the manifest header (`manifest.json:12`), `version.json` and `20_SHELL.md:256` say 0.3.7. The truth is a hybrid (only the version stream and its variants were refreshed, `manifest.json:785`); no document states that in one place, and `90_ACCEPTANCE.md:67` also says "Re-record whenever the engine changes".
- Fix: edit the R33 row to "now emitted; older engines show 'not reported'"; reword the two sentences to "version stream refreshed from Core 0.3.7; other streams recorded under 0.3.6 and retained".

### M6-06 MINOR (docs): HANDOFF is stale in three places and has no R32-R34 shell section

`HANDOFF.md:9` still lists "supported-host FX-71 publication by its owner" as pending (done in M4, `:35`); `:15` still says the cwd is "never the vault or the plugin folder" (a venv selected inside the vault gives a cwd inside it: `20_SHELL.md:76`, `README.md:21-23`); the title `:1` promises R29-R34 but no shell R32/R33/R34 section exists (only `20_SHELL.md:216,220,256`).

### M6-07 MINOR (code comments): residual unconditional-cwd and flag-name claims (M5-D02 remainder)

`launcher.ts:45-46` ("is not vault content"), `:169` ("a fixed cwd outside the vault"), `coordinator.ts:110` ("never the vault"), `main.ts:241-242` ("Never the vault or the plugin folder"), JT-12 titles `:191,212` ("outside the vault"; the fixture venv is outside, the rule is not). Also `settings.ts:47` names `--legacy-preconvert` (the flag is `--preconvert-legacy`, `launcher.ts:21`), and `jt-r33:352` cites `preconvert.prepare`, a module R34 deleted.

### M6-08 MINOR (policy, R16 disclosures)

- `README.md:53-60` (Outside-vault access) and `25_PACKAGING.md:125` list the engine, venv, sources, temp rasters and cache, but not the two optional external programs. exiftool is started automatically for standalone `png|jpg|jpeg` when found and writes lines such as `GPSPosition`, `Author` and `Artist` into the converted note (SPEC CNV-06, `10_SPEC.md:101`); the README never says so (only `:142-143` names it as a diagnostic). LibreOffice is disclosed only in the migration paragraph (`:133-146`).
- `README.md:137-138` says LibreOffice runs "in an isolated profile without network access". SPEC CNV-07 (`10_SPEC.md:823`) and the README's own command section (`:177-178`: macros and link updates disabled) support a private profile with macros/link updates off, not blocked network access.
- Fix: add one sentence each to README Outside-vault access and `25_PACKAGING.md:125` for exiftool and LibreOffice (what they read, what is written), and drop or source "without network access".

## 4. Re-audit by axis

- **Shell docs <-> code.** REQ-SHL-01..21 match code and the 296 tests except the stale prose in M6-05/06/07 (REQ-SHL-17, 04, 06, 10, 12 texts verified against code this round).
- **Contract.** argv options, progress events, startup error object, consent predicate, Base URL rule and the `version` field set (including `libreoffice*`, status vocabulary `ok|not_found|unusable` inside the shell's superset) equal the engine. The shell admits `0.3.7rc1` Core on the release segment while the engine's own `_check_core` (`cli.py:90-93`) refuses it at run time; this is the benign direction (engine refuses, not charged). One open contract risk: M6-01.
- **Security.** Re-verified: isolated interpreter prefix, absolute-only interpreter at every layer, revocable admission, raw-authority Base URL rule, env scrub (+ tool paths only), 0 matches for `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`requestUrl`/`console.`/`eval(`/`new Function`/`electron.remote`/`fetch(`/`shell:true` in `shell/src`; new R32/R33 modals render text nodes only; the uninstall command is rendered text, never run. No confidentiality, integrity or containment defect. M6-02 is not charged here: anyone who can write `data.json` can already set `enginePython`.
- **Policy.** Manifest (`isDesktopOnly:true`, id, version 2.0.0, `minAppVersion 1.14.4`, 80-char description with period), six commands, no install/telemetry/fetch, README/CHANGELOG consistent with the R33/R34 behavior; open: M6-08.
- **Goal fit.** Classify -> selective OCR with consent/provenance/Core delegation holds on the supported path; legacy conversion is opt-in, derived and marked. Open: M6-01 (a healthy engine can look unavailable), M6-02.
- **Simplicity.** No new dead code or duplicate oracle in `shell/src`; `engineSubcommand`/`SUBCOMMAND_INDEX` are exported only for test oracles (acceptable). Open: M6-04.

## 5. Consolidated class-A findings

| ID | Sev | Location | Fix size |
|---|---|---|---|
| M6-01 | MAJOR | `version-gate.ts:249,333`; `main.ts:250-276`; `cli.py:224`; `exiftool.py:26` | one budget/caching change + one JT-17 case |
| M6-02 | MINOR | `setup.ts:96,105,165` | quote the hint, one test |
| M6-03 | MINOR | `setup.ts:83-85,102-109,118-121` | POSIX quoter, one test |
| M6-04 | MINOR | `coordinator.ts:106,240,254-259,317` | unsubscribe on race end, one test |
| M6-05 | MINOR | `20_SHELL.md:220,254`; `90_ACCEPTANCE.md:67` | three sentences |
| M6-06 | MINOR | `HANDOFF.md:1,9,15` | three edits + short R32-R34 shell section |
| M6-07 | MINOR | `launcher.ts:45-46,169`; `coordinator.ts:110`; `main.ts:241-242`; `settings.ts:47`; `jt-r33:352`; `jt-12:191,212` | comment edits |
| M6-08 | MINOR | `README.md:53-60,137-138`; `25_PACKAGING.md:125` | two sentences + one removal |

No BLOCKER. One MAJOR (M6-01, derived not measured). External evidence E-01..E-15 is not deducted.

## 6. Scores (0-100 from code/doc facts only; 100 iff no open class-A finding on the axis)

| Axis | M5 | M6 | Exactly what blocks 100 |
|---|---|---|---|
| Shell docs <-> code | 96 | **95** | M6-05 (R33 row and 0.3.6 statements), M6-06 (HANDOFF), M6-07 (stale comments/flag name). Q-01/Q-02 closed. Dropped 1 because R33/R34 added new stale prose faster than M5's residuals closed. |
| Contract consistency | 97 | **94** | M6-01 (version probe budget vs optional-tool probes; cached blocked gate). Q-01 closed. |
| Security | 100 | **100** | Nothing open (M6-02/03 are correctness of copied text, not a trust-boundary defect). |
| Policy compliance | 98 | **96** | M6-08 (R16 disclosure of exiftool/LibreOffice execution and metadata written to notes; unsupported "without network access"). M6-06 operational prose. |
| Goal fit | 98 | **93** | M6-01 (healthy engine can be shown unavailable with no automatic recovery), M6-02 (migrated v1 interpreter hint with spaces yields a broken recipe), M6-03. |
| Simplicity | 96 | **97** | M6-04 (retained cancel waiters). Q-04 closed. |

Exit condition for 100 on every axis: fix M6-01..M6-08 (one budget/caching change, three small code fixes with tests, five doc/comment edits), rerun jest/tsc/build. Everything else that remains is class B (E-01..E-15).

Not verified here: `tsc` and `npm run build` (taken from orchestrator), M5-O01 scorer internals, Core 0.3.7's actual LibreOffice behavior (external), real-OS cancel (E-03).
