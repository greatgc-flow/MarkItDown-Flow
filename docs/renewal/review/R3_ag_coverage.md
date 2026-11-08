### REQ -> Covering AC Table

| REQ ID | Covering AC ID(s) |
|---|---|
| REQ-GEN-01 | UNCOVERED |
| REQ-GEN-02 | AC-019 |
| REQ-GEN-03 | AC-020 |
| REQ-GEN-04 | AC-004 |
| REQ-GEN-05 | AC-007 |
| REQ-GEN-06 | AC-008 |
| REQ-GEN-07 | AC-022 |
| REQ-GEN-08 | AC-011, AC-013 |
| REQ-GEN-09 | AC-016 (contradicts criterion) |
| REQ-SNF-01 | UNCOVERED |
| REQ-SNF-02 | UNCOVERED (AC-002 contradicts) |
| REQ-SNF-03 | UNCOVERED |
| REQ-SNF-04 | AC-001, AC-021 |
| REQ-SNF-05 | UNCOVERED |
| REQ-SNF-06 | UNCOVERED |
| REQ-SNF-07 | UNCOVERED |
| REQ-TRI-01 | UNCOVERED |
| REQ-TRI-02 | AC-003 |
| REQ-TRI-03 | AC-003, AC-019 |
| REQ-TRI-04 | UNCOVERED |
| REQ-TRI-05 | AC-003, AC-019 |
| REQ-CLS-01 | AC-001, AC-017, AC-021 |
| REQ-CLS-02 | AC-001, AC-021 |
| REQ-CLS-03 | AC-001 |
| REQ-CLS-04 | UNCOVERED |
| REQ-CLS-05 | AC-021 |
| REQ-PLN-01 | UNCOVERED |
| REQ-PLN-02 | AC-011 |
| REQ-PLN-03 | UNCOVERED |
| REQ-PLN-04 | UNCOVERED (AC-002 contradicts) |
| REQ-PLN-05 | AC-011 |
| REQ-PLN-06 | AC-011 |
| REQ-PLN-07 | UNCOVERED |
| REQ-CNV-01 | UNCOVERED |
| REQ-CNV-02 | UNCOVERED |
| REQ-CNV-03 | AC-005, AC-010 |
| REQ-CNV-04 | UNCOVERED |
| REQ-CNV-05 | UNCOVERED |
| REQ-LKP-01 | AC-007, AC-008 |
| REQ-LKP-02 | UNCOVERED |
| REQ-LKP-03 | UNCOVERED |
| REQ-LKP-04 | UNCOVERED |
| REQ-APR-01 | AC-011 |
| REQ-APR-02 | AC-011 |
| REQ-APR-03 | AC-011 |
| REQ-APR-04 | AC-011 |
| REQ-APR-05 | UNCOVERED |
| REQ-APR-06 | UNCOVERED |
| REQ-RND-01 | AC-005 (AC-006 contradicts) |
| REQ-RND-02 | AC-005 |
| REQ-RND-03 | AC-005 |
| REQ-RND-04 | UNCOVERED |
| REQ-RND-05 | UNCOVERED |
| REQ-TRX-01 | AC-022 |
| REQ-TRX-02 | AC-007 |
| REQ-TRX-03 | UNCOVERED |
| REQ-TRX-04 | UNCOVERED |
| REQ-TRX-05 | AC-007 |
| REQ-ASM-01 | AC-004 |
| REQ-ASM-02 | UNCOVERED |
| REQ-ASM-03 | UNCOVERED |
| REQ-ASM-04 | AC-009 |
| REQ-ASM-05 | AC-010 |
| REQ-ASM-06 | UNCOVERED |
| REQ-ASM-07 | UNCOVERED |
| REQ-ASM-08 | UNCOVERED |
| REQ-ASM-09 | AC-008 |
| REQ-RPT-01 | UNCOVERED |
| REQ-RPT-02 | UNCOVERED |
| REQ-RPT-03 | UNCOVERED |
| REQ-CTR-01 | UNCOVERED |
| REQ-CTR-02 | UNCOVERED |
| REQ-CTR-03 | UNCOVERED |
| REQ-CTR-04 | AC-001, AC-021 |

---

### UNCOVERED REQs

- `REQ-GEN-01`
- `REQ-SNF-01`
- `REQ-SNF-02`
- `REQ-SNF-03`
- `REQ-SNF-05`
- `REQ-SNF-06`
- `REQ-SNF-07`
- `REQ-TRI-01`
- `REQ-TRI-04`
- `REQ-CLS-04`
- `REQ-PLN-01`
- `REQ-PLN-03`
- `REQ-PLN-04`
- `REQ-PLN-07`
- `REQ-CNV-01`
- `REQ-CNV-02`
- `REQ-CNV-04`
- `REQ-CNV-05`
- `REQ-LKP-02`
- `REQ-LKP-03`
- `REQ-LKP-04`
- `REQ-APR-05`
- `REQ-APR-06`
- `REQ-RND-04`
- `REQ-RND-05`
- `REQ-TRX-03`
- `REQ-TRX-04`
- `REQ-ASM-02`
- `REQ-ASM-03`
- `REQ-ASM-06`
- `REQ-ASM-07`
- `REQ-ASM-08`
- `REQ-RPT-01`
- `REQ-RPT-02`
- `REQ-RPT-03`
- `REQ-CTR-01`
- `REQ-CTR-02`
- `REQ-CTR-03`

---

### Orphan ACs (Reference Nothing in REQ Spec)

- `AC-012`: Secrets hygiene (child process environment scrubbing, log scrubbing). No requirement in SPEC.
- `AC-014`: Azure DocIntel/Computer Vision deprecation and migration warnings. Not mentioned in SPEC.
- `AC-015`: Obsidian plugin `SetupModal` / Python `.venv` bootstrap. Not specified in REQs.
- `AC-018`: Internationalization / localization dictionaries (`en`, `ko`). Not specified in REQs.
- `AC-023`: Obsidian community release packaging constraints (character lengths, npm audit, semver tags). Not specified in REQs.

---

### ACs Whose Pass Criterion Contradicts REQ Text

- `AC-002`:
  - Contradicts `REQ-SNF-02`: AC-002 sets byte ceiling default to 100MB and blocks at Plan stage as `OVERSIZE`. REQ-SNF-02 defines byte bound default as 200 MiB (209715200 bytes) at Sniff stage with issue `E_TOO_LARGE` and action `report_only`.
  - Contradicts `REQ-PLN-04`: AC-002 triggers `OVERSIZE` on file size (100MB) or page count (500 pages). REQ-PLN-04 triggers `E_PLAN_OVERSIZE` strictly when candidate unit count `units_total > --max-units` (default 200).
- `AC-006`:
  - Contradicts `REQ-RND-01`: AC-006 mandates automatic heuristic escalation to 300 DPI for dense CJK pages (>30% code points / >40% glyph density). REQ-RND-01 mandates explicit flag `--dpi` (default 200, allowed 200|300) with zero automated CJK escalation heuristics.
- `AC-016`:
  - Contradicts `REQ-GEN-09`: AC-016 specifies bidirectional JSON-lines stream communication over stdio. REQ-GEN-09 explicitly states: "No stdin protocol" (cancellation by OS process signals only).
