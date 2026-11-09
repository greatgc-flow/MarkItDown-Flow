# M2 engine fix round 2

Date: 2026-11-09. Scope: the ten reopened M1 findings and six new findings in `M2_cx_vertical.md`, with SPEC DRAFT-3.4 amendments and regression evidence. No git commands, remote CI, release publication, or real credentials were used. `shell/**`, README.md, 20_SHELL.md, `test_class_sweep.py`, and the class_stage portion of matrix.toml belong to the concurrent owners and were not edited here.

The source/oracle repairs are implemented. Actual required-platform/reference-install evidence remains **pending**, enforced as a release failure rather than replaced by local or synthetic success. This distinction applies particularly to M1-V31/V34: fixing their test/CI path does not manufacture Linux/macOS/Python 3.10/3.14 receipts.

## Finding dispositions and red evidence

All red logs are under `build/trace/redgreen/`. `m2-initial.red.log` records 21 real failures and one positive HWP integration control before the repairs. Per-finding copies of that aggregate log preserve the same original run; they are not claimed as separately executed runs. The table names the relevant failing regression. `m2-m1-v33.red.log` and `m2-k06.red.log` are separate targeted red executions. The real-HWP control already passed before repairs; its equal-payload mixed-policy composition failed and was repaired.

| Finding | Regression / red log | Repair and result |
|---|---|---|
| M1-V04 | T-RND-81/82; `m2-m1-v04.red.log` | Actual HWP5 fixture goes through real triage, extraction, Select, Render, provider and assembly. Equal-content mixed stored/parser records also go through the real pipeline with a controlled extraction boundary. |
| M1-V05 | T-META-81; `m2-m1-v05.red.log` | Matrix opening comments now state R28 S0-S3/S13-only expansion and distinguish registration/schema/execution. Concurrent cc removed the obsolete K20 Lookup alias while updating its owned class declarations. |
| M1-V14 / M2-V01 | T-TRX-80; `m2-m1-v14.red.log`, `m2-v01.red.log` | Remove queue/reader-thread capture. One unbuffered owner polls readiness, enforces cap/deadline, closes without another reader's buffer lock, and kills/reaps the direct command child. Inherited descendant stdout cannot hold cleanup open. |
| M1-V19 / M2-V06 | T-RND-81 both orders; `m2-m1-v19.red.log`, `m2-v06.red.log` | Group equal media digests only within the same rendering/refusal policy. Stored HWP payloads remain unsupported; representative sorting cannot inherit a supported kind. Supported parser payload still completes; refused source remains placed with W_MEDIA_FORMAT and no request. |
| M1-V22 | T-CLS-80; `m2-m1-v22.red.log`, `m2-v22-extra.red.log` | Validate raster dpi_tag, page-image records, media where/reference fields and HWP stored bytes/hash, including null forms and excluding bool-as-number; also check candidate decor, options.samples, summary count/scope types, optional coverage.reason and image filter lists. Existing reviewed golden/contract tests remain unchanged as positive controls. |
| M1-V30 | T-META-80 / T-PLN-02; `m2-m1-v30.red.log` | Replace detached expected-dictionary hash loops with actual production Plan input changes, exact output-field checks and independent canonical digest checks. Include file/provider/proxy/prompt/units/status/classification/cost/threshold/sensitivity families, count changes, cache and other-file independence. Synthetic mutation/lint cases are scope(schema) with FX-60; T-PLN-55 now additionally consumes the real FX-03 mixed-PDF fixture for class-specific credit. |
| M1-V31 | T-GEN-83/86; `m2-m1-v31.red.log` | Installed CI removes pytest pythonpath injection and fixture/child-launcher source loading, asserts selected-prefix site-packages imports, and retains candidate-bound runtime receipts. Six endpoint and nine intermediate smoke receipts are mandatory. Real cross-platform receipts still pending. |
| M1-V33 | T-RND-83, T-CLS-07; `m2-m1-v33.red.log` | Every Core issue case checks a complete independently expected classification signature and exact code set. An actual Core-marked unsupported HWPX encoding with decodable PNG bytes remains unsupported in preparation/Render: no request, warning, retained placement. |
| M1-V34 | T-GEN-82/86 and PT-02; `m2-m1-v34.red.log` | Repair the formerly impossible installed-import assertion and circular workflow, enforce actual endpoint/smoke/reference/attested-release evidence. The fresh Linux reference hash install and required target jobs are still release gates, not local passes. |
| M1-V36 | T-LKP-80, T-SNF-80; `m2-m1-v36.red.log` | Ledger delegates to write.atomic_write; ledger exports the canonical hash helper directly. Sniff's extension, magic, ZIP routing and expected-extension helpers have one pure implementation shared with IO. Remove obsolete IO constants and shadow hash wrapper. |
| M2-V02 | T-GEN-80 and PT-01; `m2-v02.red.log` | Selected-venv site-packages is valid even inside the workspace; source-tree imports and locations outside that venv fail. |
| M2-V03 | T-GEN-81; `m2-v03.red.log` | Engine wheel declares direct renderer/Pillow ranges matching the shell: pdfium>=5,<6 and Pillow>=11,<14, alongside Core>=0.3.5,<0.4. Package gate rejects Python3.15 and renderer/Pillow mismatches. Reference compiler resolves these constraints with Core0.3.5. |
| M2-V04 | T-GEN-82/83/86; `m2-v04.red.log` | Compatibility checks → freeze immutable bytes → attest → six post-attestation release tests with bundle/manual inputs → final acceptance → publish. PT-17 checks independent identity/receipts, never its own final score. Scoring reads actual release-phase JUnit for release tests, not their earlier skips. |
| M2-V05 | T-RND-80; `m2-v05.red.log` | Render directory preparation failure returns per-unit E_RENDER_FAIL, pending Markdown and sibling continuation. Remove the false S6:FM5 N/A declaration; register the actual boundary. |

Additional regression found by the concurrent K06 sweep: Core0.3.5 explicitly refuses GIF/TIFF base conversion despite their supported OCR path. `m2-k06.red.log` records both real failures. T-CNV-80 now proves those explicit unsupported-format results yield clean empty base text; other conversion errors still propagate. Render remains responsible for validating raster bytes. SPEC REQ-CNV-03 and DRAFT-3.4 changelog state this narrow exception. Full-suite `--runxfail` requires the fixed class-sweep assertions to pass, without editing cc's strict-xfail marker.

## Fable deletion decisions

| Item | Decision |
|---|---|
| S-14: cli._provider_list | Agree: deleted the duplicate function. providers.describe reads the provider classes' shared DEFAULT_META; instantiated metadata and descriptions use those defaults. No dummy key/config construction is required. |
| S-15: report.publish(report_path=...) | Agree: deleted the unused parameter and duplicate report-copy branch. CLI owns the optional durable copy and terminal-error ordering; publish only emits stdout. Existing atomic-copy test now calls the shared writer, and CLI failure integration remains intact. |
| Duplicate ledger key_id / atomic writer | Deleted the shadow wrapper and independent ledger publication implementation; keep the public canonical helper and one shared atomic implementation. |
| Duplicate Sniff IO classifiers/constants | Deleted duplicate implementations and unused constants; retain sniff_pure.py because it now owns shared production routing helpers. |
| tools/lock_engine.py, engine/engine.lock, engine/lock-inventory.json | Already absent from R27; no file was fabricated merely to delete it. |
| tools/mutate.py | Already absent; corrected TESTPLAN references to the actual golden-mutation tests. |
| Other tools/*.py | Retained: Fable names no additional obsolete engine/tool file in its deletion table. Builders, transfer verification, protocol/golden generation, endpoint checks, trace and release evidence have distinct live consumers. Shell-only deletion items remain Fable's responsibility. |

No recursive file removal was used. These are precise function/branch/constant removals; no complete engine/tool source file was identified as obsolete by the supplied Fable list.

## Validation and limits

- Initial red execution: 21 failed / 1 passed. Separate unsupported-media red: 1 failed. GIF/TIFF red: 2 failed.
- Targeted repaired boundaries, Plan mutations and packaging policy: `m2-final-targeted.green.log` — 48 passed before the final GIF addition; subsequent full execution includes those added cases.
- Final full installed-wheel result: **498 passed, 12 skipped, 1 deselected, zero failures/errors/xfails**, 476.27 s, using `MDFLOW_TEST_INSTALLED=1`, the established Windows temp bridge, and `pytest engine/tests --runxfail -q -p no:cacheprovider`. XML: `build/trace/junit-m2-installed-draft34.xml`; log: `build/trace/redgreen/m2-installed-draft34.green.log`. The earlier 492-pass receipt predates the final six optional-diagnostic V1 cases.
- Final V1 classification/installed-Core controls: **116 passed**, `m2-v22-final.green.log`; its six extra red failures are in `m2-v22-extra.red.log`.
- Added real mixed-PDF Plan case plus existing class Plan/mutation controls: **12 passed**, `m2-plan-class.green.log`. Final schema-marker controls: **3 passed**, `m2-schema-markers.green.log`. These test-only marker/fixture refinements followed full-suite collection and were verified separately.
- Trace check: all five error counts zero (`m2-trace-check.log`); rechecked after final concurrent registrations.
- Final wheel: `build/trace/redgreen/m2-wheel-draft34/mdflow-2.0.0-py3-none-any.whl`. All 26 Python module bytes match current engine/src. SHA-256: `a8afe81f903ee64f087216b535e5b6c6859eca3c9e0116f5354a9531431d5702`. No rebuilt asset is substituted into a release; these are local test builds only.

The local sandbox has Python3.15 and an existing dependency environment, but no stdlib venv module or virtualenv package. For installed-mode verification, the interpreter runtime and existing dependency distributions were copied into an isolated workspace snapshot, excluding mdflow and .pth files, then the newly built wheel was installed with no index/dependency resolution. Its import is under the selected local prefix's site-packages; pip check passes. `m2-installed-imports.green.log` verifies mdflow, Core, Pillow and pdfium all import from the same local prefix. This proves installed-wheel execution without source/global dependency fallback. It does **not** prove a fresh PyPI resolution, hash-mode reference reproduction, Python3.10/3.14 compatibility, or an advertised-platform release install. No local runtime receipt was labelled as one of the required CI targets.

The pipe-read implementation was checked against Microsoft's [PeekNamedPipe reference](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe). Its documentation URL lives here so the endpoint scanner does not misclassify a code citation as a network destination.

SPEC is DRAFT-3.4 with an explicit changelog. Packaging/bootstrap and acceptance oracles now describe direct runtime constraints, actual installed execution, and post-attestation scoring. Unsupported trace subcommand examples and unregistered pytest marker selections were replaced with executable requirement-focused pytest commands. Real named/manual and cross-platform evidence is still required before release approval.
