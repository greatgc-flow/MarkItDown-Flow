# HANDOFF — current state (2026-11-11): 2.0.0 is released

Engine release/reference baseline: **Core 0.3.9** (the Core minimum is a prerequisite set by R39, see [01_DECISIONS.md](01_DECISIONS.md) and branch `feat/core-038`; 0.3.8 first shipped the public `markitdown.tools` API the engine uses, 0.3.9 fixes the PDF form feeds), SPEC DRAFT-3.8; runtime compatibility is `>=0.3.9,<0.4`. GOLDEN.lock (producer 0.3.9, triage bytes unchanged), `engine/requirements-reference.txt` and the FX-71 fixtures are regenerated against the published 0.3.9.

FX-71 protocol fixtures were first recorded on a supported host (Python 3.14.10, Core 0.3.6) and published to `shell/test/fixtures/fx71`; all streams were then re-recorded from the real engine under the published Core 0.3.9 (engine_source bound; PR #13; earlier refreshes used Core 0.3.7 and 0.3.8) (after the round-9/10/11 engine changes). The command provider's destination is home-relative (`~\bin\python.CMD` shim under the recording HOME) and the recorder's leak check rejects any absolute path outside `~` ([90_ACCEPTANCE.md](90_ACCEPTANCE.md) §6.1).

Release rule (R35, owner decision): 2.0.0 ships at `SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 deferred: post-release (R35)`; the owner supplies MAN-04 after publication (`trace.py score --post-release`). argon's earlier 89/100 HOLD in [FINAL_argon_acceptance.md](review/FINAL_argon_acceptance.md) predates R35 and is superseded.

Round 9 (merged): R37 Keep OCR pending, R38 cache at `~/.mdflow/cache` outside the vault, security review C1-C4 (C1 absolute-PATH program lookup, C2 command template secret refusal, C3 README disclosure that the version check starts exiftool/soffice, C4 absolute-path `--sensitive` matching), deferred cancel, `W_EXIFTOOL_UNUSABLE`, UI/UX polish; see [CHANGELOG](../../CHANGELOG.md).

2.0.0 is released (release run 42886235630, evidence run 42885992301, SCORE 99/100). Still open ([90_ACCEPTANCE.md](90_ACCEPTANCE.md) §7), owner only: MAN-04 (`python tools/man04_kit.py`, see [MANUAL_REVIEW_GUIDE.md](MANUAL_REVIEW_GUIDE.md)) and REQ-PKG-19/21 external evidence. MAN-01 access record: [MAN01_access_record.md](review/MAN01_access_record.md).

History: round reviews and fix reports (R3..R33, M1..M8, including M3_ENGINE_FIXES.md) are archived in [review/INDEX.md](review/INDEX.md) with commit-pinned links.

Collaboration record (requirements, design index, process, progress, results, next steps): [COLLAB.md](COLLAB.md).
