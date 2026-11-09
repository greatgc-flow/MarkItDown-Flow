# HANDOFF (2026-11-09, MECE round 2 in progress)

Branch `renewal/v2-zero-base` (local; pushing needs the user's permission: `git push -u origin renewal/v2-zero-base`).

## State
- Design ratified (01_DECISIONS R1-R28). Engine suite green at `f9d3d14` (446 passed); cx engine round 2 (M2_cx_vertical) in flight in the same tree.
- Shell: MECE round-2 fixes applied (Fable M2 X-01..X-20, S-01..S-13; see `docs/renewal/review/M2_fable_cross.md` and the disposition rows at the end of `20_SHELL.md` section 7). Jest 255/255 (`build/trace/redgreen/m2-shell.red.log` -> `m2-shell.green.json`). `tsc --noEmit` and `npm run build` are verified by the orchestrator after each round.
- Open engine/tools items from the shell round: X-11 re-record FX-71 on Python 3.14 from the 2.0.0 wheel; X-14 `version` must not fail when Core is missing; SPEC 7.3 `file: string|null` for run-level events; SPEC 8.2 `docs/providers/*.md` reference (absent); S-14/S-15 (`_provider_list` meta, `report.publish(report_path)`).

## Next steps
1. `git status`; run `python -I -m pytest engine/tests -q` and `cd shell && npx jest && npx tsc --noEmit -p . && npm run build`; commit the round-2 results.
2. Re-run the R16 README review (MAN-02) against the corrected README; MAN-04 rehearsal must include the file picker, drop confirmation and status-bar Cancel in the real app.
3. MECE round 3 if any BLOCKER/MAJOR remains; otherwise run the orchestrator-runnable gates (90_ACCEPTANCE G-*).
4. Push (needs user permission), 3-OS CI, manual MAN-01..04 (named human), release 2.0.0, cleanup worktrees/temp.
