# R5 — DRAFT-2 verification

Scope: `10_SPEC.md` DRAFT-2 against R3-01–26, binding decisions R1–R25, pinned core/GUIDE, and the SPEC 7.3/8.4/10 references in `20_SHELL.md` and `25_PACKAGING.md`. Paths below are relative to `docs/renewal/`.

Evidence: read all three current specifications and decisions; rechecked the core's 14 issue codes by AST; parsed the Plan JSON example; compared engine/shell code sets; ran the pinned triage source in memory on plain text, UTF-8 markup named CSV, and a 101-frame TIFF. No network/provider calls or implementation tests. Only this file is written; no git.

## R3 disposition

RESOLVED means the original defect has a specified correction, not passing implementation evidence. ACCEPT-REJECTION accepts the stated scope/tradeoff; new defects in the replacement contracts remain separately actionable.

| Finding | Status | One-line evidence |
|---|---|---|
| R3-01 | RESOLVED | SPEC 3.0/3.4 pins the actual states/reasons/issues; 3.2 deletes the issue-as-state rows; TRI-02 distinguishes returned issues from exceptions. |
| R3-02 | RESOLVED | SPEC 3.0 defines `is_raster` from Sniff formats; 3.2 row 17 now uses that predicate. |
| R3-03 | ACCEPT-REJECTION | SPEC RND-02/MAP-02 maps standalone `fN`; 13.6 reasonably retains one embedded-member unit with frame-0 processing and `W_MEDIA_MULTIFRAME`, matching core's inventory granularity. |
| R3-04 | PARTIAL | SPEC MAP-07/08 deduplicates IDs/Keys, but MAP-08's candidate occurrence count conflicts with body-wins placement and ASM-06's equality; 6.2 can duplicate blocks at identical-byte links. |
| R3-05 | RESOLVED | SPEC MAP-05/CNV-03 uses HWP parser-payload extraction and `payload_sha256`, avoids ZIP-opening HWP, and keeps stored streams pending. |
| R3-06 | PARTIAL | SPEC 3.2 adds V1–V4, but V3 does not require `candidate.page == N` for `pN`; unknown reason/issue literals lack a defined drift policy, and G2 bypasses validation. |
| R3-07 | RESOLVED | SPEC CLS-06, 3.2 rows 24/25 and ASM-04 distinguish incomplete inspection from FULL/PARTIAL and use actual page/frame counts for anchors. |
| R3-08 | PARTIAL | SPEC TRI-01/row 9c exposes G2b uncertainty; 13.1's G2a rejection is insufficient because valid UTF-8 does not validate CSV/TSV/JSON identity or prove media-free content. |
| R3-09 | RESOLVED | SPEC rows 0/0b/7/8 handle Sniff IO and member-versus-container errors; rows 24/25 explicitly precede positive OCR rows and retain known candidates. |
| R3-10 | RESOLVED | SPEC SNF-03/04/07 and 3.1 add 16-byte sniffing, bounded structural reads, core package markers, BigTIFF, ODF precedence and encrypted-package streams. |
| R3-11 | RESOLVED | SPEC PLN-01 and section 4 move final Plan after Render/Lookup; 10.1 makes `plan` use the same temporary conversion/rendering preparation. |
| R3-12 | PARTIAL | SPEC 7.1 binds endpoint/full command argv, but APR-07 only rehashes metadata; actual raster bytes and command environment/script identity remain unbound at send time. |
| R3-13 | PARTIAL | SPEC PLN-05/APR-02/06 adds request budgets, repeatable hashes and audit-only persistence; 13.2 rejects real billing metering reasonably but still omits R6's estimated worst-case cost cap. |
| R3-14 | PARTIAL | SPEC 5.1/LKP-04 fixes delimiter encoding, endpoint/template namespacing and basic record validation; command environment/script changes still reuse the same Key. |
| R3-15 | PARTIAL | SPEC GEN-06/ASM-09/10 correctly separates force/retry, stable provenance and edits; its new zero-publications promise conflicts with mandatory report/media publication. |
| R3-16 | ACCEPT-REJECTION | SPEC GEN-05/CNV-03/LKP-05 specifies staging, exclusive temps and per-artifact atomicity; 13.7 reasonably warns about unproven vault temps rather than deleting them. |
| R3-17 | ACCEPT-REJECTION | SPEC TRX-02/06 and 7.2 disclose inflight uncertainty; 13.3 reasonably declines a universal idempotency mechanism unsupported by the generic adapter contract. |
| R3-18 | PARTIAL | SPEC CLS-02/7.2/7.4 fixes decision, consent, error.exit and warning fields; 7.1's normative example still violates its own list/count equations and non-executable unit shapes remain undefined. |
| R3-19 | RESOLVED | SPEC 7.5/10.3 maps conversion, render, oversize, cache and runtime-provider failures explicitly; CNV-01's empty-output failure exits 2. |
| R3-20 | ACCEPT-REJECTION | SPEC SNF-01/01b adds roots, exclusions, deduplication and collision preflight; 13.5's explicit collision failure is a valid alternative to renaming. |
| R3-21 | RESOLVED | SPEC CNV-05/SEC-08 mandates offline Core, stream inputs, disabled plugins/remote clients, excluded network extras and a forbidden-socket oracle. |
| R3-22 | ACCEPT-REJECTION | SPEC 8.2 binds MIME, forbids redirects, declares proxy routing and bounds reads; 13.8's documented `shlex.split(posix=True)` grammar is deterministic on every OS. |
| R3-23 | PARTIAL | SPEC SNF-08/RND-05/06 adds Office preflight, cumulative budgets and pixel bounds; actual decompressed-byte enforcement and an explicit Office member-read cap remain unspecified. |
| R3-24 | PARTIAL | SPEC ASM-03/11 fixes YAML/comment attributes and provider text; 13.4's lossy rendering is sound, but unescaped dynamic headings can still inject reserved markers. |
| R3-25 | RESOLVED | SPEC conventions/ASM-P2/P3/SEC-02/06 distinguish path namespaces, engine diagnostics and verbatim document/member data, and describe raster attachments correctly. |
| R3-26 | PARTIAL | SPEC section 11 adds useful oracles, explicit time and casefolding; 13.9 still confuses core evidence with an independent mdflow classification oracle, and several new contracts are contradictory. |

Totals: 10 RESOLVED, 11 PARTIAL, 5 ACCEPT-REJECTION, 0 wholly UNRESOLVED. None of the accepted rejections establishes implementation correctness.

Remaining R3 fixes before TDD:

- **R3-06/08:** Require PDF ID/page agreement, structural consistency and an explicit unknown-code/reason policy. Validate claimed G2a format independently; UTF-8 alone must not select T. The probe's markup `.csv` is UTF-8 yet core reports `unknown/none/unsupported_format`; row 9 would override that with NONE.
- **R3-12/14:** Hash/verify the bytes actually read for transmission. Freeze execution configuration; include behavior-affecting command environment/configuration and script identity in the command fingerprint/Key, or explicitly declare and document a narrower cache-validity contract. Construct requests from the exact validated canonical endpoint; reject URL userinfo/query/fragment rather than silently dropping them only from the consent representation.
- **R3-13:** Keep billing explicitly uncertain, but include `estimated_max_cost = cost_hint * max_requests` or null in the hashed Plan/modal. Four requests at 0.004 with two retries have estimate 0.016 and estimated ceiling 0.048; a request-count cap is not itself an estimated USD ceiling.
- **R3-18:** Replace the 7.1 example with a complete validating object: it currently has one uncached unit, `units_total=5`, `units_cached=1`, and `requests_to_send=4`. Specify every required/optional/null field and pending-state contract.
- **R3-23:** Bound actual decompressed reads and explicit per-member Office media reads, not just declared central-directory totals; apply those bounds before parsing/extraction allocations.
- **R3-24:** Apply reserved-marker escaping to all dynamic heading fields, not just provider text/comment attributes. A model/source ID containing `<!-- /mdflow:ocr -->` survives the heading's newline-only replacement. Retain original identifiers/text in the ledger.
- **R3-26:** Generate factual input evidence from core; maintain independently reviewed mdflow row/route/need/action expectations. Core never emits mdflow classifications. Scope cross-OS hash guarantees to equal prepared raster bytes and pinned rendering inputs, or prove stronger portability separately.

## New DRAFT-2 defects

### R5-N01 — BLOCKER — Schema failure is bypassed on newly triaged G2

Location: `10_SPEC.md:TRI-01/03; 3.2 rows 9/9a/9c/10/11; section 11 TRI-03`.

Defect: All NATIVE formats now run triage, but only G1 reaches schema/exception rows. A G2b schema-2 report selects row 9c and converts; valid UTF-8 CSV can select row 9 even after triage failure. This contradicts TRI-03 and R12's fail-loud schema gate. V1–V4 is likewise only reached after these shortcuts.

Concrete fix: “Handle schema/version errors and triage exceptions for every NATIVE source before format-specific rows. Validate the report envelope before reading coverage fields. Keep format-specific core-format exceptions explicit; never bypass the schema gate for G2.”

### R5-N02 — BLOCKER — New Plan invariants cannot represent pending work

Location: `10_SPEC.md:SEL-01/02, PLN-04/05, RND-03/04, 5.1, 7.1`.

Defect: Oversize requires zero Render calls and `requests_to_send=0`, while 7.1 requires a non-null raster hash for every unit and counts every uncached Key as a request. Five unrendered uncached units therefore require both zero and five requests. Render-failed/unsupported/skipped units have the same missing-hash/status problem. The 101-frame probe also shows that raw core has no total-frame field from which PURE classification can calculate the promised uninspected-frame remainder.

Concrete fix: “Separate inventory/placement records from executable request records. Give non-executable units an explicit status/reason and nullable raster metadata; only rendered eligible misses enter the request queue. Define total/selected/skipped/pending equations and oversize semantics. Supply actual frame inventory as an explicit local-preparation input, or represent unknown remainder as null with a documented meaning.”

### R5-N03 — BLOCKER — Run hash requires a planning barrier absent from execution

Location: `10_SPEC.md:section 4; APR-02/04; 8.4; 7.3/10.1`.

Defect: Section 4 runs stages 1–12 for each file sequentially, but Approve needs a run hash of every file's final Plan before later files have been planned. An approved earlier file can populate a shared Key and change later cached flags/hash values, invalidating the advertised run-hash replay or causing duplicate requests. `approve_required` is promised to carry `run_plan_hash`, but its event shape only specifies a per-file Plan.

Concrete fix: “Prepare and finalize all file Plans before any approval/execution; define one frozen run request queue and shared-Key ownership. Calculate the aggregate hash at that barrier, then approve and execute without silently changing approved Plans. Specify the exact run-hash event/stdout envelope and cache-change replan behavior.”

### R5-N04 — MAJOR — New occurrence invariant has two incompatible owners

Location: `10_SPEC.md:MAP-08, ASM-06, 6.2, section 11 PLN-05/MAP-01..08`.

Defect: MAP-08 sets `occurrences` to the duplicate candidate count, then says body placement wins when counts differ; no update rule reconciles ASM-06's equality. Section 6.2 explicitly emits both units at a single same-hash link: two identical-byte members with two links can produce four OCR blocks. PLN-05's “same image twice -> 2 units” also conflicts with unique-ID collapse unless it specifically means two different member IDs.

Concrete fix: “Track candidate occurrence count separately from actual placement count. Set emitted occurrences after mapping, including the unmapped appendix rule. Assign each physical link one OCR placement for a shared raster, retaining contributing source IDs as provenance. Distinguish repeated references to one member from distinct members with identical bytes in every oracle.”

### R5-N05 — MAJOR — Zero publications conflicts with compulsory writes

Location: `10_SPEC.md:GEN-05/06, CNV-03/04, RPT-01, 10.4; section 11 GEN-06`.

Defect: GEN-06 now promises zero files published, not only zero Markdown rewrites. CNV-03 republishes every extracted media file, CNV-04 describes media republication from cache, and RPT-01 writes a new report when `--report` is unchanged. The warm-run oracle checks output mtimes but does not resolve these required publications.

Concrete fix: “Warm success publishes no changed Markdown/media/cache content: compare existing bytes before replacement. Define audit-report writes and any seen-metadata updates as explicit exceptions. Test media/cache mtimes and `--report`, not only Markdown.”

### R5-N06 — MAJOR — Foreign inflight state is not proof of interruption

Location: `10_SPEC.md:LKP-02/05, TRX-02/06, GEN-09; 7.2`.

Defect: Every inflight entry owned by another process is treated as interrupted, including a still-running CLI/another vault. There is no cache lock or owner-liveness rule. Also, LKP-05 permits continuing after cache-write failure while TRX-02 requires durable inflight publication before sending; which rule prevents an unrecorded request is unspecified.

Concrete fix: “Acquire an exclusive cache/run lock or per-Key claim with live-owner verification. Retry only abandoned claims. If inflight publication fails, send no request for that Key and report E_CACHE_IO; if final commit fails, retain the durable inflight record and disclose uncertainty. Do not sweep another live writer's temporary files.”

### R5-N07 — MAJOR — Cancellation deadline contradicts unit completion

Location: `10_SPEC.md:GEN-09, 8.2, section 11 GEN-09; 20_SHELL.md:SHL-16`.

Defect: “Stops after the current unit” cannot guarantee exit/report/cleanup within five seconds while a provider may block for 120 seconds plus retry backoff. Windows TerminateProcess is not a catchable shutdown path and cannot guarantee Python report emission, exit 130 or child cleanup. The shell appropriately leaves native behavior TODO-VERIFY, while SPEC's oracle asserts it unconditionally.

Concrete fix: “On cooperative cancellation abort current waits/requests and terminate owned descendants within a specified deadline; preserve interrupted request state. Define tested catchable mechanisms per OS. Forced termination is an interrupted native exit with recovery on restart, not a promised report/130. Align the engine oracle and shell supervision contract.”

### R5-N08 — MAJOR — Closed-code collector rejects the required raw report

Location: `10_SPEC.md:GEN-10, TRI-04, 7.4/7.5, section 11 GEN-10`.

Defect: The new oracle requires every `code` in reports/progress/ledger to belong to 7.5. Required verbatim `files[].triage.issues[].code` contains core values such as `external_media` and `corrupt`, which are absent from that list. Ordinary valid raw reports fail the new gate.

Concrete fix: “Validate mdflow issue/error fields against 7.5 and raw triage fields against the pinned core contract separately. Exclude `triage` from the mdflow collector; never rewrite core codes to satisfy it.”

### R5-N09 — MAJOR — Full-Plan event can exceed its new transport limit

Location: `10_SPEC.md:APR-03, 7.1/7.3; 20_SHELL.md:SHL-13`.

Defect: `approve_required` must carry the full Plan on one line, now limited to 1 MiB. No Plan-size bound limits candidate-ID lengths, unit metadata or raised unit limits. Valid Office IDs can produce a Plan larger than the shell's hard framing limit; the shell must then fail before it can show consent.

Concrete fix: “Before Approve, enforce a defined serialized Plan/event byte limit and report a small E_PLAN_OVERSIZE diagnostic without egress, or define a versioned chunk/reference transport consumed by the shell. Never truncate a hashed Plan.”

### R5-N10 — BLOCKER — Per-file shell replay changes the hashed root

Location: `20_SHELL.md:SHL-12/15; 10_SPEC.md:SNF-01, 7.1, 8.4/10`.

Defect: Initial directory input `inputs` gives `inputs/sub/a.pdf` logical path `sub/a.pdf`. Replaying that file alone makes it a file root with logical path `a.pdf`, changing both its Plan hash and output location. Retaining the original directory invocation instead replays the batch, contradicting SHL-15's one-file-at-a-time description. No root-preserving file-selection API exists.

Concrete fix: “Replay the exact original root/batch invocation and approve the applicable file hashes using SPEC's existing repeatable --yes/run hash, with fresh Plans when dependencies change. Alternatively, specify an explicit root-preserving selection contract in SPEC and consume it by reference; do not invent a shell-only flag.”

### R5-N11 — MAJOR — Incorporation references retain stale code/version contracts

Location: `20_SHELL.md:SHL-11/14/17/19, section 6; 25_PACKAGING.md:PKG-06, Objections; 10_SPEC.md:7.5/8.4/10.1`.

Defect: Shell's supposedly exhaustive code table omits 13 current codes and retains deleted `W_TRIAGE_COVERAGE`. Packaging names only four version fields and rejects protocol/schema fields as absent although SPEC now returns them. Shell's modal checklist does not expressly include new `max_requests`/`units_interrupted`, despite the incorporated 8.4 list.

Concrete fix: “Regenerate en/ko code tables from current 7.5; remove W_TRIAGE_COVERAGE. Specify and test the current version response including protocol=1, triage_schema=1 and Pillow/render compatibility; update obsolete rejection prose. Display request budget and interrupted-unit disclosure from 8.4.”

Missing shell codes: `E_CACHE_IO`, `E_OUTPUT_COLLISION`, `E_PROVIDER_INTERRUPTED`, `W_CORE_DEPENDENCY`, `W_DUPLICATE_INPUT`, `W_EXTERNAL_MEDIA`, `W_IMAGE_PROBE`, `W_MEDIA_MULTIFRAME`, `W_OUTPUT_EDITED`, `W_OUTPUT_TRUNCATED`, `W_STALE_TEMP`, `W_TRIAGE_PARTIAL`, `W_UNRESOLVED_EMBED`.

### R5-N12 — MAJOR — Collision preflight result is absent from classification

Location: `10_SPEC.md:SNF-01b, 3.2, section 4, 7.5`.

Defect: SNF-01b introduces E_OUTPUT_COLLISION with report_only, but no table row handles it. A colliding source with otherwise complete/no-candidate evidence reaches row 12 and returns convert_only, contradicting the preflight result; its source route need not be UNSUPPORTED to catch another terminal row.

Concrete fix: “Add a terminal preflight-error row before positive classification for E_OUTPUT_COLLISION, preserving the sniffed route and reporting report_only. Test two valid sources whose normalized publication paths collide; the second must never reach Convert/Render/Write.”

## Cross-document reference result

| SPEC authority | Consistent portions | Remaining mismatch |
|---|---|---|
| 7.3 progress / 7.4 report | SHL-11/12/13 and PKG-01/08 use stderr JSONL, stdout report, direct engine publication and no stdin/staging protocol. | Run-hash envelope is missing; full Plan versus 1 MiB is unresolved; shell diagnostics are stale (N03/N09/N11). |
| 8.4 consent | SHL-14/15 requires deliberate approval, immutable replay, fresh consent and no persisted authorization; packaging does not invent another consent channel. | Nested per-file replay changes root/hash; request/interruption disclosures need synchronization (N10/N11). |
| 10 CLI/version/cancel | `-m mdflow`, direct `-o`, selected interpreter, version/classify probes and R10's diagnostics-only setup align. Existing version/classify selftest recipe remains valid even though SPEC now also exposes selftest. | PKG-06's version assumptions/rejection text are stale; cancellation promises differ; headers still name R1–R23 rather than current R1–R25 (N07/N11; header update MINOR). |

R25's no-extra HWP rule agrees with SPEC GEN-01 and packaging section 1. Runner-label availability is outside this protocol verification; no external availability claim was re-certified.

## Readiness

Design readiness, not implementation acceptance: ten equal-weight checks. Five pass: exact core vocabulary (3.0); mainstream raster/HWP mapping (RND-02/MAP-05); explicit offline/MIME/redirect/proxy policy (CNV-05/8.2); per-artifact atomic publication (GEN-05); exhaustive engine exit-code map (7.5/10.3). Five fail: total validated classification (N01/N12); executable and run-wide Plan/consent (N02/N03/N10); occurrence/cache/warm-run invariants (N04–N06); independent test/cancellation/transport oracles (R3-26/N07–N09); synchronized shell/packaging contract (N11).

Must fix before TDD: the remaining R3 corrections listed above and R5-N01–N12. Do not defer contradictory schemas, consent/root semantics or acceptance oracles to implementation.

Verdict: **REJECT**. Readiness: **50/100**.
