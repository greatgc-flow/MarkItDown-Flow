# Handoff for the 2.1.0 release candidate

The strict workflow requires Core 0.3.10 and protocol 2. See [the implementation specification](../strict-markdown/PRE_TDD_SPEC_EN.md) for classification and partial-export rules.

FX-71 was re-recorded from the candidate engine on Core 0.3.10. Historical 2.0 release evidence below belongs to the earlier candidate.

Release rule (R35, owner decision): 2.0.0 ships at `SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 deferred: post-release (R35)`; the owner supplies MAN-04 after publication (`trace.py score --post-release`). argon's earlier 89/100 HOLD in [FINAL_argon_acceptance.md](review/FINAL_argon_acceptance.md) predates R35 and is superseded.

Round 9 (merged): R37 Keep OCR pending, R38 cache at `~/.mdflow/cache` outside the vault, security review C1-C4 (C1 absolute-PATH program lookup, C2 command template secret refusal, C3 README disclosure that the version check starts exiftool/soffice, C4 absolute-path `--sensitive` matching), deferred cancel, `W_EXIFTOOL_UNUSABLE`, UI/UX polish; see [CHANGELOG](../../CHANGELOG.md).

2.0.0 is released (release run 42886235630, evidence run 42885992301, SCORE 99/100). Still open ([90_ACCEPTANCE.md](90_ACCEPTANCE.md) §7), owner only: MAN-04 (`python tools/man04_kit.py`, see [MANUAL_REVIEW_GUIDE.md](MANUAL_REVIEW_GUIDE.md)) and REQ-PKG-19/21 external evidence. MAN-01 access record: [MAN01_access_record.md](review/MAN01_access_record.md).

History: round reviews and fix reports (R3..R33, M1..M8, including M3_ENGINE_FIXES.md) are archived in [review/INDEX.md](review/INDEX.md) with commit-pinned links.

Collaboration record (requirements, design index, process, progress, results, next steps): [COLLAB.md](COLLAB.md).
