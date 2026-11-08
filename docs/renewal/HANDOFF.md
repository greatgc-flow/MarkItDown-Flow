# HANDOFF (2026-11-09, orchestrator cc/opus, usage limit reached)

Branch `renewal/v2-zero-base` (LOCAL ONLY - push was denied by auto-mode classifier; user must allow or run `git push -u origin renewal/v2-zero-base`).
Last WIP commit = this file's commit. Worktrees ../mdf-wt-{core,io,shell} are merged and can be removed (`git worktree remove`).

## State
- Design ratified (01_DECISIONS R1-R28; R27 packaging simplification unanimous incl. Fable amendment: compatible ranges for pypdfium2/Pillow in PKG-06 gate, SetupModal/BOOTSTRAP + JT-10/17 fixtures -> wheel+pip).
- Engine steps 1-7 + packaging step 11 GREEN (321 pass before MECE fixes). Shell steps 8-10: jest 227/229, build OK (repo-root main.js), tsc 7 errors left.
- MECE round 1 scores: vertical 60, oracles 77, docs<->code 70, simplicity 42 (cx, review/M1_cx_vertical.md); horizontal 68 (ag, review/M1_ag_horizontal.md). Horizontal fixes: 20 tests added (test_class_closure.py, pass); matrix.toml/30_TESTPLAN edits in WIP commit.
- IN FLIGHT at handoff: cx engine fix round (stream mdf-mece-cx, request mdf-fix1-cx) fixing M1-V01..V33,V37 with red logs in build/trace/redgreen/m1-*. Its edits may land AFTER the WIP commit -> run `git status` first.
- Fable stream mdf-wt-shell-fable is ask_uncertain -> use a NEW stream for shell work.

## Next steps
1. `git status`; run `python -I -m pytest engine/tests -q` and `cd shell && npx jest && npx tsc --noEmit -p . && npm run build`; commit cx results.
2. Shell: fix remaining tsc errors (obsidian 1.14 `Plugin.settings` clash) + 2 jest failures, new Fable stream.
3. Implement R27 (engine/tools side: drop lock_engine 15-cell merge, wheel + one CI hashed requirements) and R28 (trace.py fx("all") credit rule).
4. MECE round 2 (cx vertical, ag horizontal inline <=20 KB per ask - peerhub#309, Fable docs<->code); repeat until orchestrator-runnable gates (90_ACCEPTANCE G-*) PASS.
5. Push (needs user permission), 3-OS CI, manual MAN-01..04 (named human), release 2.0.0, cleanup worktrees/temp.
