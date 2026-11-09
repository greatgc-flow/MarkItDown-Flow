# M2 recursive MECE audit — cx vertical and oracles

Fix-round follow-up: [M2_ENGINE_FIXES.md](M2_ENGINE_FIXES.md) records the DRAFT-3.4 repairs, per-finding red logs and final verification. Findings and scores below are the original pre-fix audit snapshot; actual cross-platform/reference release evidence remains a separate gate.

Date: 2026-11-09. Authority: current SPEC DRAFT-3.3, amended packaging requirements, TESTPLAN, and M1-V01–V37 in `M1_cx_vertical.md`. Scope: engine stages S0–S13, every current `stage_fm` declaration, fix-round oracles, class-closure/R28 tests, and R27 packaging integration. The M1 document also contains V38; it is checked separately below so that it is not silently lost.

**Verdict: substantial repair, incomplete closure; release remains blocked.** Of V01–V37, **27 CLOSED / 10 OPEN**. There are now **85 stage/FM N/A cells**, rather than 108; **84 accepted as bounded equivalences / 1 invalid boundary claim**. Registration has no matrix errors, but does not establish executed behavior. Newly identified problems include command-capture timeout cleanup, an impossible packaged-import assertion, incompatible package/shell admission rules, a circular release-evidence pipeline, and HWP payload-policy loss during deduplication.

Only this document was written. No code edits, git commands, installations, builds, pytest/Jest runs, release operations, or external communications were performed. Read-only Python probes used `python -B -`, in-memory fixtures/mocks, and a short child/descendant process pair; they created no audit files. The supplied engine **446 passed**, shell **230 Jest**, and trace **0 errors** are baselines, not new audit results. Existing `build/trace/junit-r27-r28-local.xml` contains 458 cases: 446 passing, 12 skipped, zero failures/errors; packaging notes also record one platform deselection. These are local evidence, not six required target receipts or a reference install. The old separate local XML is not substituted for the current baseline.

## Closure rules and source keys

CLOSED means the original defect is repaired in source or explicitly resolved by an applicable normative amendment, with an identified regression oracle. It does not certify unexecuted platforms or a release. OPEN includes a materially incomplete oracle, remaining contradiction, or repair regression. Advisory simplification proposals may close by an explicit, defensible retained design; deleting every optional feature is not a correctness requirement.

Paths below are repository-relative. Abbreviations: **M** = `engine/tests/stage_io/step7/test_m1_engine.py`; **C** = `engine/tests/stage_io/test_class_closure.py`; **U** = `engine/tests/unit/`; **P** = `engine/tests/packaging/`. Code references name the consumer boundary, not just the added test. All OPEN entries include severity and a concrete fix. M2 numbers denote newly identified findings in the current fix/R27 integration; without git/history, historical introduction is not independently certified for inherited workflow structure.

## V01–V37 verification

| M1 ID | Verdict | Test identity and code verification; remaining work where open |
|---|---|---|
| V01 | **CLOSED** | `T-META-50`, `T-TRX-57`, `T-WRT-51`, `T-PLN-53/54`, `T-RPT-52–56`. Applicable S10/S12 nominal, S13 failure/bound/provider/consent/partial, and S8 report-only cases are registered directly. `matrix.toml` no longer declares those cells N/A; `orchestrate._Pipeline.process/summarize/publish_output` implements their observable behavior. Report wrappers execute the existing counter oracle, not empty marker tests. |
| V02 | **CLOSED** | `T-SNF-50`, `T-GEN-53`, `T-CNV-52/53`, `T-TRX-54`, `T-RPT-51` directly cover discovery/run-temp, conversion-temp, interrupted durable base-cache publication, raster read, and report-copy boundaries. Code: `sniff_io.discover`, `orchestrate.run/process`, `convert._store_cache`, `transcribe.run_transcribe`, `cli.main`. The original misdelegated S0/S5/S10/S13 declarations were removed. Optional base-cache write failure remains deliberately best-effort; interruption leaves unpublished temps that reruns ignore. A separate Render-setup alias defect is M2-V05. |
| V03 | **CLOSED** | `T-CLS-50`, `T-LKP-50`, `T-ASM-50`, `T-TRX-53/54/56`, `T-TRI-50`. Code: `classify._well_typed`, `ledger.validate_entry/lookup`, and actual `transcribe.run_transcribe -> approve.verify_raster`. S3:FM9, S7:FM9, S10:FM4/5/8, S11:FM1 are no longer hidden as N/A. Consumed malformed fields and missing provenance cannot reach the previously crashing consumers. Broader unconsumed V1 type promises remain V22. |
| V04 | **OPEN — MAJOR** | `T-META-51/53`, `T-PLN-55`, `T-ASM-51` repair blanket S8/S11 class credit in `trace.test_classes`. However, `T-RND-51` manually constructs an HWP unit and extracted file; `T-CNV-03` only checks HWP extraction arguments. No test runs an HWP5 extraction result through Select, Convert, media assignment, and Render together. `matrix.toml` still aliases S6:K09 to S6:K07, while the SPEC M1 disposition claims direct integration. **Fix:** add one actual HWP extracted/stored-stream preparation-to-Render case, with pixels/status, Key/request count, and retained placement oracles; keep common schema claims bounded. |
| V05 | **OPEN — MINOR** | `T-META-52` correctly protects against the old “passing test”/“stub” wording. Yet `matrix.toml:14–16` still says `fx("all")` expands every fixture and specifically credits S8/S11 with all 20 classes; R28 `trace.test_classes` returns zero there. The S7 class alias for K20 still names S1:K14. **Fix:** replace the obsolete expansion paragraph and correct the directory owner; extend the documentation check to the actual R28 policy. Registration/execution flags themselves are honest. |
| V06 | **CLOSED** | `T-SNF-50/53` asserts explicit hidden/link/excluded roots, duplicate descent, unreadable directory failure, and `.` handling. `sniff_io._is_link` now checks lstat reparse attributes; `discover` filters/deduplicates before `_walk`; unreadable directories become observable source errors rather than empty successful runs. |
| V07 | **CLOSED** | `T-SNF-51/54`: replace a normal source or container after Sniff; assert E_SNIFF_IO, no Core conversion, no output/changed inventory. `orchestrate._source_bytes` bounds and compares length/full digest; native Triage and Convert receive the same verified owned snapshot; container expansion receives verified bytes. |
| V08 | **CLOSED** | `T-CNV-50`, `T-RND-50`, `T-CTR-50/51`, plus existing actual-byte archive tests. `_media_hashes` propagates bound errors and decrements its pass budget; `_render_media` receives configured byte/remaining limits for extracted files and fallback. `sniff_io._Expansion.expand` charges nested package inventory; `expand_container` retains discovered members and marks them report-only after later failure. DRAFT-3.3 explicitly bounds preparation passes; repeated verification is not charged as a second logical archive inventory. |
| V09 | **CLOSED** | `T-WRT-50[edited=False/True]` detects reads before containment and checks outside bytes stay intact. `orchestrate.publish_output` invokes `write._checked_target` before `is_file/read_text`, and Write revalidates publication. |
| V10 | **CLOSED** | `T-WRT-51` deletes published media, reruns, verifies exact restoration and unchanged Markdown mtime. `publish_output` now calls `write.publish_source(..., md_bytes=None, media=...)` even when Markdown replacement is skipped; a failed media result removes completed-output reporting. |
| V11 | **CLOSED** | `T-LKP-50` mutates/misses `created`; `T-ASM-50` observes only valid timezone-bearing values entering assembly. `ledger.validate_entry` now requires parseable offset-bearing, second-precision provenance; `assemble._block` can consume it. REQ-LKP-04 was amended accordingly. |
| V12 | **CLOSED** | `T-RPT-50` sends multibyte long `file` and nested `outputs`, checks serialized UTF-8 plus newline <=65536, valid JSON, identity/counters, and input immutability. `report.emit_progress` recursively reduces nested informational strings/lists; full reports and Plans are untouched. The test is a progress-stage oracle, not evidence that arbitrarily long OS filenames are constructible. |
| V13 | **CLOSED** | `T-RPT-51[empty=False/True]` asserts process/report/last-event exit 2, one terminal event, and emitted error. `orchestrate.run` can defer run_end; `cli.main` finalizes copy failure, adds file/run issues, recomputes exit, then emits the authoritative terminal event and stdout report. |
| V14 | **OPEN — MAJOR** | `T-TRX-50` proves rejection of continuously noisy stdout before a three-second timeout; `command._capture` uses a bounded queue and memory cap, and `transcribe` roots scratch under the job raster directory. **New cleanup regression M2-V01:** closing the buffered pipe can block behind the reader thread when a descendant retains stdout. **Fix:** make reader shutdown interruptible and bounded; test inherited pipe handles, timeout/cancellation, owned direct-child reaping, and scratch cleanup. |
| V15 | **CLOSED by amendment, bounded evidence** | `T-TRX-51` checks monotonic body-read expiry using a simulated drip. `openai_compat._post_once` uses `read1`, elapsed checks, and refreshed socket timeouts. REQ-GEN-09 expressly withdraws the strict DNS/TLS/header/Windows end-to-end cancellation deadline. This closes the original false guarantee; it is not a real Windows blocked-HTTP rehearsal or proof that every internal urllib operation is interruptible. |
| V16 | **CLOSED** | `T-CLI-50` rejects abbreviations and command flags on `none`; `T-PLN-50` checks none-provider cost override. `cli._parser/_options` validates exact/provider-specific syntax; `providers.build_provider` preserves the none override. Existing cost/command Plan tests cover downstream fields. |
| V17 | **CLOSED** | `T-TRX-52`: invented code becomes E_PROVIDER_OUTPUT, a secret straddling the old truncation boundary becomes `***`, later Key succeeds. `transcribe._normalise` restricts the four provider codes and calls `report.diagnostics`; `redact.redact` replaces secrets before the 500-character cap and before publication. |
| V18 | **CLOSED** | `T-SEC-50` rejects credentialed proxy configuration without exposing the dummy password. `providers._proxy` rejects userinfo before `orchestrate.run` can copy the public proxy into `plan.plan`. This is the supported factory/startup boundary; no credential-bearing approval object is created. |
| V19 | **OPEN — MAJOR** | `T-RND-51[stored=True/False]` strongly proves refusal when the manually supplied unit has the correct stored-stream kind. But `select.select` stores `_payload_kind` only on initial group creation and can later replace the representative source_id without replacing that evidence. Equal-digest parser payload/stored-stream candidates merge, and the resulting stored-stream representative can reach `render._render_media` carrying the parser kind. Probe P9 renders it successfully. **Fix:** preserve payload refusal semantics across grouping/representative selection; partition supported and unsupported HWP payload groups and test both candidate orders plus placement/zero-egress behavior (M2-V06). |
| V20 | **CLOSED** | `T-SEL-50` forces equal h12/different full hashes and gets two unmerged units. `T-CNV-54` forces that collision through orchestration and requires E_OUTPUT_COLLISION before Core/provider/output. `select.media_digest` groups by full SHA; `_Pipeline._media_hashes` rejects ambiguous display filenames. Mapping prose now distinguishes full identity from display prefix. |
| V21 | **CLOSED** | `T-SNF-52` keeps a valid literal `/Encrypt` PDF native and reports a broken HWP FileHeader as corrupt. `sniff_io._check_pdf` consults the parser security handler instead of substring scanning; `_analyze` marks missing/truncated HWP structure. REQ-SNF-07 now lists parser opening. |
| V22 | **OPEN — MINOR residual** | `T-CLS-50/51`, `T-SEL-51` repair the consumed nested containers, G1 encryption guard, and convert-only scheduling. But `_well_typed` only requires the `dpi_tag` key; strings/dicts pass. The documented V1 still promises the types of §3.0, including inventory fields. Probe: FX-09 with `rasters[0].dpi_tag={}` remains convert_and_ocr with no warning. **Fix:** validate the remaining promised nested types (including optional/null forms), or explicitly narrow V1 to consumed fields and retain the raw inventory as unvalidated evidence. Do not claim complete V1 closure from four container mutations. |
| V23 | **CLOSED** | `T-PLN-51` protects approved.oversize/prepared-snapshot wording; `plan.plan` and SPEC §§0,4,7.1/8.4 agree on actual order, prepared status/hash dependence, and the public command-template path exception. Existing Plan schema/hash tests establish the behavior that this text-only regression cannot. |
| V24 | **CLOSED** | `T-TRX-53` tampers immediately before the real Transcribe stage and asserts zero calls/no successful ledger, exit 3, approval_denied output. `C::T-TRX-08` additionally proves an unchanged Key proceeds while a replaced raster is refused. The production `run_transcribe` invokes `approve.verify_raster`, not an unused helper. |
| V25 | **CLOSED** | `T-RND-52` weakly references distinct raster objects and checks the previous one is dead before the next render. `render.render_units` stores then `del payload`; earlier temp/cleanup tests cover owned artifact lifetime. This establishes mdflow's encoded-raster retention contract, not decoder working-memory bounds. |
| V26 | **CLOSED** | `T-RND-53` instruments actual PdfPage.render and ImageFile.load, with over-limit negative and allowed positive controls. `_render_pdf_page/_render_raster_frame` check dimensions before those expensive calls. |
| V27 | **CLOSED** | `T-RND-54` compares decoded output pixels with frame 0 and proves inequality to frame 1. `_render_media` starts at the first frame; earlier `T-RND-07` supplies the exact warning oracle. |
| V28 | **CLOSED** | `T-WRT-52` runs two real colliding roots through `flow.run`, checks second report-only/error, exact first Core bytes, and one output. `discover` and `_Pipeline.discover` propagate collision results before conversion, the latter using `assemble.output_path` normalization. The new case is strong for ordinary collision propagation; reserved-name collision variation remains useful additional coverage. |
| V29 | **CLOSED** | `T-LKP-51` fails actual unit-ledger replaces, checks two provider calls, both OCR-delimited outputs, E_CACHE_IO, and exit 2. `_Pipeline.publish` keeps in-run entries before `Ledger.write`; `T-LKP-03` separately asserts atomic old/new storage. This replaces the old dict-immutability-only claim. |
| V30 | **OPEN — MINOR** | `T-PLN-52` calls production planning, but varies only dpi, threshold, sensitivity and oversize; its `prompt_version='p1'` is the baseline, combined with max_units=0. `U/test_core_select_plan.py::T-PLN-02` still mutates detached expected dictionaries. Other tests cover some provider inputs, not a complete independent binding table. **Fix:** independently change each approved input family through production Plan, checking its exact field and independently canonical hash, including proxy, prompt, file identity, raster/status, destination and cost; separately vary cache/other-file state. |
| V31 | **OPEN — MAJOR** | `T-GEN-50` checks two SPEC strings, not runtime behavior. CI declares six endpoints/nine smokes, but no corresponding executed receipts are present in the inspected evidence. `pyproject.toml` source-path injection also prevents full source pytest from proving installed-wheel execution (M2-V04). **Fix:** execute the advertised jobs, preserve resolved installs and import identities, and make required behavior suites actually use the installed wheel. Keep source lint labelled as lint. |
| V32 | **CLOSED as an oracle repair** | `P::T-GEN-52` exercises the same full-closure helper using three real local wheels; `PT-02` invokes it on the real reference lock. `assert_full_lock_rejects_dependency_mutations` checks untouched install, missing transitive pin/hash, and tampered dependency with hash mode/no index. `tools/build_engine.reference` separately runs fresh pip check/version/selftest. `T-GEN-51` alone is only a name-presence check; real release execution remains V34, not a fabricated PT-02 pass. |
| V33 | **OPEN — MINOR** | `T-CLS-52` adds exact signatures/code sets for three fallback mutations. `T-CLS-07` still allows unsupported_media without an exact warning/status oracle and mostly checks action for several codes. `C::T-TRX-09` strongly checks actual EMF refusal, but does not connect a Core unsupported_media issue to its prescribed prepared-unit outcome. **Fix:** complete an independently expected row/code signature table and one issue-to-preparation/Render case with W_MEDIA_FORMAT, retained placement, and zero egress. |
| V34 | **OPEN — BLOCKER** | The old candidate universal lock/inventory refusal is removed by R27. `T-GEN-54` proves local deterministic wheel construction/integrity, not a real reference dependency closure. `tools/build_engine.reference` expresses the new correct target-specific install contract, but no successful reference or six-target execution receipts are supplied. M2-V02/V04 additionally make current gates unsatisfiable. **Fix:** repair those concrete gates, then generate and pass real reference hash install/pip check and required compatibility evidence; retain pending release status until then. |
| V35 | **CLOSED as a design change** | `T-GEN-54`, `PT-07`, and `T-META-54`; `build_engine.build/reference` plus amended PKG-01/02/04/05/06/08/13/14 implement direct wheel, one target-labelled pip-tools reference, ordinary compatibility installs and shared subjects. Universal lock merger/public artifact catalog are gone. Real target checks remain required; this closure does not waive V34. |
| V36 | **OPEN — MINOR** | Shared ASSETS/SUBJECTS now remove a major release-list duplication (`T-GEN-54`, `build_engine`, consumers). But `Ledger.write` and `write.atomic_write` still independently implement exclusive temp/fsync/replace; `ledger.key_id` shadows its imported name; pure Sniff still differs from IO Sniff for unrecognized `.pdf` bytes. **Fix:** unify the small atomic/hash helpers and use one pure format-routing decision from IO; retain tools only for distinct users. No new framework is needed. |
| V37 | **CLOSED by explicit retained design plus repair** | `T-CNV-51`, existing `T-CNV-04`, and SPEC disposition deliberately retain the optional tested base cache. `T-TRX-55` uses a read-only `_post_once` property to prove counting no longer monkey-patches it; `_MeasuredProvider` observes explicit `requests_sent`, which HTTP increments per wire attempt. The cache-deletion proposal was advisory; remaining duplication is V36. |

The ten OPEN items are **V04, V05, V14, V19, V22, V30, V31, V33, V34, V36**. No M1 item was closed merely because a test name contains its ID.

Supplemental **V38 CLOSED**: `T-CLS-53`, `T-TRI-50`, `T-PLN-54` and `T-SEL-51` establish that Core-discovered protection/report-only and convert-only classifications cannot schedule OCR. `classify.finish` clears report-only candidates; Select checks action; orchestration gates Render. `T-TRI-50` makes Render/Lookup fail if reached, and checks no Core conversion/provider/output. Protected zero-work Plans remain observable, so the former S8:FM2 N/A was removed too.

## Newly identified fix/R27 integration defects

### M2-V01 — MAJOR: bounded command capture can block during timeout cleanup

Location: `engine/src/mdflow/providers/command.py:97,138–146`; fix-round `T-TRX-50` at M:255. The drain thread blocks in buffered `child.stdout.read1`. On timeout/cancel, the main thread kills/reaps the direct child, then calls `child.stdout.close()` **before** its bounded reader join. A descendant inheriting stdout can keep the pipe open; close waits for the reader's buffer lock. The stopped event cannot interrupt that read. Thus the new bounded-capture implementation reintroduces an unbounded completion/cleanup path even when the direct child has exited.

Read-only probe on this Windows host: `_capture([python, '-B', '-c', <spawn descendant sleeping 1.5s; exit>], started)` with `timeout_s=.15` returned E_PROVIDER_TIMEOUT after **1.57 s**, not near .15 s. The descendant was short-lived and finished; no process was left running. An indefinitely retained handle can prolong the same wait indefinitely. This probes `_capture` directly, so it isolates the timeout mechanism without creating raster/scratch files.

**Fix:** use an interruptible pipe-reading strategy and a bounded reader shutdown that never synchronously closes a buffered object while another thread owns a blocking read. Define treatment of inherited child handles/process groups explicitly. Regression: silent descendant retaining stdout, short deadline, cancellation, direct-child reaping, no surviving owned reader, and owned scratch removal; retain the noisy-output cap test as a separate positive case.

### M2-V02 — BLOCKER: packaged import isolation assertion contradicts its fixture

Location: `P/conftest.py:48,112`, `engine/tests/fixtures/gen_core.py::WorkspaceTemps`, `P/test_pt_release.py:162`; R27 `PT-01`.

`pt_temps` is rooted at `REPO/build/trace/redgreen/pt-tmp`; WorkspaceTemps explicitly requires every generated path to remain under the repository. `packaged_venv` creates its site-packages there. PT-01 then requires the import both to belong to that venv **and not to be relative to REPO**. A correctly isolated import from that fixture cannot satisfy both. A path-only probe prints `(venv containment=True, not-relative-to-REPO=False)`. The 446-pass baseline skips PT-01 because real release assets are absent; supplying the bundle exposes the contradiction on every required OS.

**Fix:** keep the sandbox-compatible test venv location and reject imports from `engine/src`/other source package roots while requiring the selected venv's site-packages; alternatively provide a genuinely external permitted test temp root. Test the assertion with both an installed-package location and `engine/src/mdflow/__init__.py`. The package root's actual import location is the oracle; repository ancestry alone is not.

### M2-V03 — MAJOR: package and shell disagree on R27 compatibility admission

Location: `P/test_pt_release.py::gate` (about lines 280–306), `shell/src/process/version-gate.ts:59–70,153`, REQ-PKG-06, REQ-SHL-17, and `engine/pyproject.toml`.

The amended package oracle accepts Python `<3.16` and any syntactically valid renderer/Pillow version. The shipping shell blocks Python >=3.15, pypdfium2 outside `[5,6)`, and Pillow outside `[11,14)`. A probe with `{python:'3.15.0', pypdfium2:'6.0.0', pillow:'14.0.0', ...valid protocol/Core...}` returns **`gate(...) == []`**, while shell source rejects it on all three dimensions. Even the simple Python 3.15 difference is observable under the declared experimental matrix. R27's ordinary install policy does not impose the shell's renderer upper bounds; package success therefore cannot certify shell admission. This is not a claim that versions in the counterexample were installed or released.

**Fix:** state one runtime admission policy. Keep 3.15 experimental-only everywhere. Either enforce documented renderer/Pillow constraints through package metadata/install instructions and matching package oracles, or follow the amended Core-policy/pip-check/selftest rule in the shell. Share counterexample fixtures across both gates and require identical verdicts. Update the still “release-locked” REQ-SHL-17 prose.

### M2-V04 — BLOCKER: R27 release evidence has no acyclic route to a passing freeze

Location: `.github/workflows/ci.yml` source/packaged test steps; `.github/workflows/release.yml::freeze/attest`; `tools/release_gate.py:29–31,48`; `tools/trace.py:392–418`; `P/test_pt_release.py::PT-13/PT-17`; `90_ACCEPTANCE.md::G-15`.

The exact dependency chain is:

1. Source pytest runs without MDFLOW_RELEASE_BUNDLE/MDFLOW_ATTEST_DIR, so release/human cases remain skips.
2. The explicit packaged rerun selects only PT-01/05/06/08/14. PT-04/13/15/17 and the release evidence cases do not acquire actual success receipts there. Named evidence is downloaded only later in freeze; pytest is not rerun then.
3. `trace.score` requires G-15's PT-04/13/14/15/17 passes on the required cells; `release_gate` requires SCORE 100 **before** modifying candidate acceptance and before the subsequent attest job.
4. PT-13 requires the bundles created by that later attest job. PT-17 requires the candidate already to contain SCORE 100, cleared blockers, and retained rollback evidence that release_gate sets only after score passes.

Therefore adding honest named files or passing the reference job cannot make this graph green. The new `T-META-54` correctly isolates PT-02 evidence but exercises none of this real workflow ordering. This is a newly identified defect in the current R27-integrated release route; no claim is made that every edge originated in R27 rather than pre-existing tooling.

There is also an independent evidence-scope defect: `engine/pyproject.toml` specifies `pythonpath=['src']`; required `python -I -m pytest engine/tests` still applies that pytest option. `engine/tests/unit/conftest.py::core_api` additionally loads `engine/src/mdflow` directly, and `engine/tests/conftest.py::cli_command` explicitly inserts that source directory in child launchers. Installing the wheel first does not change those import boundaries. `-I` only isolates Python startup paths. Only selected packaged CLI tests prove installed execution. This leaves V31's required runtime behavior claim unresolved.

**Fix:** make the existing sequence acyclic: candidate build/compatibility evidence; immutable-subject attestation and named evidence validation; actual post-attestation packaging verification; final score/publication. Make PT-17 validate independent candidate identity/job facts without demanding its own already-computed score as an input to that score. Supply the release bundle/reviews to the jobs that execute their tests and archive those actual receipts. Run the required behavior suite with pytest and fixture/launcher source injection disabled and assert the package import comes from the installed environment. Do not turn skips into success or weaken the subject-byte checks.

### M2-V05 — MAJOR: Render's remaining FM5 N/A misses setup IO

Location: `matrix.toml::S6:FM5`, `engine/src/mdflow/render.py:220`, `orchestrate.run` per-source OSError handler. This is newly identified during the remaining-N/A review, not asserted to be a newly introduced line.

The alias says temp IO always yields E_RENDER_FAIL through the unit-failure path. But `temp.mkdir(parents=True, exist_ok=True)` runs before the Render try/loop. A patched mkdir raising PermissionError escapes `render_units` with **no RenderResult**. The orchestrator maps it to E_OUTPUT_IO and abandons assembly for that source; the claimed owner S6:FM1 does not assert this path. Unit `_store` failures are caught; setup and unit-storage failures are different boundaries.

**Fix:** give Render setup failure the prescribed per-unit E_RENDER_FAIL/result semantics, or explicitly assign setup ownership and document/test the different whole-source outcome. Add a direct setup failure and a pipeline sibling-continuation oracle before accepting this cell as an alias. Merely retagging an ordinary render failure will not fix it.

### M2-V06 — MAJOR: HWP deduplication loses the representative's payload policy

Location: `engine/src/mdflow/select.py::select` group merge/representative replacement and initial `_payload_kind` assignment; `render._render_media` HWP guard. This crosses the two fix-round changes: full-digest grouping and newly carried HWP payload facts.

Start with the FX-24 golden and mutate two valid media/candidate records to have the same full digest of decodable PNG bytes: first `BinData/B.png` with `parser_image_payload`, then `BinData/A.png` with `stored_ole_stream`. Classify accepts the envelope. Select returns one unit with **source_id A, also [B], _payload_kind parser_image_payload**: merge sorts/replaces the representative but retains the old representative's kind. Supplying the extracted PNG through an in-memory mocked file read makes `_render_media` return **image/png and exactly those bytes**, instead of unconditional stored-stream refusal. The HWP guard consults the wrong evidence. Reversing the input order can instead make the supported payload inherit refusal. The issue is policy loss, not a SHA collision.

`T-RND-51` bypasses grouping by manually assigning the correct kind. `T-SEL-50` tests digest grouping without mixed HWP payload kinds. Both can pass while their composition is wrong, substantiating V04's missing vertical integration as well as reopening V19.

**Fix:** classify stored/unsupported payloads before renderable-content deduplication, partition HWP groups by refusal semantics, and keep representative-specific evidence synchronized. If the one-unit-for-identical-bytes rule needs a narrow unsupported-payload exception, amend it explicitly rather than silently allowing stored-stream OCR. Assert both candidate orders yield the same policy, stored placements remain unsupported with W_MEDIA_FORMAT/no stored-stream request, and the parser image can still complete normally. No ZIP fallback is needed.

## Every current stage/FM N/A cell

Each row judges one expanded cell, in manifest order. **VALID** permits a bounded earlier-stage/common-handler equivalence under the manifest's “not separately testable” rule; it does not mean that a scenario was executed at that stage. Owners are copied exactly, including generic owners that could be more precise. The current pass removed 23 declarations overall; the old invalid families now have direct registrations. `trace.matrix_problems(ROOT, discover_tests(ROOT))` returned `[]` in a read-only probe, independently of writing trace outputs.

| Cell | Declared owner | Judgment and explicit boundary check |
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
| S4:FM1 | S3:FM1 | VALID — Select's consumed candidate fields are checked before selection; report/action fallback is total for those fields. This does not waive V22's unconsumed inventory types. |
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
| S5:FM10 | S0:FM10 | VALID — startup dependency policy and installed contracts own Core drift. Actual runtime evidence remains V31/V34. |
| S5:FM11 | S11:FM11 | VALID — placement/unmapped outcomes belong to assembly, not conversion. |
| S6:FM2 | S3:FM2 | VALID — protected candidates now cleared; action guard prevents Render. T-TRI-50 forbids entry. |
| S6:FM5 | S6:FM1 | **INVALID — M2-V05:** setup mkdir escapes before the unit handler; not all IO failures become the claimed E_RENDER_FAIL result. |
| S6:FM6 | S10:FM6 | VALID — local rasterization never calls a provider. |
| S6:FM8 | S10:FM6 | VALID — raster preparation precedes approval; no consent branch. |
| S6:FM7 | S0:FM7 | VALID — raster files are owned temp; run cancellation owns cleanup. Command reader deadlock is S10/M2-V01. |
| S6:FM9 | S6:FM3 | VALID — pixel tripwires plus image-probe failures cover hostile raster paths; T-RND-53 checks ordering. |
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

Counts by stage: **S0 6; S1 5; S2 7; S3 4; S4 7; S5 6; S6 6; S7 8; S8 5; S9 9; S10 3; S11 7; S12 8; S13 4 = 85**. The sole invalid declaration is S6:FM5. The remaining **110 class/stage N/A declarations** were not substituted for this vertical ledger; the material HWP exception is explicitly retained under V04. Earlier all-class inflation is restricted in both R28 projections, but a restricted marker remains registration evidence, not runtime proof.

## Oracle-strength sample: newly added tests

This is a source-level adversarial oracle review, not another test run. **STRONG** means a plausible regression changes an independently expected observable assertion. **BOUNDED** is useful for its stated stage/controlled boundary but cannot support a wider claim. **WEAK** means the assertion does not establish its advertised closure. Parameter rows are not counted as separate new test identities merely to reach the sample minimum.

| New test identity / location | Assessment | What it can detect; limit or stronger fix |
|---|---|---|
| T-SNF-50 / M:42 | STRONG | Root/exclusion/dedup/readability results and exit/output behavior. Its lstat reparse implementation is also inspected; this is not a real pre-3.12 Windows junction rehearsal. |
| T-SNF-51 / M:74 | STRONG | Replacing source bytes after authoritative sniff cannot reach Core or stale cache identity. T-SNF-54 extends this to containers. |
| T-CNV-50 / M:92 | BOUNDED | Injected ZipReadError must stop later Core/output. It establishes propagation, not the inflater detecting actual lying bytes; existing archive tests supply that independent premise. |
| T-CTR-50 / M:118 | STRONG | Actual nested package inventory exhausts the configured cumulative cap and retains exact already-discovered members. |
| T-WRT-50 / M:131 | STRONG | A read spy catches the original early-read containment bug for identical and edited linked outputs; outside bytes must stay intact. |
| T-WRT-51 / M:172 | STRONG | Exact repaired media bytes plus unchanged Markdown mtime catch the skipped-publication regression. Add a media-copy failure variation to extend completion reporting evidence. |
| T-LKP-50 / M:191 | STRONG | Real warm cache provenance corruption becomes a miss and actual provider retry, not just validate_entry=False. Does not test every possible timestamp spelling. |
| T-RPT-50 / M:211 | STRONG | Independent encoded line length, JSON decode, identity/counter preservation, original event unchanged. Does not prove an entire CLI run with an OS-impossible filename. |
| T-RPT-51 / M:226 | STRONG | Real CLI process agrees with authoritative report and unique terminal event on both empty/nonempty copy failure. Mixed provider/approval precedence remains a useful extra variation. |
| T-TRX-50 / M:255 | BOUNDED | Actual infinitely noisy child is rejected promptly; proves live cap enforcement, but no inherited-handle, reader-liveness or scratch-root oracle. M2-V01 survives it. |
| T-TRX-51 / M:270 | BOUNDED | Independent synthetic clock catches missing elapsed-body checks. Fake read1/socket-free response does not prove real HTTP/socket/cancellation deadlines. |
| T-TRX-52 / M:311 | STRONG | Exact normalized code, boundary redaction bytes and later-Key success distinguish the two original defects. |
| T-RND-51 / M:344 | BOUNDED | Stored/missing HWP refusal and no ZIP fallback are direct, good stage oracles. Manually supplied units/media bypass the grouping composition defect M2-V06 and do not verify HWP extraction-to-Render wiring (V04/V19). |
| T-CNV-54 / M:867 | STRONG | Forced equal-prefix/different-full-digest media must fail before Core, provider or output. Complements T-SEL-50's independent grouping oracle. |
| T-TRX-53 / M:424 | STRONG | Tamper at real send stage; exact denied marker, no calls/ledger, exit3. C::T-TRX-08 supplies an unchanged sibling positive control. |
| T-RND-52 / M:444 | STRONG | Live object ownership fails if a prior encoded raster remains referenced when the next is produced. Carefully bounded to owned raster bytes. |
| T-RND-53 / M:464 | STRONG | Decoder tripwires plus positive controls make ordering falsifiable for both PDF and image paths. |
| T-RND-54 / M:498 | STRONG | Distinct decoded frame pixels remove the old dimension-only ambiguity. |
| T-LKP-51 / M:529 | STRONG | Actual ledger replace faults retain OCR output and sibling completion with error exit; original immutability-only test did not. |
| T-PLN-52 / M:550 | WEAK for full V30 closure | Real planning improves the old test, but four changes and one unchanged prompt do not establish every approved-input binding or exact changed field. See V30 fix. |
| T-GEN-50 / M:613 | WEAK for V31 closure | Two normative strings prove a disclosure exists, not runtime support. Keep as documentation lint; require CI execution evidence. |
| T-GEN-51 / M:622 | WEAK alone | Helper-name/call-name substring checks can pass with a broken helper. The actual offline T-GEN-52 and PT-02 invocation are the meaningful replacements. |
| T-CNV-53 / M:691 | STRONG | Interrupt actual base-cache replace, require unpublished temp/no Markdown, rerun makes a second Core call and publishes. Simulated BaseException deliberately represents crash uncertainty. |
| T-CNV-06 / C:114 | STRONG | Real Core preserves each page's independent expected text and excludes other pages' text; joined output exact. |
| T-CNV-08 / C:146 | STRONG | 1001 per-page Core calls including past inspection cap; first/last payloads independently parsed as one-page PDFs. Controlled Core output is appropriate to the conversion boundary. |
| T-CNV-09 / C:167 | STRONG | Fake Core records exact original raster bytes/hint, exactly one call and no extraction options; checks mdflow dispatch, not real Core OCR. |
| T-SEL-05 / C:264 | STRONG | Independently expected p2/p4 list, pages and absence of p1/p3; catches class-specific over-selection. |
| T-SEL-06 / C:279 | STRONG | Exact natural 1..1000 page list, no p1001, all-or-none oversize vs allowed positive control. |
| T-RND-09 / C:299 | STRONG | Only mixed-PDF scan pages produce files; rehash actual PNG bytes, validate dimensions and distinct page content. |
| T-TRX-08 / C:347 | STRONG | Exact per-page failure/success identities, continued sibling work, and actual replaced-raster refusal with unchanged sibling call. |
| T-TRX-09 / C:380 | STRONG | Exact PNG/JPEG passthrough, GIF conversion, EMF exclusion and a MIME-refusal positive/negative pair. Does not itself bind a Core unsupported_media issue (V33). |
| T-WRT-04 / C:414 | STRONG | Exact nested media/output inventory, retained byte contents, unchanged rerun, rejected hostile names and no strays. |
| T-PLN-55 / U/test_r28_plan.py:12 | BOUNDED | Ten explicit fixture identities, independent source bytes/digest and Plan request/cap/cache equations. Selected units and synthetic rasters are controlled Plan inputs; not real class execution through Render. Classification comparison iterates returned keys, so the separate exact-schema T-PLN-01 remains necessary. |
| T-ASM-51 / step7/test_r28_assemble.py:11 | STRONG | Four explicit class scenarios run orchestration/assembly/write; exact source provenance/path/base preservation and zero requests. Core text is a deliberately controlled S5 input. |
| T-META-53 / U/test_r28_trace.py:8 | STRONG | Every stage has independently listed expected all-class credit, schema/execution distinction, and explicit fixture retention. No assertion of test execution is inferred. |
| T-META-54 / U/test_r28_trace.py:21 | STRONG within scoring scope | Matrix PT-02 substitution fails; reference receipt passes; skip/failure/error reference receipts fail. Synthetic score fixture does not establish the real workflow graph (M2-V04). |
| T-GEN-54 / P/test_r27_builder.py:13 | STRONG within asset scope | Two real wheels compare bytes; overwrite and every frozen-subject mutation fail; rehashed bad wheel reference fails. Synthetic plugin bytes intentionally test verification only. No dependency resolution/install or authenticity evidence is created. |

The sample comprises **37 distinct newly added test identities**. Text-presence tests are not counted as behavioral closure. Class-stage tests now consume explicit fixtures rather than gaining S8/S11 credit from `fx("all")`; this is a real improvement without multiplying schema tests into twenty nominal copies.

## Probe receipts and practical limits

All probes ran from repository cwd with `python -B -`; production files were only read. Reproduction inputs/results are small enough to preserve here instead of creating a second artifact:

| Probe | Essential input / exact observed result | Interpretation |
|---|---|---|
| P1 | FX-09 golden triage; replace first raster dpi_tag with `'bad'`, then `{}`; each yields `convert_and_ocr`, issues `[]`. A bool px vector instead yields `convert_only / W_TRIAGE_UNKNOWN_VALUE`. | Remaining unvalidated promised field, with a validation positive control (V22). |
| P2 | CommandProvider(timeout_s=.15)._capture; direct Python child spawns a Python descendant sleeping1.5s then exits; observed `1.57 / E_PROVIDER_TIMEOUT`. | M2-V01 cleanup completion depends on inherited stdout owner. No raster/temp writes. |
| P3 | Build fixture-derived path `REPO/build/trace/redgreen/pt-tmp/.../2.0.0/Lib/site-packages/mdflow/__init__.py`; evaluate PT-01's two predicates. | `True / False`, deterministic fixture/assertion contradiction (M2-V02). |
| P4 | P::gate with valid engine/Core/protocol/schema and Python3.15, pdfium6, Pillow14. | `[]`; differs from shell's explicit limits (M2-V03). No claim those versions were installed. |
| P5 | Patch Path.mkdir to raise PermissionError and call render_units with a single bmp unit. | PermissionError escapes, no RenderResult (M2-V05). No directory created. |
| P6 | In-memory trace matrix validation and count all TOML cross-products. | `MATRIX_PROBLEMS []`; stage/FM85, class/stage110. This deliberately bypasses trace commands that write registry/report outputs. |
| P7 | R28 all-class schema registrations at S8 and S11, include_schema=True. | Both expand to **0 classes**, contradicting the retained matrix opening comment (V05). |
| P8 | `sniff_pure.detect_format(b'not a pdf','pdf')` versus IO `_by_extension('pdf')`. | **NATIVE / UNSUPPORTED**, confirming V36's still-unused alternate routing policy. |
| P9 | FX-24 mutation with equal-full-digest B/parser and A/stored records; actual Classify/Select, then `_render_media` with stat/open mocked to in-memory PNG. | **one group; representative A; kind parser_image_payload; rendered image/png, exact original bytes**. Stored-stream refusal lost across selection (M2-V06); no file was created. |

No real public-index install, cross-platform timing rehearsal, desktop operation, or provenance publication was attempted. Existing local pass counts remain useful evidence of ordinary regression coverage; they do not negate counterexamples at untested boundaries. R27's reference target limitation is legitimate and preferable to the removed universal-lock promise; the blockers above concern its actual validation and integration.

## Scores — explicit checks, not release acceptance

No dimension receives 100 while any finding remains open in that dimension. These review scores are separate from the binary acceptance mechanism and do not authorize release.

| Dimension | Score / 100 | Explicit checks and deductions |
|---|---:|---|
| Vertical closure | **73** | 27/37 original items closed (73.0%, rounded); all85 N/A cells judged, 84 acceptable aliases and one false boundary claim; actual consumed-field/cache/pre-send/collision paths improved. Open HWP integration/payload-policy composition, command cleanup, runtime/package evidence and two release blockers prevent complete closure. This is a repair-coverage score, not a severity-weighted release vote. |
| Oracle strength | **80** | Four25-point checks: observable consumer outcomes **23/25**; independent expected bytes/identities/equations **21/25**; adverse/resource-ordering/composition controls **20/25**; real installed/platform evidence **16/25**. The37-test sample includes weak text/name checks and partial Plan/HWP/deadline claims; PT-01 and release ordering are not yet executable success oracles. V04/V19/V30/V31/V33 and M2-V01/02/04/06 remain deductions. |
| Docs↔code consistency | **80** | Grammar/code/exit contracts **25/25**; prepared-snapshot/consent/cache semantics **25/25**; validation/applicability/payload-policy prose **14/25**; package/runtime/workflow policy **16/25**. Checked amended timestamp/oversize/order/proxy/deadline rules against consumers. V05/V19/V22 and M2-V03/04/05/06 leave explicit contradictions; SPEC's HWP integration disposition overstates evidence. |
| Simplicity | **68** | Direct wheel/one standard reference instead of universal merger **24/25**; shared release asset facts **20/25**; one implementation per IO/hash/routing responsibility **12/25**; clear state/evidence ownership and acyclic operation **12/25**. V36's duplicated atomic/sniff helpers, retained multi-file optional base cache, buffered-reader ownership and circular release scoring leave avoidable models. Keep the useful wheel/reference simplification; repair small ownership boundaries instead of adding another release framework. |
