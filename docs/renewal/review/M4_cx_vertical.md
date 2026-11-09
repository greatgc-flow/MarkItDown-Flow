# M4 recursive MECE audit — vertical, oracles, docs ↔ code, simplicity

Repair follow-up: [M4_ENGINE_FIXES.md](M4_ENGINE_FIXES.md) records engine repairs, red-first evidence, excluded shell/horizontal handoffs and the external-evidence acceptance inventory; [M4_SHELL_FIXES.md](M4_SHELL_FIXES.md) records the shell repairs (M4-V01, M3-V03, M3-V04, M4-V03, X-11 publication). Findings and scores below retain the original audit snapshot.

Date: 2026-11-09. Workspace: repository. Authority: current SPEC DRAFT-3.5 and SHELL/PACKAGING/TESTPLAN/ACCEPTANCE. Inputs: all three M3 reviews, `M3_ENGINE_FIXES.md`, current implementation, test assertions and local receipts. Historical reviews retain their historical verdicts.

**Verdict: improved engine boundaries; vertical and evidence closure remain incomplete.** M3's eight primary findings are **4 CLOSED / 4 OPEN**: V01, V02, H01 and O01 close; V03, V04, V05 and D01 remain open, with repaired portions identified below. Four newly demonstrated findings are M4-V01 (admission after Cancel/unload), M4-O01 (truncated collection accepted), M4-V02 (oversized numeric candidate ID crashes validation), and M4-V03 (shell/engine Base URL disagreement). M4-O01 is the remaining mechanism of M3-V05, not a second independent count of the same evidence defect.

**Scores: vertical 84/100; oracles 84/100; docs ↔ code 86/100; simplicity 92/100.** The final table enumerates every blocker to 100 in each dimension. These are audit judgments, not the release acceptance score.

Only `docs/renewal/review/M4_cx_vertical.md` is written. No code edits, git commands, installations, builds, pytest/Jest suite invocations, fixture publication, remote calls or release actions. Python probes used `python -B -`; TypeScript probes transpiled existing modules in memory with the installed TypeScript compiler. Original T-RND-90 assertion functions were called directly. Fake process/filesystem fixtures never launched an engine or wrote their modeled files. The only compiler check was `node shell/node_modules/typescript/bin/tsc --noEmit --incremental false -p shell/tsconfig.json`, which passed. This audit does not turn source inspection into an OS/manual receipt.

## Evidence actually verified

| Evidence | Observed result and scope |
|---|---|
| Engine Python 3.14 installed receipt | `build/trace/junit-m3-py314-installed.xml`: **548 cases = 536 passed + 12 skipped**, zero failures/errors. `registry-m3-py314-installed.json`: 549 collected, 548 selected; all selected nodeids exactly equal the 548 unique JUnit nodeids. Commit binding is empty, so this is local evidence. |
| Engine Python 3.15 receipt | `junit-m3-py315.xml` and its registry have the same counts and exact identity correspondence. This is the documented source-mode experimental run, not a supported endpoint installation. Both suites contain all 20 passing T-GEN-85 class cases. |
| New engine test identities | Each full XML contains T-CLS-90 ×5, T-RND-90 ×4, T-ASM-90 ×5, T-ASM-91 ×1, T-TRI-90 ×1, T-META-90 ×7, T-GEN-90 ×2 and T-META-91/92/94 plus T-GEN-92 ×1 each. No skipped repair parameter is counted as passing. |
| Shell receipt and typecheck | `junit-shell.xml`: **266 passed**, zero failures/errors/skips. Parsed, not rerun. Current no-emit TypeScript check passed independently. No new shell build or desktop result is claimed. |
| Wheel/source correspondence | All **26** Python module members of `build/trace/redgreen/m3-wheel-draft35/mdflow-2.0.0-py3-none-any.whl` equal current `engine/src` bytes. Existing `m3-installed-integrity.green.json` separately records 26 installed-module matches and the selected Python3.14 prefix. |
| Read-only trace | Called `requirement_registry`, Python/shell discovery, `coverage_problems`, Python `registration_problems`, `matrix_problems` and `golden_problems`, avoiding writing CLI entry points: unknown **0**, uncovered **0**, untagged **0**, registration **0**, matrix **0**, golden **0**. Shell discovery is included in requirement coverage; Python registration validation receives Python rows, as the CLI does. |
| Applicability | **84** stage/FM declarations; per S0–S13: **6,5,7,4,7,6,5,8,5,9,3,7,8,4**. Class/stage section expands to **71** declarations. All six disputed active class cells are now explicitly registered and absent from N/A declarations. |
| Matrix interpretation | Class/stage registration view has **213** cells, including common schema assertions; execution-registration view has **178**. The 71 declarations comprise 67 otherwise-unregistered equivalences and four covered overlays. The 35 schema-only registrations are not 35 demonstrated runtime failures: the CLI sweep also traverses early/report stages, but its extra-cell list does not register all of them. Neither 213 nor trace=0 means 213 independently executed cell oracles. |
| FX-71 publication handoff | Called `tools.record_protocol.verify` on both directories: **53 files verify** in each. Published `shell/test/fixtures/fx71`: Python3.15.2/Core0.3.5, default package gate rejects `Python range`. Staged `build/trace/redgreen/m3-fx71-py314`: Python3.14.10/Core0.3.6, default package gate returns `[]`. The owner has not published the staged fixture. |
| Missing release prerequisites | `required_executions(build/trace, 'a' * 40)` returns **15 missing target prerequisites**, six endpoint receipt groups plus nine smokes. The explicit synthetic commit is an absence inventory, not the repository's candidate identity. No `junit-reference.xml` is supplied in that evidence directory. MAN-01..04, desktop cancellation/picker/drop and genuine reference/provenance evidence remain separate obligations. |
| New probes | Actual presenter reproduces `files 2/1, done 1, pending 1` after Plan→Run; actual gates disagree on malformed renderer; actual coordinator launches after cancellation/disposal during admission; actual scorer accepts truncated inventories; actual Classify and its pipeline consumer raise on a 5,000-digit ID; actual shell URL predicate accepts endpoints the actual engine refuses. Details below. |

CLOSED means the identified defect has a concrete repair or a defensible advisory disposition, supported by inspected assertions and scoped evidence. It never waives a named release/manual gate. OPEN includes partial repairs, missing evidence and a demonstrated oracle weakness.

## Every primary M3 vertical finding and cx → shell handoff

| M3 ID | Verdict | Verification now |
|---|---|---|
| M3-V01 / M1-V22 | **CLOSED for the identified V1 payload-type defect** | `classify._well_typed` checks string type before enum membership. Direct probes with `[]`, `{}`, `None`, `7`, `future_payload` all return convert_only and exactly W_TRIAGE_UNKNOWN_VALUE; unchanged FX-24 remains convert_and_ocr. T-CLS-90's five composed cases assert zero provider calls, zero units, retained source output and a text sibling. The separate V3 digit-conversion defect is M4-V02. |
| M3-V02 / M1-V26 | **CLOSED** | `render.py:87–96` checks `ceil(width*scale) * ceil(height*scale)` before `page.render`. Direct calls to the original T-RND-90 assertion function pass all four 200/300 dpi × 0/90 rotation cases: zero decoder calls for the refused fractional allocation and one successful 72×72 control. Both full receipts contain all four passes. |
| M3-V03 / X-01 progress residual | **OPEN — shell handoff unfulfilled** | `ui/progress.ts:92,147` still stores every event and reduces the whole array on each render. `run_start` only sets total. Actual JobStatusBar sequence reproduces **files 2/1, done1, pending1** instead of Run-only 1/1, done1, pending0. Existing JT-09 compares a single stream to production `summarizeProgress`, missing this independent phase oracle and quadratic work. |
| M3-V04 / M2-V03 parity | **OPEN — partial engine repair** | T-GEN-90 and direct calls establish both package and shell gates reject empty/whitespace platform. Actual package gate rejects `pypdfium2='5.15.1???'`; actual default shell gate enables it (`version-gate.ts:100` accepts a prefix). Python/Core malformed suffixes are also accepted by both current prefix parsers; renderer mismatch alone suffices to keep the original parity finding open. |
| M3-V05 | **OPEN — narrower repair works; collection completeness remains unproven** | Registry/JUnit identity equality, per-target registries, commit check and pre-`-k`/`-m` snapshot are implemented. T-META-90 has seven useful negatives. Removing K09 only from XML, or leaving K09 deselected in the registry, fails the actual scorer. Removing K09 from both passes; keeping only K01 in both also passes. M4-O01 demonstrates the residual with real receipt identities and synthetic score controls. |
| M3-H01 | **CLOSED** | Sweep ordered selection assertions and literal cells now register S4:K05/K06/K08/K09/**K14** and S6:K04; all six are removed from N/A declarations. K04 checks p1..p1000, oversize default control and prepared raster fields. Twenty passing parameters exist in each engine XML. This closes the five cx cells and ag's sixth K14 cell. |
| M3-O01 | **CLOSED for the requested placement/member oracle gaps** | T-ASM-90 checks independently listed exact OCR IDs and pending `(id, reason)` multisets across scan/mixed PDF, GIF, real DOCX/HWP; paired closing-marker count, report placements and warm stability. T-ASM-91 checks all 1001 page anchors and exactly p1..p1000 OCR units. T-TRI-90 uses a genuinely corrupt inner Office relationship and valid archive sibling. Existing intentional output-loss log shows all five placement cases turn red. This does not claim complete semantic OCR/provenance verification. |
| M3-D01 | **OPEN — remaining current prose** | SPEC GEN-01 now names all three dependencies; TESTPLAN T-PLN-55 includes FX-03; HANDOFF no longer says 446 tests or leaves X-14/S-14/S-15 pending. However `matrix.toml:414` still says **117 cells**, actual 71. PACKAGING's final “Open SYNC-AFTER-DRAFT-3” paragraph still describes already synchronized contracts; SHELL REQ-SHL-16 still contains a pending-sync sentence while its final Open paragraph says no such item remains. These are current prose, not historical audit snapshots. |

`M3_ENGINE_FIXES.md` correctly leaves V03/V04 and FX-71 publication with shell, and release evidence outside local repair scope. Its V05 “CLOSED for Python execution evidence” claim must be bounded to an independently complete collection; the current consumer does not establish that premise. No engine event suppression is an acceptable fix for the shell's progress state.

## Every M3 Fable finding and Fable → cx handoff

| ID | Verdict | Code, oracle and remaining scope |
|---|---|---|
| N-01 | **CLOSED for concurrent admission** | `ShellCoordinator.submit` synchronously sets `reserved` before awaits, releases in `finally`; JT-09 submits twice against a pending gate and requires exactly one spawn and one BUSY. Refusal releases the flag. Cancel/unload during that same await is a different uncovered behavior, M4-V01. |
| N-02 | **OPEN for the handed-off recipes; shell launch repair CLOSED** | `ENGINE_ARGV_PREFIX` is `-I -X utf8 -m mdflow`; coordinator/utility/setup callers use the prefix and venv/home cwd. JT-12 observes every spawner and JT-11 rejects missing prefix. SetupModal recipe is isolated. **BOOTSTRAP lines26/28/40/41/79 and PACKAGING lines30/31/41/42 still use `-m mdflow` without `-I`**, including reference selftest. The explicit Fable→cx doc handoff is unfulfilled. |
| N-03 | **CLOSED** | Coordinator reports `plan.diagnostics` and adds PROTOCOL only when no diagnostic exists. JT-15 has literal expectations for E_USAGE-only startup failure and a distinct truncated-plan protocol failure. This is stronger than checking only a decoded happy Plan. |
| N-04 | **CLOSED by the authorized disclosure option** | README lines97–103 explicitly says every Windows Cancel is forced, produces no conversion report, may leave `mdflow-*` under OS temp, and tells users to delete such folders if they accumulate. `node-spawner.ts` and engine `TemporaryDirectory` lifecycle agree. There is no stale-startup sweep. Fable allowed **disclose OR clean**; automatic deletion is not necessary for finding closure. Genuine no-live-process/cancellation evidence remains a release gate. SHELL's ending cleanup handoff should stop presenting the optional sweep as mandatory. |
| N-05 | **CLOSED for silent empty selection; MAN-04 OPEN** | Picker returns explicit `empty`; main notifies `shell.notice.pickerEmpty`; JT-08 whole-plugin empty/blocked outcomes assert notices and no submission. Full-tree `webkitdirectory` enumeration remains a deliberate API tradeoff; real Electron empty-folder/large-tree behavior still requires MAN-04. |
| N-06 | **CLOSED for absent user activation** | `pickWithDomInput` returns blocked before creating the input when supplied `hasUserActivation()` is false; NodeApis supplies the real activation query. Existing picker tests cover blocked/empty/cancelled/selected, and main converts blocked to notice. This does not prove all host dialog failure modes settle. |
| N-07 | **OPEN — ordinary case repaired, URL-parser residual** | Settings tab/migration now reject ordinary non-loopback HTTP; JT-04 covers it. However `isAcceptableBaseUrl` normalizes via WHATWG `URL` while the engine uses `urllib.parse` and exact raw loopback names. Actual shell accepts `http://127.1:11434/v1`, numeric and hex aliases unchanged; actual engine refuses them. M4-V03. |
| N-08 | **CLOSED by disclosure** | Drop-toggle description and README explain that enabled local-file drops convert instead of attach; default remains false. JT-04 asserts the explicit tradeoff text; existing JT-08 checks off/text/URL/file paths. A different attachment policy is not required by this advisory finding. |
| N-09 | **CLOSED by disclosure** | Context menu/drop/locale descriptions carry reload notes; JT-04 verifies exactly those controls. Runtime registration still intentionally happens at load. |
| N-10 | **CLOSED** | `DirectorySpoolFs.read` delegates positional `readRange`; NodeFs opens/reads/closes a bounded buffer. JT-13 drains >3 windows, checks consecutive offsets including EOF, max window size, no whole-file reads, decoded result and removed spool. This proves the repaired I/O behavior, not bounded total JSON object memory. |
| N-11 | **CLOSED** | Open-log-folder creates the owned log directory before opening; whole-plugin JT-02 observes the first-use path. No need for an independent logging service. |
| N-12 | **OPEN — partially reworded** | SHELL's final Open paragraph is repaired and lists real OS/manual evidence. The same current document still calls engine synchronization pending in REQ-SHL-16 / older live disposition rows. PACKAGING's final pending-sync paragraph is also stale. Folded into M3-D01, not counted again. |
| X-11 | **OPEN — publication handoff unfulfilled** | Both published/staged recordings verify, but only the staged one passes default supported-host policy. Published JT-17 still uses `RECORDING_HOST_POLICY` widening to 3.16; published manifest remains Python3.15.2. Engine supplied the correct 53 files; shell owner must publish them and remove the local-only widening for actual-response checks. |
| S-13 | **CLOSED for the original stale HANDOFF** | HANDOFF points to M3_ENGINE_FIXES/Core0.3.6 and distinguishes engine/shell/release ownership. The original 446-test/pending-X14 statements are gone. Other current documentation drift remains M3-D01. |
| S-16 | **CLOSED** | `esbuild.config.mjs` no longer lists `@electron/remote`; production imports remain absent. |
| S-17 | **CLOSED** | Uncalled `approvableHashes` export removed; yes-file rendering remains in the launcher. |
| S-18 | **CLOSED** | Uncalled `Spool.finish` removed; `finishWith` remains the bounded-read decoder consumer. |
| S-19 | **CLOSED** | Unused `CoordinatorDeps.locale` removed. Locale belongs to actual UI/modal closures. |
| S-20 | **CLOSED** | Duplicate production `legacyFilePath` resolver removed; entry points consume NodeApis's supplied resolver. Test-local resolvers are not duplicate production behavior. |
| S-21 | **CLOSED for the re-export shim** | `ui/output-path.ts` no longer re-exports pure path helpers; consumers import `pure/paths` directly. The file correctly remains for real async `resolveDestination` and `selectImmediateFiles` behavior; deleting that implementation was never required. HANDOFF's “shim removed” means the redundant export surface. |

A concurrent `M4_fable_cross.md` appeared during final review and was read, not written by this task. Its P-01/P-02/P-03/P-06 corroborate the independently probed progress/gate/fixture/URL findings above. Its D-04 repeats the older 77-declaration count; the current TOML independently expands to **71**, so 117 must be corrected against 71. Its N-07 “CLOSED (residual P-06)” is treated here as **OPEN partial** because the same early-validation promise still fails. Additional peer-only P-04/P-05 and prose nits are not claimed as independently verified findings of this report.

## Inherited ledger carried by M3

The tables below account for the inherited findings in M3, including those already closed. Source/assertion checks and parsed passing receipts support retained closure; these tests were not rerun here. An inherited evidence gap stays OPEN even when its local oracle is repaired. Test IDs identify the current executable assertion, not merely a planned catalog row.

| M1 finding | Verdict | Current evidence / qualification |
|---|---|---|
| M1-V01 | CLOSED | T-META-50 excludes blanket nominal/report N/A; T-TRX-57/T-WRT-51 and T-RPT-52–56 assert durable effects/counters. |
| M1-V02 | CLOSED | T-SNF-50, T-GEN-53, T-CNV-52/53, T-TRX-54 and T-RPT-51 cover IO/interruption; T-RND-80 adds setup failure and sibling output. |
| M1-V03 | CLOSED for original consumer gaps | Classify/ledger and real pre-send validation remain guarded; T-CLS-50, T-LKP-50, T-ASM-50, T-TRX-53/54/56. New V3 conversion boundary is M4-V02. |
| M1-V04 | CLOSED | T-RND-81/82 compose HWP extraction/refusal; T-GEN-85[K09] has actual CLI cold/warm evidence. Common schema registration alone is not the evidence. |
| M1-V05 | CLOSED for expansion/owner drift | `fx(all)` limited to S0–S3/S13; T-META-81 and trace enforce expansion, obsolete K20 Lookup alias absent. Remaining count comment is M3-D01. |
| M1-V06 | CLOSED | Discovery excludes hidden/link/excluded roots, deduplicates descent, checks reparse attributes; T-SNF-50/53 and K20 effects. |
| M1-V07 | CLOSED | `_source_bytes` validates full length/hash before Core/Convert; T-SNF-51/54 deny replaced native/container content. |
| M1-V08 | CLOSED for byte/expansion bounds | T-CNV-50/T-RND-50/T-CTR-50/51 require no overrun and retain discovered members. Pixel boundary separately closes via M3-V02. |
| M1-V09 | CLOSED | Output containment precedes old Markdown reads and publication; T-WRT-50 asserts no outside read/write in both edited states. |
| M1-V10 | CLOSED | Warm skipped Markdown still publishes media; T-WRT-51 restores missing media without changing Markdown mtime. |
| M1-V11 | CLOSED | Ledger parses offset-bearing second-precision `created` before assembly; T-LKP-50/T-ASM-50 reject invalid provenance. |
| M1-V12 | CLOSED | T-RPT-50 bounds nested progress to 65536 UTF-8 bytes, preserves identity/counters and input immutability. |
| M1-V13 | CLOSED | CLI emits one authoritative terminal event after report-copy outcome; T-RPT-51 asserts exit/report/event agreement for empty/nonempty runs. |
| M1-V14 | CLOSED | Command capture uses one polling owner; T-TRX-50 live output cap and T-TRX-80 inherited-stdout timeout/no-reader oracle remain. No process-tree guarantee inferred. |
| M1-V15 | CLOSED by bounded amendment | T-TRX-51 asserts drip body deadline. SPEC explicitly retains DNS/TLS/header/native limitations; actual OS cancellation evidence is still owed. |
| M1-V16 | CLOSED | Exact argparse/provider-only flags and none cost override: T-CLI-50/T-PLN-50. |
| M1-V17 | CLOSED | Transcribe restricts runtime error vocabulary and redacts before truncation; T-TRX-52 asserts invented-code normalization, secret boundary and sibling continuation. |
| M1-V18 | CLOSED | Provider rejects proxy userinfo before Plan metadata; T-SEC-50 asserts secret-free configuration error. |
| M1-V19 | CLOSED | HWP stored policy remains distinct before grouping; T-RND-81 both orders checks exact raster/request and retained refused placement. |
| M1-V20 | CLOSED | Full digest groups units; h12 only names files and collision check precedes Convert; T-SEL-50/T-CNV-54. |
| M1-V21 | CLOSED | Parser security state, not literal PDF token, determines protection; malformed HWP is corrupt; T-SNF-52. |
| M1-V22 | CLOSED for original V1 nested types | T-CLS-80 ×14 plus T-CLS-90 ×5 close the identified malformed-field/type failures. M4-V02 is a separate V3 invalid-ID crash; broad “all malformed reports are total” is still false. |
| M1-V23 | CLOSED | Prepared Plan snapshot/approved oversize placement remains binding; T-PLN-51 and production T-PLN-02. |
| M1-V24 | CLOSED | Raster hash reverified immediately before provider call; T-TRX-53 / T-TRX-08 deny changed raster and preserve sibling behavior. |
| M1-V25 | CLOSED | Render releases previous encoded payload before next raster; T-RND-52 weak-reference assertions. This is not decoder working-set certification. |
| M1-V26 | CLOSED | Original T-RND-53 plus independent fractional T-RND-90 negative/allowed controls and four current direct passes. |
| M1-V27 | CLOSED | Embedded multiframe media uses frame zero; T-RND-54 compares actual decoded pixels against both frames. |
| M1-V28 | CLOSED | Discovery uses Assemble reserved-name normalization; T-WRT-52 requires collision report and preserved first output. |
| M1-V29 | CLOSED | Transcription survives failed ledger publication; T-LKP-51 asserts both sibling OCR outputs, requests and IO failure. |
| M1-V30 | CLOSED | Production T-PLN-02 mutates real inputs, checks exact fields and independent canonical hashes; source-fragment lint is supplementary. |
| M1-V31 | **OPEN — evidence** | Installed Windows3.14 local receipt and wheel correspondence exist. Six candidate-bound supported endpoint receipts and nine smokes are absent from required evidence paths; M4-O01 also limits certification. |
| M1-V32 | CLOSED as an oracle repair | Real small-wheel lock control rejects missing transitive pin/hash and modified dependency; T-GEN-52. Actual reference execution remains V34. |
| M1-V33 | CLOSED | T-CLS-07's 14 exact independent policy cases pass in both receipts; T-RND-83 composes real unsupported-media observation, zero send and pending output. |
| M1-V34 | **OPEN — release/reference evidence** | Real Linux3.14 Core0.3.6 hash-mode reference and supported targets, provenance and named reviews remain unsupplied. Twelve local release/evidence skips stay skipped. |
| M1-V35 | CLOSED as a design disposition | Direct wheel + one scoped reference + range-resolved targets replace universal lock; ASSETS/SUBJECTS are shared. Real target receipts remain mandatory. |
| M1-V36 | CLOSED | Ledger delegates atomic publication to Write and key identity to hashing; Sniff uses pure routing. T-LKP-80/T-SNF-80 protect canonical helpers. |
| M1-V37 | CLOSED by retained design | Optional base cache has behavioral reuse tests T-CNV-04/51; `_MeasuredProvider` counts explicit attempts, T-TRX-55. Deletion was advisory. |
| M1-V38 | CLOSED | Report-only classification clears candidates, Select checks action and orchestration excludes preparation/publication; T-CLS-53/T-TRI-50 and protected/corrupt sweep controls. |

| M2 vertical finding | Verdict | Current evidence |
|---|---|---|
| M2-V01 | CLOSED | T-TRX-80 timeout/no-reader plus capture polling implementation; descendant ownership follows bounded SPEC amendment. |
| M2-V02 | CLOSED | Installed-import helper accepts selected venv site-packages inside workspace while refusing engine/src/outside-prefix; T-GEN-80 has both negative controls. |
| M2-V03 | **OPEN** | Numeric compatibility ranges fixed, blank platform now fixed; renderer syntax parity remains M3-V04. |
| M2-V04 | CLOSED for DAG/isolation defect | Engine excludes release tests, immutable freeze precedes attestation, six verify-release jobs precede scoring; T-GEN-82/83 and workflow checks. Collection completeness remains separately OPEN as M3-V05/M4-O01. |
| M2-V05 | CLOSED | Render setup mkdir failure becomes per-unit E_RENDER_FAIL, pending output and surviving text sibling; T-RND-80. |
| M2-V06 | CLOSED | Rendering/refusal policy participates in group key before sorting; T-RND-81 checks both candidate orders. |

All **30 M2 disputed horizontal cells** carried in M3 are now CLOSED as execution registrations: S4 K05/K06/K08/K09; S6 K04/K08; S7 K03/K04/K06/K07/K08/K09; S9 K04/K05/K06/K07/K08/K09; S10 K04/K06/K08/K09; S12 K03/K04/K05/K06/K08/K09/K11/K18. M3 ag's additional **S4:K14** is also CLOSED. The original stage effects remain in T-GEN-85, and placement limits are closed by T-ASM-90/91 and T-TRI-90. All six active-cell N/A removals were independently checked. Ag's four stale covered declarations (**S6:K08, S6:K09, S5:K14, S4:K11**) remain **OPEN as redundant documentation**, under M3-D01; the covered-cell precedence is explicit in the manifest and no coverage hole is inferred from these overlays. The 67 remaining uncovered class equivalences retain M3's bounded ownership judgment.

| M2 Fable item carried in M3 | Verdict | Rechecked boundary / oracle |
|---|---|---|
| X-01 | **OPEN residual** | Visible Cancel wiring remains; progress leak/quadratic presenter is M3-V03. New admission cancellation gap is M4-V01. |
| X-02 | CLOSED | Launcher passes configured Base URL over host value via environment; JT-12. URL syntax discrepancy is N-07/M4-V03. |
| X-03 | CLOSED | Blocked/null migration makes settings/history writes read-only; whole-plugin JT-03/05 require unchanged bytes. |
| X-04 | CLOSED | Interpreter commits only on blur/Enter, absolute path required; JT-10 checks no typing probes and one committed probe. |
| X-05 | CLOSED implementation; MAN-04 OPEN | DOM/webUtils resolver replaces remote dialogs; JT-08/02 test outcomes. Real Electron behavior remains separate. |
| X-06 | CLOSED | Drop selection is confirmed with default Cancel; JT-08 modal and entry-point paths. |
| X-07 | CLOSED text; MAN-02 OPEN | README persistence/model/network/storage disclosures match code; named review remains owed. |
| X-08 | CLOSED | Consent uses egress and requests_to_send >0; JT-14/15 retain informational cached files. |
| X-09 | CLOSED | Run-level file:null warning/error accepted by framing and SPEC; JT-13. |
| X-10 | CLOSED | Destination revalidated before replay/yes-file; JT-09/15 symlink-change negative controls. |
| X-11 | **OPEN** | Supported-host fixture is staged, not published; verifier/gate observations above. |
| X-12 | CLOSED | Selftest first announces the retired-command routing; whole-plugin JT-02. |
| X-13 | CLOSED | DPI/priority/maxUnits/threshold/sensitive controls persist bounded options; JT-04. |
| X-14 | CLOSED | Version dispatch precedes Core startup gate and returns eight-field diagnostic response; T-CLI-80 ×3, T-GEN-87 ×3 remain passing. |
| X-15 | CLOSED | Background probe does not block onload; submissions await current gate; JT-02. Unload of an already waiting submission is M4-V01. |
| X-16 | CLOSED original stale references | yes-file/catalog/provider recipe and stale HANDOFF repairs verified; remaining prose inconsistencies are M3-D01 and N-02's explicit recipe handoff. |
| X-17 | CLOSED | No production electron.remote dependency; its dead build external also removed under S-16. |
| X-18 | CLOSED | History stores first path plus additional count; JT-07 checks omitted other paths. |
| X-20 | CLOSED by disclosure | README discloses vault/plugin-local cache/spool/consent/log syncing; implementation paths agree. |

No X-19 exists in the carried list. S-01 through S-12 remain CLOSED: duplicate argv/errors modules and three barrels removed; only yes-file authorization; replay oracles in test fixtures; dead history fact/production trace removed; environment diagnostics consumed; shared path helpers; no `this.load()` test convenience; coordinator entry/progress inputs used; current ignore rules. S-13's original HANDOFF repair closes as above. S-14 and S-15 remain CLOSED: provider DEFAULT_META is canonical (`T-GEN-84`), and `report.publish` owns stdout while CLI owns durable-copy/error ordering (`T-GEN-84`, T-RPT-51). S-16..S-21 are individually verified above. These retained simplifications do not fix the remaining presenter history.

## Round-3 oracle strength

| Test family | What its oracle establishes | What it does not establish |
|---|---|---|
| T-CLS-90 ×5 | Mutates real HWP report at orchestration seam; independently asserts row11a/code, zero units/calls, output and sibling continuation, original report unchanged. Tests list/dict as well as scalar invalid values. | It repairs the particular V1 enum boundary. It does not exercise V3 numeric ID conversion; M4-V02 is not covered. |
| T-RND-90 ×4 | Actual pdfium documents and real renderer, supported DPI/rotation, fractional over-bound refusal **before** decode and an allowed exact-size control. Current direct assertion calls passed. | PDF helper boundary, not a memory benchmark or every PDFium transformation. This scope is sufficient for M3-V02. |
| T-ASM-90 ×5 | Independent unit-ID/pending-reason multisets, paired delimiters, placements/transcribed count and warm cache/output stability. DOCX/HWP use actual Core conversion. Existing intentional dropped-block control turns all five red. | `published_units` accepts any syntactically valid key hash and does not map distinct transcript text back to each raster; retained golden/provenance/provider tests carry that separate responsibility. It is a placement oracle, not total OCR correctness. |
| T-ASM-91 | Independently enumerates 1001 page anchors and exact 1000 OCR IDs, verifies p1001 has no invented unit. Uses actual small PDF renders. | Small pages make it inexpensive; not a performance certification for 1000 normal-sized pages. |
| T-TRI-90 | A real truncated Office relationship within an otherwise valid archive reaches Core; independently expected corrupt issue/review, retained member result and valid sibling output. | An injected bad Core dictionary would not have supplied this evidence. This one real case does not enumerate every Core corruption mode. |
| T-META-90 ×7 | Complete 20-parameter positive controls; unchanged inventory catches missing XML case, duplicate/substitution, skipped/failed case, stale commit and absent registry. Scoring and endpoint prerequisites share the validator. | It never truncates **both** inventory and XML. The expected universe is supplied by the same run rather than an independently complete collection. M4-O01 survives all seven green cases. |
| T-GEN-90 ×2 | Literal empty/whitespace platform negatives against otherwise supported response; exact typed problem. | No cross-language malformed-version table; M3-V04 remains. |
| T-META-91/92/94 | Current Core reference/dependency hook and handoff/catalog strings; reference producer remains 0.3.6 while minimum endpoint metadata is 0.3.5. Golden integrity check passes. | String-presence checks cannot catch omitted `-I`, stale matrix count or live pending-sync prose. META-94 metadata substitution is not an actual minimum-endpoint install. |
| T-GEN-92 | Observes exact recorder child argv `[sys.executable,'-I','-m','mdflow','version']`, cwd and stripped PYTHONPATH/PYTHONHOME. Stronger than only examining environment construction. | Child is mocked; selected-prefix installed import provenance comes from separate wheel/install evidence. No live shadow-module attack is performed by this test. |
| Updated T-GEN-85 | Six explicit active-cell registrations, ordered selected units, K04 cap/default oversize/raster facts; literal cell marker and reached table must agree. Full local XML proves all 20 cases ran. | Some HWP/HWPX media IDs/statuses are wildcards in this selection table. Exact HWP publication is supplied by companions. Common schema and registration counts still must not be reported as per-cell runtime evidence. |
| JT-09 atomic admission | Two submissions in the same tick against a deferred gate; literal one accepted/one BUSY, one launch and owned-child cancellation. | No Cancel/dispose while the first admission itself is deferred; M4-V01. |
| JT-12/JT-11 isolation | Actual request builders/coordinator/version/selftest/setup dependencies are exercised; prefix/cwd checked; invocation oracle has a missing-prefix negative. | FakeSpawner proves argv/cwd construction, not real OS module resolution. Installed `-I` recording is independent engine evidence. It does not cover the two unamended prose recipes. |
| JT-04 URL/reload/drop | Real settings UI and migration reject ordinary insecure endpoints; literal persisted value checks; exact reload/tradeoff hints. | WHATWG host aliases absent; both table and migration reuse the same predicate, leaving M4-V03. |
| JT-08 picker / JT-02 logs | Explicit empty/blocked notices, no job submission; creating log directory before opening. Production resolver and picker remain thin. | Headless events are not Electron user activation, native dialog, empty-directory enumeration or OS permission evidence; MAN-04 remains. |
| JT-13 spool | >3 windows, independent offsets/max lengths, zero whole-file reads, successful decode and final removal; actual DirectorySpoolFs with fake filesystem. | Fake readRange does not test native NodeFs syscall failures. Source inspection confirms NodeFs uses positional open/read/close. No observed remaining quadratic I/O. |
| JT-15 startup / captureProbe | Startup E_USAGE diagnostic is independently expected without false protocol notice; malformed Plan remains protocol failure; synchronous spawn-error handling avoids timer TDZ. | Not an admission-lifecycle test. Existing progress JT-09 remains self-derived from the production summarizer on one Run, so M3-V03 is still missed. |

## New defects demonstrated by probes

### M4-V01 — MAJOR: cancellation/unload during admission is undone

Location: `shell/src/ui/coordinator.ts:138–193,220`. REQ-SHL-16 requires cancellation/unload to prevent launches. `admit` checks `disposed` only before `await gate()`. After gate/destination/listing awaits it unconditionally sets `isActive=true` and **resets `cancelled=false`**. The new reservation fixes two-job admission, but does not invalidate a canceled pending admission.

Probe loaded actual TypeScript modules in memory, actual ShellCoordinator plus existing FakeFs/FakeSpoolFs/FakeClock/FakeSpawner/settings builders. Gate was a deferred promise; destination/input were valid. The fake child was blocked until cleanup. Sequence: call `submit`; flush to pending gate; call `cancel()` or `dispose()`; resolve the same enabled gate; await submission and flush.

| Operation while gate awaits | Actual accepted | Actual spawns | Actual active | Actual disposed |
|---|---|---|---|---|
| Control: neither | true | 1 | true | false |
| `cancel()` | **true** | **1** | **true** | false |
| `dispose()` | **true** | **1** | **true** | **true** |

Expected canceled/disposed rows: no engine launch. There was no real engine or OS process: these are observed requests to the production coordinator's injected spawner. A final explicit Cancel settled each fake job. The dispose row directly models plugin unload while the background version gate is pending, without requiring a user-visible Cancel button during admission.

Minimal repair: invalidate pending admission on cancel/dispose and check that state after awaited admission work/before making a job active. A small admission generation/token or equivalent per-attempt state avoids reusing a previous job's cancel flag. Preserve synchronous reservation. Regression: the deferred-gate table above plus cancellation/disposal during destination/nonrecursive listing, zero launches and a fresh later submission control. Do not add a process supervisor to fix an admission predicate.

### M4-O01 — MAJOR oracle residual: a truncated collection certifies itself

Locations: `engine/tests/conftest.py:79`, `tools/trace.py:311,342`, `engine/tests/unit/test_m3_trace.py:11`. The hook snapshots all **collected** items before filters, but selection by test path/nodeid/parameter occurs during collection. A registry generated from a partial collection can therefore omit the missing parameter entirely. `rows_passed` asks only whether all matching identities **present in that registry** passed. Neither it nor `execution_receipt` establishes the full parameter universe of the candidate's callable.

Two independent in-memory probes:

1. Read the actual source T-GEN-85 row, actual `registry-m3-py315.json`, actual JUnit identities/results. `rows_passed([source_row], receipt)` is **True**. Remove only the real `[K09]` identity from both structures; result remains **True**. This uses the actual long source callable name and actual local receipt identities, with no file mutation.
2. Exercise actual `score` with explicitly synthetic source/acceptance/oracle/target data: six complete target controls, all 20 K parameters, synthetic candidate `'a'*40`, and manual attestation deliberately failing. Only source discovery and external evidence reads are substituted; production receipt/scoring logic runs. Results:

| Inventory / JUnit change on the modeled target | Actual automated result |
|---|---|
| Complete 20 parameters | **93/93, all 17 gates PASS** |
| Remove K09 from JUnit only | **0/93, all FAIL** — repaired negative control |
| Keep K09 in inventory but deselect it | **0/93, all FAIL** — repaired negative control |
| Remove K09 from both | **93/93, all PASS** — residual false acceptance |
| Keep only K01 in both | **93/93, all PASS** — residual false acceptance |

Manual result stays **0/7** throughout; no actual release score/review is fabricated. Fixed CI commands currently collect the full files, so this is not evidence that the recorded local runs omitted K09: their real inventories contain all 20. It is a defect in the advertised missing/not-collected evidence guarantee and a gap in T-META-90's independent oracle.

Minimal repair: produce/verify a canonical **complete collection** for the candidate/target independently of the execution selection; bind its content to the receipt and compare every required parameter against it. Ensure restricted file/nodeid collection cannot define that canonical universe. Extend the existing negative table by removing K09 from both and by collecting only K01, with the real full collection as expectation. Merely adding another self-reported count or accepting a matching pair of truncated files does not close it.

### M4-V02 — MAJOR robustness: V3 numeric IDs can abort the pipeline

Location: `engine/src/mdflow/classify.py:132–148`, called without a ValueError boundary by `_Pipeline.process`. This is V3 invalid-ID handling, separate from M3-V01's repaired HWP V1 payload kind.

Read-only probes load FX-02 PDF and FX-12 GIF golden reports/reviewed Sniff. Unchanged controls return convert_and_ocr. Replace only the first candidate ID with `'p' + '9'*5000` or `'f' + '9'*5000`; keep candidate page and all other fields unchanged. Both actual Classify calls raise:

`ValueError: Exceeds the limit (4300 digits) for integer string conversion: value has 5000 digits`.

The regex accepts the string and `int(match[1])` raises before checking its finite page/frame range. SPEC §3.2 V3 requires out-of-range IDs to become row11b **W_TRIAGE_INCONSISTENT**, convert_only, not an exception.

A second probe used actual generated PDF bytes, matching source length/SHA, actual `_Pipeline`/none provider and only a controlled triage return plus suppressed temporary `Path.write_bytes`. The same ValueError escaped `process`, before scheduling or publication. No filesystem failure was injected. This demonstrates a malformed-dependency-report boundary; it does **not** establish that current Core naturally emits a 5,000-digit ID for an input file.

Minimal repair: bound/compare the numeric spelling before conversion or treat failed conversion as V3 false; do not raise the interpreter's global integer limit. Regression: both PDF/raster oversized spellings, ordinary out-of-range/valid controls, exact row11b warning and one composed sibling-continuation/no-provider assertion. The repaired HWP type tests do not cover this branch.

### M4-V03 — MINOR: URL normalization defeats the new early-validation promise

Locations: `shell/src/pure/settings.ts:148–170`, tab/migration callers, and `engine/src/mdflow/providers/openai_compat.py::canonical_destination`. This is N-07's remaining mechanism.

Actual pure predicates were run without network access:

| Base URL | Shell `isAcceptableBaseUrl` | Engine `canonical_destination` |
|---|---|---|
| `http://127.0.0.1:11434/v1` | true | `http://127.0.0.1:11434/v1/chat/completions` |
| `http://127.1:11434/v1` | **true** | **ProviderConfigError** |
| `http://2130706433:11434/v1` | **true** | **ProviderConfigError** |
| `http://0x7f000001:11434/v1` | **true** | **ProviderConfigError** |

WHATWG URL normalizes each alias to 127.0.0.1 before checking the shell allowlist. The setting is retained as its original spelling and passed unchanged through MDFLOW_BASE_URL; urllib's host remains the alias and fails the engine's exact loopback set. Thus the UI saves a value that fails only at job startup, contrary to the predicate comment/N-07 repair claim. This is an admission/UX mismatch; no insecure network send is demonstrated.

Minimal repair: align accepted raw authority spellings with the engine, or explicitly canonicalize the persisted/passed value under a documented common rule. Keep the engine's loopback rule. Regression: the same alias/control table at shell predicate, persisted settings and engine consumer; don't derive expected engine acceptance from WHATWG's normalized host.

## Recheck of every stage/FM N/A declaration

All **84** expanded cells are still defensible **bounded ownership/equivalence declarations**, not evidence of 84 passing scenarios. Each table row explicitly lists every declared failure mode for its stage. `→` is the actual TOML owner. The full current declarations were parsed, all owners are registered, no floor cell is N/A, and S6:FM5 remains applicable/directly covered by T-RND-80.

| Stage | Every declared N/A cell's FM → owner | Rechecked boundary / qualification |
|---|---|---|
| S0 (6) | FM2→S1:FM2; FM3→S1:FM3; FM4→S3:FM4; FM6→S10:FM6; FM8→S9:FM8; FM11→S3:FM11 | Protection, source bounds/refusal, per-Key provider failure, approval and coverage belong to per-source owners. Configuration/startup dependency failures retain direct applicable cells. |
| S1 (5) | FM6→S10:FM6; FM7→S0:FM7; FM8→S9:FM8; FM10→S2:FM10; FM11→S3:FM11 | Sniff is local inspection without durable result publication or consent; forwards source facts. Parser runtime availability does not create a Core-vocabulary consumer here. Whole-run forced-cancel evidence remains OPEN. |
| S2 (7) | FM3→S1:FM3; FM5→S2:FM1; FM6→S10:FM6; FM7→S0:FM7; FM8→S9:FM8; FM11→S3:FM11; FM12→S0:FM12 | Preflight mdflow bounds precede Core; triage wraps local failure, forwards coverage, stays offline/read-only. Golden/whole-run determinism owns repeatability; no independent ledger/concurrency state. |
| S3 (4) | FM5→S3:FM1; FM6→S3:FM1; FM7→S3:FM1; FM8→S9:FM8 | Classify is pure, no IO/provider/durable partial commit or consent branch. M4-V02 leaves its applicable validation owner OPEN; purity does not imply total validation. |
| S4 (7) | FM1→S3:FM1; FM9→S3:FM1; FM10→S3:FM1; FM5→S3:FM1; FM6→S3:FM1; FM7→S3:FM1; FM8→S3:FM1 | Select consumes Classify-validated candidate fields and has no IO/provider/approval effect. Full-digest identity collision retains its own direct FM12. Upstream M4-V02 is not silently repaired by this delegation. |
| S5 (6) | FM2→S3:FM2; FM4→S3:FM4; FM6→S10:FM6; FM8→S10:FM6; FM10→S0:FM10; FM11→S11:FM11 | Action guard excludes report-only inputs, Core conversion is offline and pre-consent; placement/unmapped outcomes belong to Assemble. Generic FM8 owner means no-egress equivalence. Actual dependency/endpoint evidence remains OPEN at startup/release owner. |
| S6 (5) | FM2→S3:FM2; FM6→S10:FM6; FM8→S10:FM6; FM7→S0:FM7; FM9→S6:FM3 | Protected sources produce no units, rasterization is local/pre-consent, run owns temporary lifetime. Pixel/probe refusal covers hostile raster paths; the fractional owner now has T-RND-90. Forced kill can leave temp residue, explicitly disclosed; no claim of handled cleanup after native death. |
| S7 (8) | FM2→S3:FM2; FM4→S3:FM2; FM3→S7:FM1; FM6→S10:FM6; FM7→S10:FM7; FM8→S9:FM8; FM10→S7:FM1; FM11→S7:FM1 | No report-only eligible units. Lookup is local/read-only, each entry is hit/miss; invalid version is invalid-entry path, writes occur later. No ledger byte cap is specified, so validation is not a bounded-memory claim. Cache hits need no new consent. |
| S8 (5) | FM1→S9:FM8; FM5→S9:FM8; FM6→S9:FM8; FM7→S9:FM8; FM8→S9:FM8 | Plan is pure over prepared inputs; describes provider/approval facts without a request or durable commit. T-GEN-04, not the generic owner label alone, supplies purity evidence. |
| S9 (9) | FM1→S0:FM1; FM2→S3:FM2; FM4→S3:FM2; FM5→S9:FM8; FM6→S9:FM8; FM7→S9:FM8; FM9→S8:FM9; FM10→S9:FM8; FM11→S9:FM3 | Yes-file syntax/IO is CLI-owned; approval predicate is pure. Report-only zero-request Plans need no consent, sensitivity is a Plan fact, changed approved bytes invalidate hash, subset approval is per-file bounded selection. |
| S10 (3) | FM1→S10:FM6; FM2→S3:FM2; FM11→S11:FM6 | Provider exceptions are per-Key failures with continuation; protected sources yield no jobs; pending/failed placement is consumed by Assemble. Live request/cancel/IO failures retain direct cells. |
| S11 (7) | FM5→S12:FM5; FM7→S12:FM5; FM2→S3:FM2; FM4→S3:FM2; FM3→S10:FM3; FM8→S11:FM6; FM10→S11:FM0 | Pure assembly has no publication commit; action excludes report-only. Provider text bound is upstream, anchor count has direct coverage, missing/denied consent is pending grammar, release owns output grammar. No overall Markdown byte cap is invented. |
| S12 (8) | FM1→S11:FM9; FM2→S3:FM2; FM4→S3:FM2; FM3→S10:FM3; FM6→S11:FM6; FM8→S11:FM6; FM10→S11:FM0; FM11→S11:FM11 | Write consumes normalized relative names and prepared bytes/media; publishing denied/failed/pending bytes has no new provider/consent interpretation. IO/containment stay directly applicable. |
| S13 (4) | FM2→S13:FM10; FM4→S13:FM10; FM7→S0:FM7; FM12→S0:FM12 | Protection/refusal are bounded code-forwarding equivalences with real report-only/no-output assertions, not code-set checks alone. Run owns cancellation/terminal semantics. Warm report timestamps are explicitly exempt from byte equality. Shell's Plan→Run presenter bug is a downstream consumer defect, not a new report IO owner. |

The N/A declarations therefore do not require a new stage or duplicate provider/consent checks in pure functions. The **owners** still carry M4-V02 and missing real OS/runtime evidence. N-04 disclosure closes its particular privacy-documentation finding; it does not close a real-process release gate or promise stale-temp cleanup.

## Scores and exact blockers to 100

Each dimension uses five checks of 20 points, as in M3. An open item keeps its affected check below 20. Overlapping inherited IDs are aliases, not additional defect counts.

| Dimension | Five component scores (/20) | Score | Exactly what blocks 100 |
|---|---|---|---|
| Vertical | S0–S4 validation/selection **18**; S5–S7 preparation/cache **20**; S8–S10 admission/approval/lifecycle **17**; S11–S13 publication/UI consumption **16**; installed/release closure **13** | **84/100** | **M4-V02** malformed V3 ID exception; **M4-V01** canceled/disposed admission still launches; **M4-V03 / N-07** saved URL refused by engine; **M3-V03 / X-01** Plan/Run progress contamination; **M3-V04 / M2-V03** renderer gate disagreement; **M3-V05 / M4-O01** incomplete execution universe can certify; **X-11** supported-host fixture unpublished; **M1-V31/V34** missing endpoint/smoke/reference/provenance/real-OS/named-review evidence. |
| Oracles | Independent expected values **18**; real composed boundaries **20**; adversarial boundary controls **15**; complete executed-case inventory **13**; honest release/fixture evidence **18** | **84/100** | **M4-O01** missing-in-both inventory/JUnit negative absent; **M4-V01/V02/V03** deferred-admission cancellation, oversized numeric ID and raw-host-alias cases absent from repair tests; **M3-V03** progress expectation still production-derived/single-stream; **M3-V04** no shared full-syntax gate table; **X-11/M1-V31/V34** published fixture/required real target/reference/OS/manual evidence outstanding. No new placement-oracle deficit is charged after T-ASM-90/91/T-TRI-90. |
| Docs ↔ code | Engine normative facts **18**; shell behavior promises **17**; policy/consumer parity **16**; trace/fixture/applicability claims **17**; operational prose **18** | **86/100** | **N-02 recipe handoff** missing `-I` in BOOTSTRAP/PACKAGING; **M3-D01** 117-versus-71 heading, four redundant covered N/A declarations, obsolete live pending-sync prose, optional N-04 cleanup still phrased as owed; **M3-V03/V04** documented progress/runtime admission claims exceed behavior; **M4-V01/V02/V03** cancellation/validation/URL promises exceed behavior; **M3-V05/M4-O01** complete-parameter evidence claim exceeds validator; **X-11** actual-response fixture requires widened policy rather than supported-host default. Honest pending release receipts are not themselves a prose defect. |
| Simplicity | Canonical helpers **20**; dead shell surfaces **20**; retained designs justified **20**; bounded progress state **14**; single current ownership/accounting prose **18** | **92/100** | **M3-V03** unbounded event history and whole-history reduction on each event, also leaking phases; **M3-D01** stale counts, redundant covered declarations and conflicting pending-sync/optional-cleanup status. S-01..S-21 original removals/dispositions otherwise stand. A new framework, process-tree subsystem or automatic temp sweep is not required for this score. |

Required follow-up remains small and owner-specific: shell fixes admission cancellation, incremental per-run progress, gate syntax, raw URL policy and publishes the verified supported-host fixture; engine fixes V3 bounded ID parsing and independently complete collection evidence; document owners amend isolation recipes and current applicability/status prose. Real release/reference/desktop/manual receipts remain mandatory after those repairs. This audit makes no source changes.
