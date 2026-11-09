# M7 cross-cutting MECE audit (cc)

Reviewer: cc. Date: 2026-11-09. Workspace = repo, branch `main` (PR #2 merged, HEAD `c40a704`). Read-only: file reads, greps and one `npx jest --ci --reporters=default` from `shell/` (**28 suites, 310/310 passed**, 4.1 s; default reporter, no receipt XML rewritten). Engine 685 pass, `tsc` clean and 3-OS CI green are taken from the orchestrator and were not re-run (sandbox); no git was run. No code edits. The only file written is this one.

Inputs: `M6_cc_cross.md`; `shell/src` (`main.ts`, `process/version-gate.ts`, `process/setup.ts`, `ui/coordinator.ts`, `ui/setup-modal.ts`, `pure/i18n.ts`); `shell/test/jt-m6-shell-round6.test.ts` and the JT-10/17 sources; `20_SHELL.md` (REQ-SHL-10/17, rows 218-221, 255), `HANDOFF.md`, `README.md`, `CHANGELOG.md`, `25_PACKAGING.md:125`, `90_ACCEPTANCE.md` (E-16 row, `:67`), `manifest.json`, `versions.json`.

Two classes stay apart: **(A)** findings fixable in code or docs now; **(B)** external evidence (E-01..E-15, plus E-16 added in M6 for the cold-start measurement), tracked in 90_ACCEPTANCE §7 and never deducted. Severity: BLOCKER = release-blocking MUST violation or user harm; MAJOR = MUST/doc-code mismatch or contract risk with user-visible effect; MINOR = drift, UX, copy-text correctness.

---

## 1. Verification of every M6_cc_cross finding

| ID | M6 sev | Status | Evidence at HEAD |
|---|---|---|---|
| M6-01 (version probe budget; blocked gate cached) | MAJOR | **CLOSED** (code); measurement is external E-16 | Engine side: the cx disposition appended to M6 (0.5 s deadline per optional probe, cached outcomes, T-CLI-87/88/89, 685 pass). Shell side: `version-gate.ts:332` `VERSION_PROBE_BACKOFF_MS = 1000`; `:338-340` `isTransientGate` (timeout, spawn_failed); `:343-350` `probeVersion` retries a timeout exactly once; `main.ts:254-258` `currentGate` returns a cached gate only when it is not transient, else `refreshGate()`; `main.ts:261-280` shares the in-flight probe and drops a result superseded by an interpreter change; `setup-modal.ts:112` shows `shell.setup.probeTimeout` (en `i18n.ts:280`, ko `:484`) instead of "blocked (timeout)". Tests `jt-m6-shell-round6`: retry-once and double-timeout (`:72,80`), `isTransientGate` table (`:98-105`), plugin-level "spawn failure at load is not cached; next job re-probes; a definite verdict is cached" (`:107-128`), incompatibility verdict stays cached with one probe (`:130+`), Setup modal wording in both locales (`:145`). Docs: REQ-SHL-10 and REQ-SHL-17 name per-attempt 5 s, one retry after 1 s, never-cached transient gates; `30_TESTPLAN.md:415`; `CHANGELOG.md:56-57`; `20_SHELL.md:221`; E-16 in ACCEPTANCE. |
| M6-02 (unquoted migrated hint) | MINOR | **CLOSED** | `setup.ts:94` `PLAIN_COMMAND`, `:101-104` `bootstrapCommand` (plain command stays; else `& 'path'` on Windows, `sh` quote on POSIX), used at `:116,125`. Test `:202-232`: spaced Windows path, spaced POSIX path, five plain commands, `python3; rm -rf ~` stays inside quotes, end-to-end through `collectSetupDiagnostics`. A residual quoting gap on a different input is M7-01. |
| M6-03 (POSIX uses PowerShell quoting) | MINOR | **CLOSED** | `setup.ts:88-91` `shQuote` (`'\''`), used for every POSIX line (`:122-129`) and the POSIX uninstall (`:139`). Test `:234-243` pins both quoters with an apostrophe path and `not.toContain("o''brien")` in the POSIX block. |
| M6-04 (retained cancel waiters) | MINOR | **CLOSED** | `coordinator.ts:258-272` `cancelSignal()` returns `{signal, release}`; `:330-336` releases in `finally` after the race. Test (`:296-302`) asserts retained waiters 1 while consent is open, 0 after cancel. |
| M6-05 (stale LibreOffice / Core 0.3.6 prose) | MINOR | **CLOSED** | `20_SHELL.md:220` now says SPEC 10.1 defines the fields, the engine emits them, "not reported" only for an older engine; `20_SHELL.md:255` and `90_ACCEPTANCE.md:67` state the hybrid ("version stream and its variants refreshed from Core 0.3.7 in R34; the other streams recorded under Core 0.3.6 and retained"). One historical leftover: M7-03. |
| M6-06 (HANDOFF stale) | MINOR | **CLOSED for the three named lines** | Pending list `HANDOFF.md:9` no longer lists FX-71; the "never the vault or the plugin folder" claim no longer appears (grep 0 matches); a "Shell (MECE round 6, cc as shell owner)" section `:43-50` covers R32-R34, M6-01..08 and receipts. Residual: M7-03. |
| M6-07 (stale comments/flag names) | MINOR | **CLOSED** | Greps over `shell/` for `never the vault`, `is not vault content`, `Never the vault or the plugin folder`, `legacy-preconvert`, `preconvert.prepare`: 0 hits in source; remaining mentions are the guard test strings themselves (`jt-m6-shell-round6:309-314`) and conditional wording (`launcher.ts:45` "lies outside the vault for the documented venv", JT-12 `:38,199` "in this fixture"). |
| M6-08 (R16 disclosures, "without network access") | MINOR | **CLOSED** | `README.md:62-72` (exiftool automatic for `png|jpg|jpeg`, metadata lines such as `GPSPosition`/`Author`/`Artist` written into the note; LibreOffice only with the toggle, private profile, macros and link updates disabled, temporary copy not kept); `25_PACKAGING.md:125` names both programs; "without network access" is gone (0 matches; `README.md:68,148` say "private profile"). Test `:316-325`. |

Carried rows re-checked, no regression: shell suite 310/310; `manifest.json` (id `markitdown-flow`, 2.0.0, `minAppVersion 1.14.4`, `isDesktopOnly:true`, 80-char description) equals `versions.json` `"2.0.0": "1.14.4"`; `main.js` is git-ignored and its bundle contains `isTransientGate`/`probeTimeout` (built from current source); grep over `shell/src` for `innerHTML|outerHTML|insertAdjacentHTML|requestUrl|console.|eval(|new Function|fetch(|shell:true|XMLHttpRequest|WebSocket` finds only the comments naming removed APIs and the `node:child_process`/`electron` adapters (`node-spawner.ts`, `node-apis.ts`) that REQ-SHL-12 allows.

All eight M6 class-A findings are CLOSED. The M6 residual list is empty.

## 2. New defects (class A)

### M7-01 MINOR (goal fit, copied-text correctness): PowerShell `quote()` doubles only the ASCII apostrophe

`setup.ts:84-86` `quote()` doubles `'`. PowerShell also treats the typographic quotes U+2018, U+2019, U+201A and U+201B as single-quote characters, both as string delimiters and as the escape-by-doubling trigger (about_Quoting_Rules). A Windows profile or folder name with U+2019 (for example `C:\Users\O’Brien\venv\Scripts\python.exe`, common when a name was typed in a word processor) renders as `& 'C:\Users\O’Brien\venv\Scripts\python.exe' -m pip uninstall -y markitdown`. PowerShell closes the string at `’`, so the pasted command either fails to parse or runs different tokens. The same function quotes the migrated bootstrap hint (`bootstrapCommand`, `:103`), `venvDir` and `downloadDir` in the Windows block. The text is only rendered for the user's own terminal and the interpreter path is already controlled by whoever writes `data.json`, so this is not a trust-boundary defect (not charged to Security), but the copied recipe can be wrong or misparsed. No test uses a typographic quote (grep of `shell/src` and `shell/test` for U+2018..U+201B: 0 hits). Fix: `value.replace(/['\u2018\u2019\u201A\u201B]/g, (c) => c + c)`; add one JT-10 case with `O’Brien` and one with `‘` in the hint.

### M7-02 MINOR (goal fit / UX): admission waits on the gate with no status or Cancel for up to about 11 s

After the M6-01 repair, a transient gate is re-probed by every job and `probeVersion` can take attempt 5 s + 1 s backoff + attempt 5 s = **11 s** on a hung interpreter (`version-gate.ts:249,332,343-350`). `ShellCoordinator.admit` awaits that gate at `coordinator.ts:173` before `progress.begin(...)` (`:206`), so the status-bar item and its Cancel button do not exist yet; the user clicked Convert and sees nothing for up to 11 s, then a `shell.RUNTIME` notice. The settings tab has the same shape: `main.ts:196-199` `save` awaits `refreshGate()` after an interpreter change. `cancel()` still refuses the pending admission (`admissionInterrupted`, M4-V01), but only a command-palette invocation can reach it. Before M6 the wait was at most 5 s and not repeated per job. No data is at risk; REQ-SHL-16's visible Cancel is specified for the job (planning, approval, conversion), so this is not a MUST violation. Fix (small): call `progress.begin('probe')`-style phase (or a one-line notice "checking the engine...") when the cached gate is absent or transient, and end it on refusal; test with a hung child that the item exists during the probe and is removed on the refusal.

### M7-03 MINOR (docs): HANDOFF round-4 section still states the FX-71 publication as "Core 0.3.6" in the present tense

`HANDOFF.md:39` (under "Shell (MECE round 4)") says the staged recording "(Python 3.14.10, Core 0.3.6, 53 files + manifest) is published ... byte for byte". Since R34 the version stream and variants are refreshed from Core 0.3.7 (`manifest.json:12,785`, `20_SHELL.md:255`, `90_ACCEPTANCE.md:67`), so the sentence is no longer true for the published files. The section is dated history (only `HANDOFF.md:31` is labelled "historical; superseded"), so a reader of `:39` alone gets the wrong Core version. Fix: append "(version stream and variants refreshed from Core 0.3.7 in R34; see 20_SHELL section 7)" to `:39`, or label the round-4 section historical.

## 3. Re-audit by axis

- **Shell docs <-> code.** REQ-SHL-10/17 now state the retry, backoff, never-cached transient gates and the "no answer in time" wording, matching `version-gate.ts` and `setup-modal.ts`; JT rows in `30_TESTPLAN.md:415` agree; test counts quoted in docs (310 / 28 suites) equal the run. Open: M7-03.
- **Contract.** `version` argv and field set, the exit-1 `E_CORE_CONFLICT` shape, progress events, the consent predicate and Base URL rule are unchanged and equal the engine. The shell's 5 s per-attempt budget sits above SPEC 10.1's 3 s healthy-machine target with 2 s headroom (engine disposition in M6 cx), and a slow first answer is retried once, so a healthy engine is no longer shown unavailable; cold-start proof is E-16 (class B). Nothing open.
- **Security.** Re-verified by grep: no HTML injection sinks, no network API, no `shell:true`, no `eval`; interpreter prefix `-I -X utf8`, absolute-only interpreter at admission, revocable gate, env scrub, uninstall command rendered never executed. M7-01 is wrong copied text, not a confidentiality, integrity or containment defect (a writer of `data.json` already controls `enginePython`). Nothing open.
- **Policy.** Manifest and `versions.json` agree; no telemetry/install/fetch code; README and `25_PACKAGING.md:125` now disclose exiftool and LibreOffice and no longer claim a blocked network; CHANGELOG (`:56-57`) records the retry and "no answer" behavior. Nothing open.
- **Goal fit.** Classify -> selective OCR with consent, provenance and Core delegation holds; legacy conversion stays opt-in and marked derived; transient probe failures recover without user action. Open: M7-01, M7-02.
- **Simplicity.** `cancelSignal` no longer accumulates resolvers; `isTransientGate` is one 3-line predicate shared by `main.ts` and tests; `shQuote`/`quote`/`bootstrapCommand` are small and used; no dead code or duplicated oracle found in the M6 changes (`retainedWaiters` is a test helper). Nothing open.

## 4. Consolidated class-A findings

| ID | Sev | Location | Fix size |
|---|---|---|---|
| M7-01 | MINOR | `shell/src/process/setup.ts:84-86` | one regex + two test cases |
| M7-02 | MINOR | `ui/coordinator.ts:173,206`; `main.ts:196-199`; `version-gate.ts:343-350` | a phase/notice during gate wait + one test |
| M7-03 | MINOR | `HANDOFF.md:39` | one clause |

No BLOCKER, no MAJOR. All M6 findings CLOSED. External evidence E-01..E-15 (and E-16) is not deducted.

## 5. Scores (0-100 from code/doc facts only; 100 iff no open class-A finding on the axis)

| Axis | M6 | M7 | Exactly what blocks 100 |
|---|---|---|---|
| Shell docs <-> code | 95 | **99** | M7-03 (HANDOFF.md:39 present-tense "Core 0.3.6" publication claim). |
| Contract consistency | 94 | **100** | Nothing open. |
| Security | 100 | **100** | Nothing open. |
| Policy compliance | 96 | **100** | Nothing open. |
| Goal fit | 93 | **97** | M7-01 (typographic quotes break the PowerShell recipe/uninstall command), M7-02 (silent gate wait up to about 11 s with no status or Cancel). |
| Simplicity | 97 | **100** | Nothing open. |

Exit condition for 100 on every axis: fix M7-01 (one regex, two tests), M7-02 (one status phase, one test) and M7-03 (one clause), rerun jest/tsc/build. Everything else that remains is class B.

Not verified here: `tsc` and `npm run build` (orchestrator), real-OS behavior of the retry and cold-start latency (E-16), real-OS cancel (E-03), the engine suite (taken from the orchestrator's 685 pass).
