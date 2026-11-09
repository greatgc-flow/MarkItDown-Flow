# M2 engine follow-up: Fable handoffs

Scope: X-11, X-14, SPEC 7.3/8.2, S-14/S-15 from `M2_fable_cross.md`. No git commands. Engine wheel, protocol fixture generation, fixture-dependent Jest assertions and engine documentation only; no shell production changes.

| Handoff | Result and evidence |
|---|---|
| X-14 | Fixed. `cli.main` dispatches `version` before `_check_core`; the existing eight fields are always emitted, with `markitdown-gc: unavailable` for missing Core and the actual string for incompatible installed Core. Other commands retain the startup gate. `T-CLI-80` tests missing/old/new Core, all fields, exit 0, empty stderr and zero sockets. `T-GEN-87` rejects unavailable/malformed/empty Core in package admission without the former TypeError. SPEC REQ-GEN-02, 10.1 and DRAFT-3.4 changelog agree. |
| X-11 | Re-recorded from the current installed 2.0.0 wheel: 25 recorded + 28 derived files; `python -I tools/record_protocol.py --verify` verifies all 53. The recorder no longer injects engine/src through PYTHONPATH (`T-GEN-89`). `T-GEN-88` checks current identity, manifest/host consistency, exact gate verdict, hashes and derived variants. Added labelled `version.core-unavailable.json` and `version.python-3.15.json`. **The supported-Python release recording remains pending:** the available dependency snapshot runs Python 3.15.2, accurately reported and rejected by the release gate. No runtime field was rewritten to imply 3.14 support. |
| SPEC 7.3 file:null | Already done in M2: warning/error `file` is a logical string or null for a run-level issue. No duplicate change. |
| SPEC 8.2 docs/providers | Fixed the absent reference with a link to `docs/providers/command.md`: executable local adapter skeleton, stdout contract, Azure/peerhub integration boundaries, egress/environment declarations and cache invalidation. Also replaced stale two-chunk-queue wording with the implemented polling stdout owner. |
| S-14 | Already done in M2: `providers.describe()` reads provider class defaults; `cli._provider_list` is absent. Existing `T-GEN-84` passed again. |
| S-15 | Already done in M2: stdout-only `report.publish(value, *, stdout)` has no report_path parameter; CLI owns durable report-copy publication. Existing `T-GEN-84` passed again. |

## TDD and recording provenance

- X-14 red: `build/trace/redgreen/m2-x14.red.log`, six failures before either repair; green: `m2-x14.green.log`, six passed.
- X-11 red: `m2-x11.red.log` catches stale 2.0.0.dev0; `m2-x11-installed.red.log` catches the recorder's forced source injection. The host-policy oracle diagnoses experimental Python rather than treating local fixture verification as release admission.
- Recording: `m2-x11-record.green.log`, generated first under `build/trace/redgreen/fx71-followup-stage2`, verified, then copied byte-for-byte to FX-71. Work/output resolved inside the repository; existing fixtures were retained until generation and verification succeeded. Final verification: `m2-x11-verify.green.log`.
- Recorder command: selected workspace interpreter `build/trace/redgreen/m2-installed-env/Scripts/python.exe -I tools/record_protocol.py --out build/trace/redgreen/fx71-followup-stage2 --work build/trace/redgreen/fx71-followup-work2`; verification uses `python -I tools/record_protocol.py --verify`.
- The installed snapshot uses the established opt-in Windows test-temp bridge, scoped to this repository, via a build-only sitecustomize file. This bypasses restricted-token mode-0700 temp-directory failures for fixture generation; it is not shipped in the wheel or evidence of real desktop permission behavior.
- Wheel: `build/trace/redgreen/followup-wheel/mdflow-2.0.0-py3-none-any.whl`, SHA-256 `b7c63a2ee7aee0a6dd1342119f36ff7ac76641ce78765ac3d6240989269a852e`. All 26 installed module bytes equal the wheel and current engine/src. `pip check` passes. This is local installed-wheel execution, not fresh public dependency resolution.
- Python 3.14.5 was found in a local runtime cache, but its required native dependencies are absent. Local wheel caches lack compatible Pillow/lxml/etc.; package resolution is blocked. Logs: `m2-followup-py314-install.log`, `m2-followup-index-probe.log`. A dependency-equipped supported interpreter is needed to finish the release-host part of X-11.

## Validation

- Targeted installed checks: **14 passed** (`m2-followup-final-targeted.green.log`).
- Full installed-wheel pytest: **507 passed, 12 release/evidence skips, one platform deselection; zero failures/errors/xfails**, 402.82 s (`m2-followup-full.green.log`, `build/trace/junit-m2-followup.xml`). Command: selected snapshot interpreter `-I -m pytest engine/tests --runxfail -q -p no:cacheprovider --junitxml=build/trace/junit-m2-followup.xml`, with installed mode and the established Windows test-temp bridge enabled. The skipped release/manual evidence is not claimed as passed.
- Trace check: **zero** unknown requirements, uncovered requirements, untagged tests, registration errors and matrix errors (`m2-followup-trace.log`).
- Fixture-dependent shell assertions: JT-10 uses the recorded engine identity; JT-17 checks the new derived unavailable-Core/experimental-Python cases. The recording preserves the existing scenario hashes, counts and consent flow. Jest execution belongs to the orchestrator; no Jest pass is claimed here.
