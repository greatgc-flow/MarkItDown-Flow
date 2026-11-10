# HANDOFF — current state (2026-11-10)

Engine release/reference baseline: **Core 0.3.7** (published on PyPI), SPEC DRAFT-3.8; runtime compatibility is `>=0.3.7,<0.4`. GOLDEN.lock uses producer 0.3.7, and `engine/requirements-reference.txt` pins the published Core hashes.

FX-71 protocol fixtures were recorded on a supported host (Python 3.14.10, Core 0.3.6) and published to `shell/test/fixtures/fx71`; since R34 the `version` stream and its variants are refreshed from Core 0.3.7, and the other streams are retained.

Peer review: MECE round 8 (ag, cx, cc) left no open code/doc finding. argon's independent final acceptance ([FINAL_argon_acceptance.md](review/FINAL_argon_acceptance.md)) scores 89/100 (automated 89/93, manual 0/7): HOLD.

Pending before 2.0.0 ([90_ACCEPTANCE.md](90_ACCEPTANCE.md) §7): freeze the candidate commit; G-15 release bundle and attestations on the six release targets; named MAN-01..04 reviews (MAN-01 access record: [MAN01_access_record.md](review/MAN01_access_record.md)); `python tools/trace.py score` = 100/100. Local test passes are not these receipts.

History: round reviews and fix reports (R3..R33, M1..M8, including M3_ENGINE_FIXES.md) are archived in [review/INDEX.md](review/INDEX.md) with commit-pinned links.
