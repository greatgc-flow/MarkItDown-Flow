# R7 — TDD ratification

Vote: TDD may start. No remaining BLOCKER makes test-first implementation impossible. The MAJOR/MINOR items below remain assigned work; this vote does not approve release or claim tests pass.

Scope: `10_SPEC.md` DRAFT-3, all R5-N01–N12 and all eleven R5 PARTIAL dispositions, plus `20_SHELL.md` / `25_PACKAGING.md` protocol synchronization. Only this file is written; no git. Static checks ran in memory with bytecode writes disabled; no provider/network calls.

Reviewed snapshot SHA-256 prefixes: SPEC `b9124dec94751d97`; shell `3144a1ce306409a0`; packaging `3e4188b5652e884e`. Locations below are relative to `docs/renewal/`.

## R5 findings

RESOLVED means the original contradiction has a usable specified correction. ACCEPT-CUT accepts removal of the responsible feature; ACCEPT-REJECTION accepts the narrower declared contract. UNRESOLVED items here are MAJOR and can be fixed during TDD.

| Finding | Disposition | Evidence |
|---|---|---|
| R5-N01 | RESOLVED | SPEC TRI-02/03, CLS-06 and 3.2 place schema/exception/V1–V4 handling before every NATIVE format shortcut; section 11 tests PDF and G2 failures. |
| R5-N02 | RESOLVED | SPEC 5.1 permits pending statuses with null raster fields; PLN-04/05 and 7.1 count only executable Keys; RND-02 supplies frame totals outside PURE classification. Oversize-raster metadata is an edge case in T04 below. |
| R5-N03 | ACCEPT-CUT | SPEC PLN-02, section 4, 8.4 and 12.2 remove the run hash/barrier and normalize cached units in the hashed per-file object; sequential cache fills no longer invalidate consent. |
| R5-N04 | RESOLVED | SPEC MAP-03/08, ASM-06 and 6.2 separate informational refs from placements, merge identical media, and emit one block per distinct linked unit per line. |
| R5-N05 | RESOLVED | SPEC GEN-05/06 compares published bytes, exempts audit reports and removes ledger seen updates; unchanged media/cache targets need no rewrite. Correct the remaining report oracle during TDD (T04). |
| R5-N06 | ACCEPT-CUT | SPEC LKP-02, TRX-02/06, 7.2 and 13.2 remove inflight/liveness/sweeping; concurrent duplicate calls and crash retries are explicitly disclosed rather than misclassified. |
| R5-N07 | ACCEPT-REJECTION | SPEC GEN-09, 10.3 and 13.8 distinguish cooperative exit 130 from forced native death and withdraw the five-second engine promise; SHL-16 retains five-second supervision. |
| R5-N08 | RESOLVED | SPEC GEN-10 and section 11 explicitly exclude raw triage from mdflow-code validation; PKG-08 and SHL-13 make the same distinction. |
| R5-N09 | ACCEPT-CUT | SPEC APR-03/7.3 and SHL-13 remove full Plans from progress; full Plans use `plan` stdout. Remaining summary-size limits are T05. |
| R5-N10 | RESOLVED | SPEC SNF-01/8.4 and SHL-12/15 preserve original ordered roots, cwd and destinations for batch replay, avoiding nested-file root changes. |
| R5-N11 | RESOLVED | SPEC 7.5 and shell section 6 have exactly the same 50 active codes; SHL-17/20 and PKG-06 now consume complete version/selftest contracts. Authorization-file synchronization is T01. |
| R5-N12 | RESOLVED | SPEC 3.2 row 0c handles E_OUTPUT_COLLISION before conversion; section 11 SNF-01b requires a never-reaches-Convert spy. |

## R5 PARTIAL findings

| Finding | Disposition | Evidence |
|---|---|---|
| R3-04 | RESOLVED | SPEC MAP-03/08, ASM-06 and 6.2 resolve duplicate-reference counts, same-byte members and link placement ownership. Guard abbreviated hash grouping during implementation (T07). |
| R3-06 | RESOLVED | SPEC 3.2 V3 requires PDF ID/page agreement and null non-PDF pages; CLS-04 defines unknown-reason warning versus unknown-issue validation failure, including G2. |
| R3-08 | ACCEPT-CUT | SPEC 3.1/3.2 removes the CSV/TSV/JSON media-free shortcut; only core-validated txt/log can take the G2a NONE path. |
| R3-12 | ACCEPT-REJECTION | SPEC APR-07 hashes actual send bytes; 7.1/8.2 uses the validated canonical destination. Section 13.10 explicitly narrows command script/env-value validity to the user's model version label; accept that declared limitation. |
| R3-13 | RESOLVED | SPEC PLN-08/7.1 adopts hashed est_max_cost = cost_hint × max_requests; unknown cost is explicit and actual billing remains unpromised. |
| R3-14 | UNRESOLVED | SPEC glossary/8.2 says command env names affect identity, but the normative Key in 5.1/7.2 still omits both command_env_names and provider_fingerprint (T02, MAJOR). |
| R3-15 | RESOLVED | SPEC GEN-05/06, ASM-09/10 specifies byte preservation, report exceptions, stable OCR time and edited-output handling; retry/force remains separate. |
| R3-18 | RESOLVED | SPEC 7.1 example now has three units, two eligible Keys, six maximum requests, est_max_cost 0.024000 and status counts summing to three; nullable pending records are specified. |
| R3-23 | UNRESOLVED | SPEC SNF-09 bounds mdflow reads, but its cited core constants belong to ocr_triage, not proof that Core conversion/extract_media reads are bounded (T03, MAJOR). |
| R3-24 | RESOLVED | SPEC ASM-11 now applies esc_head to all dynamic heading fields as well as text/attributes; ledger originals preserve the accepted lossy-rendering contract. |
| R3-26 | RESOLVED | SPEC CLS-05 separates Core-generated evidence from reviewed mdflow classification.json expectations; 10.4 conditions cross-OS hash stability on equal prepared bytes. |

Disposition totals: 15 RESOLVED, 4 ACCEPT-CUT, 2 ACCEPT-REJECTION, 2 UNRESOLVED. All four previous R5 BLOCKERs have a specified correction or an accepted cut.

## Shell / packaging consistency

| Check | Result | Evidence |
|---|---|---|
| Code table equals SPEC 7.5 | PASS | Parsed active first-column table cells only: SPEC 50, shell 50, no missing/extra/duplicate shell rows. SHL-19 / PKG-09 require the same test for en/ko implementations. |
| Consent via --yes-file | UNRESOLVED — MAJOR | SPEC APR-02/10.2 supports it, but neither shell nor packaging mentions it; SHL-15 and PKG-08 still prescribe repeated argv hashes. Those remain valid engine syntax but do not satisfy this requested synchronization. T01 owns the correction. |
| No run hash | PASS | SPEC 8.4 and shell SHL-14/15 use independent per-file hashes; packaging PKG-08/section 8 explicitly excludes the run hash/barrier. Historical cut descriptions are not active protocol fields. |

Summary/full-Plan separation, full version fields, original-root replay, diagnostics-only setup and native-versus-cooperative cancellation agree in substance. `SYNC-AFTER-DRAFT-3` labels describe outstanding implementation evidence; they do not independently block TDD.

## Fix during TDD

Owners: Fable = engine/spec; cc = shell/packaging; ag = contract/oracle tests. These are work assignments in this review, not messages sent to other agents.

| ID | Severity | Owner | Concrete correction and test |
|---|---|---|---|
| T01 | MAJOR | cc; ag | Update SHL-15 and PKG-08 to write accepted per-file hashes to a private temporary --yes-file and replay the identical batch with that option. Keep hashes out of settings/history/logs; delete the owned file on handled exits. Test large selections, cancellation and partial approval; preserve no-run-hash behavior. |
| T02 | MAJOR | Fable; ag | Add sorted command_env_names, or the declared provider fingerprint, to the canonical cache Key and validation schema. Test that changing the forwarded name set cannot reuse the old record. Keep script/env-value changes under the explicitly accepted model-label/force contract. |
| T03 | MAJOR | Fable; ag | Establish installed-Core conversion/extraction read limits with source/contract evidence, or enforce a bounded conversion boundary. The constants in ref/ocr_triage_0.3.5.py.txt govern triage's _office/_hwp/read functions; they do not certify CNV-03. Test oversized Office media and actual streamed byte overruns. |
| T04 | MAJOR | Fable; ag | Pin report counter semantics for no_provider, approval_required and approval_denied: use total = cached + transcribed + failed + pending and define eligible separately. Correct section 11 GEN-06: cold/warm reports differ in cache/request counters as well as timestamps. For oversize rasters, define metadata-only frame inventory or nullable unknown total despite zero Render calls. Add red fixtures for each case. |
| T05 | MAJOR | Fable; cc; ag | Enforce the serialized 64 KiB progress budget for every dynamic field, not only message length and sensitive-hit count. Long file/member IDs, model/endpoint strings and long globs remain unbounded. Bound display summaries without truncating the full approved object; test UTF-8 byte lengths and oversized identifiers. Specify multi-Plan stdout framing and test decoding 50 Plans plus truncated EOF. |
| T06 | MAJOR | Fable; cc; ag | Execute real POSIX/Windows cancellation and forced-restart tests. Verify the required process-group/signal setup and owned-child cleanup, preserve actual native exit status, and never fake report/130 on forced death. Keep failed runtime/packaged checks release-blocking. |
| T07 | MAJOR | Fable; ag | Keep selection PURE: defer Office member hashing/grouping to local preparation, then finalize unit count/priority before planning. Use full SHA-256/byte equality to verify h12 groups; a 12-hex filename prefix alone must not merge different payloads. Test repeated IDs, identical bytes under different IDs, mixed priorities and a forced prefix collision. |
| T08 | MINOR | Fable; ag | Align auxiliary prose/oracles with the actual core: row-17's K/P note still uses PDF-only K for rasters; encrypted/limit failures can have null totals or no candidates; CT-14 must distinguish filesystem-path leakage from intentionally retained member IDs. Add edge fixtures rather than accepting broad string-scan assertions. |

No additional approval or design round is required before writing tests for these owned corrections. Release still requires the specified runtime, CI, security and manual evidence.

Readiness: **88/100**. Equal-weight scoped checks: 21/23 prior dispositions closed for kickoff, plus code parity and no-run-hash pass; command cache identity, conversion bounds and --yes-file synchronization remain open (23/26 checks).

VOTE: **APPROVE-TDD**.
