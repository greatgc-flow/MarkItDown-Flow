# M6 recursive MECE audit — vertical, oracles, docs ↔ code, simplicity

2026-11-09. Workspace: repository. Authority: SPEC DRAFT-3.8, SHELL, PACKAGING, TESTPLAN and ACCEPTANCE. Baseline: [M5_cx_vertical.md](M5_cx_vertical.md), checked against current sources, executable assertions, local receipts and R33/R34 changes.

**Code/doc scores: vertical 96/100; oracles 94/100; docs ↔ code 92/100; simplicity 96/100.** Three of M5's five primary mechanisms are CLOSED; two remain OPEN. Three new mechanisms are demonstrated below. Aliases are accounted for without additional findings. External acceptance evidence makes no deduction in these scores.

Only this file was written. No code, tests, fixtures, configuration, other documentation or evidence artifacts were changed. No git commands, network queries, installations, builds, full pytest/Jest runs or release actions were performed. Python probes used `python -B -`; TypeScript was transpiled in memory. Coordinator/EngineRun probes used production modules, existing in-memory filesystem/process/clock fixtures and an inert Obsidian Modal base. They launched no engine, LibreOffice or provider. Synthetic evidence controls below were confined to memory and are not acceptance receipts.

## Evidence actually checked

| Check | Result and limit |
|---|---|
| Current engine receipt | `build/trace/junit-r34-followup-full.xml`: **679 cases, 667 passed, 12 skipped, zero failures/errors**. Collection has **680 identities / 679 selected**, including all 20 T-GEN-85 parameters. Registry v3 seals the exact collection bytes; collection `suite_sha256` equals current `tools.trace.suite_digest`. Candidate commit is empty. `build/trace/r34-followup-full.log:11` records 667 passed / 12 skipped / 1 deselected. This is local evidence, not six supported installed-target receipts. |
| Earlier engine receipt | `build/trace/r34-junit-engine.xml`: 678 cases, 666 passed / 12 skipped; its collection is stale against current test sources. It is superseded locally by the follow-up receipt above. No receipt was rewritten. |
| Shell execution | `build/trace/junit-shell.xml`: **296 passed**, zero failures/errors/skips. `junit-shell-local.xml` also has 296 passing cases, but its JT-17 range title still says Core >=0.3.5; current source/current `junit-shell.xml` say >=0.3.7. `collection-shell-local.json` has 296 identities and an intact registry seal, but its source digest is stale and commit is `local-r33`. These old companions cannot establish current candidate-bound execution. |
| Typecheck | Compiler API using the absolute `shell/tsconfig.json` through `getParsedCommandLineOfConfigFile`, no emit/incremental output: **74 root files, zero diagnostics**. The initial incomplete-config harness's type-resolution errors were corrected; they are not source defects. |
| Trace integrity | Direct read-only calls: requirement unknown/uncovered/untagged **0/0/0**; `registration_problems=[]`, `matrix_problems=[]`, `golden_problems=[]`. These establish registration/integrity, not every runtime property. |
| Matrix | **84** expanded stage/FM declarations; per S0..S13: **6,5,7,4,7,6,5,8,5,9,3,7,8,4**. **59** expanded class/stage N/A declarations, matching the header. Direct original T-META-05/06 assertions pass: no covered/N/A overlap and no count mismatch. R33 removed K12's eight formerly N/A execution cells. |
| Golden reference | Actual `tools.golden.verify` succeeds with reference producer **Core 0.3.7**. T-META-91/94 retain independent reference-pin/producer checks (`engine/tests/packaging/test_m3_release.py:22`, `:56`); current compatible Core is not substituted into the seal. Integrity does not supply a new independent human review or a fresh Linux reference install. |
| Published FX-71 | Actual `tools.record_protocol.verify` returns **0**, **53 files verified**, including derived transformations. Manifest and `version.json` report Python **3.14.10 / Core 0.3.7**. R34 refreshed the version probe/variants while retaining earlier sealed protocol streams (`docs/renewal/20_SHELL.md:256`); this is not a new recording of every R33 legacy path. |
| Version syntax controls | **155** actual shell/package-gate comparisons: five version fields × 31 valid/malformed suffixes; **zero disagreements**. Includes M5's garbage, lone `+`, repeated dots, rc/post/dev/local and trailing whitespace controls. Separate short-release boundary probes reveal M6-O01 below. |
| Evidence consumer controls | Actual `execution_receipt` plus `shell_rows_passed`: full **True**; omit **rejected**; omit + duplicate **rejected**; substitute **rejected**; skip **False**; stale candidate **rejected**; source mismatch **rejected**. See M5-O01 closure for the synthetic-control boundary. |
| Consent/progress probes | Three completed dismissals on one coordinator retain **1,2,3** cancellation waiters; dispose clears them. Actual `EngineRun` with a valid successful report accepts `convert` without diagnostics but flags `preconvert` as `shell.PROTOCOL`. Details below. |

User-provided context is recorded: **PR #1 merged and three-OS CI green**, engine 667 passes on Core 0.3.7, shell 296 Jest passes. No remote CI artifacts or merge SHA were fetched. The user's reported CI completion is not treated as a failure; exact target/phase/candidate receipts and release/human obligations are tracked separately at the end.

## Every primary M5 finding

“CLOSED” closes the specified mechanism, not an external acceptance gate. A distinct newly found counterexample is identified separately instead of erasing an actual repair.

| M5 ID | Verdict | Current evidence |
|---|---|---|
| **M5-V01**, malformed package-version syntax; M3-V04 / M2-V03 / Fable P-02 syntax residual | **CLOSED for the malformed-suffix defect** | Shell now requires both the package character grammar and PEP 440 grammar at `shell/src/process/version-gate.ts:136`, `:146`, `:156`. All five M5 counterexamples are refused; rc/post controls remain admitted. JT-17 independently lists the repaired spellings (`shell/test/jt-17-version-gate.test.ts:117`, `:145`, `:153`); package T-GEN-96 remains at `engine/tests/packaging/test_m4_docs.py:35`. Actual 155-case comparison agrees. **Broader “every spelling” range parity has a NEW numeric-arity defect, M6-O01**, rather than the old malformed-suffix failure. |
| **M5-O01**, counts replacing shell execution identities | **CLOSED in producer/consumer code** | Fixed complete Jest collection at `tools/trace.py:359`; expanded cases, no executed/skipped collection cases, source-file completeness and uniqueness at `:374`–`:389`; candidate/source seal at `:350`, `:423`; exact unique JUnit matching at `:464`–`:478`; shell branch invokes it at `:657`, `:687`. T-META-97 has ten passing adversarial parameters and T-META-98 checks quoted titles/platform guards (`engine/tests/unit/test_m5_trace.py:34`, `:10`). In-memory controls use the 296 real case identities, an explicitly synthetic candidate/source seal and the one renamed Core title aligned to current XML: full positive covers **237 applicable Windows source registrations**; omission/duplication/substitution/skip/staleness negatives fail. This tests validator behavior, not the authenticity of synthetic receipts. CI collects before executing (`.github/workflows/ci.yml:128`); actual three-target artifacts remain external. |
| **M5-S01**, completed consent cancellation waiters | **OPEN — unchanged mechanism** | Resolver appended at `shell/src/ui/coordinator.ts:254`–`:258`, losing side of `Promise.race` at `:317`; normal job finalizer at `:218`–`:222` never releases it. Direct three-job reproduction retains 1,2,3 waiters. Only Cancel/dispose drains them (`:240`). JT-16 tests active consent cancellation (`shell/test/jt-16-cancel-ui.test.ts:131`), not normal multi-job subscription lifetime. |
| **M5-D01**, two live pending-sync disposition clauses | **CLOSED** | The former pending clauses now explicitly say synchronization is complete and OS/execution receipts remain external (`docs/renewal/20_SHELL.md:193`, `:196`). This is a semantic prose check, not merely absence of the old SYNC token. The independent HANDOFF publication-status defect is new M6-D01. |
| **M5-D02**, unconditional outside-vault cwd promise | **OPEN — narrowed to remaining comments/oracle wording** | Normative `20_SHELL.md:76`, `:205` now acknowledge a venv inside the vault; README agrees. Production comments still claim “not vault content”, safety even without `-I`, and “outside the vault” (`shell/src/process/launcher.ts:45`, `:169`); coordinator says “never the vault” (`shell/src/ui/coordinator.ts:110`). JT-12's external-venv-only fixture/title repeats this (`shell/test/jt-12-spawn-replay.test.ts:38`, `:191`, `:212`). Actual helper returns `C:\Users\alice\Vault\venv` for a selected interpreter beneath that directory. Isolation remains intact; this is a doc/comment overclaim. |

## Recursive carried ledger from M5

All inherited IDs in M5 are accounted for here, including CLOSED items. Test IDs denote current executable assertions; engine receipt membership is local execution evidence within the limits above. Aliases refer to the same mechanism and do not multiply deductions.

### M3/M4 vertical and oracle handoffs

| IDs carried by M5 | Verdict | Current code/oracle evidence |
|---|---|---|
| M3-V01 / M1-V22, HWP V1 payload kinds | **CLOSED** | T-CLS-90 at `engine/tests/stage_io/step7/test_m3_engine.py:17`: five malformed-type cases; all five pass in current receipt. `_well_typed` checks string type before enum membership (`engine/src/mdflow/classify.py:131`). |
| M3-V02 / M1-V26, fractional PDF allocation | **CLOSED** | `engine/src/mdflow/render.py:87`; ceil-scaled dimensions checked before render. T-RND-90 at `test_m3_engine.py:46`: four passing DPI/rotation cases with refused fractional and admitted exact boundaries. |
| M3-V03 / X-01 / P-01, progress contamination and quadratic presenter | **CLOSED** | `shell/src/ui/progress.ts:50` resets per-run state; JT-09 literal Run-only object (`jt-09-output-busy.test.ts:257`) and JT-16 Plan→Run UI counts/no history (`jt-16-cancel-ui.test.ts:202`). T-RPT-91 (`engine/tests/stage_io/step7/test_m4_engine.py:44`) passes with independent invocation counters. New M6-V01 concerns stage vocabulary, not counter contamination. |
| M3-V04 / M2-V03 / P-02, gate parity | **OPEN only for NEW M6-O01** | Original malformed text/platform/range repairs stand; numeric release tuple arity still disagrees. Both actual gates were called with the same changed field. |
| M3-V05 / M4-O01, Python full-parameter universe | **CLOSED in code** | `tools/trace.py:395`, `:423`, `:483` retain fixed independent collection and exact identity/parameter matching. T-META-90: 14 passing mutations; T-META-96: restricted execution cannot define the full universe (`engine/tests/unit/test_m3_trace.py:13`, `test_m4_trace.py:11`). Current collection retains all 20 T-GEN-85 parameters. |
| M3-H01; all 30 disputed earlier horizontal cells; M3 S4:K14 | **CLOSED as scoped execution registrations** | T-GEN-85 (`engine/tests/stage_io/test_class_sweep.py:252`), all 20 parameters pass; T-ASM-90/91 and T-TRI-90 check effects. Direct T-META-05/06 and current matrix show no covered/N/A overlap. Registration is not a new semantic proof for every cell. |
| M3-O01, placement/member oracles | **CLOSED for original gaps** | T-ASM-90/91 and T-TRI-90 (`test_m3_engine.py:89`, `:117`, `:134`): respectively 5/1/1 passing cases, independently expected IDs/reasons, uninspected anchor and corrupt-member/sibling continuation. |
| M3-D01 / Fable D-01 / N-12, synchronization/applicability prose | **CLOSED for M5's residual** | The two live status rows are corrected; matrix header equals 59 actual remaining declarations. A newly located current HANDOFF statement remains M6-D01. |
| M4-V01, Cancel/dispose during admission | **CLOSED** | `shell/src/ui/coordinator.ts:156`, `:171`, `:177`, `:196`: interrupt checks after gate/destination/listing. JT-16 deferred gate Cancel/dispose/control (`jt-16-cancel-ui.test.ts:261`, `:286`, `:304`) retained. Reservation remains synchronous. |
| M4-V02, oversized V3 numeric IDs | **CLOSED** | Bounded numeric spelling before `int` at `engine/src/mdflow/classify.py:164`; T-CLS-91 (`test_m4_engine.py:15`), four passing PDF/GIF cases with zero provider work, output and surviving sibling. |
| M4-V03 / N-07 / P-06, raw URL authority | **CLOSED for demonstrated aliases/userinfo** | `shell/src/pure/settings.ts:181`, JT-04 raw-authority negatives (`jt-04-migration-map.test.ts:222`): empty userinfo, shorthand/integer/hex/octal/trailing-dot hosts rejected; literal loopbacks retained. No universal parser-equivalence claim is made. |
| X-11 / P-03, supported-host fixture publication | **CLOSED** | Actual 53-file verifier succeeds; Core 0.3.7/Python3.14 fixture passes default gate. JT-17 (`jt-17-version-gate.test.ts:39`) expects actual producer identity; T-GEN-97 verifies recorder argv. No widened host policy needed. |
| N-02 / D-02, isolated operational recipes | **CLOSED for missing `-I`** | T-META-95 (`engine/tests/packaging/test_m4_docs.py:11`), BOOTSTRAP/PACKAGING recipes and fixed `ENGINE_ARGV_PREFIX` (`shell/src/process/launcher.ts:31`). Cwd comment residual remains M5-D02. |
| N-04, Windows residue disclosure/recovery | **CLOSED within original implementation/disclosure scope** | README Windows caveat; owned temp leases/recovery in `engine/src/mdflow/runtime_temp.py`; T-GEN-93/94/95 (`engine/tests/unit/test_m4_temp.py:11`, `:29`, `:70`) retain real native-death and live/unowned/link negatives. Real app/OS release rehearsal remains E-03/E-09. |

### Every carried M1 vertical item

| M1 ID | Verdict | Retained current evidence/scope |
|---|---|---|
| V01 | **CLOSED** | T-META-50, T-TRX-57, T-WRT-51, T-RPT-52..56: applicable stages, durable outputs and report counters. |
| V02 | **CLOSED** | T-SNF-50, T-GEN-53, T-CNV-52/53, T-TRX-54, T-RPT-51, T-RND-80: IO/interruption boundaries and sibling effects. |
| V03 | **CLOSED for original gaps** | T-CLS-50, T-LKP-50, T-ASM-50, T-TRX-53/54/56: validation reaches actual consumer, raster and assembly boundaries. |
| V04 | **CLOSED** | T-RND-81/82, T-GEN-85[K09]: real HWP extraction/stored-stream refusal, both candidate orders. |
| V05 | **CLOSED** | T-META-81 plus T-META-05/06; explicit current applicability, no blanket execution-stage fixture claim. |
| V06 | **CLOSED** | T-SNF-50/53: roots, exclusions, links and deduplication. |
| V07 | **CLOSED** | T-SNF-51/54; `_source_bytes` (`engine/src/mdflow/orchestrate.py:73`) rechecks length/hash before using source bytes. |
| V08 | **CLOSED** | T-CNV-50, T-RND-50, T-CTR-50/51: source/media/nested expansion bounds. |
| V09 | **CLOSED** | T-WRT-50: containment before reading skipped/old output. |
| V10 | **CLOSED** | T-WRT-51: restore missing media without replacing preserved Markdown. |
| V11 | **CLOSED** | T-LKP-50/T-ASM-50: invalid timestamp/provenance cannot become a cache hit/assembled transcript. |
| V12 | **CLOSED** | T-RPT-50: bounded nested progress fields preserve identity/counters. |
| V13 | **CLOSED** | T-RPT-51: durable report-copy failure agrees with terminal exit/event. |
| V14 | **CLOSED within amended scope** | T-TRX-50/80: bounded command capture, timeout, inherited pipe/no-reader behavior; no general descendant-tree promise inferred. |
| V15 | **CLOSED within bounded amendment** | T-TRX-51: drip-body deadline; documented native/DNS/TLS limitations remain. |
| V16 | **CLOSED** | T-CLI-50/T-PLN-50: exact options/provider scope and none-provider cost. |
| V17 | **CLOSED** | T-TRX-52: error vocabulary/redaction before storage and sibling continuation. |
| V18 | **CLOSED** | T-SEC-50: proxy userinfo excluded from Plan metadata. |
| V19 | **CLOSED** | T-RND-81 both orders: HWP stored-stream policy survives grouping/deduplication. |
| V20 | **CLOSED** | T-SEL-50/T-CNV-54: full digest identity; shortened filename collision refused. |
| V21 | **CLOSED** | T-SNF-52: literal encryption flag and malformed HWP header handling. |
| V22 | **CLOSED** | T-CLS-80/90 and T-SEL-51; V1 malformed types safe, convert_only schedules no OCR. V3 bound additionally T-CLS-91. |
| V23 | **CLOSED** | T-PLN-51/T-PLN-02: approved snapshot/options/unit bound and actual production hash. |
| V24 | **CLOSED** | T-TRX-53/T-TRX-08: changed raster refused immediately before send. |
| V25 | **CLOSED** | T-RND-52: prior encoded payload released before next render; no native working-set certification inferred. |
| V26 | **CLOSED** | T-RND-53/90: pixel limit before decode and conservative fractional allocation. |
| V27 | **CLOSED** | T-RND-54: actual animated media's first-frame pixels. |
| V28 | **CLOSED** | T-WRT-52: output collision/reserved-name handling. |
| V29 | **CLOSED** | T-LKP-51: output/sibling survive ledger-write failure. |
| V30 | **CLOSED** | T-PLN-02 (`engine/tests/unit/test_core_select_plan.py:102`), META-80 and PLN-52: production Plan/hash, not detached expected hashing. |
| V31 | **OPEN — external only** | E-01/E-05/E-12/E-13; no deduction. User reports green CI; exact endpoint/smoke/install companions were not fetched here. |
| V32 | **CLOSED as oracle repair** | T-GEN-52 (`engine/tests/packaging/test_pt_release.py:216`): actual small-wheel hash/transitive dependency mutation; genuine fresh reference install stays E-14. |
| V33 | **CLOSED** | T-CLS-07 (`engine/tests/unit/test_core_classify.py:192`) exact issue-policy expectations; T-RND-83 connects unsupported-media classification to refused preparation/placement. |
| V34 | **OPEN — external only** | E-06/E-08/E-09/E-14/E-15; no deduction. |
| V35 | **CLOSED as design disposition** | Reference versus compatibility targets and common assets/subjects remain explicit in `docs/renewal/25_PACKAGING.md` and `tools/build_engine.py`; executions/provenance external. |
| V36 | **CLOSED** | T-LKP-80/T-SNF-80: shared atomic-write/hash/format decisions. |
| V37 | **CLOSED by retained design** | T-CNV-04/51 intentional base-cache reuse; T-TRX-55 explicit attempt measurement rather than patching provider methods. |
| V38 | **CLOSED** | T-CLS-53/T-TRI-50 and protected/corrupt sweeps: no executable work/output for report-only inputs. |

### Every carried M2 and Fable P/D/N/X item

| ID(s) | Verdict | Current evidence and precise residual |
|---|---|---|
| M2-V01 | **CLOSED** | T-TRX-80 (`engine/tests/stage_io/step7/test_m2_engine.py:21`), timeout/no-reader and single polling owner. |
| M2-V02 | **CLOSED** | T-GEN-80 (`engine/tests/packaging/test_m2_packaging.py:13`): installed-prefix positive and source/outside-prefix negatives. |
| M2-V03 | **OPEN only as M6-O01** | Original malformed syntax is closed; actual short-release comparison still breaks broader gate parity. |
| M2-V04 | **CLOSED for original DAG/isolation defect** | T-GEN-82/83 (`test_m2_packaging.py:36`, `:57`), current attest→verify→score workflow and installed-mode fixtures. Python completeness separately closed above. |
| M2-V05 | **CLOSED** | T-RND-80 (`test_m2_engine.py:40`), setup failure becomes per-unit pending and sibling succeeds. |
| M2-V06 | **CLOSED** | T-RND-81 (`test_m2_engine.py:62`), policy preserved in both equal-payload orders. |
| P-01 | **CLOSED** | M3-V03, JT-09/16 literal reset/UI oracles above. |
| P-02 | **CLOSED for original syntax; broader parity OPEN M6-O01** | Actual malformed suffixes now fail both gates; short valid release segments expose a separate package oracle defect. |
| P-03 | **CLOSED** | Verified published FX-71/default-policy admission above. |
| P-04 | **CLOSED** | `shell/src/pure/settings.ts` absolute interpreter validation; coordinator refuses before gate/spawn (`:168`); JT-04/JT-09 relative-input negatives. |
| P-05 | **CLOSED for rejected settings** | `shell/src/ui/settings-tab.ts:72`, whole-plugin JT-04 (`shell/test/jt-02-plugin-round2.test.ts:183`): notice plus persisted-value restoration. No claim that every storage write succeeds. |
| P-06 | **CLOSED** | Raw authority/userinfo alias controls in M4-V03/JT-04. |
| D-01 / N-12 | **CLOSED for pending-sync clauses** | `20_SHELL.md:193`, `:196`; separate HANDOFF publication claim is M6-D01. |
| D-02 | **CLOSED** | T-META-95 and isolated recipes. |
| D-03 | **OPEN as M5-D02** | README/normative cwd corrected; production comments and external-fixture-only oracle wording remain. Historical dated HANDOFF sections are not treated as new test counts. |
| D-04 / ag covered-cell declarations | **CLOSED** | Current 59-cell expansion, T-META-05/06, no covered/N/A overlap. |
| N-01 | **CLOSED** | `coordinator.ts:145` reservation across awaits; JT-09 same-tick deferred-gate double submit. |
| N-02 | **CLOSED for isolation; cwd prose OPEN M5-D02** | Fixed prefix and every request builder; JT-11/JT-12. |
| N-03 | **CLOSED** | `coordinator.ts:303` preserves actual Plan diagnostics, adds PROTOCOL only if absent; JT-15 E_USAGE versus truncated-Plan controls. |
| N-04 | **CLOSED in implementation/disclosure scope** | Owned-temp tests/disclosure above; real app evidence E-03/E-09. |
| N-05 | **CLOSED in implementation** | `shell/src/process/dom-picker.ts:43` empty outcome; JT-08/JT-02 notice and zero submit. |
| N-06 | **CLOSED for absent activation** | `dom-picker.ts:72`, real activation source in `node-apis.ts`; JT-08 blocked path never clicks input. |
| N-07 | **CLOSED** | M4-V03 raw URL policy. |
| N-08 | **CLOSED by disclosure** | JT-04 plus README enabled-drop disclosure; `shell/src/ui/entry-points.ts:55`. Default remains off. |
| N-09 | **CLOSED by disclosure** | JT-04/settings-tab reload notes for context menu/drop/locale. |
| N-10 | **CLOSED** | `shell/src/process/spool-fs.ts:28`, `node-apis.ts:63`; JT-13 exact ranged-read windows/EOF/removal, zero whole-file reads. No total-JSON-memory guarantee inferred. |
| N-11 | **CLOSED** | Whole-plugin JT-02 first-use log-folder creation before opening; Node mkdir implementation retained. |
| X-01 | **CLOSED** | Incremental progress/reset above; waiter retention is a different lifetime. |
| X-02 | **CLOSED** | JT-12 configured Base URL wins in constructed engine environment. |
| X-03 | **CLOSED** | JT-03/05 failed-read/newer-schema persistence stays read-only. |
| X-04 | **CLOSED** | JT-10 committed interpreter changes; no partial-typing probe. |
| X-05 | **CLOSED in implementation** | JT-08/02 picker and Node resolver; real Electron/app outcome remains E-09. |
| X-06 | **CLOSED** | JT-08 drop confirmation defaults to Cancel. |
| X-07 | **CLOSED in text** | README disclosures and JT-04; named README/app review remains E-09. |
| X-08 | **CLOSED** | JT-14/15 egress AND requests-to-send consent predicate. |
| X-09 | **CLOSED** | JT-13 run-level `file:null` framing. |
| X-10 | **CLOSED** | JT-09/15 destination revalidation before replay. |
| X-11 | **CLOSED** | Verified 53 published files/default gate, above. |
| X-12 | **CLOSED** | JT-02 compatibility selftest routing notice. |
| X-13 | **CLOSED** | JT-04 run-option controls. |
| X-14 | **CLOSED** | T-CLI-80/T-GEN-87 (`engine/tests/stage_io/step7/test_fable_handoff.py:10`, `engine/tests/packaging/test_fable_handoff.py:12`): version with absent Core and package refusal without crash. |
| X-15 | **CLOSED** | JT-02 background probe; waiting admission disposal covered by JT-16/M4-V01. |
| X-16 | **CLOSED for original references; current residuals separate** | M5-D02 and M6-D01 name current conflicting prose explicitly; no blanket “all docs current” claim. |
| X-17 | **CLOSED** | JT-01/source: no remote dialog API. |
| X-18 | **CLOSED** | JT-07 first path + count history, `coordinator.ts:91`. |
| X-20 | **CLOSED** | README cache/transcription/log synchronization disclosure and JT-04. There is no carried X-19. |

### Every carried simplicity item

| Fable ID | Verdict | Current evidence |
|---|---|---|
| S-01 | **CLOSED** | Redundant production `pure/argv.ts` absent; real launcher used by JT-04/11/12. |
| S-02 | **CLOSED** | Red-phase `pure/errors.ts` absent; actual code vocabulary is in `shell/src/pure/codes.ts`. |
| S-03 | **CLOSED** | No production `index.ts` barrel in pure/process/ui; imports address actual modules. |
| S-04 | **CLOSED** | `Authorization` only has yes-file form (`shell/src/process/launcher.ts:81`); JT-15 batch authorization. |
| S-05 | **CLOSED** | Replay/oracle helper is test-local `shell/test/fixtures/protocol.ts`; launcher owns real argument construction. |
| S-06 | **CLOSED** | No production `outputsCreated`; history facts derive from process/report results (JT-07/13). |
| S-07 | **CLOSED** | No production `pure/trace.ts`; `tools/trace.py` consumes actual registrations and exact receipts. |
| S-08 | **CLOSED** | `collectSetupDiagnostics` uses `environmentDiagnostics` (`shell/src/process/setup.ts:184`), JT-10. |
| S-09 | **CLOSED** | Shared `pure/paths.ts` used by output validation/log/main; `ui/output-path.ts:6` imports directly. |
| S-10 | **CLOSED** | No production `this.load()` test convenience call; whole-plugin JT-02 uses lifecycle. |
| S-11 | **CLOSED** | Entry point feeds job log (`coordinator.ts:294`); EngineRun events feed progress (`:265`). |
| S-12 | **CLOSED** | `.gitignore` scopes actual build/dependency/cache/local-vault/worktree output; no retired v1 generated-script block. |
| S-13 | **CLOSED for original stale counts/pending-X14; NEW status drift OPEN M6-D01** | Original 446-test/pending-X14 claims remain gone. Current top-level pending-publication sentence contradicts verified files. |
| S-14 | **CLOSED** | T-GEN-84 (`engine/tests/packaging/test_m2_packaging.py:66`), canonical provider DEFAULT_META/describe. |
| S-15 | **CLOSED** | T-GEN-84 and T-RPT-51: report owns stdout, CLI durable-copy/error ordering. |
| S-16 | **CLOSED** | No `@electron/remote` production import/external in `shell/esbuild.config.mjs`; JT-01. |
| S-17 | **CLOSED** | No production `approvableHashes`; actual `renderYesFile` remains (`launcher.ts:182`), JT-15. |
| S-18 | **CLOSED** | `shell/src/pure/spool.ts` has used `finishWith`/`discard`, no redundant exported `finish`. |
| S-19 | **CLOSED** | `CoordinatorDeps` has no unused locale dependency (`coordinator.ts:44`). |
| S-20 | **CLOSED** | No production `legacyFilePath`; entry points use supplied Node resolver (JT-08). |
| S-21 | **CLOSED** | Output-path direct pure helper imports, no re-export shim (`ui/output-path.ts:6`). |

## Open inherited mechanisms: exact remaining work

### M5-S01 — MINOR, retained cancellation subscriptions

Production `cancelSignal()` pushes a resolver for each consent race (`coordinator.ts:254`); normal consent completion leaves it behind (`:317`). The job finalizer resets activity/engine/progress only (`:218`). The direct probe uses the actual published `consent-1-plan.stdout.json`, production decoder/coordinator, fake process/filesystem and consent resolving `{approved:false}` on one persistent coordinator:

| Completed job | Accepted | Active afterward | History entries | Retained waiters |
|---|---|---|---|---|
| 1 | true | false | 1 | **1** |
| 2 | true | false | 2 | **2** |
| 3 | true | false | 3 | **3** |

Dispose drains the count to zero. These jobs make no provider requests and launch only fake Plan processes. No wrong authorization or live child leak is demonstrated. Minimal closure: remove the job-owned subscription when the race settles, including exceptional completion, or release it in a guaranteed job finalizer. Add a normal multi-job approve/dismiss lifetime oracle expecting zero retained waiters, followed by a correctly cancelled next job. No new cancellation framework is needed.

### M5-D02 — MINOR, cwd comments still exceed the corrected contract

`engineWorkingDirectory('win32', 'C:\Users\alice\Vault\venv\Scripts\python.exe')` actually returns **`C:\Users\alice\Vault\venv`**. The unconditional outside-vault comments at `launcher.ts:45`, `:169` and `coordinator.ts:110` are therefore false; JT-12 only proves its chosen external venv fixture. `20_SHELL.md:76` now explicitly allows this nested case. Minimal closure: align comments and oracle wording with that contract; retain fixed `-I -X utf8 -m mdflow`. A small nested-venv helper assertion can make the limited cwd claim explicit. No containment requirement, install change or import vulnerability is inferred.

## New defects

### M6-V01 — MINOR, legacy conversion emits a stage the shell rejects

**Trigger:** enable legacy preconversion and process an eligible DOC/PPT/RTF/HWP<5 source. `engine/src/mdflow/orchestrate.py:235` calls `self.stage(logical, 'preconvert', convert.convert_legacy, ...)`. `_Pipeline.stage` emits the supplied name (`:133`–`:136`) after conversion returns, including a handled `E_PRECONVERT` result.

**Contract/consumer:** SPEC's explicit stage vocabulary omits `preconvert` (`docs/renewal/10_SPEC.md:480`); shell's Stage union/set and decoder likewise omit it (`shell/src/pure/framing.ts:11`, `:15`, `:102`). Unknown **event names** can be ignored; this is a known `stage` event with a rejected field, so that rule does not save it.

**Read-only reproduction:** actual `_Pipeline.stage('legacy.rtf', 'preconvert', inert_callback)` emits a normal v1 stage JSON line through the production reporter. Feed an equivalent line and a published valid successful report into actual `EngineRun` with the existing fake spawner/spool. The report bytes/exit are held constant; change only the stage field:

| Stage | decodeEvent | stdout/report | EngineRun outcome | Diagnostics |
|---|---|---|---|---|
| `convert` | event | valid | complete | `[]` |
| `preconvert` | **invalid/schema** | valid | complete | **`['shell.PROTOCOL']`** |

Thus the opt-in path reports a protocol fault on otherwise successful work and drops that progress event. **It does not prevent conversion or force a failed outcome** in this probe. `EngineRun` adds the visible diagnostic at `shell/src/process/engine-process.ts:268`; coordinator forwards run diagnostics (`coordinator.ts:361`).

**Oracle hole:** T-CNV-94 (`engine/tests/stage_io/step7/test_r33_engine.py:151`) asserts that a required stage subset is present; its assertion permits an extra invalid stage. The R33 shell test checks flag/environment/version/results projections (`shell/test/jt-r33-legacy-preconvert.test.ts:149`, `:350`) using older streams/synthetic report issues, without passing the new engine progress through the shell decoder. All four T-CNV-94 parameters pass locally while this composed boundary fails.

**Small closure:** keep the existing vocabulary by reporting the preparation under the appropriate existing conversion stage, or explicitly amend the producer/SPEC/consumer together. Add a composed opt-in progress test requiring zero invalid frames/PROTOCOL diagnostics, with ordinary and handled-failure controls. Do not introduce another pipeline stage solely to describe an implementation helper.

### M6-O01 — MINOR, package version oracle compares unnormalized release tuples

This is separate from M5's repaired malformed-version syntax. `engine/tests/packaging/_support.py:352` returns a variable-length tuple of leading dotted integers. `gate()` compares that tuple against three-component engine bounds (`engine/tests/packaging/test_pt_release.py:318`). Python lexicographic comparison makes `(2, 0) < (2, 0, 0)` and `(2, 1) < (2, 1, 0)` true. Shell normalizes missing patch to zero (`shell/src/process/version-gate.ts:162`).

Actual shell and package gates, each given the supported published response with **only `mdflow` changed**:

| Engine text | Shell enabled | Package problems | Documented release-segment range |
|---|---|---|---|
| `2.0` | true | **`['engine range']`** | Inside >=2.0.0,<2.1.0 |
| `2.0rc1` | true | **`['engine range']`** | Inside, suffix ignored |
| `2.0.0` | true | `[]` | Inside |
| `2.0.0rc1` | true | `[]` | Inside, suffix ignored |
| `2.1` | **false** | **`[]`** | Outside |

These spellings pass both syntax grammars. The package oracle can falsely certify a response at its forbidden engine upper boundary; it can also reject the lower-bound equivalent spelling. The normal engine emits `2.0.0`; no claim is made that today's real candidate reports `2.1`. This is an executable oracle/contract defect, not missing release evidence.

JT-17's syntax/range table (`shell/test/jt-17-version-gate.test.ts:103`, `:117`) and T-GEN-96's twelve cases (`engine/tests/packaging/test_m4_docs.py:24`) omit these shared boundary spellings. The shell comment claiming package agreement on every spelling (`version-gate.ts:154`) and normative same-spelling agreement (`20_SHELL.md:96`) still exceed the actual pair.

**Small closure:** normalize release components consistently before package comparison, preserving the documented suffix-ignored policy. Add the five literal controls above to both actual gate tests. Do not weaken the working shell upper bound or remove full syntax validation. The 155 suffix controls passing establishes the M5 grammar repair, not complete range equivalence.

### M6-D01 — MINOR, current HANDOFF still lists completed local publication as pending release evidence

`docs/renewal/HANDOFF.md:9` puts “supported-host FX-71 publication by its owner” in the current **Pending release evidence** summary. Actual publication has already happened: the production verifier checks all 53 published files successfully; default gate admission and JT-17 verify the supported producer; HANDOFF's own later M4 paragraph at `:35` says it is published, and R34's current fixture note is `20_SHELL.md:256`.

The dated M3/M4 counts and original Core 0.3.6 recordings are valid historical statements and are not findings. The defect is the unqualified current top-level pending-local-work sentence. This is locally correctable prose, not E-10's genuine packaged-candidate execution obligation. Minimal closure: remove publication from that current pending list and keep the distinct packaged execution, real app, provenance and named-review gates in ACCEPTANCE §7. No additional status document is necessary.

## R33/R34 vertical ownership and oracle assessment

| Boundary family | Current facts and useful oracle | Open code/doc mechanism |
|---|---|---|
| S0 runtime/version and process admission | Core >=0.3.7,<0.4; fixed isolated prefix, absolute interpreter, admission interruption checks; T-CLI-83 ten collision-entry cases and T-CLI-86 loaded-version mismatch pass. Core owns installation-conflict detection (`engine/src/mdflow/core_guard.py:49`). | M6-O01 package acceptance oracle; M5-D02 cwd comments. Actual production shell grammar repair is closed. |
| S1 discovery / S2 triage | Immutable source length/hash recheck, bounded container reads, corrupt member/sibling oracle; T-SNF-50..54/T-TRI-90. Core triage evidence stays verbatim. | No additional demonstrated code defect. |
| S3 classify / S4 select | Total V1/V3 boundaries; full content identities; R33 T/NONE groups tested independently by T-CLS-93 (CSV/TSV/JSON versus markup warning); 20-class sweep retained. | No additional demonstrated code defect. |
| S5 convert / S6 render / S7 lookup | R34 delegates LibreOffice to Core through documented stream options; engine-local `preconvert.py` absent. Marker/Markdown/media bounds and original/derived provenance in `engine/src/mdflow/convert.py:95`. T-CNV-91/92/93/94/95: **1/3/2/4/5** passing cases, including both real LibreOffice integrations in the existing receipt. T-RND-90/T-LKP-50/51 protect render/cache boundaries. | M6-V01 new progress stage crosses out of the agreed protocol. No missing real integration receipt is silently scored as a defect. |
| S8 plan / S9 approve / S10 transcribe | Plan binds exact returned Markdown provenance and prepared raster identities (`engine/src/mdflow/plan.py:62`); T-CNV-94 verifies denial, approved replay, real placement, durable unit ledger and warm hit for four legacy filters. JT-14/15 preserve batch/consent predicate. | M5-S01 retained normal consent subscriptions. No unauthorized egress demonstrated. |
| S11 assemble / S12 write / S13 report and UI | Original report/file identity retained, DERIVED frontmatter, in-situ placement/media publication; T-ASM-90/91, T-WRT-50/51, T-RPT-51/91 and literal JT-09/16 reset expectations. R33 derived result badge has independent projection assertions. | M6-V01 produces visible PROTOCOL despite valid successful report. M6-D01 misstates local publication status. |

Oracle strengths remain scoped: exact placement IDs do not establish semantic OCR accuracy for every raster; seal equality does not prove independent authorship; stage subset assertions do not validate a closed stage vocabulary. Read-only trace integrity and current test-source binding do not replace installed compatibility execution. The M6 horizontal file's initial four INVALID cells are negative/non-reach assertions, as its appended adjudication explains; current matrix overlap checks find no reopened registration hole.

Simplicity assessment: retain canonical hash/path/atomic-write helpers, the useful base cache, test-local replay helpers and Core-owned LibreOffice/process management. Do not add a second launcher, evidence scorer, cancellation framework or status document. The remaining lifetime fix is one removable subscription; protocol/range fixes need shared boundary assertions and small owner edits.

## External evidence ledger — zero code/doc deductions

Authority: `docs/renewal/90_ACCEPTANCE.md:71` (§7), E-01..E-15. **OPEN here means exact required receipt not independently established in this workspace audit.** It does not contradict the user's report of merged PR #1 and green three-OS CI. Those reported completed runs are recorded; their artifacts were not fetched, relabeled or synthesized. Code/doc audits cannot close named-human, published-release or real-app requirements by editing assertions.

| ID | Separate status and remaining evidence boundary |
|---|---|
| E-01 | **Reported CI green; OPEN exact-receipt verification.** Six supported installed endpoints (3 OS × Python3.10/3.14), JUnit/registry/collection/runtime, exact candidate. Local 667-pass source evidence does not independently supply these companions. |
| E-02 | **Reported three-OS CI green; OPEN exact-receipt verification.** Three named OS shell install/typecheck/build/Jest outcomes and current sealed inventories. Local 296-pass XML/old collection are not three candidate-bound target artifacts. |
| E-03 | **OPEN — real OS/process evidence.** Cooperative and forced cancellation, actual Windows/native status and absence of owned live processes. In-memory probes do not substitute. |
| E-04 | **OPEN — exact endpoint execution evidence.** Real contract-min Core0.3.7 and newest-compatible contract-max outcomes/schema negative on required target. |
| E-05 | **OPEN — public artifacts/fresh installs.** Six fresh wheel installs, pip check/version/selftest, terminal-launch sentinels and reference hash-mode installation. |
| E-06 | **OPEN — release/provenance.** Exact tag/release and six release executions with constrained attestations for all subjects. Merged PR alone does not create these. |
| E-07 | **OPEN — candidate final acceptance evidence.** Actual candidate-bound trace/score command receipts and manual 7/7. M5-O01 consumer code is closed; synthetic controls are never this score. |
| E-08 | **OPEN — named human.** Candidate-bound MAN-01 clean-room attestation, distinct implementer/reviewer. |
| E-09 | **OPEN — named humans/real app.** MAN-02 README, MAN-03 bilingual meaning, MAN-04 actual 3 OS × minimum/current Obsidian rehearsal. |
| E-10 | **OPEN — real packaged execution.** Actual PT-06/PT-08 bundle outcomes/companions on supported targets. Local publication is CLOSED and is not this gate. |
| E-11 | **OPEN — post-publication.** Post-deploy report/cleanup and rollback if applicable; unscored even by acceptance. |
| E-12 | **OPEN — exact smoke receipts.** Nine candidate-bound Python3.11/3.12/3.13 smokes across required OS/architectures. |
| E-13 | **OPEN — exact phase/target companions.** Genuine full collection/v3 registries/runtime evidence per candidate target and release/reference phase. Current engine collection has blank commit; stale shell companions are not upgraded by the new validator. |
| E-14 | **OPEN — reference execution.** Fresh Linux x64/Python3.14 **Core0.3.7** complete hash-mode closure/install reports/metadata/licenses and tamper negatives. Source pins and GOLDEN.lock alone cannot close it. |
| E-15 | **OPEN — release and named-review outcomes.** Constrained provenance for every subject, exact tag/SHA, six post-attestation execution sets and candidate-bound independent review files. |

## Scores and exactly what blocks 100

These are code/doc audit scores, not the generated release acceptance score. Five components per dimension, each /20; deductions are judgments about the demonstrated mechanisms. **100 iff there is no open code/doc finding in that dimension.** The blocker column is exhaustive; aliases are not extra findings. All external rows, receipt staleness/blank candidate bindings, and M1-V31/V34 carry **zero deductions**.

| Dimension | Components (/20) | Score | Exact blockers to 100 |
|---|---|---|---|
| Vertical | Runtime/admission 20; discovery/classification/selection 20; preparation/render/cache 20; approval/publication 20; engine→shell progress 16 | **96/100** | **M6-V01 only:** enabled legacy conversion emits a stage the shell rejects. |
| Oracles | Independent literal expectations 20; composed protocol boundaries 18; normalized version-boundary expectations 16; complete Python universe 20; exact shell execution identities 20 | **94/100** | **M6-V01:** legacy stage subset/projection tests miss producer→decoder incompatibility. **M6-O01:** package tuple oracle falsely admits `2.1` and refuses `2.0`/`2.0rc1`. |
| Docs ↔ code | Engine protocol facts 18; shell behavior/comments 18; gate parity explanation 18; current handoff status 18; recipes/applicability 20 | **92/100** | **M6-V01:** emitted stage contradicts SPEC vocabulary. **M5-D02:** remaining unconditional cwd comments/oracle wording. **M6-O01:** claimed every-spelling gate agreement is false. **M6-D01:** current HANDOFF calls completed local publication pending. |
| Simplicity | Canonical helpers 20; removed dead surfaces 20; bounded lifecycle state 18; one current status account 18; justified retained designs/Core ownership 20 | **96/100** | **M5-S01:** one retained resolver per completed consent job. **M6-D01:** conflicting current local-publication status. |

The complete demonstrated open code/doc set is **M5-S01, M5-D02, M6-V01, M6-O01, M6-D01**. Closing external evidence alone changes none of these code/doc scores; repairing these mechanisms alone supplies none of E-01..E-15's required external outcomes.
