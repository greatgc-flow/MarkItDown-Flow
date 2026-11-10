# HANDOFF — current state (2026-11-10)

Engine release/reference baseline: **Core 0.3.7** (published on PyPI), SPEC DRAFT-3.8; runtime compatibility is `>=0.3.7,<0.4`. GOLDEN.lock uses producer 0.3.7, and `engine/requirements-reference.txt` pins the published Core hashes.

FX-71 protocol fixtures were first recorded on a supported host (Python 3.14.10, Core 0.3.6) and published to `shell/test/fixtures/fx71`; all streams were re-recorded under Core 0.3.7 in commit 0461501. Round 9's absolute command path changes the `consent-*` command-provider streams, which must be re-recorded ([90_ACCEPTANCE.md](90_ACCEPTANCE.md) §6.1).

Release rule (R35, owner decision): 2.0.0 ships at `SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 deferred: post-release (R35)`; the owner supplies MAN-04 after publication (`trace.py score --post-release`). argon's earlier 89/100 HOLD in [FINAL_argon_acceptance.md](review/FINAL_argon_acceptance.md) predates R35 and is superseded.

Round 9 (merged): R37 Keep OCR pending, R38 cache at `~/.mdflow/cache` outside the vault, security review C1-C4 (absolute-PATH program lookup, command template secret refusal, absolute-path `--sensitive` matching), deferred cancel, `W_EXIFTOOL_UNUSABLE`, UI/UX polish; see [CHANGELOG](../../CHANGELOG.md).

Pending before 2.0.0 ([90_ACCEPTANCE.md](90_ACCEPTANCE.md) §7): freeze the candidate commit and run its CI; G-15 release run (bundle and attestations on the six release targets); named MAN-01..03 reviews bound to that final commit (MAN-01 access record: [MAN01_access_record.md](review/MAN01_access_record.md)). Any fix makes a new candidate and the reviews must name it. Local test passes are not these receipts.

History: round reviews and fix reports (R3..R33, M1..M8, including M3_ENGINE_FIXES.md) are archived in [review/INDEX.md](review/INDEX.md) with commit-pinned links.
