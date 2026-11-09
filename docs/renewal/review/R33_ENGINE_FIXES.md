# R33 engine implementation and owned M5 closures

2026-11-09. Engine source, tests, renewal documents, README and the trace/CI evidence path only. No git command or shell source edit was performed. This is local source-mode evidence, not a release attestation or a named human review.

## Implementation

- `--preconvert-legacy` / `preconvert_legacy=True` is off by default. DOC, PPT, RTF and pre-5 HWP use user-installed LibreOffice, with `SOFFICE_PATH` taking precedence over PATH. Windows uses the installed console launcher when the GUI executable is selected. No dependency is installed.
- The bridge uses a private profile, disables macros, active content, untrusted links and automatic link updates, and passes an OS/runtime environment allowlist without provider credentials or inherited proxies. A shared timeout covers version probing and conversion. Windows assigns a suspended launcher to a Job Object before resuming it; POSIX uses a private process group. Timeout/cancellation terminates the owned tree. Windows capture-file cleanup retries briefly after kernel process termination to accommodate delayed file-handle release.
- Derived bytes are hashed, re-sniffed and checked against source/archive bounds. The derived output file is deleted after hashing; its profile and workspace are removed before downstream stages use the owned snapshot. Frontmatter contains original/derived SHA-256 and `fidelity: DERIVED`; the report carries `W_PRECONVERTED` with tool/version. Original report identity and output name remain intact. The Plan binds original identity and derived provenance, so a changed derived hash requires new consent.
- CSV/TSV/JSON are T/NONE without the media warning. Markdown/HTML/XML/EPUB and aliases are T/NONE with `W_MEDIA_NOT_INSPECTED`. Existing validation guards retain precedence. IPYNB/MSG/XLS retain their previous policy.
- Distribution metadata is checked afresh before CLI/programmatic conversion, triage, classification, cache reuse, version and selftest. A temporary sys.path containing a fake upstream `markitdown` dist-info produces `E_CORE_CONFLICT` before Core import.
- K12's eight execution N/A cells were removed; 59 class/stage N/A declarations remain. The enabled legacy media test verifies approval denial/replay, one transcription/placement, media publication, durable ledger storage and a cached warm rerun for all four filters.

## Reviewed golden amendment

These are explicit R33 policy values, not classifications generated from the implementation. Historical independent reviews are preserved inside each review record. The amendment identifies Codex as the implementing reviewer and does not claim a new independent human review.

| Files changed under `engine/tests/golden/` | Reason |
|---|---|
| `FX-30/classification.json`, `FX-30/classification.review.json` | CSV becomes NONE/T and drops `W_MEDIA_NOT_INSPECTED`. |
| `FX-31/classification.json`, `FX-31/classification.review.json` | HTML becomes NONE/T and retains the media warning. |
| `FX-32/classification.json`, `FX-32/classification.review.json` | Markdown becomes NONE/T and retains the media warning. |
| `FX-33/classification.json`, `FX-33/classification.review.json` | EPUB becomes NONE/T and retains the media warning. |
| `GOLDEN.lock` | Reseals those eight policy/review files. Core 0.3.6 and all Core triage oracles are unchanged. |

Existing policy assertions in the class sweep, Core issue table and R30 conversion review were amended consistently. `tools/golden.py verify` verifies all 150 sealed files.

## Owned M5 findings

- **M5-O01:** The scorer requires exact unique JUnit identities against a separate, complete expanded Jest `--collectTests` inventory. Collection runs no test/hook bodies, binds candidate and source/config/spec bytes, and emits the existing v3 registry/collection companions. CI collects before execution. Missing, duplicate, substituted, skipped, failed, stale and tampered receipts fail. Source discovery now preserves escaped/embedded quotes and explicit POSIX/WINDOWS guards. T-META-97/98 supply the positive and adversarial controls. The current local shell receipt was also checked against its independently collected 296 identities; this is local evidence only.
- **M5-D01:** Live pending-sync clauses in `20_SHELL.md` now distinguish completed contract synchronization from external OS/release receipts.
- **M5-D02:** Normative cwd prose now agrees with the selected venv root and isolated imports, including venvs inside the vault. Shell implementation comments belong to the shell owner and were not edited here.
- M5-V01 and M5-S01 are shell-owned mechanisms; this report does not claim their implementation. Historical audit snapshots and external acceptance obligations remain separate.

## Evidence

- Red-first: `build/trace/redgreen/r33-engine.red.log` records 25 expected failures before R33 implementation; `r33-m5.red.log` and `r33-m5-inventory.red.log` precede the corresponding evidence fixes. `r33-env.red.log` precedes subprocess environment scrubbing.
- Focused engine run: `build/trace/redgreen/r33-engine.green.log`, 20 passed. Both real LibreOffice integration cases ran; neither skipped. DOC and RTF were generated from a generated DOCX at test time. An absent soffice is the only permitted integration skip.
- M5 controls: `build/trace/redgreen/r33-m5.green.log`, 11 passed.
- Full suite: `build/trace/junit-r33-full.xml` and `build/trace/redgreen/r33-full.green.log`.
- Trace: `build/trace/redgreen/r33-trace.green.log` and `build/trace/r33-matrices.json`.

Final full-suite result: **641 passed, 12 skipped, 1 deselected in 333.36 seconds**, Python 3.15.2 on Windows. Both real LibreOffice cases passed. The independent collection digest matches the final test sources and the execution registry seal matches its collection. The 12 skips require release bundles, reference installation evidence or human records; the one deselection is platform-specific. These do not close any release gate. Python 3.15 source-mode execution does not replace supported installed-target CI.
