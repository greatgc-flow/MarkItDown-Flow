# M8 cross-cutting MECE audit (cc) - confirmation

Reviewer: cc. Date: 2026-11-09. Branch `fix/mece-r7` (PR #3, HEAD `46ea2fd`). Read-only: file reads, greps, `git show` of `6ee21dc` and `46ea2fd`. Engine 691 pass and shell 316 jest / tsc clean are taken from the orchestrator and were **not re-run** (sandbox refused the redirected jest run). No code edits. Only this file is written. External evidence (E-01..E-16) is class B and not deducted.

## 1. M7_cc_cross findings

| ID | Sev | Status | Evidence |
|---|---|---|---|
| M7-01 (PowerShell `quote()` ASCII-only) | MINOR | **CLOSED** | `setup.ts` `quote()` now `value.replace(/['‘’‚‛]/g, (c) => c + c)`; POSIX `shQuote` unchanged. `jt-m7-shell-round7.test.ts:24-35` loops U+2018/2019/201A/201B and `'`: uninstall command, `Set-Location`, `-m venv`; plus the POSIX non-change. |
| M7-02 (silent gate wait up to about 11 s) | MINOR | **CLOSED for the visible item; one residual (M8-01)** | `JobPhase` gains `check` (`progress.ts`); `coordinator.ts:180-181` `begin('check')` before `await gate()`; `:158-161` `finally` ends the item for every refused admission (including a thrown `admit`), and an admitted job re-begins and ends it once; en and ko text `shell.progress.phase.check`. Tests `:86-118`: begin before the gate resolves, refusal ends it, admitted job has one `end`, both locales. Settings-save path: `main.ts:196-201` now `void this.refreshGate()` (no await), the next job waits on the shared probe under the check item; `jt-m7-settings-save.test.ts` shows `save` returns while the probe hangs and that the probe is still started. |
| M7-03 (HANDOFF `:39` "Core 0.3.6" present tense) | MINOR | **CLOSED** | `HANDOFF.md:39` is now "was published in round 4 ... since R34 the version stream and variants are refreshed from Core 0.3.7, see 20_SHELL section 7". |

## 2. Regression probe of the round-7 shell changes

- `submit` `finally` resets `checking` and `reserved` on every path; `checking && !admitted` ends the item once; the admitted path ends it in `runJob().finally` as before. No double `end`, no leaked item on throw or on `BUSY` (BUSY returns before `begin`).
- `begin('check')` is after the absolute-interpreter and empty-selection refusals, so those paths open no item. Zero-spawn guarantees on cancel/unload are unchanged (`admissionInterrupted` still re-checked after the gate).
- `void this.refreshGate()`: `probeVersion` resolves to a gate value and does not reject in the tested paths; the result is still dropped if the interpreter changes again (`main.ts` supersede check); `gateProbe` is cleared in `finally`. `currentGate` shares the in-flight probe, so there is one probe and no duplicate.
- Settings-tab note: after an interpreter change the Setup view no longer waits for the new gate inside `save`; the doc row in `20_SHELL.md` (M7 row) states this and matches the code.
- No new innerHTML/network/`shell:true`/eval sinks in the diff.

## 3. New finding (class A)

### M8-01 MINOR (goal fit): Cancel during the `check` phase does not take effect until the probe settles

`cancel()` (`coordinator.ts:~246`) sets `admissionCancelled` and signals `cancelWaiters`, but `admit` awaits `this.deps.gate()` directly (`:182`), not a race against the cancel signal (the M6-04 `cancelSignal()` is used only in the consent race, `:342`). With a hung interpreter the user presses the new Cancel and the item stays for up to the remaining ~11 s, then refuses with `shell.CANCELLED`. The test releases the gate right after `cancel()` (`jt-m7-shell-round7.test.ts:93-94`), so it does not show this. No data at risk, zero spawns still hold, and the M7-02 requirement (visible status and Cancel) is met; this is a responsiveness gap in the Cancel just added. Fix (small): `Promise.race([gate(), cancelSignal.signal])` in `admit`, release in `finally`, `end` the item at once; one test where the gate never resolves and Cancel resolves `submit` with `shell.CANCELLED`.

## 4. Scores (code/doc facts only; 100 iff no open class-A finding)

| Axis | M7 | M8 | Blocks 100 |
|---|---|---|---|
| Shell docs <-> code | 99 | **100** | Nothing open. |
| Contract consistency | 100 | **100** | Nothing open. |
| Security | 100 | **100** | Nothing open. |
| Policy compliance | 100 | **100** | Nothing open. |
| Goal fit | 97 | **99** | M8-01 (Cancel in the checking phase waits for the probe). |
| Simplicity | 100 | **100** | Nothing open (`checking` flag is small and used). |

Exit condition for 100: M8-01 (race the gate against the cancel signal, one test). Not verified here: jest/tsc/build re-run, real-OS cancel (E-03), cold-start latency (E-16).
