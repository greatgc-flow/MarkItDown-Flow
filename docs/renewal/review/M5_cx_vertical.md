# M5 recursive MECE audit — vertical, oracles, docs ↔ code, simplicity

Date: 2026-11-09. Workspace: repository. Authority: SPEC DRAFT-3.5, SHELL, PACKAGING, TESTPLAN and ACCEPTANCE. Reviewed all three M4 audits and both M4 repair reports against current sources, assertions and existing local receipts. Historical audit snapshots are not current promises.

**Scores from code/doc facts only: vertical 96/100; oracles 92/100; docs ↔ code 94/100; simplicity 96/100.** Five distinct mechanisms remain open: incomplete shell version syntax, shell execution scoring by counts, retained consent cancellation waiters, residual live pending-sync prose, and an unconditional outside-vault cwd promise. The first, fourth and fifth are residuals; the shell scoring and waiter defects are newly demonstrated. Aliases below are not additional findings. No missing CI, release, real-app or named-human receipt reduces these scores.

**Scope:** this audit writes only `docs/renewal/review/M5_cx_vertical.md`. No code, fixture, test, configuration or other documentation edits; no git commands, installs, builds, release actions, remote queries or pytest/Jest suite runs. Python probes used `python -B -`; TypeScript modules were transpiled in memory with the installed compiler. Coordinator probes used actual production modules, existing in-memory fake filesystem/clock/spawner fixtures and an inert Obsidian Modal base. They launched no real engine and wrote no modeled files to disk. Synthetic evidence controls are explicitly identified below and are never release receipts.

## Evidence and limits

| Check actually performed | Result and interpretation |
|---|---|
| Existing Python3.14 installed receipt | `build/trace/junit-m4-py314-installed.xml`: **580 cases, 568 passed, 12 skipped, zero failures/errors**. Its v3 registry contains 581 collected / 580 selected identities; its independent collection contains 581, including all 20 T-GEN-85 parameters. Candidate commit is empty. |
| Existing Python3.15 source receipt | `build/trace/junit-m4-py315.xml`: the same counts, zero failures/errors and all 20 sweep parameters. Experimental source-mode evidence, not a supported installed endpoint. |
| Receipt freshness | Both registry-to-collection hashes match. **Both collection suite digests differ from current `suite_digest`**. T-META-06 exists now (`engine/tests/test_meta.py:80`) but has no case in either XML. Thus the existing 568-pass receipts describe an earlier test-source snapshot; they do not establish a complete current-source run. This is an evidence limitation, not a code defect or score deduction. No receipt was rewritten. |
| Existing shell receipt | `build/trace/junit-shell.xml`: **277 passed**, zero failures/errors/skips; nine JT-17 cases. Parsing this local receipt does not establish E-02's three OS executions or candidate binding. |
| Current typecheck | Compiler API loaded the absolute `shell/tsconfig.json`, constructed the program with no emit/incremental output, and returned **71 root files, zero diagnostics**. An initial relative-config harness produced type-resolution errors; correcting the harness resolved them. Those initial harness errors are not product findings. |
| Current trace, without writing CLI entry points | `coverage_problems` over Python + shell discovery: unknown/uncovered/untagged **0/0/0**; Python `registration_problems`, `matrix_problems`, `golden_problems`: **[] / [] / []**. These are registration/integrity checks, not executions of every matrix cell. |
| Current matrix | **84** expanded stage/FM declarations and **67** expanded class/stage N/A declarations. Header says 67. Direct calls to the original **T-META-05 and T-META-06 assertion functions pass**: no covered/N/A overlap; header equals expansion. No collect-only hook was invoked. |
| Current engine/wheel correspondence | All **27** Python module members in `build/trace/redgreen/m4-wheel/mdflow-2.0.0-py3-none-any.whl` equal current `engine/src` bytes. This establishes source/wheel correspondence, not a fresh reference dependency resolution. |
| Published FX-71 | Actual `tools.record_protocol.verify` returns **0**, reporting **53 files verified**. Published manifest records Python3.14.10/Core0.3.6 (`shell/test/fixtures/fx71/manifest.json:6`, `:12`). Actual default shell and package gates admit `version.json`. A remaining `RECORDING_HOST_POLICY` name in JT-17 is an alias of `RELEASE_LOCK`, not a widened policy. |
| Current adversarial probes | Deferred gate/destination/listing × control/Cancel/dispose; oversized PDF/GIF IDs; Plan→Run reset; full Python collection versus truncated execution; malformed versions through both actual gates; real shell receipt identities with omission/duplication; three successive completed consent jobs; venv cwd inside vault. Outcomes are detailed below. |

User-supplied context: branch pushed, PR #1 open, genuine three OS CI running. No git or remote API was used to verify or bind those facts to a SHA. Running CI is neither a failure nor a completed receipt. Acceptance §7 remains the external-evidence ledger.

## Every M4 cx finding and carried primary handoff

“CLOSED” below closes the identified code/doc mechanism within its stated scope. It does not close a release/manual gate. “OPEN — external” carries no code-score penalty.

| ID / aliases in M4 | Verdict | Current evidence |
|---|---|---|
| M3-V01 / M1-V22, HWP V1 payload kind | **CLOSED** | T-CLS-90, `engine/tests/stage_io/step7/test_m3_engine.py:17`, retains five composed malformed-type cases with zero requests, retained output and sibling continuation; 5/5 in the installed receipt. The separate V3 boundary is closed below. |
| M3-V02 / M1-V26, fractional PDF allocation | **CLOSED** | `engine/src/mdflow/render.py:87` checks ceil-scaled allocation before render. T-RND-90 at `test_m3_engine.py:46` independently asserts refused fractional and allowed exact-size cases for two DPIs/two rotations; 4/4 in receipt. |
| M3-V03 / X-01 / Fable P-01, progress contamination/quadratic presenter | **CLOSED** | `shell/src/ui/progress.ts:50` resets all summary fields on `run_start`; `:112` stores one summary, `:148` updates it directly. JT-09 at `shell/test/jt-09-output-busy.test.ts:257` has a literal Run-only expected object; JT-16 at `jt-16-cancel-ui.test.ts:202` checks Plan pending 9, Run 4/4 pending 0, Cancel retained and no `events` field. Direct Plan→Run reducer probe gives files1/1, done1, pending0. T-RPT-91 at `engine/tests/stage_io/step7/test_m4_engine.py:44` independently checks per-invocation engine counters. |
| M3-V04 / M2-V03 / Fable P-02, gate parity | **OPEN — residual M5-V01** | Empty platform, `???` and leading whitespace repairs work. Shell `releaseSegment` still accepts alphabetic/punctuation suffixes that package `Version` rejects: `shell/src/process/version-gate.ts:108` versus `engine/tests/packaging/test_pt_release.py:296`. Direct cross-language counterexamples below. |
| M3-V05 / M4-O01, Python complete-parameter evidence | **CLOSED in producer/consumer code** | Fixed full-root independent collection in `tools/trace.py:332`; selection environment stripped at `:339`; v3 registry binds collection bytes at `:352`; consumer verifies source/commit/hash and returns the canonical universe at `:360`, `:407`. T-META-90 (`engine/tests/unit/test_m3_trace.py:13`) now has 14 negatives, 14/14 in receipt. T-META-96 (`engine/tests/unit/test_m4_trace.py:11`) checks actual restricted collection against a separate complete universe. Audit in-memory copies of real identities: full sweep **True**; remove K09 from registry + XML **False**; keep only K01 in both **False**. Actual candidate-target evidence remains E-13. New shell-specific M5-O01 is a different consumer path. |
| M3-H01, active class/stage registrations | **CLOSED** | T-GEN-85 (`engine/tests/stage_io/test_class_sweep.py:253`) retains all 20 class parameters, explicit selection/render effects and active cells; 20/20 in receipt. T-META-05 plus current TOML independently show the six active-cell handoffs and all four redundant overlays are absent from N/A. |
| M3-O01, placement/member oracles | **CLOSED for identified gaps** | T-ASM-90 at `test_m3_engine.py:89` has exact independent OCR IDs/pending reasons; T-ASM-91 at `:117` has 1001 anchors/exact 1000 units; T-TRI-90 at `:134` uses genuinely corrupt inner Office bytes and a surviving sibling. Receipt: 5/5, 1/1, 1/1. These assert placement and continuation, not semantic OCR accuracy for every raster. |
| M3-D01, current applicability/status prose | **OPEN — narrow residual M5-D01** | Count is now 67 (`engine/tests/matrix.toml:414`), all four covered overlays removed, and the old SYNC token is gone. However live SHELL disposition rows still say “engine synchronization is pending” and “final contract-test sync remains pending” (`docs/renewal/20_SHELL.md:190`, `:193`), contradicting `:3` and `:247`. Token absence in T-META-95 does not establish semantic prose consistency. |
| M4-V01, Cancel/unload undone during admission | **CLOSED** | `shell/src/ui/coordinator.ts:154` checks disposal/admission cancellation after gate (`:168`), destination (`:174`) and listing (`:193`); `cancel` sets admission state at `:235`. JT-16 deferred-gate Cancel/dispose/control cases start at `shell/test/jt-16-cancel-ui.test.ts:261`, `:286`, `:304`. Audit additionally deferred destination and listing: all six cancellation/disposal combinations refuse with **zero spawns, inactive, zero history**; three controls admit and spawn exactly once. |
| M4-V02, 5000-digit V3 candidate ID exception | **CLOSED** | `engine/src/mdflow/classify.py:134` bounds numeric spelling before `int`, returning invalid V3 on conversion failure. Direct FX-02/FX-12 controls remain convert_and_ocr; 5000-digit p/f IDs become **convert_only / UNKNOWN / exactly W_TRIAGE_INCONSISTENT**, without exception. T-CLS-91 at `engine/tests/stage_io/step7/test_m4_engine.py:15` covers PDF/GIF × long/ordinary out-of-range, zero provider work, retained output and successful sibling; 4/4 in receipt. |
| M4-V03 / N-07 / Fable P-06, raw Base URL parity | **CLOSED for demonstrated aliases/userinfo** | `shell/src/pure/settings.ts:181` uses raw authority, rejects any `@`, and compares literal loopback host spelling. Direct shell/engine probes both refuse empty userinfo, `127.1` and hex host aliases; both admit exact 127.0.0.1 and [::1]. JT-04 negatives at `shell/test/jt-04-migration-map.test.ts:222` additionally cover numeric/octal/trailing-dot aliases. No claim of universal equivalence between URL parsers is needed for this closure. |
| X-11, supported-host fixture publication | **CLOSED** | Published 53-file verifier succeeds; manifest Python3.14.10/Core0.3.6; JT-17 at `shell/test/jt-17-version-gate.test.ts:39` explicitly expects both identities and default-policy admission. Recorder label is isolated; T-GEN-97 at `engine/tests/packaging/test_m4_docs.py:45`, 1/1 in receipt. Publication is local code/fixture work, distinct from E-10 real bundle execution. |
| N-02, BOOTSTRAP/PACKAGING isolated recipes | **CLOSED for missing -I** | T-META-95 at `engine/tests/packaging/test_m4_docs.py:11` examines every matching version/selftest recipe in both files; current recipes include `-I -m mdflow`. Production launch prefix remains `shell/src/process/launcher.ts:24`. The unconditional cwd wording is separately OPEN as M5-D02. |
| N-04, Windows residue disclosure/recovery | **CLOSED in identified code/doc scope** | README discloses forced Windows termination and residue. `engine/src/mdflow/runtime_temp.py:43` recognizes marked owned trees, checks plain paths and takes OS locks; `:86` holds a lease for a new run. T-GEN-93/94/95 at `engine/tests/unit/test_m4_temp.py:11`, `:29`, `:70` protect live/unowned/linked trees and test real abrupt exit/native kill; 1+2+1 passing receipt cases. Unmarked legacy residue stays manual; E-03/E-09 real OS/app obligations remain external. |
| M1-V31, six endpoints/nine smokes | **OPEN — external only** | Local installed correspondence exists. Candidate-bound supported target and intermediate smoke receipts require E-01/E-05/E-12/E-13; a current test definition or an in-progress CI run cannot supply those outcomes. No score deduction. |
| M1-V34, reference/provenance/named reviews | **OPEN — external only** | Actual Linux3.14 hash-mode reference, release/provenance and named review outcomes require E-06/E-08/E-09/E-14/E-15. The twelve skipped local release/evidence cases remain skips. No score deduction. |

## Every M4 Fable finding and horizontal artifact finding

This table accounts for the M4 cross-audit's ten local P/D findings, its twenty carried M3 shell items and the ag artifact handoff. Repeated rows are aliases of mechanisms above, not extra score deductions.

| M4 ID | Verdict | Evidence / exact remaining scope |
|---|---|---|
| P-01 | **CLOSED** | M3-V03 row; literal JT-09 reset oracle and JT-16 presenter assertions, `shell/src/ui/progress.ts:50`. |
| P-02 | **OPEN** | M5-V01. Anchoring the regex repairs `???`; it does not implement package PEP 440 syntax. |
| P-03 | **CLOSED** | X-11 row; all 53 published files verify and actual default gates admit the recording. |
| P-04 | **CLOSED** | `shell/src/pure/settings.ts:314` requires printable absolute interpreter; `shell/src/ui/coordinator.ts:165` refuses bad interpreter as RUNTIME before gate/spawn. JT-04 at `jt-04-migration-map.test.ts:246`; JT-09 at `jt-09-output-busy.test.ts:282`. |
| P-05 | **CLOSED for rejected inputs** | `shell/src/ui/settings-tab.ts:51` applies a commit or emits `shell.settings.rejected` and restores persisted text. Whole-plugin JT-04 at `shell/test/jt-02-plugin-round2.test.ts:183` checks notice + revert for interpreter/output/URL/bounds and nonempty en/ko messages. This does not claim persistence succeeds under every OS write failure. |
| P-06 | **CLOSED** | M4-V03 row; actual raw-host/userinfo negatives now fail before persistence. |
| D-01 / N-12 | **OPEN — residual** | M5-D01: `20_SHELL.md:190`, `:193` retain unqualified pending synchronization in the live disposition table. The repaired paragraphs and absent old token do not erase these sentences. |
| D-02 / N-02 recipes | **CLOSED** | T-META-95 / actual BOOTSTRAP and PACKAGING recipes contain -I. |
| D-03 | **OPEN — partial, M5-D02** | The original HANDOFF typecheck note, CHANGELOG Windows caveat (`CHANGELOG.md:23`) and README venv-in-vault caveat (`README.md:21`) are repaired. The same cwd overclaim survives normatively in `20_SHELL.md:76` and production comments at `launcher.ts:35`, `coordinator.ts:107`. |
| D-04 / ag covered-cell declarations | **CLOSED** | Header 67, exactly 67 expanded declarations, zero covered/N/A overlap; direct T-META-05/06 assertions pass. Removed S6:K08, S6:K09, S5:K14 and S4:K11. M4 ag's 67 remaining equivalences remain valid as registrations; no new horizontal hole was demonstrated. |
| N-01 | **CLOSED** | Synchronous `reserved` guard/release at `coordinator.ts:142`; JT-09 same-tick deferred-gate double submission at `jt-09-output-busy.test.ts:158`. |
| N-02 launch isolation | **CLOSED for execution isolation; cwd prose OPEN above** | `launcher.ts:24` fixed -I/-X utf8 prefix; JT-11/JT-12 cover actual request builders and prefix negatives. Choosing a nested venv does not remove -I. |
| N-03 | **CLOSED** | `coordinator.ts:300` forwards actual Plan diagnostics and adds PROTOCOL only if none exist. JT-15 independently expects E_USAGE and a distinct truncated-Plan failure. |
| N-04 | **CLOSED** | Disclosure + scoped owned-temp recovery above; genuine process inventory/app rehearsal remain E-03/E-09. |
| N-05 | **CLOSED in implementation** | Explicit empty result in `shell/src/process/dom-picker.ts:43`; JT-08/JT-02 require an empty-selection notice and zero submit. Full-tree Electron picker behavior remains E-09/MAN-04. |
| N-06 | **CLOSED for absent activation** | `dom-picker.ts:72` returns blocked before creating/clicking input when activation is false; real activation query in `shell/src/process/node-apis.ts:157`; JT-08 covers blocked outcome. Not a guarantee about every host dialog failure. |
| N-07 | **CLOSED for identified URL defect** | M4-V03/P-06 row; raw aliases and empty userinfo rejected. |
| N-08 | **CLOSED by disclosure** | JT-04 checks explicit enabled-drop tradeoff; README picker/drop disclosure agrees with `shell/src/ui/entry-points.ts:55`. Default drop remains off. |
| N-09 | **CLOSED by disclosure** | JT-04 checks reload notes for context-menu/drop/locale; settings tab provides them for load-time registration controls. |
| N-10 | **CLOSED** | `shell/src/process/spool-fs.ts:28` delegates positional ranged read; Node implementation at `node-apis.ts:63`; JT-13 checks multi-window offsets/lengths/EOF, zero whole-file reads and removal. No new total-JSON-memory claim. |
| N-11 | **CLOSED** | Whole-plugin JT-02 first-use open-log-folder path observes directory creation before open; Node mkdir is `node-apis.ts:106`. |
| N-12 | **OPEN as D-01** | Only the two remaining pending-sync sentences are charged; honest E-01..E-15 pending evidence is not stale synchronization prose. |
| X-11 | **CLOSED** | Published fixture/default-policy evidence above; no host-policy widening remains. |
| S-13 | **CLOSED for original stale handoff** | `docs/renewal/HANDOFF.md` now has M4 engine/shell updates and corresponding local receipts. Earlier sections expressly labeled round3 are historical; their old counts are not charged as current results. Normative cwd/status residuals are charged at their current live locations above. |
| S-16 | **CLOSED** | `shell/esbuild.config.mjs` no longer lists @electron/remote; no production import found. |
| S-17 | **CLOSED** | No `approvableHashes` occurrence in shell production source; launcher retains the actual yes-file renderer. |
| S-18 | **CLOSED** | `shell/src/pure/spool.ts` retains used `finishWith` and `discard`, no redundant `finish` export. EngineRun's unrelated private finish is not the removed API. |
| S-19 | **CLOSED** | `CoordinatorDeps` at `shell/src/ui/coordinator.ts:44` has no unused locale dependency. |
| S-20 | **CLOSED** | No `legacyFilePath` production occurrence; entry points consume the supplied Node resolver. |
| S-21 | **CLOSED** | `shell/src/ui/output-path.ts` imports pure path helpers directly, no re-export shim. Its real async destination/nonrecursive selection logic remains necessary. |

## New probes and precise remaining defects

### M5-V01 — MINOR, residual: shell still accepts malformed package versions

**Code:** `shell/src/process/version-gate.ts:99` claims agreement on every spelling, but `:108` only restricts the suffix's characters. The package gate additionally calls `packaging.version.Version` (`engine/tests/packaging/test_pt_release.py:296`). A character allowlist is not a version grammar.

Actual gates were called with copies of the published supported `version.json`, changing one field only:

| Field / input | Actual shell enabled | Actual package problems |
|---|---|---|
| pypdfium2 = `5.15.1garbage` | **true** | `pypdfium2 version is malformed` |
| pypdfium2 = `5.15.1+` | **true** | `pypdfium2 version is malformed` |
| pypdfium2 = `5.15.1..` | **true** | `pypdfium2 version is malformed` |
| python = `3.14garbage` | **true** | `Python range` |
| mdflow = `2.0.0garbage` | **true** | `engine range` |
| pypdfium2 = `5.15.1rc1` / `5.15.1.post1` | true / true | [] / [] |
| pypdfium2 = actual trailing newline | false | `pypdfium2 version is malformed` |

This is a demonstrated admission/contract disagreement, not evidence that the normal installed dependencies emit such values. No network/package lookup was involved. The original `???` and whitespace cases are repaired; they do not close the general malformed-text parity finding.

**Oracle gap:** T-GEN-96 explicitly rejects `3.14garbage` (`engine/tests/packaging/test_m4_docs.py:29`), while JT-17's purported matching syntax table omits that spelling (`shell/test/jt-17-version-gate.test.ts:121`). The tables are independently green while the same field/input disagrees. The M4 shell repair description copied the package regex but omitted its added `Version` check.

**Small closure:** give the shell a bounded, complete version grammar consistent with the package gate's accepted policy; exercise the same independently enumerated malformed/valid spellings for all five version fields on both sides. Keep rc/dev/post/local and existing release-segment range semantics. Include the five concrete negatives above. Updating comments or weakening the package validator does not repair parity.

### M5-O01 — MAJOR oracle defect, NEW: duplicate shell cases can replace missing cases

**Code:** `tools/trace.py:559` reduces shell cases to `(filename, tid)` boolean lists. `:602` accepts any all-green list with length at least the discovered source-row count. It never checks which JT description executed, duplicate execution identities, or a candidate/source binding for shell XML. Python's repaired canonical-universe validator is bypassed by this branch.

**Read-only reproduction:** load the actual nine JT-17 source registrations and actual nine passing JT-17 cases from `build/trace/junit-shell.xml`. Invoke the production `score` function with in-memory XML trees under the three expected shell filenames. Supply an explicitly synthetic 17-gate table selecting JT-17, synthetic successful command-oracle records and a synthetic candidate `'a' * 40`; keep manual review deliberately missing. Only discovery/external evidence reads are substituted; the real shell scoring branch executes. No evidence files are created.

| Case set for each modeled shell target | Actual automated result | Manual result |
|---|---|---|
| All nine distinct actual cases | **93/93; all 17 PASS** | 0/7 |
| Omit the “blocked gate yields zero conversions” case | **0/93; all 17 FAIL** | 0/7 |
| Omit that same case, duplicate the first passing case instead | **93/93; all 17 PASS** | 0/7 |

The omitted real test is `shell/test/jt-17-version-gate.test.ts:173`. The duplicate is the actual packaged-version happy case at `:39`. These are synthetic scoring controls using real identities, **not** the project's acceptance score and **not** evidence of omission in the existing local receipt. The observed 277-pass XML itself contains the nine distinct JT-17 cases. The defect is that the consumer cannot distinguish the negative from its positive control.

JT-21 (`shell/test/jt-21-trace.test.ts`) rejects duplicate registrations inside a test module; that does not authenticate exported execution cases or reject duplicates during scoring. T-META-90's duplicate/omitted-parameter mutations cover Python receipts, not this branch.

**Small closure:** validate exact unique shell execution identities against an independently complete, candidate/source-bound Jest inventory, including expanded cases. Reject missing, duplicate, substituted, stale, skipped and failed cases. Add omitted-only and omit-plus-duplicate controls around the actual scorer. Reuse the existing evidence path and avoid a parallel scoring system. The absent final CI evidence remains E-02/E-07; this validator defect is independently code-fixable now and therefore affects oracle scores.

### M5-S01 — MINOR simplicity/lifetime defect, NEW: completed consent jobs retain waiters

**Code:** `shell/src/ui/coordinator.ts:251` appends a resolver to `cancelWaiters`; `:314` races that signal against consent. Normal consent completion never removes the losing resolver. The only draining operation is a later Cancel/dispose (`:237`); the job finalizer (`:215`) does not release it.

**Actual coordinator probe:** one persistent coordinator, real published `consent-1-plan.stdout.json`, real decoder, existing fake process/filesystem, remote provider settings with a test key, and consent resolving `{approved:false}`. Submit and await three successive jobs, with no Cancel between them:

| Completed job | Accepted | Active after completion | History entries | Retained cancellation waiters |
|---|---|---|---|---|
| 1 | true | false | 1 | **1** |
| 2 | true | false | 2 | **2** |
| 3 | true | false | 3 | **3** |

Each job launches only its fake Plan, records pending consent, and performs zero provider/network work. Dispose drains the count back to zero. Thus retention grows with completed normal consent jobs for the lifetime of the loaded plugin. No wrong authorization or process leak was demonstrated; this is a small but real resource-lifetime defect.

**Small closure:** make the cancellation subscription removable when the consent race settles, or release job-owned waiters in a guaranteed finalizer. Add a multi-job lifecycle oracle with independently expected zero retained waiters after normal approve/dismiss and correct cancellation for the next job. No event bus, new cancellation framework or process supervisor is needed.

### M5-D01 — MINOR, residual: live synchronization status still contradicts itself

`docs/renewal/20_SHELL.md:190` says “engine synchronization is pending”; `:193` says “final contract-test sync remains pending.” The same live document says its contracts have been checked (`:3`) and that the relevant synchronization/engine handoffs are complete (`:247`). The rows are in a live “Disposition in this document” table, without an as-of qualifier.

M4's removal of the literal `SYNC-AFTER-DRAFT-3` token is real. T-META-95 (`engine/tests/packaging/test_m4_docs.py:11`) only tests that token's absence and selected evidence/recipe strings; it cannot detect these semantically identical residual statements. The matrix's count/overlays and the other repaired PACKAGING/TESTPLAN/ACCEPTANCE paragraphs are closed and are not charged again.

**Small closure:** remove the two obsolete pending clauses or explicitly label those rows historical as-of dispositions; retain §7's genuinely external evidence as the current pending ledger. No extra test framework is required for two prose edits.

### M5-D02 — MINOR, residual at a new location: unconditional cwd promise exceeds implementation

`docs/renewal/20_SHELL.md:76` requires every spawn cwd to be the selected venv root and also says it is **never** the vault/plugin folder, with a matching outside-vault oracle promise. Production comments repeat the unconditional claim at `shell/src/process/launcher.ts:35` and `shell/src/ui/coordinator.ts:107`.

Actual `isAbsolutePath` admits `C:\Users\alice\Vault\venv\Scripts\python.exe`; actual `engineWorkingDirectory('win32', value)` returns **`C:\Users\alice\Vault\venv`** (`launcher.ts:41`). No containment refusal exists in this helper or interpreter admission. README already explicitly permits/explains this case (`README.md:21`). The current docs therefore disagree with each other and the actual cwd calculation.

The fixed `-I -X utf8 -m mdflow` prefix remains intact. This probe establishes a contract/documentation inconsistency, not a restored vault import attack. JT-12 uses an external venv fixture and proves that fixture's cwd; it cannot prove the unconditional statement for arbitrary configured paths.

**Small closure:** align the normative rule and comments with the README: selected interpreter's venv root is cwd, and isolation excludes cwd from imports even if that venv is inside the vault. If outside-vault placement is truly required, admission must enforce it and the README must agree. The former is the smaller change consistent with current behavior.

## Retained inherited ledger — no silent omissions

M4 also carried the following earlier findings. Current definitions/assertions were checked against their scoped M4 disposition, source registration and existing receipt identities; the full suites were not rerun. Test IDs here refer to executable assertions, not only catalog entries. Evidence-only rows are separated above and below.

| Carried M1 ID | Verdict | Retained concrete oracle / scope |
|---|---|---|
| V01 | CLOSED | T-META-50; T-TRX-57, T-WRT-51, T-RPT-52..56: applicable/report cells and durable counter effects. |
| V02 | CLOSED | T-SNF-50, T-GEN-53, T-CNV-52/53, T-TRX-54, T-RPT-51, T-RND-80: IO/interruption boundaries and siblings. |
| V03 | CLOSED for original gaps | T-CLS-50, T-LKP-50, T-ASM-50, T-TRX-53/54/56: actual consumer/ledger/raster validation; M4-V02 separately verified closed above. |
| V04 | CLOSED | T-RND-81/82 and T-GEN-85[K09]: actual HWP extraction/refusal/cold-warm path. |
| V05 | CLOSED | T-META-81 and trace; no blanket fx(all) at execution stages; current header/overlays verified with META-05/06. |
| V06 | CLOSED | T-SNF-50/53: discovery roots, exclusions, links/reparse and deduplication. |
| V07 | CLOSED | T-SNF-51/54; `_source_bytes` at `engine/src/mdflow/orchestrate.py:72` rechecks bytes/hash before conversion. |
| V08 | CLOSED | T-CNV-50, T-RND-50, T-CTR-50/51: source/media/expansion bounds; separate fractional render control retained. |
| V09 | CLOSED | T-WRT-50 and containment before old output read in `orchestrate.py:394`. |
| V10 | CLOSED | T-WRT-51: missing media restored on skipped Markdown publication. |
| V11 | CLOSED | T-LKP-50/T-ASM-50: timestamp/provenance validation before assembly. |
| V12 | CLOSED | T-RPT-50: bounded progress line with retained counters/identity. |
| V13 | CLOSED | T-RPT-51: terminal event follows durable report-copy outcome. |
| V14 | CLOSED within amended process scope | T-TRX-50/80: bounded capture, deadline, inherited pipe/no-reader controls; no descendant-tree guarantee inferred. |
| V15 | CLOSED within bounded amendment | T-TRX-51 drip-body deadline; native/DNS/TLS limits remain documented, real-OS evidence external. |
| V16 | CLOSED | T-CLI-50/T-PLN-50: exact CLI/provider options and none-provider cost behavior. |
| V17 | CLOSED | T-TRX-52: runtime vocabulary/redaction and sibling continuation. |
| V18 | CLOSED | T-SEC-50: proxy userinfo cannot leak into Plan metadata. |
| V19 | CLOSED | T-RND-81 both orders: HWP stored/refused media policy before grouping. |
| V20 | CLOSED | T-SEL-50/T-CNV-54: full digest identity, shortened filename collision refused. |
| V21 | CLOSED | T-SNF-52: parser security state and malformed HWP corruption. |
| V22 | CLOSED for identified V1 types | T-CLS-80/90; V3 oversized IDs separately closed by T-CLS-91/direct probes. |
| V23 | CLOSED | T-PLN-51/T-PLN-02: prepared snapshot, approved bounds and exact production hash behavior. |
| V24 | CLOSED | T-TRX-53/T-TRX-08: raster mutation denied immediately before send. |
| V25 | CLOSED | T-RND-52: prior encoded payload release; no decoder working-set certification. |
| V26 | CLOSED | T-RND-53/90: pre-decode exact pixel allocation boundary. |
| V27 | CLOSED | T-RND-54: embedded multiframe media selects frame zero against decoded controls. |
| V28 | CLOSED | T-WRT-52: reserved output name/collision handling. |
| V29 | CLOSED | T-LKP-51: transcription result survives ledger publication failure. |
| V30 | CLOSED | Production T-PLN-02, supplemented by META-80; not a detached expected-hash calculation. |
| V31 | OPEN — external only | E-01/E-05/E-12/E-13, no deduction. |
| V32 | CLOSED as oracle repair | T-GEN-52 at `engine/tests/packaging/test_pt_release.py:216`: real small-wheel hash/transitive-dependency negatives; actual reference execution remains E-14. |
| V33 | CLOSED | T-CLS-07's independent policy cases and T-RND-83 unsupported-media composition. |
| V34 | OPEN — external only | E-06/E-08/E-09/E-14/E-15, no deduction. |
| V35 | CLOSED as design disposition | Scoped reference + compatibility targets and shared assets/subjects retained; actual release evidence external. |
| V36 | CLOSED | T-LKP-80/T-SNF-80: canonical atomic-write/hash/routing helpers. |
| V37 | CLOSED by retained design | T-CNV-04/51 base-cache reuse and T-TRX-55 explicit attempt measurement remain useful. |
| V38 | CLOSED | T-CLS-53/T-TRI-50 and protected/corrupt sweep: report-only sources have zero executable units/output. |

| Carried M2 item | Verdict | Evidence |
|---|---|---|
| V01 | CLOSED | T-TRX-80 timeout/no-reader and single polling owner. |
| V02 | CLOSED | T-GEN-80 installed-prefix positive plus source/outside-prefix negatives. |
| V03 | OPEN | Same M5-V01 version syntax mechanism; numeric ranges/platform repairs remain closed. |
| V04 | CLOSED for original DAG/isolation defect | T-GEN-82/83 and current workflow structure; Python collection residual separately closed by v3 code. |
| V05 | CLOSED | T-RND-80 per-unit setup failure, pending output/sibling continuation. |
| V06 | CLOSED | T-RND-81 both candidate orders preserve policy before deduplication. |
| All 30 disputed horizontal cells and M3 S4:K14 | CLOSED as execution registrations | T-GEN-85 plus T-ASM-90/91/T-TRI-90 effects; current T-META-05 shows none simultaneously declared N/A. Registration alone is not claimed as fresh per-cell execution. |

Carried Fable X items: **X-01 CLOSED** for progress (JT-09/16; new waiter defect is distinct); **X-02 CLOSED** configured Base URL environment (JT-12); **X-03 CLOSED** read-only failed/newer-schema persistence (JT-03/05); **X-04 CLOSED** committed interpreter edits (JT-10); **X-05 CLOSED in implementation** picker/resolver (JT-08/02), E-09 still external; **X-06 CLOSED** drop confirmation/default Cancel (JT-08); **X-07 CLOSED in text**, E-09 named README review external; **X-08 CLOSED** requests/egress consent predicate (JT-14/15); **X-09 CLOSED** file:null progress (JT-13); **X-10 CLOSED** destination revalidation (JT-09/15); **X-11 CLOSED** publication above; **X-12 CLOSED** retired selftest routing notice (JT-02); **X-13 CLOSED** run-option controls (JT-04); **X-14 CLOSED** startup version without Core (T-CLI-80/T-GEN-87); **X-15 CLOSED** background probe (JT-02), waiting unload now covered by M4-V01; **X-16 CLOSED for original references**, current prose residuals tracked separately; **X-17 CLOSED** no remote dialog API (JT-01/source); **X-18 CLOSED** first path + count history (JT-07); **X-20 CLOSED** storage/sync disclosure (README). There was no X-19 in the carried ledger.

Carried simplicity S-01..S-12 retain their scoped **CLOSED** dispositions: redundant argv/errors/barrels removed; yes-file is authorization; replay helpers remain test-local; dead history/trace surfaces removed; environment diagnostics consumed; shared path helpers; no production test-loading API; coordinator inputs used; ignore rules scoped. **S-13 CLOSED** for its original stale handoff above. **S-14 and S-15 CLOSED** under T-GEN-84 (`engine/tests/packaging/test_m2_packaging.py:66`) and T-RPT-51: canonical provider DEFAULT_META, report publisher ownership and CLI copy/error ordering. **S-16..S-21 CLOSED individually above.** M5-S01 is a new retained subscription, not a reopening of an unrelated deleted helper.

## Recursive vertical applicability and oracle quality

The current 84 stage/FM declarations expand per S0..S13 to **6,5,7,4,7,6,5,8,5,9,3,7,8,4**, unchanged from M4. The 67 class/stage equivalences now have no covered overlays. Current `matrix_problems=[]` confirms declared coverage/ownership structure, not the truth of every runtime property.

| Boundary family | Current owner facts and independently useful oracle | Remaining code/doc defect |
|---|---|---|
| S0 startup, runtime policy and lifecycle | CLI startup errors/version; isolated child argv; private owned runtime leases; deferred admission now invalidated across all three probed await boundaries. T-GEN-93/94/95, JT-11/12/16. | Shell/package version syntax M5-V01. Genuine OS/native evidence stays external. |
| S1 discovery / S2 Core triage | Source hash/length revalidation; link/exclusion bounds; actual corrupt inner document with surviving sibling, T-SNF-50..54 and T-TRI-90. | No additional demonstrated finding. |
| S3 Classify / S4 Select | Type-before-enum validation; bounded p/f numeric spelling; action guard; full-digest selection and per-class ordered IDs. T-CLS-80/90/91, T-SEL-50, T-GEN-85. | Original oversized-ID exception repaired; no additional demonstrated finding. |
| S5 Convert / S6 Render / S7 Lookup | Offline local preparation; conservative allocation before decoder; media policy before grouping; validated ledger entry before assembly; no new consent/provider owner in these stages. T-RND-80..83/90, T-LKP-50/51/80. | No additional demonstrated finding; native renderer memory is not inferred from small fixtures. |
| S8 Plan / S9 Approve / S10 Transcribe | Prepared hash-bound snapshot; request/egress predicate; consent-bound raster recheck; bounded provider failure vocabulary and continuation. T-PLN-02/51, T-TRX-52/53/80, JT-14/15. | Completed shell consent subscription retention M5-S01. No wrong approval demonstrated. |
| S11 Assemble / S12 Write / S13 Report and presenter | Exact placement IDs/reasons and preserved uninspected anchors; containment before reading old outputs; durable publication; independent per-invocation progress and per-run UI reset. T-ASM-90/91, T-WRT-50/51, T-RPT-51/91, JT-09/16. | No remaining Plan/Run counter contamination. Shell execution evidence consumer is M5-O01, not an output-placement defect. |

Oracle judgments: the expanded T-META-90 negatives and independent collector materially close the Python evidence problem; they do not validate the separate shell branch. Literal progress assertions at JT-09/16 now supplement reducer-equivalence checks; equality to the same reducer alone would be insufficient. Placement tests remain independently valuable but do not pair every transcript's semantics with its raster. Named language/authorship judgments are not replaced by key/set checks. Exact equality of a wheel's source modules does not establish fresh dependency resolution or release provenance.

No extra stages, duplicated pure-stage IO tests, process-tree subsystem, cache rewrite or broad architecture change is justified by this pass. The remaining fixes are a version grammar/table, execution identity validation, one removable subscription and narrow prose corrections.

## External evidence ledger — excluded from all four code/doc scores

Authority: `docs/renewal/90_ACCEPTANCE.md:71` (§7), E-01..E-15. **OPEN below means this audit has not independently verified the required external receipt**, not that an in-progress run failed. User reports the branch is pushed and real CI is running. Code fixes cannot manufacture these outcomes. Conversely, §7's existence does not excuse the code-fixable M5-O01 validator defect.

| ID | Status / evidence needed to close |
|---|---|
| E-01 | **OPEN — external verification**: six candidate-bound supported installed engine CI cells; preserve JUnit/registry/collection/runtime evidence. Local 568 passes do not close it. |
| E-02 | **OPEN — external verification**: three OS shell install/typecheck/build/Jest outcomes with named OS XMLs. Local 277 passes do not close it. |
| E-03 | **OPEN — external verification**: actual cooperative/forced cancellation and owned-process inventory on supported OS, including real Windows; fake coordinator probes do not close it. |
| E-04 | **OPEN — external verification**: real contract-min/max dependency resolution and contract executions. Current workflow definitions are supporting code facts only. |
| E-05 | **OPEN — external verification**: public artifacts, six fresh wheel installs, pip check/version/selftest and terminal-launch sentinel receipts. |
| E-06 | **OPEN — external verification**: actual tagged release, six release-test executions and constrained attestations. No tag/release action taken here. |
| E-07 | **OPEN — external verification**: candidate-bound final trace/score command evidence and manual 7/7. Also repair M5-O01 before trusting its shell completeness claim. Synthetic score controls are not this result. |
| E-08 | **OPEN — named human**: distinct implementer/reviewer MAN-01 clean-room attestation, validated for the actual candidate. |
| E-09 | **OPEN — named humans / real app**: MAN-02 README, MAN-03 bilingual meaning and MAN-04 three OS × minimum/current Obsidian rehearsals with actual identities/outcomes. |
| E-10 | **OPEN — external verification**: actual packaged-candidate PT-06/PT-08 executions on release targets and evidence companions. Published FX-71 is now locally closed and is not a substitute. |
| E-11 | **OPEN — post-publication**: actual post-deploy report/cleanup log and rollback if required; expressly unscored even by acceptance. |
| E-12 | **OPEN — external verification**: nine intermediate Python3.11/3.12/3.13 smoke receipts across three OS on the same candidate. |
| E-13 | **OPEN — external verification**: genuine per-phase/per-target complete-parameter v3 evidence. Producer/consumer Python code is repaired; old blank-commit/stale-suite local receipts are not relabeled. |
| E-14 | **OPEN — external verification**: fresh Linux x64/Python3.14 Core0.3.6 hash-mode reference plus install reports, metadata/licenses and tamper negatives. The offline local dependency bridge is not this evidence. |
| E-15 | **OPEN — release / named humans**: constrained provenance for every subject, six post-attestation execution sets, exact tag/SHA and candidate-bound named review files. |

## Scores and exactly what blocks 100

Five components per dimension, each /20. Deductions are audit judgments about open demonstrated code/doc mechanisms; they are not the release acceptance score. Aliases are counted once per affected check. **100 requires no open finding in that dimension.** External E-01..E-15 and M1-V31/V34 have zero deductions, regardless of receipt availability.

| Dimension | Components (/20) | Score | Exhaustive blockers to 100 |
|---|---|---|---|
| Vertical | S0–S4 validation/selection 20; S5–S7 preparation/cache 20; admission/cancellation 20; approval/publication/UI effects 20; runtime admission parity 16 | **96/100** | **M5-V01 only**: shell admits malformed versions the package gate rejects (M3-V04/M2-V03/P-02 residual). |
| Oracles | Literal independent expected values 20; composed boundaries 20; adversarial cross-language controls 16; complete Python parameter universe 20; shell execution completeness 16 | **92/100** | **M5-V01**: apparently matching but unequal syntax tables omit shared counterexamples; **M5-O01**: omit-one-plus-duplicate shell case falsely passes scorer. |
| Docs ↔ code | Engine normative facts 20; shell behavior promises 18; runtime contract explanation 18; evidence completeness claims 18; operational recipes/applicability 20 | **94/100** | **M5-D01**: two live pending-sync clauses; **M5-D02**: unconditional outside-vault cwd promise/comments; **M5-V01**: claimed package/shell syntax agreement is false; **M5-O01**: shell completeness claim exceeds count-only validator. |
| Simplicity | Canonical helpers 20; removed dead surfaces 20; retained designs justified 20; bounded state/lifetime 18; one current ownership/status account 18 | **96/100** | **M5-S01**: obsolete cancellation resolver retained per completed consent job; **M5-D01**: conflicting live synchronization status. |

The original admission-cancellation, progress, V3-ID, Python collection, supported-host publication and matrix-cleanup mechanisms have concrete repairs and scoped evidence. The five mechanisms listed above are the complete open code/doc set demonstrated by this audit; external acceptance remains independently mandatory.
