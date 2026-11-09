# M3 recursive MECE audit — vertical closure, oracles, docs ↔ code, simplicity

Repair follow-up: [M3_ENGINE_FIXES.md](M3_ENGINE_FIXES.md) records the DRAFT-3.5/Core0.3.6 engine repairs, red/green evidence, supported-host recording handoff and remaining excluded-owner/release obligations. Findings and scores below retain the original audit snapshot.

Date: 2026-11-09. Workspace: repository. Authority: SPEC DRAFT-3.4, current SHELL/PACKAGING/TESTPLAN/ACCEPTANCE documents. Predecessors: `M2_cx_vertical.md`, `M2_ag_horizontal.md`, `M2_fable_cross.md`; repair claims: `M2_ENGINE_FIXES.md`, `M2_ENGINE_FOLLOWUP.md` and SHELL §7. Finding IDs retain their originating round; “new” below means newly demonstrated in this audit, not a claim about historical introduction.

**Verdict: substantial closure; incomplete validation and release evidence.** The six M2 vertical findings are **5 CLOSED / 1 OPEN** (runtime-policy parity has a residual mismatch). The 38 inherited M1 findings are **34 CLOSED / 4 OPEN**, including a newly reopened pixel-bound finding. Of M2 horizontal's 30 disputed cells, **25 CLOSED / 5 OPEN** as execution registrations. Fable's 19 X findings are **16 CLOSED / 3 OPEN**; its 15 S proposals are **14 CLOSED / 1 OPEN**. Overlapping findings are cross-referenced, not counted as independent defects.

**Scores: vertical closure 80/100; oracle strength 76/100; docs ↔ code 82/100; simplicity 88/100.** Every dimension has an explicit open item; none qualifies for 100. These are audit scores, not generated release acceptance.

Only this file is written. No code changes, git commands, installations, builds, pytest/Jest invocations, remote queries, release actions or external communications. Python probes used `python -B -` and in-memory mocks; the TypeScript probe transpiled existing source in memory using the existing `shell/node_modules/typescript`. No probe files or receipts were generated. A deliberately short-lived command descendant was allowed to finish. Direct calls to existing test assertion functions are distinguished from pytest runs below.

## Evidence and checks actually performed

| Check | Observation and limit |
|---|---|
| Existing engine receipt | `build/trace/junit-m2-followup.xml`: **519 cases = 507 passed + 12 skipped**, zero failures/errors. All K01–K20 class-sweep parameter cases passed; no xfail is used to count them as passing. The follow-up log records `--runxfail` and one platform deselection. This audit parsed the XML; it did not rerun the full suite. |
| Existing shell receipt | `build/trace/junit-shell.xml`: **255 passed**, zero failures/errors/skips. Parsed, not rerun. |
| Installed-source correspondence | All **26 Python module members** of `build/trace/redgreen/followup-wheel/mdflow-2.0.0-py3-none-any.whl` equal the corresponding current `engine/src` bytes. This supports use of the local repair receipt; it does not establish supported-platform installation or dependency resolution. |
| Read-only trace check | Called `requirement_registry`, `discover_tests`, `discover_shell_tests`, `coverage_problems`, `registration_problems`, `matrix_problems` directly, avoiding the CLI's registry write. Counts: unknown requirements **0**, uncovered **0**, untagged **0**, registration errors **0**, matrix errors **0**. Registration is not an execution oracle. |
| Applicability enumeration | Expanded current TOML cross-products: **84 stage/FM declarations**. Counts S0–S13: **6,5,7,4,7,6,5,8,5,9,3,7,8,4**. All 84 are defensible ownership/equivalence declarations with the qualifications below. The false S6:FM5 alias was removed and has a direct test. |
| Original assertion functions, read-only inputs | `T-CLS-80`: all **14** existing mutations pass; `T-CLS-07`: all **14** exact issue policies pass. Read-only substitutes supply the reviewed golden Sniff dictionaries instead of generating files; the production classifier and original assertions execute. This is narrower than rerunning their pytest fixtures. |
| Production Plan binding | Directly called the current `T-PLN-02` assertion function with the existing pure `gen_core` builders: production-input mutations, field expectations, independent canonical hashes, cache/status and other-file independence all pass. No filesystem fixtures required. |
| Fable handoffs | Direct CLI calls with missing/0.3.4/0.4.0 Core metadata: exit **0**, eight fields, correct Core diagnostic, empty stderr; socket connect patched to reject attempts. Direct `T-GEN-87` calls pass all three malformed/unavailable cases. Direct `T-GEN-88` passes and recorder verification reports **53 files**. |
| Command timeout repair | Actual `_capture` with timeout `.15`, a direct child exiting after launching a descendant retaining stdout for 1.2 s: **E_PROVIDER_TIMEOUT in 0.151 s**, zero `mdflow-command-output` reader threads. Waited until the short-lived descendant finished. No scratch file was used. |
| Release evidence inventory | `required_executions(build/trace, <explicit synthetic commit>)` reports **15 missing prerequisites**: six endpoint receipt pairs and nine smokes. No target-named endpoint/reference success evidence is supplied here. This inventory result establishes absence, not a candidate commit verdict. |
| New adversarial probes | HWP type crash; fractional-page pixel overrun; Plan→Run progress double counting; divergent gate verdicts; incomplete-parameter score acceptance. Inputs, outputs and fixes are documented below. |

CLOSED means the original defect is repaired, or its advisory proposal has an explicit defensible disposition, with a named code boundary and regression oracle. It does not waive real OS/manual/reference evidence. OPEN includes residual behavior, missing executable registration, or a demonstrated weak oracle. Source-only checks do not manufacture runtime success.

## Every finding carried by M2 vertical

Paths are repository-relative. **M1** = `engine/tests/stage_io/step7/test_m1_engine.py`; **M2E** = `.../test_m2_engine.py`; **C** = `engine/tests/stage_io/test_class_closure.py`; **U** = `engine/tests/unit`; **P** = `engine/tests/packaging`. Test IDs identify assertions, not merely names suggesting closure.

| Inherited ID | Verdict | Current source and oracle evidence |
|---|---|---|
| M1-V01 | CLOSED | Nominal/aggregate cells remain directly registered (`T-META-50`, `T-TRX-57`, `T-WRT-51`, `T-PLN-53/54`, `T-RPT-52–56`). `process`, `summarize`, `publish_output` expose durable output and exact counters; no blanket report N/A replacement. |
| M1-V02 | CLOSED | Discovery, run-temp, Convert temp/cache interruption, raster read and report-copy errors retain direct tests (`T-SNF-50`, `T-GEN-53`, `T-CNV-52/53`, `T-TRX-54`, `T-RPT-51`). Render setup now separately covered by `T-RND-80`. |
| M1-V03 | CLOSED for its identified consumer gaps | Classify checks consumed containers; ledger validates provenance; Transcribe performs real pre-send validation (`T-CLS-50`, `T-LKP-50`, `T-ASM-50`, `T-TRX-53/54/56`, `T-TRI-50`). The broader V1 promise remains OPEN under V22/M3-V01. |
| M1-V04 | CLOSED | M2E `T-RND-82` uses actual HWP5 triage/extraction, selection, provider and assembly. `T-RND-81[False/True]` composes equal payloads with opposite policies, exact parser raster, one request, two retained placements and stored refusal. `T-GEN-85[K09]` adds real CLI cold/warm behavior. |
| M1-V05 | CLOSED for the original expansion/owner drift | TOML header now says `fx("all")` expands only S0–S3/S13; `T-META-81` checks that text; `trace.test_classes` enforces it. Obsolete K20 Lookup alias is gone. Other stale documentation is M3-D01, not silently treated as fixed. |
| M1-V06 | CLOSED | `sniff_io.discover/_is_link` filters explicit hidden/link/excluded roots, deduplicates descent, recognizes reparse attributes and exposes read failures. `T-SNF-50/53`, sweep K20, protect these effects. |
| M1-V07 | CLOSED | `_source_bytes` checks length/full hash; native Core/Convert use the same owned snapshot; archives are verified before expansion. Replacement tests `T-SNF-51/54` require no changed conversion/output/inventory. |
| M1-V08 | CLOSED | `_media_hashes`, bounded member reads and `_render_media` propagate actual-byte limits; expansion retains discovered members after later bounds. `T-CNV-50`, `T-RND-50`, `T-CTR-50/51`. Pixel rounding is a separate reopened V26 boundary. |
| M1-V09 | CLOSED | `publish_output` checks containment before reading existing Markdown and Write rechecks publication. `T-WRT-50[False/True]` observes outside-read avoidance and intact outside bytes. |
| M1-V10 | CLOSED | Skipped Markdown still calls `publish_source(..., None, media)`; missing media is restored and Markdown mtime preserved by `T-WRT-51`. |
| M1-V11 | CLOSED | `ledger.validate_entry` requires parseable timezone-bearing second-precision `created`; invalid values become misses before `_block`. `T-LKP-50`, `T-ASM-50`. |
| M1-V12 | CLOSED | `report.emit_progress` bounds nested informational values including UTF-8/newline. `T-RPT-50` checks exact byte ceiling, JSON validity, preserved identity/counters and immutable input. |
| M1-V13 | CLOSED | CLI defers terminal emission until optional copy errors update report/exit. `T-RPT-51` covers empty/nonempty runs and exactly one authoritative terminal event. |
| M1-V14 | CLOSED | `command._capture/_read_ready` has one unbuffered polling owner; no reader-thread/close lock. `T-TRX-80` plus new 0.151 s inherited-handle probe; original live output cap remains `T-TRX-50`. Direct child cleanup remains in `finally`. |
| M1-V15 | CLOSED by bounded amendment | `read1` body deadline/socket timeout implemented; `T-TRX-51` tests drip expiry. SPEC withdraws an absolute DNS/TLS/header/Windows cancellation guarantee. Real OS rehearsal remains a release gate. |
| M1-V16 | CLOSED | Exact argparse flags, command-only options and none cost override remain in `_parser/_options/build_provider`; `T-CLI-50`, `T-PLN-50`. |
| M1-V17 | CLOSED | `transcribe._normalise` restricts runtime provider errors; diagnostics redact before truncating. `T-TRX-52` checks boundary-spanning secret, invented code and next-Key continuation. |
| M1-V18 | CLOSED | Provider factory rejects proxy userinfo before public Plan metadata exists; `T-SEC-50`. |
| M1-V19 | CLOSED | Select includes refusal policy in media grouping; stored HWP `_unsupported_media` cannot inherit parser eligibility. `T-RND-81` checks both candidate orders and exact egress/placement. This does not imply malformed payload kinds are total (M3-V01). |
| M1-V20 | CLOSED | Full digest owns grouping; h12 only names files and is collision-checked before Convert. `T-SEL-50`, `T-CNV-54`. |
| M1-V21 | CLOSED | PDF protection consults parser security state; malformed HWP headers become corruption. `T-SNF-52`, `sniff_io._check_pdf/_analyze`. |
| M1-V22 | **OPEN — MAJOR residual** | Fourteen new nested-field mutations pass, including the original dpi-tag failures. But `_well_typed` set-membership on a list/dict `payload_kind` raises TypeError. Probe reaches the real pipeline Classify consumer. SPEC V1 and `T-CLS-80`'s “all promised nested types” closure remain incomplete: M3-V01. |
| M1-V23 | CLOSED | Plan is a prepared snapshot and `oversize` is approved/hash-bound. `plan.plan`, SPEC §§4/7.1/8.4, `T-PLN-51`, production `T-PLN-02`. |
| M1-V24 | CLOSED | Production Transcribe calls `verify_raster` immediately before provider use. `T-TRX-53`, C `T-TRX-08` require refused tampered Key, zero tampered egress and unchanged sibling success. |
| M1-V25 | CLOSED | Render stores then deletes encoded `payload`; `T-RND-52` observes previous object release before the next raster. This is encoded-payload lifetime, not decoder working-memory certification. |
| M1-V26 | **OPEN — MAJOR reopened** | Integer-size negative/positive tests `T-RND-53` still pass, but PDF precheck rounds down while pdfium allocates ceil dimensions. Actual 72.1 pt square at 72 dpi produces 73×73 after a 72×72 bound check: M3-V02. |
| M1-V27 | CLOSED | `_render_media` uses frame zero; `T-RND-54` compares decoded pixels against both frames; `T-RND-07` checks warning semantics. |
| M1-V28 | CLOSED | Discovery collision precheck uses `assemble.output_path` including reserved-name normalization; `T-WRT-52` checks first bytes preserved and second report-only. |
| M1-V29 | CLOSED | Transcription stays in `entries` before cache write; a failed durable ledger write cannot discard output. `T-LKP-51` checks two requests, both OCR outputs, error/exit; `T-LKP-03` covers atomic storage. |
| M1-V30 | CLOSED | Current `T-PLN-02` changes real Plan inputs and asserts corresponding fields plus independent canonical hashes; includes identity, provider/destination/proxy/prompt, unit data/status/counts, cost, sensitivity, cache/other-file independence. Direct read-only execution passed. `T-META-80` is supportive lint only. |
| M1-V31 | **OPEN — MAJOR evidence** | Source injection is removed in installed mode; root/unit/child fixtures honor it; session start asserts prefix/site-packages. Local wheel correspondence/507-pass receipt supports local execution. Six supported endpoint and nine smoke receipts are absent; no cross-platform claim follows. Scorer completeness also remains M3-V05. |
| M1-V32 | CLOSED as an oracle repair | `assert_full_lock_rejects_dependency_mutations` requires untouched install and rejects missing transitive pin/hash and changed dependency. `T-GEN-52` exercises real small local wheels; PT-02 uses the actual reference. Real reference execution remains V34. |
| M1-V33 | CLOSED | `T-CLS-07` now has independently expected exact signatures/code sets for all 14 codes; all 14 direct assertion calls passed. `T-RND-83` takes a real Core unsupported-media issue through preparation, refusal, zero requests, warning and retained placement. |
| M1-V34 | **OPEN — BLOCKER evidence** | Wheel/reference and post-attestation routes exist, but successful Linux3.14 reference hash reproduction and six supported target installations are not present. Twelve local release/evidence skips stay skips. X-11's unsupported fixture host and M3-V05 also prevent claiming release closure. |
| M1-V35 | CLOSED as a design change | Direct wheel, one target-labelled reference, range-based compatibility installs and shared `ASSETS/SUBJECTS` replace the universal lock/catalog. `build_engine`, `T-GEN-54`, PT-07, `T-META-54`. Actual receipts remain mandatory. |
| M1-V36 | CLOSED | `Ledger.write` delegates atomic publication to `write.atomic_write`; `ledger.key_id` is the canonical imported helper; IO Sniff imports pure routing functions. `T-LKP-80`, `T-SNF-80`. No duplicated hash wrapper or second ledger temp/replace loop remains. |
| M1-V37 | CLOSED by retained design | Optional base cache remains intentional and tested (`T-CNV-04/51`). `_MeasuredProvider` observes explicit request counts rather than replacing `_post_once` (`T-TRX-55`). Deletion was advisory, not a correctness prerequisite. |
| M1-V38 | CLOSED | Report-only classifications clear candidates; Select checks action; orchestration excludes Render for them. `T-CLS-53`, `T-TRI-50`, `T-PLN-54`, `T-SEL-51`, sweep protected/corrupt no-output controls. |

| M2 ID | Verdict | Verification of the original finding |
|---|---|---|
| M2-V01 | CLOSED | Buffered queue reader removed; actual inherited-stdout timeout returns in 0.151 s. `T-TRX-80` checks deadline/no reader; existing cancellation/scratch tests supply separate lifecycle coverage. Trusted command descendants are explicitly command-owned under amended SPEC. |
| M2-V02 | CLOSED | `P/_support.installed_import` accepts a workspace-local selected venv's site-packages while rejecting `engine/src` and outside-prefix imports. PT-01 calls it; `T-GEN-80` has both negative controls. No impossible “not under repository” condition remains. |
| M2-V03 | **OPEN — MINOR residual** | Original Python3.15/pdfium6/Pillow14 counterexamples are fixed by direct wheel ranges, package gate and shell ranges (`T-GEN-81`, JT-17). Full admission parity still fails for empty platform and malformed renderer suffix: M3-V04. Neither new handoff test exercises these fields across both gates. |
| M2-V04 | CLOSED for the original graph/isolation defects | CI excludes release tests from ordinary installed engine suite; freeze verifies immutable subjects; attest precedes six `verify-release` jobs; `accept-release` scores afterward; PT-17 no longer consumes its own final score. `T-GEN-82/83`, workflow dependency/source inspection. No claim of executed release. Parameter completeness is a separate new scoring defect, M3-V05. |
| M2-V05 | CLOSED | Setup `mkdir` is caught within `render_units` and returns E_RENDER_FAIL per selected unit. `T-RND-80` observes pending Markdown and sibling text output. S6:FM5 is no longer N/A. |
| M2-V06 | CLOSED | Group key contains rendering/refusal policy before representative sorting; supported/stored equal payloads stay separate. Both orders in `T-RND-81` assert one exact parser raster request and explicit stored pending placement. |

## M2 horizontal findings: all 30 cells and remaining weak-oracle claims

K05 is single raster and K06 multiframe raster, as the M2 orchestrator correction states; the original PPTX/XLSX labels are not reused. CLOSED below means a relevant current assertion and execution registration exist. Actual CLI sweep effects can be stronger than the manifest's remaining declarations: a declaration overlaid by a registration is not itself a coverage hole.

| M2 disputed cells | Verdict | Current evidence / residual |
|---|---|---|
| S4:K05 | **OPEN** | Sweep executes Select and checks total, but supplies no S4 extra registration; manifest still delegates to K02. M3-H01. |
| S4:K06 | **OPEN** | Same: real multiframe case, no class-specific S4 execution registration. M3-H01. |
| S4:K08 | **OPEN** | Same: HWPX CLI composition exists, S4 remains N/A-only. M3-H01. |
| S4:K09 | **OPEN** | Same: HWP composition exists, S4 remains N/A-only. M3-H01. |
| S6:K04 | **OPEN** | Sweep renders the capped PDF with fixed expected counts, but neither primary fixture projection nor `cells` registers K04:S6. M3-H01. |
| S6:K08 | CLOSED | `T-RND-83` directly registers Core-identified HWPX encoding refusal; sweep K08 supplies normal successful real-CLI preparation/egress. Existing N/A declaration is overlaid. |
| S7:K03, S7:K04, S7:K06, S7:K07, S7:K08, S7:K09 | CLOSED, each | `T-GEN-85` literal per-cell registrations; independently fixed class counts, cold misses/transcription, warm cached counts, zero added requests/sockets, bytes and mtimes stable. |
| S9:K04, S9:K05, S9:K06, S9:K07, S9:K08, S9:K09 | CLOSED, each | `T-GEN-85`: no-consent run produces no socket/request, exact pending count and approval hash; yes-file replay records approver/hash and exact request accounting. |
| S10:K04, S10:K06, S10:K08, S10:K09 | CLOSED, each | `T-GEN-85`: eligible/transcribed counts, unit events, request totals and transcript presence; all actual parameter receipts present locally. Payload/provenance completeness limit is M3-O01. |
| S12:K03, S12:K04, S12:K05, S12:K06, S12:K08, S12:K09, S12:K11, S12:K18 | CLOSED, each | `T-GEN-85`: expected output paths exist, published tree/media counts match, transcript appears where expected, recursive bytes/mtime unchanged on warm run. Exact placement integrity is not established by this sweep alone (M3-O01). |

Read-only projection independently confirmed the five N/A-only cells above, `T-RND-83` for S6:K08, and `T-GEN-85` for every other listed cell. There are **77 expanded class-stage declarations**, despite the stale “117 cells” comment. No claim that trace's zero structural errors resolves the five semantic delegation findings.

| M2 remaining weak claim | Verdict and explicit check |
|---|---|
| K02 Convert empty text/fallback structure | CLOSED: `T-CNV-07` checks real Core gives three clean empty page strings, preserves page count and media emptiness; assembly/sweep carries those pages through. No additional undocumented fallback metadata is required. |
| K02 Transcribe timeout/retry per scanned page | CLOSED as bounded composition: C `T-TRX-07` checks exact rendered bytes sent for three pages and individual texts; `T-TRX-03` tests shared provider failures/retry/timeout. A repeat of every transport failure for every file class is not a separate contract. |
| K03 mixed PDF Render/Lookup/Write | CLOSED for class reach/cache/publication: C `T-RND-09` checks p2/p4 only, distinct hashes/dimensions; sweep checks cold/warm output and egress. The suggested independent PDF inline-media OCR path is not normative: PDF units are whole pages. Exact per-unit published block count remains M3-O01. |
| K07 Lookup/Approve and multi-media Plan | CLOSED: sweep's fixed two eligible units, no-consent zero egress, hash-bound replay, cold/warm counters; `T-PLN-55` separately consumes reviewed class candidates and checks pure Plan/cache behavior. Its pure-stage expected count is derived from Select, so the sweep's independent count is important. |
| K14 corrupted member Triage | **OPEN as suggested oracle expansion**: `T-CTR-03` checks independent member Sniff, `T-CTR-50/51` check bounds/retained inventory, sweep K14 is a valid archive. No new sweep corruption→Triage→sibling-success case is present. Keep as an oracle gap, not a demonstrated engine failure (M3-O01). |
| K14 S5 N/A text versus registered grid | CLOSED as bounded wrapper distinction: container index is assembled from members; member conversion is observable in sweep. The wrapper's common Convert no-op may emit a stage event; it is not a separate Core conversion. Explicit declaration/registration precedence is documented. |
| K15 explicit downstream exclusion | CLOSED: sweep report-only `NEVER` forbids Render/Assemble/Write and asserts no publication/socket. `T-TRI-50` additionally fails if protected Core-discovered units reach Render/Lookup. |
| K16 empty Plan/no uncaught error | CLOSED: sweep's corrupt case checks zero units/egress, report-only signature/error/output absence across Plan/run/rerun; `T-PLN-13`, `T-ASM-18` are separate controls. |

## Every M2 Fable finding and simplification proposal

The shell findings were rechecked because this is a repository audit, not only an engine rereview. Source changes and regression assertions support code closure; real desktop/manual evidence remains outside local Jest.

| ID | Verdict | Code / documentation / oracle |
|---|---|---|
| X-01 | **OPEN — MINOR residual** | Cancel is now visibly wired in `main.ts`→`JobStatusBar`→`coordinator.cancel` throughout Plan/consent/Run; `jt-16-cancel-ui` exercises actual button clicks and engine stop. Progress events are forwarded, but counts combine Plan with Run: M3-V03. Original blocker is repaired; progress subclaim is not fully closed. |
| X-02 | CLOSED | `launcher.engineEnvFor` supplies persisted Base URL over host value; `buildSpawnRequest` uses it. README/SHL-06 agree; JT-12 checks configured endpoint behavior. |
| X-03 | CLOSED | `settingsReadOnly` covers blocked/null migration; tab renders no writers; every `saveSettings` refuses. Whole-plugin JT-03/05 exercises settings/history paths preserving original bytes. |
| X-04 | CLOSED | `ShellSettingsTab.committed` uses blur/Enter, skips unchanged values; interpreter requires absolute path. Whole-plugin JT-10 checks zero typing probes and one committed probe. |
| X-05 | CLOSED for implementation | `pickWithDomInput`, `webUtils.getPathForFile`/legacy path resolver replace remote dialogs; missing DOM capability raises a notice. JT-08/02 cover selection/cancel/unavailable. Actual Obsidian picker remains MAN-04 evidence. |
| X-06 | CLOSED | `DropConfirmModal` lists selection and returns Convert/Cancel decision; main awaits it; JT-08 checks both outcomes. |
| X-07 | CLOSED | README names `data.v1.json`, model setting/`--model`, configured Base URL, inside-vault cache/spool/consent/logs and sync implications. These match current persist/launcher/storage paths. Named MAN-02 review is still required. |
| X-08 | CLOSED | `needsConsent` and `buildConsentView` use provider egress and `requests_to_send > 0`; informational cached files do not require acknowledgement. JT-14/15. |
| X-09 | CLOSED | SPEC warning/error `file` allows null; shell framing accepts run-level null; JT-13 covers it. |
| X-10 | CLOSED | `destinationStillValid` reruns real destination resolution before replay; refusal blocks launch. JT-09 negative revalidation controls; ordinary filesystem race limits are unchanged. |
| X-11 | **OPEN — release-host evidence** | FX-71 now records actual installed 2.0.0, all 53 hashes/derivations verify; source injection removed. Recorded host remains Python3.15.2; package/default shell gate blocks it. PT-06's optional-field positive variant also inherits Python3.15 and fails. Supported-host rerecording remains necessary; widened JT policy is labelled local-only. |
| X-12 | CLOSED | Selftest command first emits `shell.notice.selftestRouter`; JT-02 verifies retirement explanation. |
| X-13 | CLOSED | Settings UI exposes dpi/minPriority/maxUnits/approveThreshold/sensitive with bounds; whole-plugin JT-04 checks all persisted fields. |
| X-14 | CLOSED | `version` dispatch precedes `_check_core`; missing/incompatible Core is diagnostic JSON. `T-CLI-80` and `T-GEN-87`; current direct calls pass. Other commands retain startup gate. |
| X-15 | CLOSED | `onload` starts background refresh; jobs await shared `currentGate`; commands register without waiting for probe. Whole-plugin JT-02. |
| X-16 | **OPEN — MINOR residual docs** | yes-file references, missing mutate tool/provider recipe, README CLI section and CHANGELOG are repaired. `HANDOFF.md` still lists the now-fixed X-14, provider document and S-14/S-15 as pending, and reports 446 engine tests. M3-D01. |
| X-17 | CLOSED | No `electron.remote`/`@electron/remote` production dependency; picker uses DOM plus `webUtils`. Same implementation/oracle as X-05. |
| X-18 | CLOSED | `historyInputLabel` stores first path plus additional count; `jt-16-cancel-ui` history assertion checks remaining paths absent. |
| X-20 | CLOSED by disclosure | README explicitly states plugin-local data may sync with vault/plugins. Storage paths agree; relocation is optional. |

There is no X-19 in M2's consolidated finding list; no finding is invented to fill that numbering gap.

| Proposal | Verdict | Explicit simplification check |
|---|---|---|
| S-01 | CLOSED | Duplicate production `pure/argv.ts` absent; JT-04 uses real launcher construction. |
| S-02 | CLOSED | Red-phase `pure/errors.ts` absent. |
| S-03 | CLOSED | Three unused production barrels absent. |
| S-04 | CLOSED | `Authorization` has only yes-file form; no production repeated-yes branch. |
| S-05 | CLOSED | Protocol replay/oracle helpers reside in `shell/test/fixtures/protocol.ts`; production launcher contains snapshot/env/argv behavior. |
| S-06 | CLOSED | `outputsCreated` removed from production history facts. |
| S-07 | CLOSED | Production `pure/trace.ts` absent; Python trace consumes req registrations/JUnit. |
| S-08 | CLOSED | `setup.collectSetupDiagnostics` consumes `environmentDiagnostics` to expose variable presence. |
| S-09 | CLOSED | Log/output/main use shared `pure/paths.ts`; no separate private log joiner. |
| S-10 | CLOSED | `onload` has no `this.load()` test convenience call. |
| S-11 | CLOSED | Entry point feeds log status; EngineRun events feed progress. Neither parameter is unused now. |
| S-12 | CLOSED | `.gitignore` refreshed to actual build/cache/dependency/worktree paths; retired v1 generated-script/release patterns gone. |
| S-13 | **OPEN — MINOR residual** | CHANGELOG has 2.0.0 and BRIEF explicitly superseded. HANDOFF was refreshed for shell fixes but remains stale after engine follow-up. One current handoff is preferable to another summary file; M3-D01. |
| S-14 | CLOSED | `cli._provider_list` absent; `providers.describe` and instances use provider DEFAULT_META. `T-GEN-84`. |
| S-15 | CLOSED | `report.publish(value, *, stdout)` owns only stdout; CLI owns durable copy/error ordering. `T-GEN-84`, `T-RPT-51`. |

## Oracle strength of the tests added since M2

| Test family | Strength checked | Limit / required next oracle |
|---|---|---|
| `stage_io/step7/test_fable_handoff.py` — T-CLI-80 ×3 | Calls real isolated CLI with one metadata field changed. Asserts exact eight-key set, Core sentinel/value, protocol/schema, all required strings, exit0, empty stderr, zero socket log. Direct CLI probes corroborate. | Metadata substitution is a good missing-distribution boundary test, not a full Core-uninstalled venv install. No need to conflate the two. |
| `packaging/test_fable_handoff.py` — T-GEN-87 ×3 | Real package gate receives otherwise-valid response; incompatible Core yields a typed Core-range problem. Independent expected failure, no production serializer used for expectation. | Only unavailable/not-a-version/empty Core are covered. It does not establish full shell/package parity; M3-V04 survives. |
| Same file — T-GEN-88 | Current engine identity, manifest/host consistency, exact host gate verdict, all recorded hashes/derivations, labelled derived variants. Direct call and 53-file verifier pass. | Intentionally accepts honest unsupported-host recording as a *local* fixture. It cannot close X-11 or PT-06; optional-field positive case remains blocked until supported-host recording exists. |
| Same file — T-GEN-89 | Confirms recorder environment omits PYTHONPATH/PYTHONHOME. | Structural environment check only: constructor creates test work dirs, and test asserts neither actual child import origin nor wheel identity. Current local wheel equality and follow-up install logs are separate evidence. Improve by observing the actual recording child's selected-prefix import if extending this oracle; do not claim this two-key assertion alone proves installation. |
| M2E T-TRX-80 | Real inherited stdout, tight elapsed upper bound, exact timeout code, absence of old reader thread; direct current probe corroborates. | Does not itself assert cancellation, direct PID death or scratch cleanup. Existing separate cancellation/command-input tests retain those responsibilities. No single-test claim of all lifecycle cases. |
| M2E T-RND-80 | Injects real Render setup IO error through orchestration; exact issue, pending count/reason/output and sibling output. | Strong repair-specific boundary; broad `Path.mkdir` injection is constrained by source index/name. It is not just a manually constructed RenderResult. |
| M2E T-RND-81 ×2, T-RND-82 | Both representative orders; real stages outside controlled triage/extraction, exact parser raster and source identity, one request, stored pending placement; separate actual Core HWP extraction case. | T-RND-82 alone only checks PNG signature, not fixture-specific decoded pixels. T-RND-81 supplies exact byte composition. Neither mutates malformed payload_kind; M3-V01 remains. |
| M2E T-RND-83 | Core actually produces unsupported_media; controlled extraction contains decodable PNG bytes under refused encoding; no request, exact pending/placement and warning. | Strong adversarial issue→preparation integration; complements the exact pure Core-code policy table. |
| T-CLS-80; updated T-CLS-07 | Fourteen specific malformed nested values now fall back with exact signature/code; all 14 Core policies have independent expected signatures/codes/retained IDs. Direct calls pass. | “All nested types” is too strong: HWP container-valued payload_kind crashes. Add list/dict values to enum-boundary negatives and assert sibling continuation, not only action membership. |
| Updated T-PLN-02, T-META-80, T-PLN-55 | Real production Plan inputs changed independently; exact fields and independently canonical hash; pure class cases use reviewed fixture/classification. | META-80 merely bans two old source strings. PLN-55's expected count comes from Select; independent sweep counts are necessary and present. These are bounded pure-stage oracles, not Render/transport tests. |
| T-LKP-80, T-SNF-80, T-META-81, T-GEN-84 | Assert canonical helper identity/delegation, pure/IO routing equality, correct expansion prose, removed duplicate signatures. | Appropriate structural oracles for requested simplification; they do not replace atomic-write/format/publication behavioral suites. |
| M2 packaging T-GEN-80/81/82/83/86 | Positive/negative import locations, exact range counterexamples, workflow DAG checks, installed-mode fixtures, failed/skipped/wrong-commit receipt controls. | 82/83 are source/configuration checks. 86's positive synthetic XML has one arbitrary testcase; it does not prove required parameter inventory. Real score consumer accepts the same omission, M3-V05. |
| T-CNV-80 ×2 | Calls real Core for GIF/TIFF; exact clean-empty ConvertResult. Sweep K06 now passes with `--runxfail`, so no known-gap success substitution. | Negative suppression scope also includes BMP/WEBP in production; general Convert exception tests protect other exceptions, but these two parameter cases alone do not prove every format/exception pair. No observed defect from that bounded gap. |
| T-GEN-85 ×20 class sweep | Real isolated CLI, loopback guard including DNS/connect/sendto, independent per-class route/action/issues/count/output expectations; no-consent zero egress, hash replay, exact cold/warm request and unit events, media tree count, byte/mtime stability and temp cleanup. Reads all 20 successful actual XML cases. | For successful output it checks transcript *presence*, not exact OCR/pending block/placement identities and multiplicity; K04 does not inspect the uninspected page's published anchor; negative transport and corrupted inner-archive cases are absent. Five observed stage cells are unregistered. M3-O01/M3-H01. |
| New shell progress JT-09 within `jt-16-cancel-ui` | Exercises forwarding and rendered fields; Cancel tests click actual controls in all phases and preserve hidden-details behavior. | Expected numeric strings come from production `summarizeProgress` on one Run stream; no Plan→Run sequence or independent literal counter table. Thus both the phase-state bug and repeated rescanning survive (M3-V03). |

## New defects demonstrated by probes

### M3-V01 — MAJOR: malformed HWP payload kind crashes Classify

Location: `engine/src/mdflow/classify.py:101`, `_well_typed`; `_Pipeline.process` calls Classify before its only per-source OSError boundary can handle this TypeError. This is residual M1-V22, not a new provider issue.

Probe: load FX-24 `triage.json` and its reviewed Sniff; replace only `media[0].payload_kind`. `[]` and `{}` each raise **TypeError (unhashable set element)**. `None`, `7` and `"unknown"` correctly produce convert_only with W_TRIAGE_UNKNOWN_VALUE. A second probe called actual `_Pipeline.process` with the actual HWP bytes, a controlled triage return and only `Path.write_bytes` suppressed; the TypeError escaped that consumer too. No filesystem error was injected into Classify.

Expected: every V1 type violation returns row11a, no candidate scheduling, and later source files can continue. Actual: membership of an unhashable JSON container in the payload-kind set raises before returning a classification; `run` does not catch TypeError, so batch/report completion can be lost.

Minimal fix: type-check `payload_kind` before enum membership, as already done for payload hashes; audit other enum boundaries for the same assumption. Regression: list/dict payload kinds plus valid parser/stored controls through Classify and one real orchestration sibling-continuation case. Existing 14 T-CLS-80 rows omit this field entirely.

### M3-V02 — MAJOR: PDF pixel bound uses round while rasterization uses ceil

Location: `engine/src/mdflow/render.py:94`, `_render_pdf_page`. Reopens M1-V26's boundary completeness.

Read-only actual-pdfium probe:

```python
doc = pdfium.PdfDocument.new()
page = doc.new_page(72.1, height=72.1)
page.close()
png = render._render_pdf_page(doc, {"page": 1}, 72, 5184)
image = Image.open(io.BytesIO(png))
# image.size == (73, 73); pixels == 5329 > 5184
doc.close()
```

Control: a 72 pt square produces 72×72, exactly 5184 pixels. No exception occurs for the over-limit fractional page. Additional actual-pdfium probes at supported **200 and 300 dpi**, using page side `72.1 * 72 / dpi` pt, both also produced **73×73 = 5329 pixels** under the same 5184 cap. The existing test uses a grossly low bound of 1 and an ordinary integer-sized positive control, so it cannot distinguish round from ceil.

Minimal fix: derive a conservative pre-render size matching pdfium's allocation (including rotation/scale), reject before `PdfPage.render`; retain a defensive post-render check without presenting that as prevention. Add a fractional-dimension case immediately above the allowed area, a permitted boundary control, and an observed zero render-call assertion on refusal. The 72 dpi helper probe isolates rounding; the two supported-dpi probes confirm the same defect on the CLI's allowed scales.

### M3-V03 — MINOR behavior / simplicity: Plan progress survives into Run

Location: `shell/src/ui/progress.ts:122–134` and `coordinator.runJob/execute`. Residual X-01 progress behavior; Cancel itself is fixed.

Probe transpiled actual `JobStatusBar` and its i18n dependency in memory and supplied a fake element implementing the small DOM interface. Sequence:

1. `begin('plan')`; one-file run_start, file_end `{done:0,pending:1,failed:0}`, run_end exit3.
2. `phase('consent')`, `phase('run')`; second one-file run_start and file_end `{done:1,pending:0,failed:0}`.
3. Actual rendered detail: **`stage -, files 2/1, units done 1, pending 1, failed 0`**. The Run-only summary is **1/1, done1, pending0, failed0**.

`phase` changes only the label. `begin` is called once per job; both engine processes' events enter the same array. Old exit/stage/pending state also survives until overwritten. Moreover every event appends to that array and `render` rescans the entire history, giving quadratic update work and unbounded presenter history for a large selection.

Minimal fix: reset presentation state when a new engine run_start arrives (preserve the visible Cancel/phase), and maintain a small incremental summary instead of storing/reducing the whole stream on each event. Keep the separate pure summarizer only if it has a distinct consumer. Add an independently expected Plan→consent→Run counter sequence, plus a large-event linear-work check if performance is tested. No new event bus or state framework is needed.

### M3-V04 — MINOR: package and shell admission still diverge

Locations: `P/test_pt_release.py::gate`, `shell/src/process/version-gate.ts::evaluateVersionResponse/releaseSegment`. Residual M2-V03; ordinary declared numeric ranges now agree.

Probe used the actual FX-71 response, with Python set to supported `3.14.0` **only in memory** to isolate the mutated field. Ran the real Python gate and transpiled actual TypeScript gate:

| Single mutated field | Package gate | Default shell gate |
|---|---|---|
| `platform = ""` | `[]` (admit) | blocked, reason/field `platform` |
| `pypdfium2 = "5.15.1???"` | `pypdfium2 version is malformed` | enabled |
| Python3.15 / pdfium6 / Pillow14 | blocked | blocked; original M2 range examples repaired |

The package gate checks only platform type; the shell's release-segment parser accepts arbitrary trailing characters. Fable's malformed-Core test exercises neither counterexample.

Minimal fix: specify identical nonempty-platform and full version-syntax rules, allowing the documented release/prerelease forms deliberately, then run the same valid/invalid response table through both consumers. Avoid a new runtime policy service; one small shared data fixture and bounded parsers suffice.

### M3-V05 — MAJOR oracle: release score cannot detect missing parameter cases

Locations: `tools/trace.py::discover_tests/score` (notably lines450/464/470); `required_executions`; `T-GEN-86` positive control. This is independent of the repaired release DAG.

`discover_tests` records a parameterized callable once. `score.passed` only requires receipt count ≥ the number of source callable rows sharing its TID; it does not require the collected parameter nodeids. Thus T-GEN-85 needs only **one** passing receipt to certify its **20** class scenarios. The same issue affects T-CLS-80's 14 mutations, T-CLS-07's 14 codes and other parameter families. `registry.json` is not consumed for this comparison.

Probe executed actual `score` with **in-memory, explicitly synthetic controls**: source registry unchanged; each applicable target's XML had one passing testcase per callable (no parameter suffix); release tests routed to release XML, reference PT-02 to its reference XML, shell callables likewise. `Path.glob`, XML parsing, oracle JSON read and manual-attest results were patched only to supply those controls. No files were written and no real review was invented. Result: **`SCORE 100/100 (automated 93/93, manual 7/7)`**, including **G-02 PASS**, despite 19 missing sweep classes per target. The manual/oracle controls isolate the automated receipt consumer; they are not claimed to be independently valid release evidence.

Minimal fix: compare actual collected per-target test nodeids/parameter identities against actual JUnit cases, accounting for intentional platform/release/reference deselection. Fail omitted, duplicate-substituted, skipped, failed and stale identities. Preserve/merge target-specific registries rather than relying on whichever `registry.json` is last downloaded. Regression: remove only K09 or a single malformed-field parameter from otherwise-complete receipts and require failure; duplicating K01 must not repair it. Required whole jobs being green is useful context, but the advertised missing/not-collected evidence rule needs this explicit oracle.

### M3-H01 — carried OPEN: five active class cells remain N/A-only

These are M2's S4:K05/K06/K08/K09 and S6:K04, not five newly discovered runtime defects. Current sweep actually traverses these stages and asserts downstream fixed counts, but its `reached()`/literal `cells` list only records S7/S9/S10/S12. The original manifest delegates the five cells to other classes. Direct read-only projection returns no execution assertion for any of them.

Minimal fix: extend the existing sweep's per-class reach/registration table, and add selection ID/order/cap and capped-render status/pixel expectations where downstream counts alone are insufficient. Remove superseded delegation declarations. Do not create thirty near-duplicate tests or declare these executed cells N/A again.

### M3-O01 — MINOR oracle residual: class sweep does not establish exact published placement

For successful outputs the sweep asserts `(TRANSCRIPT in text) is (path in egress)` and absence of approval_required; it does not assert each expected OCR unit/Key/block or pending placement appears exactly once. For a multi-unit source, one transcript occurrence can satisfy these publication predicates even if another block is lost or duplicated. Report/event counts are checked independently, but are not compared to parsed Markdown placement counts in this test. Warm stability only preserves whatever first output was produced.

Keep the existing independent assembly goldens and zero-loss tests; extend this same vertical sweep with expected unit IDs and block/pending placement counts, exact status reasons, and the capped PDF's uninspected-page anchor. One corrupted inner archive member with a valid sibling would close M2's remaining K14 Triage suggestion. This is an open strength limit, not evidence that current production assembly loses those units.

### M3-D01 — MINOR docs ↔ code / simplicity: current operational prose is inconsistent

Explicit checks found:

- SPEC §11 GEN-01 hook (`10_SPEC.md:637`) still requires distribution dependencies exactly `{markitdown-gc}`. Current pyproject, PT-01 and amended REQ-GEN-01 require **three** direct dependencies including pdfium/Pillow. Following both oracles is impossible.
- `HANDOFF.md` says engine round2 in progress/446 passed and lists X-14, missing provider doc and S-14/S-15 as pending; actual source, `docs/providers/command.md` and the 507-pass follow-up contradict those statements.
- Matrix class-stage heading says **117 cells**; actual expanded current declarations are **77**. `T-PLN-55`'s TESTPLAN fixture row omits FX-03 although current test includes it. Neither mismatch is caught by current header/string checks.

Minimal fix: update the exact hook, handoff and catalog/comment rows; link the handoff to the existing repair reports rather than multiplying status summaries. Preserve historical audit snapshots as labelled history. Extend focused documentation consistency checks to current normative facts, not old source fragments.

## Every remaining stage/FM N/A cell

All **84** expanded declarations below were rechecked against current stage ownership and consumer code. **VALID** means impossible at that boundary or a bounded equivalence to the named owner; it does not certify a passing execution there. In particular, the S6:FM9 owner still has M3-V02's implementation/oracle defect, and upstream Classify totality still has M3-V01. Those do not create a distinct IO/provider operation in a pure stage, but they prevent claiming full owner closure.

| Cell | Owner | Judgment and boundary checked |
|---|---|---|
| S0:FM2 | S1:FM2 | VALID — protection belongs to source inspection; no startup protected state. |
| S0:FM3 | S1:FM3 | VALID — source/archive bounds; invalid CLI bound is usage, not startup size state. |
| S0:FM4 | S3:FM4 | VALID — per-file format refusal; runtime dependency incompatibility is FM10. |
| S0:FM6 | S10:FM6 | VALID — provider results are per Key; factory errors are configuration. |
| S0:FM8 | S9:FM8 | VALID — approval binds a per-file Plan, not startup. |
| S0:FM11 | S3:FM11 | VALID — coverage/caps are source/unit facts. |
| S1:FM6 | S10:FM6 | VALID — Sniff does not invoke a provider. |
| S1:FM7 | S0:FM7 | VALID — no Sniff durable commit; run cancellation owns cleanup. |
| S1:FM8 | S9:FM8 | VALID — Sniff precedes consent. |
| S1:FM10 | S2:FM10 | VALID — Core vocabulary/schema is consumed by Triage, not magic parsing. PDF parser availability remains a runtime dependency concern. |
| S1:FM11 | S3:FM11 | VALID — no partially accepted OCR inventory in SniffResult. |
| S2:FM3 | S1:FM3 | VALID — mdflow preflight bounds run earlier; Core coverage limits are forwarded to Classify. |
| S2:FM5 | S2:FM1 | VALID — run_triage wraps local inspection errors as E_TRIAGE_FAIL. |
| S2:FM6 | S10:FM6 | VALID — offline Core inspection is not a provider operation. |
| S2:FM7 | S0:FM7 | VALID — read-only inspection; no durable Triage result publication. |
| S2:FM8 | S9:FM8 | VALID — Triage precedes approval. |
| S2:FM11 | S3:FM11 | VALID — forwards coverage unchanged; Classify owns interpretation. |
| S2:FM12 | S0:FM12 | VALID — CT-03 golden regeneration/whole-run determinism; no independent ledger/concurrency state. |
| S3:FM5 | S3:FM1 | VALID — pure classifier has no IO boundary. |
| S3:FM6 | S3:FM1 | VALID — no provider calls. |
| S3:FM7 | S3:FM1 | VALID — no durable effect to partially commit. |
| S3:FM8 | S9:FM8 | VALID — source classification is independent of consent. |
| S4:FM1 | S3:FM1 | VALID — Select's consumed candidate fields are checked before selection; report/action fallback is total for those fields. Upstream V1 totality remains M3-V01; Select does not repair Classify. |
| S4:FM9 | S3:FM1 | VALID — validated IDs and payload digests cross the consumed boundary; full-digest collision behavior now has S4:FM12 coverage. |
| S4:FM10 | S3:FM1 | VALID — candidate vocabulary rejection happens in Classify. |
| S4:FM5 | S3:FM1 | VALID — pure Select performs no IO. |
| S4:FM6 | S3:FM1 | VALID — no provider calls. |
| S4:FM7 | S3:FM1 | VALID — no durable selection side effect. |
| S4:FM8 | S3:FM1 | VALID — runs before approval, does not authorize egress. |
| S5:FM2 | S3:FM2 | VALID — convert_source action guard excludes protected report-only sources. |
| S5:FM4 | S3:FM4 | VALID — same guard excludes unsupported/legacy report-only sources. |
| S5:FM6 | S10:FM6 | VALID — Core conversion is configured offline. |
| S5:FM8 | S10:FM6 | VALID — conversion has no authorization branch; no egress. The reason is correct although this generic owner is not the best label. |
| S5:FM10 | S0:FM10 | VALID — startup dependency policy and installed contracts own Core drift. Actual runtime evidence remains M1-V31/V34. |
| S5:FM11 | S11:FM11 | VALID — placement/unmapped outcomes belong to assembly, not conversion. |
| S6:FM2 | S3:FM2 | VALID — protected candidates now cleared; action guard prevents Render. T-TRI-50 forbids entry. |
| S6:FM6 | S10:FM6 | VALID — local rasterization never calls a provider. |
| S6:FM8 | S10:FM6 | VALID — raster preparation precedes approval; no consent branch. |
| S6:FM7 | S0:FM7 | VALID — raster files are owned temp; run cancellation owns cleanup. Command inherited-pipe repair is S10/M2-V01, now closed by T-TRX-80 and the current deadline probe. |
| S6:FM9 | S6:FM3 | VALID — pixel tripwires plus image-probe failures cover hostile raster paths; T-RND-53 checks ordering, but M3-V02 leaves fractional PDF sizing OPEN at that owner. |
| S7:FM2 | S3:FM2 | VALID — no protected eligible units; T-TRI-50 forbids lookup. |
| S7:FM4 | S3:FM2 | VALID — unsupported report-only units likewise absent; action guard is the operative fact, despite generic protected owner. |
| S7:FM3 | S7:FM1 | VALID — no specified ledger byte cap; per-Key entry validation is the declared contract. This accepts absence of a size requirement, not bounded arbitrary-cache memory. |
| S7:FM6 | S10:FM6 | VALID — lookup is local. |
| S7:FM7 | S10:FM7 | VALID — read-only lookup; ledger publication/replace interruption tested at Transcribe/Ledger. |
| S7:FM8 | S9:FM8 | VALID — a cache hit needs no new consent; remaining misses go to Approve. |
| S7:FM10 | S7:FM1 | VALID — ledger v2 is an invalid-entry/miss case. |
| S7:FM11 | S7:FM1 | VALID — entry is a valid hit or miss; no partially accepted entry state. |
| S8:FM1 | S9:FM8 | VALID — Plan is pure over validated pipeline inputs; no separate runtime failure vocabulary. Purity evidence is T-GEN-04, rather than the generic owner alone. |
| S8:FM5 | S9:FM8 | VALID — no Plan IO. |
| S8:FM6 | S9:FM8 | VALID — constructs public provider metadata, makes no request. |
| S8:FM7 | S9:FM8 | VALID — no durable Plan commit. |
| S8:FM8 | S9:FM8 | VALID — records approval facts; authorization decision belongs to Approve. |
| S9:FM1 | S0:FM1 | VALID — malformed yes/yes-file syntax rejected during CLI parsing. |
| S9:FM2 | S3:FM2 | VALID — protected zero-work Plans have requests_to_send=0, so no consent needed. |
| S9:FM4 | S3:FM2 | VALID — unsupported/legacy zero-work Plans use the same no-request predicate. |
| S9:FM5 | S9:FM8 | VALID — Approve is pure; yes-file IO already belongs to CLI. |
| S9:FM6 | S9:FM8 | VALID — no provider request in predicate. |
| S9:FM7 | S9:FM8 | VALID — no durable approval side effect. |
| S9:FM9 | S8:FM9 | VALID — sensitive-path matches are Plan facts; hash comparison is the approval boundary. |
| S9:FM10 | S9:FM8 | VALID — changed schema/approved bytes invalidate opaque approval hash. |
| S9:FM11 | S9:FM3 | VALID — subset approval is independently asserted as per-file bounded selection. |
| S10:FM1 | S10:FM6 | VALID — raised provider exceptions become per-Key failure; T-TRX-03 and C::T-TRX-08 check continuation. |
| S10:FM2 | S3:FM2 | VALID — protected sources have no jobs. |
| S10:FM11 | S11:FM6 | VALID — retained pending/failed unit placement is asserted in assembly/report; no extra partial-provider result type. |
| S11:FM5 | S12:FM5 | VALID — pure assembly has no IO; output publication is Write. |
| S11:FM7 | S12:FM5 | VALID — no partially committed assembly artifact. |
| S11:FM2 | S3:FM2 | VALID — protected report-only source is not assembled; C::T-ASM-17 confirms no output. |
| S11:FM4 | S3:FM2 | VALID — same report-only action guard excludes legacy/unsupported assembly. |
| S11:FM3 | S10:FM3 | VALID — provider text is bounded before assembly; anchor-count behavior separately covered at FM11. No overall output-byte cap is specified. |
| S11:FM8 | S11:FM6 | VALID — T-ASM-15 independently asserts approval_required and approval_denied marker strings. |
| S11:FM10 | S11:FM0 | VALID — output grammar is release-owned, with exact schema/golden oracles. |
| S12:FM1 | S11:FM9 | VALID — output naming is normalized upstream; actual write failures are FM5. |
| S12:FM2 | S3:FM2 | VALID — protected report-only sources publish no Markdown. |
| S12:FM4 | S3:FM2 | VALID — same action exclusion for unsupported/legacy. |
| S12:FM3 | S10:FM3 | VALID — no separate Write output-size bound is specified; provider truncation is upstream. |
| S12:FM6 | S11:FM6 | VALID — Write receives pending/failure Markdown, no provider state. |
| S12:FM8 | S11:FM6 | VALID — same byte-publication contract after denied/missing approval. |
| S12:FM10 | S11:FM0 | VALID — Write consumes paths/bytes, not a versioned output vocabulary. |
| S12:FM11 | S11:FM11 | VALID — partial placements decided before publication. |
| S13:FM2 | S13:FM10 | VALID as bounded forwarding equivalence — C::T-PLN-12/T-ASM-17 and T-GEN-07 assert protection/report/no-output behavior; code-set owner alone is insufficient. |
| S13:FM4 | S13:FM10 | VALID as bounded forwarding equivalence — T-PLN-53/T-GEN-07 assert report-only refusal; aggregate counter changes have direct cells now. |
| S13:FM7 | S0:FM7 | VALID — run cancellation owns terminal exit130/report; forced kill has no report. No strict blocked-header deadline inferred. |
| S13:FM12 | S0:FM12 | VALID — T-GEN-06 covers warm output/cache preservation and explicit report timestamp exception; complete cold/warm report byte equality is not claimed. |


S6:FM5 is deliberately absent from this table: it is applicable and directly registered by T-RND-80. Current stage/FM declarations fell from 85 to 84 solely by removing that invalid alias. Generic owners such as S5:FM8→S10:FM6 are accepted only for the stated no-egress equivalence, not as evidence of an executed consent test inside Convert. Report FM2/FM4 remain bounded forwarding equivalences supported by real report-only/no-output cases; pure-stage declarations do not hide their downstream IO owners.

## Explicit score checks

Each dimension is five checks worth 20 points each. Partial credit measures the reviewed closure/strength of that check, not an estimated percentage of hidden bugs. An open finding caps its affected check below 20; a dimension may reach 100 only when it has no open finding. Release prerequisites remain binary regardless of these audit scores.

| Dimension | Check 1 /20 | Check 2 /20 | Check 3 /20 | Check 4 /20 | Check 5 /20 | Score |
|---|---|---|---|---|---|---|
| Vertical closure | S0–S4 malformed input/selection: **12** (M3-V01, five M2 class cells) | S5–S7 preparation/cache: **17** (fractional pixel cap, M3-V02) | S8–S10 approval/send/lifecycle: **19** (core repairs strong; full gate parity residual) | S11–S13 publish/report/UI consumption: **18** (M3-V03; exact sweep publication oracle remains bounded) | Installed/release closure: **14** (M1-V31/V34, X-11 and M3-V05) | **80/100** |
| Oracle strength | Independent expected data/values: **16** (progress self-derived expectations; sweep placement predicates) | Real composed boundaries: **18** (actual HWP, class sweep; corrupted inner archive still absent) | Negative/boundary controls: **16** (unhashable enum, fractional pixels, gate parity missed) | Complete executed-case inventory: **10** (M3-V05 accepts missing parameters) | Honest evidence scope/fixtures: **16** (507/255 and unsupported-host limits explicit; real release prerequisites absent) | **76/100** |
| Docs ↔ code | Engine normative shapes/hooks: **17** (V1 promise and stale GEN-01 hook) | Shell behavior promises: **16** (progress counts, M3-V03) | Package/shell runtime policy: **16** (M3-V04, actual target receipts missing) | Fixture/trace/catalog claims: **16** (X-11, five N/A-only cells, stale fixture/count rows) | Operational status and ownership: **17** (HANDOFF stale despite current repair reports) | **82/100** |
| Simplicity | Canonical atomic/hash/format helpers: **20** (M1-V36 fixed) | Dead shell surface/oracles removed: **20** (S-01–S-12 substantive deletions/consumers verified) | Retained optional designs justified: **20** (base cache, direct wheel/reference, env-only credentials) | Minimal bounded progress state: **12** (whole history plus quadratic rescans and phase leak, M3-V03) | Single current documentation/accounting source: **16** (S-13/M3-D01; strengthen existing sweep rather than duplicate per-cell tests) | **88/100** |

No source repair is requested or performed by this audit. Before vertical closure can be claimed, resolve M3-V01/V02 and the five carried class registrations; before release evidence can certify it, resolve M3-V05 and supply the supported-host/reference/target/manual receipts. M3-V03/V04, M3-O01 and M3-D01 keep their affected dimensions below 100 even after those larger gates are repaired.
