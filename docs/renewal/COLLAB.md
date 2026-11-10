# MarkItDown-Flow 2.0 renewal — collaboration record

Single entry point for the owner and every peer (cc, cx, ag). It states what was asked, where the
design lives, how the work is run, what happened, and what is next. Normative detail stays in the
linked documents; this file only indexes and summarizes them.

## 1. Requirements

Owner goal (2026-11-09): rebuild MarkItDown-Flow from zero on top of markitdown-gc; classify every
input as no-OCR (T), OCR-needed (S) or mixed (M) and transcribe selectively; review whether components
such as peerhub are needed; design to TDD-ready, implement by TDD, run recursive mutual MECE reviews
with vertical/horizontal closure checks, score every item, repeat until all items are 100, then release.

Owner directives, all recorded in [01_DECISIONS.md](01_DECISIONS.md):

| Area | Decisions |
|---|---|
| Architecture, contracts | R1-R28 (engine CLI + clean-room Obsidian shell, content-addressed ledger, consent by plan hash, never re-transcribe) |
| Scope | R29 no markitdown-gc LLM captioning · R30 no-OCR path first · R31/R40 exiftool for standalone png/jpg/jpeg · R33/R34 legacy formats via LibreOffice inside markitdown-gc |
| Release process | R35 MAN-01..03 by named peer cross-review, MAN-04 after release (release at 99/100) · R36 evidence simplification |
| Product behaviour (round 9) | R37 "Keep OCR pending" converts all no-OCR content · R38 plugin cache outside the vault (`~/.mdflow/cache`) |
| Core | R39 markitdown-gc 0.3.8 ships first and 2.0.0 requires it |

Operating rules (owner): peers collaborate through peerhub with unanimous consensus on material
decisions; English between AIs, Korean to the owner; VerySimple; plan before execution; no
re-transcription; quota paced to each pool's reset (check every turn, spend surplus on reviews and
preparation); fix recurring bottlenecks structurally before continuing.

## 2. Analysis and design

| Document | Content |
|---|---|
| [10_SPEC.md](10_SPEC.md) | engine pipeline Sniff → Triage → Classify (T/S/M) → Select → Plan → Convert → Lookup → Approve → Render → Transcribe → Assemble → Write → Report; codes (SPEC 7.5); security; CLI |
| [20_SHELL.md](20_SHELL.md) | Obsidian shell requirements REQ-SHL-01..21, consent modal, settings migration, i18n |
| [25_PACKAGING.md](25_PACKAGING.md) | wheel/plugin assets, CI matrix, action pins, release and evidence workflows |
| [30_TESTPLAN.md](30_TESTPLAN.md) | every test id ↔ REQ, fixtures FX-*, generated stage×failure-mode and class×stage matrices |
| [90_ACCEPTANCE.md](90_ACCEPTANCE.md) | gates G-01..G-17 (93 automated points) + MAN-01..04 (7), external evidence |
| [MANUAL_REVIEW_GUIDE.md](MANUAL_REVIEW_GUIDE.md) | how named peer reviews and evidence records are produced and rebound |
| [review/INDEX.md](review/INDEX.md) | archived review rounds (commit-pinned permalinks) |

Traceability is generated, not hand-kept: `python tools/trace.py check` must report
`unknown_req=0 uncovered_req=0 untagged_tests=0 registration_errors=0 matrix_errors=0`.

## 3. How the work is run

- **Roles.** Orchestrator (this repository's Claude Code session) plans, merges, runs the full suites
  and releases. cc implements and reviews; cx and ag give independent reviews and the named MAN
  attestations (the MAN-01 reviewer must differ from the shell implementer).
- **Loop per round.** Independent strict score → defect list → fixes in separate worktrees (one per
  concern) → cross-review of each diff → orchestrator verification (engine pytest, shell jest +
  typecheck, trace check, FX-71 verify) → integration branch → CI → re-score.
- **Peer tooling.** Peers run tests with `python D:/Engram2/_sys/tools/devbin/pt.py [--src DIR] [--gha]
  [--tmp DIR] -- <pytest args>` (no env-var prefixes); FX-71 is re-recorded with
  `python -I tools/record_protocol.py --engine-src <engine/src>`; evidence records move to a new
  commit only via `tools/rebind_evidence.py` (refuses when attested paths changed).
- **Line endings.** One policy: `.gitattributes` `* text=auto eol=lf`; byte-sealed fixtures
  (`engine/tests/golden`, `engine/tests/fixtures`, `shell/test/fixtures/fx71`) are `-text`.
- **Quota.** Profiles by task tier (bulk=standard, code=effort, review/design=deepthink); reuse a
  stream for follow-ups; send only actionable summaries; read-only `peerhub monitor --snapshot` each
  turn, `observation refresh` at most every 30-60 min.

## 4. Progress

| When | Round / step | Outcome |
|---|---|---|
| 11-09 | Design to TDD-ready, TDD M1-M8, MECE rounds 1-8 | engine + shell built; PRs #1-#6; markitdown-gc 0.3.7 (legacy converter, co-install guard) |
| 11-10 | Release attempts on 2.0.0 | release-only defects found one per CI cycle: evidence placeholder scan (#8, #9), PT-04 import (#10) |
| 11-10 | Round 9: strict independent score (~82 mean) | D1-D7, security review C1-C5, UI/UX polish, docs archive, R37, R38; integration branch `integ/2.0.0-rc` (PR #13) |
| 11-10 | Round 10 | redaction regression, bare SOFFICE_PATH, JT-12, covered+N/A matrix check, HANDOFF/CHANGELOG/README |
| 11-10 | Round 11 | redaction gaps, FX-71 re-recorded; found and fixed an absolute-path leak in recordings (home-relative destination) |
| 11-10/11 | R39: markitdown-gc 0.3.8 | gc PRs #72-#78 merged (xls, docx/tsv, audio, pdf headings, xlsx, public API, upstream); release PR #79 |
| 11-11 | Structural fixes (owner directive) | EOL policy, deterministic T-CLI-87, recorder `--engine-src`, rebind tool, peer test launcher, peer memory diet |

## 5. Results so far

- Independent scores (cc, strict): round 9 start ≈ goal 86 · vertical 90 · horizontal 88 · TDD 88 ·
  security 92 · docs 82 · release 60 · simplicity 72; after round 10 ≈ 90 · 94 · 94 · 91 · 93 · 88 · 70 · 78.
  Remaining deductions are tracked in the latest re-score; release readiness rises only with the
  real release run.
- Named reviews at the round-11 candidate: MAN-01 PASS (cx), MAN-02 PASS (ag argon), MAN-03 PASS
  (ag flash, 292 rows) — to be re-done on the final 0.3.8 candidate (R39).
- Lessons filed: MarkItDown-Flow #11 (artifact size, fixed), #14 (release dry-run), markitdown-gc
  #80 (guard vs source checkouts), peerhub #337 (headless peers, quota), LK #55 (global ag rules).

## 6. Next steps

1. markitdown-gc: merge #79, tag `v0.3.8`, confirm PyPI.
2. MarkItDown-Flow: public `markitdown.tools` switch (branch `feat/core-038`), pins `>=0.3.8,<0.4`,
   regenerate goldens + GOLDEN.lock, re-record FX-71, reference hashes, README known-limitations.
3. Merge structural + docs branches into `integ/2.0.0-rc`; CI; independent re-score.
4. MAN-01..03 on the final commit; evidence (`evidence.yml`); move tag `2.0.0`; `release.yml`; verify.
5. After release: MAN-04 (owner rehearsal kit `tools/man04_kit.py`), Core/plugin follow-ups.
