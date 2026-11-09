# M8 vertical confirmation

2026-11-09. Repository workspace; `fix/mece-r7` / PR #3 supplied by the user, not independently checked. Scope: M7-V01 and M7-D01..D03 plus adjacent round-7 regressions. Only this file written; no git or code edits. E-01..E-16 are excluded from scores.

| M7 finding | Status | Current evidence |
|---|---|---|
| **M7-V01** | **CLOSED** | `engine/src/mdflow/convert.py:203–258, 275–308` binds format, extension, extraction policy, disabled plugins and exiftool path/version through the canonical digest; validates metadata identity; stores tool fallbacks under the no-tool identity. REQ-CNV-04 (`10_SPEC.md:99`) agrees. T-CNV-96 (`engine/tests/stage_io/test_m7_cache.py:28`) has independent literal real-Core TXT/CSV expectations, both orders and no-call warm reuse; T-CNV-97 (`:56`) rejects legacy/missing/mismatched/non-object metadata. T-CNV-88 (`engine/tests/stage_io/test_r31_exiftool.py:134`) includes changed executable paths at equal version. |
| **M7-D01** | **CLOSED** | SPEC conformance row (`10_SPEC.md:757`) says fourteen fields and includes all six optional-tool fields, matching production CLI composition (`engine/src/mdflow/cli.py:240–249, 300–304`) and T-CLI-02's exact response set (`engine/tests/stage_io/step7/test_cli.py:55–58`). |
| **M7-D02** | **CLOSED** | ACCEPTANCE G-14 (`90_ACCEPTANCE.md:30`) says six required plus four experimental cells, retaining required macOS arm64. Actual PT-07 was called directly and passed against workflow YAML, including the non-substitution policy. |
| **M7-D03** | **CLOSED** | SHELL's final Open paragraph (`20_SHELL.md:256`) explicitly closes version syntax and consent waiter repairs; its remaining pending work concerns external OS/manual receipts. No contradictory local repair request remains there. |

Fresh quick probes (`python -B`, cache reads/writes intercepted in memory; filesystem mutations blocked):

- Real installed Core **0.3.7**: literal cold TXT/CSV outputs, both shared-cache orders and zero-Core-call warm reuse **PASS**; all four invalid/legacy metadata controls **PASS**.
- Fake Core/tool controls through actual cache load/store: same-version executable change, version change, tool absence, warm reuse, failure fallback and recovery **PASS**. Nine format identities remain distinct; extraction policy is bound. No adjacent cache regression reproduced.
- Current read-only trace helpers: unknown/uncovered/untagged/registration/matrix errors **0/0/0/0/0**. Corrected documentation inventories agree with the checked code/tests/workflow.

Existing `build/trace/junit-m7-engine-full.xml`: **691 passed, 12 skipped**, zero failures/errors; all ten relevant T-CNV-96/97/88 and T-CLI-02 parameters passed. Existing shell XML contains **317 passes**, versus the supplied 316 baseline; neither full suite was rerun. These local receipts establish no external acceptance outcome. Two initial harness attempts stopped at the probe's process guard during Windows platform discovery; corrected probes above completed, with disk writes still blocked.

| Dimension | Score | Exactly what blocks 100 |
|---|---:|---|
| Vertical | **100/100** | None |
| Oracles | **100/100** | None |
| Docs ↔ code | **100/100** | None |
| Simplicity | **100/100** | None |

**Open code/doc set: empty within this confirmation scope.** The repair uses the existing canonical hashing and cache helpers; no parallel conversion mechanism or duplicate pending-status account was introduced. Scores concern code/doc facts only, not release acceptance.
