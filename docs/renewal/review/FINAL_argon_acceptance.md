Superseded by R35 (owner decision): MAN-04 is post-release. 2.0.0 is released at `SCORE 99/100 (automated 93/93, manual 6/7); MAN-04 deferred: post-release (R35)` (90_ACCEPTANCE §4); the 100/100 threshold and the "do not convert M-01..M-04 into post-release checks" recommendation below are historical.

(1) SUFFICIENCY TO TAG AND PUBLISH 2.0.0 NOW: NO.
Under 90_ACCEPTANCE.md (§1, §3, §4, §6, §7), release requires `SCORE 100/100 (automated 93/93, manual 7/7)` produced by `python tools/trace.py score` on the frozen candidate commit. AI peer reviews (ag/cx/cc MECE 100s) and PR test passes do not substitute for candidate-bound release artifacts, cryptographic attestations, or named human sign-offs.

PROVEN (Automated Compatibility & Code/Doc Baseline — 89/93 automated weight):
- G-01..G-14, G-16, G-17 (89 pts): Engine unit/contract suites (691 pytest across required 3 OS x py3.10/py3.14 cells against markitdown-gc 0.3.7), shell suite (317/317 jest, tsc, build), traceability (`trace.py check` 0 errors), classification, zero unit loss/duplication, warm rerun idempotency, consent/egress blocks, hostile-input security, process cancel/atomicity, settings migration, i18n parity, and release validator unit tests.

NEEDS EXTERNAL EVIDENCE (11/100 weight + candidate-bound M2 pipeline receipts):
- G-15 Release artifacts (4 pts): Candidate-bound `build/trace/` release bundle receipts (`junit-release-<os>-py<ver>.xml` across 6 targets), frozen `SUBJECTS` (wheel, 3 plugin assets, `reference-requirements.txt`, bootstrap, notices, LICENSE, `SHA256SUMS`), and live `gh attestation verify` (`PT-04, PT-13..15, PT-17`).
- M-01 Clean-room attestation (3 pts): `trace.py attest MAN-01` signed by a named human reviewer distinct from implementer.
- M-02 README disclosures (2 pts): `trace.py attest MAN-02` signed by a named human reviewer.
- M-03 en/ko meaning review (1 pt): `trace.py attest MAN-03` signed by a named bilingual human reviewer.
- M-04 Real-app release rehearsal (1 pt): `trace.py attest MAN-04` on real Obsidian (min + current) across 3 OSes (fresh install, 1.0.8 upgrade, rollback, consent, warm rerun, real Windows cancel/restart, terminal env launch) plus packaged candidate replay (`E-10`).

(2) TOP RELEASE RISKS:
1. Real-Obsidian desktop integration gap (M-04 / E-09 / E-10): Jest mocks Obsidian APIs; real Electron child-process spawning, PATH/terminal env inheritance, and Windows process-tree forced kill/restart can fail in live Obsidian despite 317/317 Jest passes.
2. Mixed FX-71 protocol recording baseline (§6.1 / G-12): Non-`version` streams in `fx71` were recorded under Core 0.3.6 while `version` was refreshed on Core 0.3.7; packaged candidate replay (`E-10`) against live 0.3.7 is still unexecuted.
3. Supply-chain & bundle assembly drift (G-15): Until `SUBJECTS` are frozen, hashed in `reference-requirements.txt`/`SHA256SUMS`, attested via GitHub OIDC (`gh attestation verify`), and verified across all 6 release targets (`PT-17`), packaging mismatch can break `--require-hashes` installs.
4. Optional external binary hazards in the wild: Opt-in LibreOffice (legacy DOC/PPT/RTF/HWP<5) and ExifTool rely on host installations; slow startup or zombie processes on user machines could hit the 0.5s probe / 3s response ceiling or leave orphan processes on Windows.
5. Bilingual UX/consent misinterpretation (M-03): Key parity (`G-16`) is proven, but unreviewed Korean/English error/consent phrasing risks user confusion on egress/cost boundaries.

(3) RECOMMENDATION: HOLD-FOR-MANUAL (and M2 release-bundle gate G-15).
Do not convert M-01..M-04 into post-release checks. 90_ACCEPTANCE.md (§1, §3 M2 execution order, §4, REQ-PKG-17) explicitly forbids partial credit, score typing, or post-publication deferral of MAN-01..04 (only REQ-PKG-19/21 are post-publish). Freeze the candidate commit, complete `MAN-01..04` human attestations, build/attest the release subjects, run the 6-target release suite (`G-15`), and require `trace.py score` == 100/100 before publishing 2.0.0.

(4) FINAL ACCEPTANCE SCORE: 89 / 100 (Automated: 89/93, Manual: 0/7) — HOLD.
Formula (per `90_ACCEPTANCE.md` §1-§3):
`Score = Sum(W_i * I(G_i == PASS)) + Sum(W_j * I(M_j == PASS))`
- Automated `G-01..G-14, G-16, G-17` = `5+7+9+6+8+7+8+6+5+6+5+5+5+4+2+1` = 89 / 93 (`G-15` = 0/4 pending frozen candidate attestation/bundle receipts).
- Manual `M-01..M-04` = `0+0+0+0` = 0 / 7 (pending `trace.py attest MAN-01..04`).
- Total = `89 + 0 = 89 / 100` (Threshold for release: `100 / 100`).
