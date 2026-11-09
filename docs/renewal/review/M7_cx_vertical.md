# M7 recursive MECE audit — vertical, oracles, docs ↔ code, simplicity

2026-11-09. Workspace: repository. Baseline: [M6_cx_vertical.md](M6_cx_vertical.md), including its engine repair and corrected slow-tool follow-up dispositions. Authority: current SPEC DRAFT-3.8, SHELL, PACKAGING, TESTPLAN and ACCEPTANCE. User context: main contains merged PR #2, engine 685 passes, shell 310 Jest passes, three-OS CI green, round-6 repairs landed. No git or remote CI lookup was performed.

**Code/doc scores: vertical 94/100; oracles 96/100; docs ↔ code 94/100; simplicity 98/100.** All five mechanisms in M6's final open code/doc set are CLOSED at their original locations/scope. Four NEW findings remain: one conversion-cache defect, two incorrect live documentation inventories and one newly located stale pending-fix sentence. External evidence contributes no deductions. The exhaustive blockers appear in the score table below.

Only this file was written. No code, tests, fixtures, configuration, receipts or other documentation were edited. No git, installation, build, full pytest/Jest run, release action, network request or provider request was performed. Python probes used `python -B -`; TypeScript was transpiled in memory. Cache writes were intercepted into a dictionary; shell probes used existing fake processes/filesystems/clocks and an inert Modal base. These probes are reproducible controls, not acceptance receipts.

## Evidence and execution limits

| Check performed in this audit | Result and boundary |
|---|---|
| Read both accepted engine follow-up receipts | `build/trace/junit-m6-followup-default.xml` and `junit-m6-followup-reversed-final.xml`: each **697 cases, 685 passed, 12 skipped**, zero failures/errors. Each JUnit identity set exactly equals its registry's 697 selected identities; independent collections contain 698 identities. Both collection byte seals and current `tools.trace.suite_digest` match. Both candidate commits are empty. The suite digest binds tests/config, not production source or a release candidate. These are local historical executions, not freshly run installed-target tests. |
| Check inherited engine test identities | Every explicitly named engine test ID in M6 resolves to a current test definition and passing cases in the default follow-up receipt. Additional abbreviated range members used below were checked too. Examples: T-CLS-90 **5**, T-RND-90 **4**, T-GEN-85 **20**, T-META-90 **14**, T-META-97 **10**, T-CNV-94 **4**, T-CNV-92 **3**, T-GEN-96 **23**, T-CLI-87/88/89 **3/3/1** passing parameters. This checks existing execution membership, not a new execution of those cases. |
| Read shell receipt | `build/trace/junit-shell.xml`: **310/310 passed**, including **15 M6-labelled cases**, zero failures/errors/skips. Older `junit-shell-local.xml` contains 296 cases and no M6 cases; it is not used as current shell evidence. Three-target candidate-bound shell companions remain external. |
| Current TypeScript compiler API | Absolute `shell/tsconfig.json`, parsed with `getParsedCommandLineOfConfigFile`; `createProgram`/`getPreEmitDiagnostics`, no emit: **75 root files, zero diagnostics**. The earlier M6 prose's 76-file count is a historical receipt, not a present requirement. |
| Actual read-only trace helpers | Current unknown/uncovered/untagged/registration/matrix errors **0/0/0/0/0**. Used Python registrations for `registration_problems`/`matrix_problems`, combined Python/Jest registrations for requirement coverage, and the CLI's separate Jest planned-requirement checks. An initial harness incorrectly passed Jest rows to the Python-only validator; the corrected invocation passes and the harness error is not a finding. `trace.py check/report/score` were not invoked because they write artifacts. |
| Original matrix assertions, called directly | T-META-05/06 **PASS** (`engine/tests/test_meta.py:58`, `:83`): no covered/N/A overlap; **59** expanded class/stage N/A declarations equal the header. The M6 horizontal file's four original INVALID claims remain adjudicated negative/non-reach assertions, not reopened holes. |
| Golden and FX-71 integrity | Actual `tools.golden.verify` succeeds with producer **Core 0.3.7**; actual `tools.record_protocol.verify` reports **53 files verified**, including derived transformations. Neither establishes independent human authorship, a new all-stream recording or fresh reference installation. |
| Package/documentation assertions, called directly | All **23 T-GEN-96** parameters PASS, including the five M6 numeric-arity controls; T-META-91/92/95 and **PT-07** PASS. PT-07 independently establishes **six required plus four experimental** workflow cells from repository YAML, not their execution outcomes. |
| Shell composed protocol controls, executed read-only | Existing `build/trace/m6-composed-consumer.cjs` feeds its stored ordinary/legacy-success/handled-failure controls through current framer and `EngineRun`: **17/20/16 frames**, zero invalid frames and no `shell.PROTOCOL`. Handled failure retains only `engine.E_PRECONVERT`; the original `preconvert` stage remains an invalid negative. These stored controls are not newly produced engine streams; current producer source and T-CNV-92/94's closed-vocabulary assertions provide the producer evidence. |
| Actual shell version gate | `2.0`, `2.0rc1`, `2.0.0`, `2.0.0rc1` enabled; `2.1` blocked. Separate space/tab/LF/CR/CRLF/U+2028/U+2029 suffix controls rejected by both actual gates. No reproduced range/syntax disagreement. |
| Actual coordinator lifecycle | Three completed jobs per mode: **approve 0/0/0**, **dismiss 0/0/0**, **rejected consent promise 0/0/0** retained waiters. Approve produces three Plan→Run pairs; dismiss/reject produce Plan only. A pending consent has one waiter; Cancel leaves zero and launches no Run. Exceptions still propagate; no new error-handling claim is inferred. |
| Adjacent shell controls | Actual timeout→backoff→successful version retry: exactly two requests, enabled. Actual nested-venv cwd returns `C:\Users\alice\Vault\venv`. Bootstrap path-with-spaces and POSIX apostrophe literals pass. |
| NEW format-sensitive cache control | Real installed Core **0.3.7**, real `sniff_pure` and `convert_source`/cache loader/store; only cache filesystem reads/writes replaced by dictionary storage. Identical `.txt`/`.csv` bytes yield different cold Markdown but the same cache key. Both processing orders incorrectly reuse the first format's body; details in M7-V01. No real cache files were created. |

The corrected final T-CLI-87 evidence takes precedence over the invalid earlier slow-tool claim. `test_m6_engine.py:39` isolates PATH and both overrides; `:58` requires exact override sources; `:61` checks actual launch markers. The accepted default/reversed receipts contain all three passing cases. `build/trace/m6-followup-summary.json` records the 202-case step7 reversal; this audit checked both accepted identity sets/seals and did not rerun the full suites or independently re-execute that ordering.

## Every M6 primary finding and repair disposition

Verdicts close the demonstrated mechanism only. Historical statements remain historical. Aliases are not additional findings or deductions.

| M6 finding / inherited residual | M7 verdict | Current evidence |
|---|---|---|
| **M5-S01 / cross-audit M6-04**, completed consent cancellation subscriptions | **CLOSED** | `shell/src/ui/coordinator.ts:258` returns a removable waiter; `:334` releases it in `finally` around the consent race. JT-15 normal approve/dismiss and JT-16 active Cancel at `shell/test/jt-m6-shell-round6.test.ts:275`, `:292`. Direct current coordinator controls above also exercise rejected promises: all finished jobs retain zero waiters. |
| **M5-D02 / D-03 / N-02 cwd residual / cross-audit M6-07**, unconditional outside-vault comments/oracle wording | **CLOSED** | `shell/src/process/launcher.ts:43` explicitly permits a venv inside the vault; utility comment `:171`, coordinator `:110`, and main `:240` agree. JT-12 source-wording oracle at `shell/test/jt-m6-shell-round6.test.ts:308`; JT-12 invocation tests retain isolated prefix/actual venv-root assertions. `docs/renewal/20_SHELL.md:76` and HANDOFF `:19` match the actual nested helper result. No unconditional containment promise remains in the cited surfaces. |
| **M6-V01**, legacy preparation emits unknown `preconvert` progress stage | **CLOSED** | Current producer uses `self.stage(logical, 'convert', ...)` at `engine/src/mdflow/orchestrate.py:235`. T-CNV-94 at `engine/tests/stage_io/step7/test_r33_engine.py:151` now requires the **entire** emitted stage set to be inside SPEC 7.3, across four legacy filters. T-CNV-92 `:208` does so for all three handled failures and surviving sibling. Current decoder/EngineRun controls accept `convert`, reject `preconvert`, and preserve the real conversion diagnostic. |
| **M6-O01 / M3-V04 / M2-V03 / P-02 numeric-arity residual**, package tuple boundary disagreement | **CLOSED** | `engine/tests/packaging/_support.py:352` takes the first three components and zero-pads. `test_pt_release.py:318` compares normalized engine bounds; actual T-GEN-96 `test_m4_docs.py:40` passes all 23 cases, including short releases, upper boundaries and extra components. Both actual gates give the intended five M6 results. The original malformed-suffix repair remains closed too. |
| **M6-D01 / S-13 current status residual**, HANDOFF calls completed local publication pending | **CLOSED** | `docs/renewal/HANDOFF.md:9` now lists reference/CI/desktop/provenance/named-review obligations, excludes publication; `:13` explicitly closes M6-D01 while retaining packaged execution E-10. Actual 53-file publication integrity passes. Historical M4 producer/version statements are not current pending-work claims. |
| **M6 engine disposition: cross-audit M6-01**, optional version-probe execution exceeds shell budget | **CLOSED in code/local oracle scope** | exiftool `engine/src/mdflow/exiftool.py:27`, `:42`; LibreOffice `engine/src/mdflow/cli.py:231`: each execution deadline **0.5 s**. Bounded per-environment caches at exiftool `:53`, CLI `:215`; diagnostic exception boundary CLI `:240`. T-CLI-87/88/89 at `test_m6_engine.py:24`, `:67`, `:102` retain real slow-tool, deadline/cache and injected-exception checks. SPEC `10_SPEC.md:595` scopes the 3-second healthy-machine target and native/OS limits. Real-host measurement remains external, with no deduction. |
| **M6 follow-up oracle defect**, containment stripped fake-tool overrides; old timing claim could pass without launching selected fake tools | **CLOSED** | Corrected test restores explicit child environment before imports/temp bridge, isolates PATH, requires both sources and exact launch markers (`test_m6_engine.py:39`, `:49`, `:58`, `:61`). Autouse cache reset at `:11`. Only final default/reversed receipts above are accepted for this claim. The invalid earlier timing evidence is not reused. |

For completeness, the adjacent shell M6-01..08 mechanisms referenced by M6's dispositions were inspected as well: retry/nonreuse in `shell/src/process/version-gate.ts:342` and `shell/src/main.ts:256`; executable-path/POSIX quoting in `shell/src/process/setup.ts:88`, `:103`; cancellation release above; settled LibreOffice/hybrid-recording prose in `20_SHELL.md:220`, `:255` and `90_ACCEPTANCE.md:67`; HANDOFF's round-6 shell section; corrected cwd/flag/module comments; external-program/metadata disclosures in `README.md:63` and `25_PACKAGING.md:125`. **All CLOSED within their original code/text scope**; JT-10/12/15/16/17 M6 regressions are in the 310-case shell receipt. The separately located pending-code sentence in the hybrid-recording paragraph is M7-D03. Named disclosure/meaning reviews and real-host timing are separate external evidence.

## Recursive inherited ledger from M6

Every inherited row in M6 is carried below. Test IDs identify current executable assertions; their engine execution membership was checked as described above. File/line references anchor the especially relevant implementations and regressions; IDs sharing an original mechanism share its disposition. CLOSED does not mean every possible adjacent defect has been ruled out: M7-V01 is a newly demonstrated cache-input omission, not a reason to discard the original base-cache design repair.

### M5 and M3/M4 handoffs

| Carried ID(s) | Verdict | Evidence and scope |
|---|---|---|
| M5-V01 | **CLOSED** | Actual full-syntax gates; JT-17 valid/malformed suffix controls; T-GEN-96's 23 parameters. M6-O01's separate numeric-arity residual is now closed above. |
| M5-O01 | **CLOSED** | `tools/trace.py:423` requires current candidate/source-bound independent collection; `:464` matches exact unique JUnit identities; `:495` checks all expanded shell cases. T-META-97 ten adversarial parameters and T-META-98 quoted/platform controls (`engine/tests/unit/test_m5_trace.py:34`, `:10`) pass in accepted receipt. Actual CI collection still precedes Jest at `.github/workflows/ci.yml:128`. No exact-receipt outcome is inferred from these validators. |
| M5-D01 | **CLOSED for its two clauses** | Both synchronization dispositions state completion at `20_SHELL.md:193`, `:196`; genuine OS/execution obligations remain explicit. Newly located current pending-fix prose at `:255` is M7-D03. |
| M5-S01; M5-D02 | **CLOSED** | Current release-in-finally and limited cwd contract, verified in the primary table. |
| M3-V01 / M1-V22 | **CLOSED** | T-CLS-90 five malformed V1 payload cases; string-before-enum check at `engine/src/mdflow/classify.py:131`. |
| M3-V02 / M1-V26 | **CLOSED** | T-RND-90 four DPI/rotation boundary cases; ceil-scaled preallocation bound at `engine/src/mdflow/render.py:87`. |
| M3-V03 / X-01 / P-01 | **CLOSED** | Incremental/reset presenter `shell/src/ui/progress.ts:50`; JT-09/16 literal Run-only counts/no retained presenter history; T-RPT-91 (`test_m4_engine.py:44`) independent invocation counters. Stage-vocabulary repair is separately closed. |
| M3-V04 / M2-V03 / P-02 | **CLOSED** | Original full syntax plus repaired normalized range comparison; T-GEN-96 and current shell/package probes above. |
| M3-V05 / M4-O01 | **CLOSED in oracle code** | `tools/trace.py:423`, `:483`: independent full collection plus exact parameter execution; T-META-90 fourteen mutations, T-META-96 restricted-inventory negative (`test_m3_trace.py:13`, `test_m4_trace.py:11`). Current accepted inventories preserve all 20 T-GEN-85 parameters. External phase/target execution remains E-13. |
| M3-H01; 30 disputed horizontal cells; M3 S4:K14 | **CLOSED as scoped execution registrations** | T-GEN-85 twenty-class sweep (`engine/tests/stage_io/test_class_sweep.py:252`), T-ASM-90/91 and T-TRI-90 effects; direct T-META-05/06 and current zero matrix errors. Negative/non-reach coverage remains valid; registration alone is not universal semantic proof. |
| M3-O01 | **CLOSED** | T-ASM-90/91 and T-TRI-90 (`test_m3_engine.py:89`, `:117`, `:134`): independent placement IDs/reasons, uninspected anchor and corrupt-member/sibling continuation. |
| M3-D01 / D-01 / N-12 | **CLOSED** | Settled sync clauses, current 59-cell N/A count, corrected HANDOFF summary; current literal checks above. |
| M4-V01 | **CLOSED** | Coordinator interrupt checks after awaited admission work (`coordinator.ts:156`, `:171`, `:177`, `:196`); JT-16 deferred gate Cancel/dispose/control at `jt-16-cancel-ui.test.ts:261`, `:286`, `:304`. Synchronous reservation retained. |
| M4-V02 | **CLOSED** | Bounded V3 numeric spelling at `classify.py:164`; T-CLS-91 four PDF/GIF cases (`test_m4_engine.py:15`), zero provider work and surviving sibling. |
| M4-V03 / N-07 / P-06 | **CLOSED for demonstrated aliases/userinfo** | Raw-authority check `shell/src/pure/settings.ts:181`; JT-04 alias/userinfo negatives at `jt-04-migration-map.test.ts:222`. No universal URL-parser equivalence claim. |
| X-11 / P-03 | **CLOSED for local publication** | Actual 53-file verifier, supported producer and default gate; JT-17 at `jt-17-version-gate.test.ts:39`, T-GEN-97 recorder argv. Packaged candidate replay stays E-10. |
| N-02 / D-02 | **CLOSED** | Isolated prefix `launcher.ts:31`, limited cwd comments, direct T-META-95 and JT-11/12 actual invocation assertions. |
| N-04 | **CLOSED within implementation/disclosure scope** | `engine/src/mdflow/runtime_temp.py` owned leases/recovery, README Windows caveat; T-GEN-93/94/95 (`engine/tests/unit/test_m4_temp.py:11`, `:29`, `:70`) real native-death/live/unowned/link controls. E-03/E-09 still separate. |

### Every carried M1 vertical item

| M1 ID | Verdict | Retained current evidence |
|---|---|---|
| V01 | **CLOSED** | T-META-50, T-TRX-57, T-WRT-51 and T-RPT-52..56: applicable stages, durable effects and report accounting (`test_m1_engine.py:583`, `:740`; `test_orchestrate.py:265`). |
| V02 | **CLOSED** | T-SNF-50, T-GEN-53, T-CNV-52/53, T-TRX-54, T-RPT-51 and T-RND-80: stage IO/interruption and sibling effects. |
| V03 | **CLOSED for original validation gaps** | T-CLS-50, T-LKP-50, T-ASM-50, T-TRX-53/54/56 validate real consumers. New format-dependent base-cache omission is M7-V01, not a previously repaired ledger-validation case. |
| V04 | **CLOSED** | T-RND-81/82 and T-GEN-85[K09]: extracted HWP payload/stored-stream policy in both candidate orders. |
| V05 | **CLOSED** | T-META-81 and direct T-META-05/06: explicit applicability and no covered/N/A overlap. |
| V06 | **CLOSED** | T-SNF-50/53: selected roots, exclusions, links and deduplication (`test_m1_engine.py:42`, `:842`). |
| V07 | **CLOSED** | T-SNF-51/54 and `_source_bytes` at `engine/src/mdflow/orchestrate.py:73`: bounded length/hash recheck before consumption. |
| V08 | **CLOSED** | T-CNV-50, T-RND-50 and T-CTR-50/51: source, media and nested-expansion bounds. |
| V09 | **CLOSED** | T-WRT-50 (`test_m1_engine.py:131`): containment before reading skipped/existing output. |
| V10 | **CLOSED** | T-WRT-51 (`:172`): missing media restored without replacing preserved Markdown. |
| V11 | **CLOSED** | T-LKP-50/T-ASM-50 (`:191`, `:755`): invalid ledger timestamp/provenance cannot supply hit/transcript. |
| V12 | **CLOSED** | T-RPT-50 (`:211`): bounded nested progress fields preserve identity/counts. |
| V13 | **CLOSED** | T-RPT-51 (`:226`): report-copy failure agrees with terminal exit/event. |
| V14 | **CLOSED within amended scope** | T-TRX-50/80: bounded capture, timeout and inherited-pipe/no-reader handling. No universal descendant-tree guarantee inferred. |
| V15 | **CLOSED within amended scope** | T-TRX-51 (`:270`): drip-body deadline; documented native/DNS/TLS limitations retained. |
| V16 | **CLOSED** | T-CLI-50/T-PLN-50 (`:293`, `:304`): exact provider/option scope and none-provider cost. |
| V17 | **CLOSED** | T-TRX-52 (`:311`): error vocabulary/redaction before storage and sibling continuation. |
| V18 | **CLOSED** | T-SEC-50 (`:333`): proxy userinfo excluded from Plan metadata. |
| V19 | **CLOSED** | T-RND-81, both equal-payload orders: stored-stream policy survives deduplication. |
| V20 | **CLOSED** | T-SEL-50/T-CNV-54 (`:362`, `:867`): full digest identity and shortened-name collision refusal. |
| V21 | **CLOSED** | T-SNF-52 (`:375`): literal encryption flag and malformed HWP header. |
| V22 | **CLOSED** | T-CLS-80/90, T-SEL-51 and T-CLS-91: V1/V3 malformed inputs safe; convert_only schedules no OCR. |
| V23 | **CLOSED** | T-PLN-51/T-PLN-02: approved snapshot/options/unit bound and actual production Plan hash. |
| V24 | **CLOSED** | T-TRX-53/T-TRX-08 (`test_m1_engine.py:424`, `test_class_closure.py:347`): changed raster refused before send. |
| V25 | **CLOSED** | T-RND-52 (`test_m1_engine.py:444`): prior encoded payload released before next render. No native working-set certification claimed. |
| V26 | **CLOSED** | T-RND-53/90: predecode pixel cap and conservative fractional allocation. |
| V27 | **CLOSED** | T-RND-54 (`:498`): actual animated first-frame pixels. |
| V28 | **CLOSED** | T-WRT-52 (`:515`): output collision/reserved-name handling. |
| V29 | **CLOSED** | T-LKP-51 (`:529`): output/sibling survive ledger-write failure. |
| V30 | **CLOSED** | T-PLN-02 (`engine/tests/unit/test_core_select_plan.py:102`), T-META-80 and T-PLN-52 use production Plan/hash. |
| V31 | **OPEN — external only; zero deduction** | E-01/E-05/E-12/E-13 in `90_ACCEPTANCE.md:81`, `:85`, `:92`, `:93`; reported green CI recorded, exact candidate/target evidence not independently established here. |
| V32 | **CLOSED as oracle repair** | T-GEN-52 (`engine/tests/packaging/test_pt_release.py:216`): actual small-wheel hash/transitive tamper control; fresh reference install remains E-14. |
| V33 | **CLOSED** | T-CLS-07's 14 literal issue-policy cases (`engine/tests/unit/test_core_classify.py:192`) and T-RND-83's classification→refused-preparation/placement assertion. |
| V34 | **OPEN — external only; zero deduction** | E-06/E-08/E-09/E-14/E-15, ACCEPTANCE §7: release/provenance, named reviews, real app and fresh reference receipts. |
| V35 | **CLOSED as design disposition** | Reference versus compatibility targets/common subjects in `25_PACKAGING.md:9`, `:51` and `tools/build_engine.py`; execution/provenance stays external. |
| V36 | **CLOSED** | T-LKP-80/T-SNF-80: canonical atomic-write/hash/format decisions. |
| V37 | **CLOSED for original simplicity concern** | T-CNV-04/51 retains useful base-cache reuse; T-TRX-55 counts attempts explicitly. M7-V01 requires correct cache identity, not deletion of the cache. |
| V38 | **CLOSED** | T-CLS-53/T-TRI-50 and protected/corrupt sweeps: report-only inputs create no executable work/Markdown. |

Unqualified `:line` references in this M1 table refer to `engine/tests/stage_io/step7/test_m1_engine.py`; test IDs are also explicit where another file applies.

### Every carried M2 and Fable P/D/N/X item

| ID(s) | Verdict | Current evidence / preserved scope |
|---|---|---|
| M2-V01 | **CLOSED** | T-TRX-80 (`test_m2_engine.py:21`): timeout/no-reader and single polling owner. |
| M2-V02 | **CLOSED** | T-GEN-80 (`engine/tests/packaging/test_m2_packaging.py:13`): installed-prefix positive, source/outside-prefix negatives. |
| M2-V03 | **CLOSED** | Syntax and numeric-arity repairs above; actual gate controls/T-GEN-96. |
| M2-V04 | **CLOSED for original DAG/isolation defect** | T-GEN-82/83 (`test_m2_packaging.py:36`, `:57`); attest→verify→score DAG/installed fixtures. Full parameter-universe repair remains closed separately. |
| M2-V05 | **CLOSED** | T-RND-80 (`test_m2_engine.py:40`): setup failure becomes per-unit pending; sibling succeeds. |
| M2-V06 | **CLOSED** | T-RND-81 (`:62`): policy survives both equal-payload orders. |
| P-01 | **CLOSED** | M3-V03; JT-09/16 literal presenter reset and UI expectations. |
| P-02 | **CLOSED** | Full syntax plus normalized numeric range; T-GEN-96/JT-17/current two-gate controls. |
| P-03 | **CLOSED** | Actual FX-71 53-file publication verifier and default gate admission. |
| P-04 | **CLOSED** | Absolute interpreter validation `shell/src/pure/settings.ts`; coordinator pre-gate refusal at `:168`; JT-04/JT-09 relative-input negatives. |
| P-05 | **CLOSED** | `shell/src/ui/settings-tab.ts:72`, whole-plugin JT-04 (`jt-02-plugin-round2.test.ts:183`): notice and persisted-value restoration on rejection. |
| P-06 | **CLOSED** | M4-V03/JT-04 raw-authority alias and userinfo controls. |
| D-01 / N-12 | **CLOSED** | `20_SHELL.md:193`, `:196` settled synchronization; corrected HANDOFF publication summary. |
| D-02 | **CLOSED** | Direct T-META-95; isolated BOOTSTRAP/PACKAGING recipes and actual launcher prefix. |
| D-03 | **CLOSED** | M5-D02 closure above: normative prose, production comments, test wording and nested-venv helper agree. Historical counts are not current claims. |
| D-04 / ag covered-cell declarations | **CLOSED** | Current 59-cell N/A expansion, direct T-META-05/06, zero covered/N/A overlap. |
| N-01 | **CLOSED** | Coordinator `:145` synchronous reservation across awaits; JT-09 deferred-gate overlapping submissions. |
| N-02 | **CLOSED** | Fixed isolated argv everywhere; limited cwd contract now consistent; JT-11/12/M6 source-wording test. |
| N-03 | **CLOSED** | Coordinator `:319` preserves actual Plan diagnostics; adds PROTOCOL only if none. JT-15 startup E_USAGE versus truncated-Plan controls. |
| N-04 | **CLOSED in implementation/disclosure scope** | T-GEN-93/94/95 and Windows caveat; external app/OS rehearsal stays E-03/E-09. |
| N-05 | **CLOSED in implementation** | `shell/src/process/dom-picker.ts:43` empty outcome; JT-08/JT-02 notice and zero submission. |
| N-06 | **CLOSED for absent activation** | Picker activation check `dom-picker.ts:72` and Node activation source; JT-08 blocked path never clicks input. |
| N-07 | **CLOSED** | M4-V03/P-06 raw Base URL authority validation. |
| N-08 | **CLOSED by disclosure** | JT-04 plus enabled-drop trade-off disclosure; default remains off (`shell/src/pure/settings.ts:133`). |
| N-09 | **CLOSED by disclosure** | Context-menu/drop/locale reload notes at `settings-tab.ts:158`; whole-plugin JT-04. |
| N-10 | **CLOSED** | Directory spool ranged-read implementation `shell/src/process/spool-fs.ts:28`, Node `readRange`; JT-13 exact windows/EOF/removal and zero whole-file reads. No total-JSON-memory guarantee inferred. |
| N-11 | **CLOSED** | Whole-plugin JT-02 creates the log folder before opening; Node mkdir implementation retained. |
| X-01 | **CLOSED** | Incremental/reset presenter, JT-09/16; completed consent subscription lifetime is now closed too. |
| X-02 | **CLOSED** | JT-12 configured Base URL wins over host value in actual spawn environment. |
| X-03 | **CLOSED** | JT-03/05: failed reads/newer schema keep persistence read-only. |
| X-04 | **CLOSED** | JT-10 probes committed interpreter changes, not partial typing. |
| X-05 | **CLOSED in implementation** | JT-08/02 picker and Node file resolver; real Electron/app result remains E-09. |
| X-06 | **CLOSED** | JT-08 local-file drop confirmation defaults to Cancel. |
| X-07 | **CLOSED in text** | README outside-vault/network/cost/migration disclosures plus JT-04/M6 disclosure regression; MAN-02 remains E-09. |
| X-08 | **CLOSED** | JT-14/15: egress AND requests-to-send predicate (`coordinator.ts:86`). |
| X-09 | **CLOSED** | JT-13 run-level `file:null` framing. |
| X-10 | **CLOSED** | JT-09/15 destination revalidation before replay; coordinator `:354`, `:365`, `:390`. |
| X-11 | **CLOSED for local publication** | Actual verified 53-file FX-71 corpus/default gate; E-10 remains actual packaged execution. |
| X-12 | **CLOSED** | Whole-plugin JT-02 compatibility selftest routing notice. |
| X-13 | **CLOSED** | Whole-plugin JT-04 editable run options with SPEC validation. |
| X-14 | **CLOSED** | T-CLI-80/T-GEN-87 (`engine/tests/stage_io/step7/test_fable_handoff.py:10`, `engine/tests/packaging/test_fable_handoff.py:12`): absent-Core version/packaged gate without crash. |
| X-15 | **CLOSED** | JT-02 background load probe; JT-16/M4-V01 revokes pending admission on disposal. |
| X-16 | **CLOSED for original references/residuals** | Corrected cwd surfaces and HANDOFF summary above. Newly located live summary/status errors are explicitly M7-D01/D02/D03; no blanket documentation-current claim. |
| X-17 | **CLOSED** | JT-01/source inventory: no `@electron/remote` import/build external. |
| X-18 | **CLOSED** | JT-07 first-path-plus-count history; `coordinator.ts:91`, `:293`. |
| X-20 | **CLOSED** | README cache/transcription/log synchronization disclosure; JT-04. M6 carries no X-19. |

### Every carried simplicity item

| Fable ID | Verdict | Current evidence |
|---|---|---|
| S-01 | **CLOSED** | `shell/src/pure/argv.ts` absent; real launcher used by JT-04/11/12. |
| S-02 | **CLOSED** | `pure/errors.ts` absent; actual vocabulary in `pure/codes.ts`, JT-SHL-19-01. |
| S-03 | **CLOSED** | No production `index.ts` barrel in pure/process/ui; source inventory/JT-01 import checks and direct import at `shell/src/ui/output-path.ts:6`. |
| S-04 | **CLOSED** | `Authorization` at `launcher.ts:83` exposes only yes-file form; JT-15 batch replay. |
| S-05 | **CLOSED** | Protocol oracle helper remains under `shell/test/fixtures/protocol.ts`; launcher owns production argv. |
| S-06 | **CLOSED** | No production `outputsCreated`; JT-07/13 derive outcome from process/report. |
| S-07 | **CLOSED** | No production `pure/trace.ts`; `tools/trace.py:423` checks real receipts, supported by T-META-90/96/97. |
| S-08 | **CLOSED** | `collectSetupDiagnostics` calls `environmentDiagnostics` at `setup.ts:204`; JT-10. |
| S-09 | **CLOSED** | Canonical `pure/paths.ts` used directly, including `ui/output-path.ts:6`. |
| S-10 | **CLOSED** | No production test-convenience `this.load()`; whole-plugin JT-02 uses lifecycle. |
| S-11 | **CLOSED** | Coordinator job logging and EngineRun progress subscription remain wired (`coordinator.ts:278`, `:307`). |
| S-12 | **CLOSED** | `.gitignore:1` scopes current generated/dependency/cache/local output; retired v1 generated-script block absent. Read as a file only. |
| S-13 | **CLOSED for original locations** | Original stale counts/pending-X14 claims absent; M6-D01's publication residual also corrected (`HANDOFF.md:9`). The newly located conflicting pending-fix sentence is M7-D03. |
| S-14 | **CLOSED** | T-GEN-84 (`test_m2_packaging.py:66`): canonical provider DEFAULT_META/describe. |
| S-15 | **CLOSED** | T-GEN-84/T-RPT-51: report publisher owns stdout; CLI owns durable-copy/error ordering. |
| S-16 | **CLOSED** | No remote Electron import/external in production/esbuild; JT-01. |
| S-17 | **CLOSED** | No production `approvableHashes`; used `renderYesFile` at `launcher.ts:184`, JT-15. |
| S-18 | **CLOSED** | `pure/spool.ts:45`, `:77` retains used `finishWith`/`discard`; no redundant exported finish. |
| S-19 | **CLOSED** | `CoordinatorDeps` has no unused locale dependency (`coordinator.ts:44`); current compiler has zero diagnostics. |
| S-20 | **CLOSED** | No production `legacyFilePath`; JT-08 exercises supplied Node resolver. |
| S-21 | **CLOSED** | `ui/output-path.ts:6` imports pure helpers directly; no re-export shim. |

## NEW findings

### M7-V01 — MAJOR, base-cache identity omits the format that determines conversion

**Trigger:** two ordinary inputs contain the same bytes but have different text/tabular formats, for example `sample.txt` and `sample.csv` containing:

```text
Name,Amount
Alice,42
Bob,17
```

`sniff_pure.detect_format` legitimately uses the extension for these no-magic formats (`engine/src/mdflow/sniff_pure.py:95`, `:109`). The source SHA-256 is identical: `08f6e005ea37fe226ea2c395e73112444684a1aee001a3fa720327bde74cabdb`. Current Core 0.3.7 returns the plain text for `.txt` and a Markdown table for `.csv`.

`convert_source` computes `ext = _hint(fmt)` at `engine/src/mdflow/convert.py:266`, but loads by source hash and optional exiftool variant alone at `:271`. `_cache_paths` at `:203` includes the Core version and no format. A hit returns before format-dependent conversion. `_load_cache` at `:210` neither receives nor validates the format. Store at `:298` uses the same incomplete identity.

The read-only control used actual Core conversion and actual loader/store functions, intercepting cache `Path.read_text` and `write.atomic_write` into a dictionary. No conversion-result stub was used. Both controls completed with empty issues:

| Sequence with one shared cache | Required result | Actual result / Core calls |
|---|---|---|
| Cold CSV, no cache | Markdown table | Table; `.csv` called. Establishes an independent expected result. |
| TXT fills cache, then CSV | TXT plain text; CSV table | CSV returns TXT's plain text; no second-format Core call. |
| Fresh cache: CSV fills cache, then TXT | CSV table; TXT plain text | TXT returns CSV's table; no second-format Core call. |

The `.csv` body should be `| Name | Amount |\n| --- | --- |\n| Alice | 42 |\n| Bob | 17 |`; after TXT primes the cache it is `Name,Amount\nAlice,42\nBob,17\n`. Reversing the order reverses the corruption. This is deterministic reuse of the wrong conversion result, not a hash collision, rename prohibition, provider defect or missing CI receipt. The returned wrong base body proceeds to Assemble/Write (`orchestrate.py:420`, `:422`); a non-force rerun can preserve that incorrect output under normal existing-output rules.

**Oracle gap:** T-CNV-04 (`engine/tests/stage_io/test_convert_io.py:146`) compares same-format PDF/DOCX reruns; T-CNV-51 (`test_m1_engine.py:631`) checks a same-name TXT rerun with a Core spy. Neither checks identical bytes under different admitted format hints against independent cold outputs. All pass while this counterexample fails. Original M1-V37's decision to retain a useful cache remains sound.

**Small closure:** bind the base cache to the effective conversion format/hint, preserve Core/exiftool dimensions, and reject legacy cache entries lacking the newly required format identity. Update REQ-CNV-04's documented cache identity (`10_SPEC.md:99`) accordingly. Add both-order TXT/CSV controls with literal cold expectations plus same-format reuse controls. Retain the cache and existing canonical helpers; no second conversion pipeline or generalized caching framework is needed.

Scored in **vertical** and **oracles**. The existing SPEC cache-key recipe agrees with current code but is insufficiently discriminating; it is included in this mechanism's repair, not counted again as an independent docs-agreement finding.

### M7-D01 — MINOR, current conformance row specifies an obsolete exact version-field inventory

`docs/renewal/10_SPEC.md:757`, the live CLI 10.1–10.3 conformance row, says version keys are **exactly eight gate keys plus the three exiftool keys** and cites T-CLI-81. That is eleven keys. Current §10.1 at `:587`, `:591` requires the eight gate keys **plus six tool keys**, including `libreoffice`, `libreoffice_status`, `libreoffice_source`.

The actual producer adds all six at `engine/src/mdflow/cli.py:240`, `:303`; T-CLI-02 independently expects all fourteen (`engine/tests/stage_io/step7/test_cli.py:55`), as does PT-06 (`engine/tests/packaging/test_pt_release.py:343`). The verified FX-71 `version.json` also contains fourteen. An implementation satisfying the old row's exact-key assertion would fail the current contract.

**Small closure:** update that one live conformance row to all fourteen fields and cite the current complete-response assertion. The historical R31 change log is not a finding. No engine behavior or external receipt is needed to close this prose defect. Scored only in **docs ↔ code**.

### M7-D02 — MINOR, acceptance G-14's expected matrix cardinality disagrees with the implemented policy

`docs/renewal/90_ACCEPTANCE.md:30` still specifies **six required plus three allowed-failure cells** for G-14. Current REQ-PKG-07 (`25_PACKAGING.md:51`) explicitly requires **six required plus four experimental cells**: three Python 3.15 cells and one macOS Intel/Python 3.12 experiment.

The actual workflow has the three-by-three matrix and an Intel include (`.github/workflows/ci.yml:60`, `:61`, `:64`); `continue-on-error` at `:56` includes both experimental conditions. PT-07 (`engine/tests/packaging/test_pt_ci.py:65`, `:68`) asserts exactly six/four; its direct read-only invocation passes. ACCEPTANCE §7's runner-policy paragraph already recognizes the Intel experiment. This is a conflicting current expected-result cell, not a claim that CI did not run or a reason to penalize external-evidence completion.

**Small closure:** change G-14's expected cardinality to six required/four experimental, retaining required-arm64 and allowed-failure exclusions. No new runner, CI execution or release action is needed. Scored only in **docs ↔ code**.

### M7-D03 — MINOR, live Open paragraph still requests completed syntax and waiter repairs

The unqualified final `Open:` paragraph at `docs/renewal/20_SHELL.md:255` says M5_cx_vertical tracks shell version syntax and consent waiters and that **“those require code fixes.”** Both mechanisms are repaired: the same document's M5 syntax disposition at `:218` states full syntax validation is done, and its M6 disposition at `:221` states the consent race releases its waiter. Current full-syntax gate controls and actual coordinator lifecycle probes above independently confirm both closures.

This is distinct from the two already-corrected pending-sync rows (M5-D01) and HANDOFF's corrected publication sentence (M6-D01). The newly located sentence is current operational prose, not a dated pre-fix audit. Its surrounding real-OS/manual evidence remains valid and should remain open.

**Small closure:** replace only the sentence's pending-code-fix claim with the completed dispositions and keep actual OS/manual receipts separate. No code fix, extra status document or external evidence can be required to correct it. Scored in **docs ↔ code** and **simplicity**, consistently with M6's deduction for conflicting current status accounts.

## Vertical boundary and simplicity assessment

| Boundary family | Code/doc facts checked | Open mechanism |
|---|---|---|
| S0 startup/runtime/admission | Core conflict delegation, isolated absolute interpreter, complete version gate, bounded optional version executions, retry/transient nonreuse and post-await admission interruption; T-CLI-83/86/87..89, JT-12/16/17. | No demonstrated runtime/admission defect. M7-D01/D02 are incorrect inventory text; M7-D03 incorrectly calls completed code repairs pending. |
| S1–S4 discovery/triage/classify/select | Immutable bounded source snapshot; total V1/V3 validation; actual placement/member oracles; full candidate identities; R33 T/NONE literal expectations and twenty-class sweep. | No additional demonstrated defect in these stages. |
| S5–S7 conversion/render/cache | Core-owned legacy conversion; corrected closed progress vocabulary; bounded render/ledger validation. Independently exercised different Sniff hints with identical bytes. | **M7-V01**: first-format base cache contaminates another admitted format. |
| S8–S10 Plan/approval/transcribe | Exact approved snapshot/raster identity; egress-and-remaining-work predicate; one yes-file replay; removable consent waiter. Approve/dismiss/reject/Cancel lifecycle controls. | No additional demonstrated authorization/lifetime defect. |
| S11–S13 assemble/write/report/UI | Independent placement IDs/reasons, missing-media restoration, report-copy terminal agreement and Run-only progress counts; derived result projection retained. | M7-V01's wrong base body reaches downstream consumers; same finding, no second deduction. |

Simplicity's only open finding is **M7-D03**, a conflicting current status sentence. Retain canonical path/hash/atomic-write helpers, test-local replay helpers, incremental presenter state, useful base caching and Core-owned LibreOffice containment. The previously retained consent resolver is now released on normal and exceptional completion. No new duplicate launcher, private process-tree manager, scoring system or status account is justified. The cache repair needs one complete input identity and focused assertions; documentation needs two inventory-row edits and one status-sentence edit.

## External evidence ledger — no code/doc deductions

Authority: [90_ACCEPTANCE §7](../90_ACCEPTANCE.md#7-external-evidence-pending). **OPEN here means exact required evidence was not independently established by this local audit**, not that the user's reported green CI failed. PR #2 merged and three-OS CI green are recorded as user-provided completed context. These items cannot be closed by source edits or synthetic PASS files, and they block none of the code/doc 100s.

| ID | Separate status and required evidence |
|---|---|
| E-01 | **Reported CI green; OPEN exact-receipt verification.** Six required installed engine targets, actual candidate SHA and JUnit/registry/collection/runtime companions. |
| E-02 | **Reported three-OS CI green; OPEN exact-receipt verification.** Three current candidate-bound shell install/typecheck/build/Jest evidence sets. Local 310-pass XML is scoped local evidence. |
| E-03 | **OPEN — real OS/process evidence.** Cooperative/forced stop, actual Windows native status and no owned live process; fake-process probes do not replace it. |
| E-04 | **OPEN — exact endpoint receipts.** Actual contract-min Core0.3.7 and newest-compatible contract-max/schema-negative runs on the required target. |
| E-05 | **OPEN — public artifacts/fresh installs.** Six wheel installs, pip check/version/selftest and terminal-launch sentinels; reference hash-mode install. |
| E-06 | **OPEN — release/provenance.** Actual 2.0.0 tag/release, six release executions and constrained attestations for all subjects. |
| E-07 | **OPEN — candidate acceptance evidence.** Genuine candidate-bound trace/score/oracle outcomes and manual 7/7. Passing local validator controls do not manufacture that score. |
| E-08 | **OPEN — named human.** Independent candidate-bound MAN-01, distinct implementer/reviewer and clean-room inputs. |
| E-09 | **OPEN — named humans/real app.** MAN-02 disclosures, MAN-03 bilingual meaning, MAN-04 real OS × minimum/current Obsidian rehearsal. |
| E-10 | **OPEN — real packaged candidate execution.** PT-06/PT-08 outcomes/companions on supported targets. Local FX-71 publication/integrity is CLOSED separately. |
| E-11 | **OPEN — post-publication.** Deployment report/cleanup and rollback if needed; acceptance itself treats this as unscored. |
| E-12 | **OPEN — exact smoke receipts.** Nine candidate-bound intermediate Python smokes on required architectures. |
| E-13 | **OPEN — target/phase identity companions.** Full real collection/v3 registry/runtime evidence for required candidate, release and reference executions. Empty-candidate local receipts are not relabelled. |
| E-14 | **OPEN — fresh reference execution.** Linux x64/Python3.14/Core0.3.7 complete hash closure, install reports, metadata/licenses and tamper negatives. Golden seal verification is not an install. |
| E-15 | **OPEN — actual release and independent reviews.** Exact tag/SHA, six post-attestation execution sets, constrained provenance and candidate-bound named records. |
| E-16, added by the shell M6 repair | **OPEN — real cold-start measurements.** Windows/macOS hosts with actual optional tools, cold profiles and repeated timings. Engine bounding and fake-tool launch regressions are locally CLOSED, but do not supply those real-host observations. |

M1-V31/V34 are aliases of these external obligations. Receipt staleness, blank local candidate bindings, missing real-app or named-human observations and unperformed publication cause **zero deductions** below. In contrast, M7-D02 is a locally correctable contradictory expected count and is scored as documentation.

## Scores and exactly what blocks 100

Audit scores are judgments about demonstrated code/doc mechanisms, not the generated release acceptance score. Five components per dimension, each /20. **100 iff no open code/doc finding in that dimension.** The blocker column is exhaustive; alias rows and downstream effects do not multiply deductions.

| Dimension | Components (/20) | Score | Exact blockers to 100 |
|---|---|---|---|
| Vertical | Runtime/admission 20; discovery/classification/select 20; conversion/render/cache 14; approval/transcription 20; publication/protocol/UI 20 | **94/100** | **M7-V01 only:** identical bytes in different admitted formats reuse the wrong base conversion result. |
| Oracles | Independent literal expectations 20; complete Python universe 20; exact shell execution identities 20; composed protocol/version boundaries 20; cache-input discrimination 16 | **96/100** | **M7-V01 only:** existing cache tests cover same-format reuse and omit both-order identical-byte/different-format cold-oracle controls. |
| Docs ↔ code | Protocol conformance summary 18; implemented gate/cwd contract 20; CI-policy summary 18; recipes/disclosures 20; current owner/status account 18 | **94/100** | **M7-D01:** live CLI conformance row says eleven exact version keys instead of fourteen. **M7-D02:** G-14 says three experimental cells instead of four. **M7-D03:** current Open paragraph still requests completed syntax/waiter repairs. |
| Simplicity | Canonical helpers 20; bounded lifecycle state 20; removed unused surfaces 20; useful retained designs/Core ownership 20; one settled owner/status account 18 | **98/100** | **M7-D03 only:** contradictory current status duplicates completed repairs as pending local work. All original carried simplicity mechanisms are closed. |

The complete open code/doc set is **M7-V01, M7-D01, M7-D02, M7-D03**. Every M6 primary mechanism and code/doc residual is closed at its original scope; only explicitly separated external-evidence items remain open in the inherited ledger. M7-D03 records a newly located status sentence rather than reopening a corrected historical location.
