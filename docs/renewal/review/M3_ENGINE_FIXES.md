# M3 engine fix round — DRAFT-3.5 / Core 0.3.6

Date: 2026-11-09. Scope: the OPEN/new items in [M3_cx_vertical.md](M3_cx_vertical.md), within the user's engine ownership restrictions. No git commands, remote CI, release publication, shell edits, class_stage TOML edits or class-sweep edits were performed by this task. Historical review snapshots and their audit scores remain historical.

The engine runtime repairs and new independent oracles are implemented. Core **0.3.6** is the release/reference baseline; compatibility stays **>=0.3.5,<0.4**, including the minimum 0.3.5 contract endpoint. Every sealed triage byte is unchanged. Windows Python **3.14.10** uses the requested interpreter at `D:/Engram2/_sys/data/temp/mdf_venv314/Scripts/python.exe` and the newly built installed wheel.

Shell-only changes and actual release/CI/manual receipts remain separate obligations. The user explicitly excluded the affected shell and horizontal source files from engine edits; their remaining work is identified below instead of changing the engine protocol to hide shell defects.

## Finding dispositions

| Finding / inherited finding | Result and concrete evidence |
|---|---|
| M3-V01 / M1-V22 | **CLOSED.** `_well_typed` checks payload-kind string type before set membership. `T-CLS-90` exercises list/dict/null/number/unknown string through real orchestration: exact row11a warning, zero scheduled units/provider calls, retained source output and successful text sibling. Existing real parser/stored controls remain in `T-RND-81/82`. |
| M3-V02 / M1-V26 | **CLOSED.** `_render_pdf_page` uses `ceil` for both allocation dimensions, matching the installed pdfium implementation. `T-RND-90` covers supported 200/300 dpi and rotations 0/90, proves no render call for over-limit fractional allocation, and checks an allowed 72×72 raster control. |
| M3-V03 / Fable X-01 progress residual | **OPEN — shell owner.** The affected `JobStatusBar` remains under excluded `shell/**`. Its Plan/Run history and repeated full reductions require the shell fix described by the audit. Engine event semantics remain intact; removing Plan events would conceal the consumer bug. Cancel's earlier repair remains implemented. |
| M3-V04 / M2-V03 parity residual | **OPEN — engine half repaired, shell half pending.** Package admission now rejects blank/whitespace platform with a typed platform problem (`T-GEN-90`). It continues rejecting malformed renderer versions. The shell's prefix parser still admits `5.15.1???`; strict syntax parity requires the excluded shell change. No package gate was weakened to admit that value. |
| M3-V05 | **CLOSED for Python execution evidence.** Pytest captures every collected parameter before -k/-m deselection and emits canonical nodeid properties. Each JUnit has its own candidate-bound `registry-<target/phase>.json`. Shared receipt validation rejects missing, duplicate, substituted, mistagged, skipped, failed or stale identities; required callable parameters must all be selected and pass. Scoring and endpoint prerequisites use the same validator. PT-02 retains reference-only scope. `T-META-90` has complete 20-class positive controls and seven negative mutations; `T-META-54` and `T-GEN-86` use explicit synthetic identity-bearing controls. Jest retains its separate existing title/registration projection. |
| M3-H01 / M2 horizontal active-stage declarations | **CLOSED by verified existing-owner repair; no engine edit to protected files.** Current class sweep includes S4 K05/K06/K08/K09/K14 and S6 K04 with ordered selection/status assertions. All 20 class cases passed on each interpreter, and each of the six stage cells projects to T-GEN-85. Full verification is reported below; the engine task preserves the protected file boundaries. |
| M3-O01 / K14 corrupted-member oracle | **CLOSED by companion tests.** `T-ASM-90` independently checks the exact published unit IDs, paired OCR delimiters and pending reasons/counts for scanned/mixed PDF, multiframe GIF, real DOCX and real HWP, then verifies warm stability. `T-ASM-91` checks all 1001 capped-page anchors and exactly p1..p1000 OCR blocks. `T-TRI-90` puts a corrupt Office relationship inside an otherwise valid archive and verifies the actual Core observation, retained member result and successful valid sibling. The protected sweep was not edited to add these assertions. |
| M3-D01 / Fable X-16 / S-13 | **OPEN only for the protected matrix comment; engine-owned documentation repaired.** SPEC GEN-01 hook lists all three actual dependencies; DRAFT-3.5 documents schema/pixel/receipt/reference semantics. HANDOFF points to current repair evidence and owner-specific pending gates. TESTPLAN includes FX-03 in T-PLN-55 and all new registrations. The excluded class_stage heading still says 117 cells while the current owner-edited section expands to 71. That comment must be corrected by its horizontal owner; no matrix section was edited by this task. |
| Fable X-11 | **Engine handoff ready; shell publication pending.** A fresh recording from installed mdflow 2.0.0/Core0.3.6/Python3.14.10 is staged at `build/trace/redgreen/m3-fx71-py314`. All 53 files verify, default package admission succeeds, and every derived version verdict matches its independent expectation. No `shell/test/fixtures/fx71` file was changed. Its owner must publish the staged bytes and run fixture-dependent shell checks. |
| M1-V31 | **OPEN — remaining platform evidence.** Local Windows Python3.14 installed-wheel verification is performed here. It is not six candidate-bound supported endpoint CI runs or nine intermediate smokes; no local receipt is named as a missing CI target. |
| M1-V34 | **OPEN — real reference/release evidence.** The reference compiler now pins Core0.3.6 and keeps Linux x64/Python3.14 scope. A Windows run cannot establish that fresh hash-mode reference install, licenses, six targets, provenance or named desktop reviews. The repaired gates continue rejecting missing evidence. |

## Red-first evidence

All logs are under `build/trace/redgreen/`.

- `m3-regressions.red.log`: actual pre-repair HWP TypeErrors (2), fractional allocation failures (4), incomplete/duplicate/substituted/stale/missing-registry scoring failures (5), platform admission failures (2) and current-reference/docs failures (2). This aggregate also contains one early *test expectation* correction: the corrupted relationship preserves Core's `review` decision rather than inventing `unknown`. That row is not claimed as a production defect. The preceding `m3-initial.red.log` also records two fixture-setup issues that were corrected before relying on the regressions.
- `m3-core-reference.red.log`: the original golden verifier incorrectly required the current minimum endpoint's version to equal the reference producer; the 0.3.6 seal must remain labelled 0.3.6 while endpoint reports are compared byte-for-byte.
- `m3-recorder-isolation.red.log`: actual recorder argv lacked `-I`, despite its stripped environment. `T-GEN-92` observes the child launch; the recorder now uses the selected interpreter's isolated installed module.
- `m3-placement-oracle.red.log`: explicitly labelled **intentional output-loss mutation control**. In memory, one actual assembled OCR block is removed while report/placement counts are retained. All five new format cases turn red. This establishes oracle strength; it is not a claim that the unmodified production assembler loses a block.

`m3-targeted.green.log` records the first repaired target set: **52 passed** on Python3.14 before the final DOCX/recorder additions. The full results below include those additions. `m3-protected-sweep.green.log` separately records K05's current-owner sweep control.

The `m3-hwp.red.log`, `m3-pixels.red.log`, `m3-parameter-receipts.red.log`, `m3-platform.red.log` and `m3-docs.red.log` files are labelled excerpts from the same original aggregate red execution, not invented independent runs.

## Core migration and provenance

- `tools/build_engine.py` generates reference input/header with exact **Core0.3.6**. PT-02's exact-pin/header and offline complete-closure controls, release rehearsal validation/samples, fixture tools, assembly provenance examples, README/CHANGELOG, BOOTSTRAP and active packaging documentation agree.
- The minimum compatibility endpoint and `>=0.3.5,<0.4` ranges deliberately remain 0.3.5. `tools/contract_endpoint.py` still deduplicates only when the newest public version equals that minimum, not when it equals the separate release reference.
- `tools/golden.py` validates the seal's **reference producer** (0.3.6), then installed-Core contract tests regenerate and compare the observations. The current endpoint is never relabelled as the producer. Invalid reference version and report-byte mutations still fail.
- All **50** sealed `triage*.json` files remain unchanged. Only FX-03 assembly `tools` provenance changed from 0.3.5 to 0.3.6, with the corresponding existing lock hashes resealed. The official `tools/golden.py gen --fx FX-03` sealer then verified the same Core0.3.6 corpus (`m3-golden-seal.green.log`); every original triage digest remains identical. Classification decisions, Sniff reviews and document source hashes were not rewritten. Migration evidence: `m3-core-migration.json`.
- Archived 0.3.5 guide/source copies retain their names and line numbers; [the reference note](../ref/README.md) explains their relationship to 0.3.6. Historical audit/verification receipts retain their actual versions.

## Python3.14 setup and recording limits

The requested venv already contained Core0.3.6, pytest, Pillow13.0.0 and pdfium5.15.1, but lacked pip/hatchling. Full `requirements-build.txt` installation was attempted (`m3-bootstrap-py314.log`); the configured index could not supply pip-tools7.6.2. Necessary pure build tools were installed offline from the existing local installed-distribution snapshot (`m3-build-wheels/`, `m3-bootstrap-py314-offline.log`). These are test setup artifacts, not published dependency wheels or fresh-resolution evidence.

The local Windows sandbox denies access to directories created with mode0700, including Python3.14 tempfile directories. Installing the engine wheel and recording therefore use the established opt-in repository-only `_sandbox_temp_prelude` from the test conftest, executed by build-only launchers. The recording child remains `-I`, imports the installed wheel, and adds no engine/src path. This workaround is not shipped and is not real desktop permission/cancellation evidence.

Engine wheel: `build/trace/redgreen/m3-wheel-draft35/mdflow-2.0.0-py3-none-any.whl`. Build/install logs: `m3-wheel-build.green.log`, `m3-py314-install-bridge.green.log`. Recording log: `m3-fx71-py314-record.log`; recording launcher: `m3-record-bridge.py`. The staged parent version and all derived versions pass the default package gate expectations; no runtime field was rewritten to simulate a supported host.

## Final verification

| Verification | Actual result / artifact |
|---|---|
| Full Python3.14.10 installed wheel, Core0.3.6 | **536 passed, 12 skipped, 1 platform deselection; zero failures/errors/xfails**, 812.30 s. `junit-m3-py314-installed.xml`, `m3-full-py314-installed.log`. Command: requested interpreter `-I -m pytest engine/tests --runxfail -q -p no:cacheprovider --junitxml=build/trace/junit-m3-py314-installed.xml`, with installed mode and repository-only Windows temp bridge. |
| Full Python3.15.2 source, Core0.3.6 | **536 passed, 12 skipped, 1 platform deselection; zero failures/errors/xfails**, 671.17 s. `junit-m3-py315.xml`, `m3-full-py315.log`. Same suite/--runxfail/cache controls, source mode. |
| Final focused verification after import/registration cleanup | **29 passed** on the installed Python3.14 wheel, 25.05 s. `junit-m3-final-targeted.xml`, `m3-final-targeted.green.log`. |
| Every collected Python identity | Each suite collected **549** cases, deselected one platform case and emitted **548 unique selected nodeids** matching its actual JUnit exactly. All 20 T-GEN-85 class parameters pass in each XML. Local inventories have no candidate commit binding and are not advertised as release receipts. |
| Wheel correspondence | All **26** installed Python modules match both wheel and current engine/src; mdflow/Core/Pillow/pdfium all resolve under the selected Python3.14 prefix (`m3-installed-integrity.green.json`). Pip check reports no broken requirements (`m3-pip-check.green.log`). Wheel SHA-256 **8957dbb0b5433f6ea97881f5e063e9fc53c6dff2c69139465b48b206b7ea2759**. |
| Trace / matrices | All five trace error counters **0** (`m3-trace.green.log`); `matrices-m3.json` is a registration/applicability view. Six formerly delegated horizontal cells project to T-GEN-85. |
| Golden integrity | All **50** original triage report digests unchanged; reference seal records Core0.3.6. |
| Supported-host FX-71 staging | **53 files** verify; parent default gate admits Python3.14.10/Core0.3.6, all derived verdicts correct. The `unknown-optional-field` variant now succeeds under the default release policy. |

After the full suites, only unused test imports and the fractional synthetic test's fixture registration were cleaned up; the latter now has FX-60 without implying it consumes the actual FX-08 class fixture. The final focused run and trace check cover these metadata/import-only edits. No engine runtime module changed after the tested wheel was built.

`m3-final-verification.json` records counts, wheel/source correspondence, original triage digests and protected-path observations. Concurrent owners changed shell files and class_stage content during this session; this engine task neither writes those files nor restores other owners' work. The captured before/after hashes are observations of the shared workspace, not a claim that other owners made no changes.

The twelve absent release/evidence cases remain skipped. Shell progress/parser repairs, the protected class-stage comment, FX-71 publication by its owner, real required CI/reference installs and named reviews remain explicit handoffs. No local green run or synthetic control is promoted into those missing receipts.
