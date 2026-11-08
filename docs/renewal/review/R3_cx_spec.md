# R3 — Core/spec adversarial audit

Reviewed `10_SPEC.md` against binding `00_BRIEF.md`, `01_DECISIONS.md` including amended R10 and R15–R18, and the pinned references. Locations below are relative to `docs/renewal/`. Core line numbers refer to `ref/ocr_triage_0.3.5.py.txt`.

Evidence: read all 526 spec lines and 977 core lines plus GUIDE; extracted issue literals and REQ definitions with AST/regex; executed the pinned core in memory on generated TIFF/Office bytes. A capped-PDF probe substituted only the parser document, exercising the actual core loop and verdict logic. Decision-table witnesses below evaluate the written predicates, not an engine implementation. No real OCR/network calls. Only this review file is written.

## A. Exact core contract and vocabulary

The following inventory is exact for the reference; mdflow vocabulary must be distinguished from it.

| Core surface | Actual contract / evidence | Spec consequence |
|---|---|---|
| Verdict | `ocr_recommended`, `review`, `no_candidates`, `unknown`; high candidates win over low; fatal inspection can retain candidates while verdict stays `unknown` (214–221, 387–428) | Verdict literals are correct; verdict alone does not establish exhaustive inspection. |
| Coverage | `complete`, `partial`, `none`, `not_applicable`; `reason` is optional explanatory text, not an enum (30–56, 173–185) | `media_not_inspected` and `unsupported_format` are issue codes, never states. `not_run` is correctly identified as mdflow-only. |
| Root fields | `decision`, `coverage`, `summary`, `candidates`, `issues`, `file`, `options`, `schema_version=1`, `rules_version="1"`, `pages`, `rasters`; `media` is added by Office/HWP handlers (30–56, 626–627, 901–902) | Preserve this shape; do not require `media` for every format. |
| File / coverage / summary | `file={sha256,bytes,format}`; format is `unknown|pdf|image|hwp|docx|pptx|xlsx|hwpx`. Coverage has `pages_total`, `pages_inspected`, `limits`; summary has `scope="inspected"`, `pages_with_text`, `nonspace_chars`, `image_occurrences`, `candidates_high`, `candidates_low`, optionally `media_small` (30–56, 615–655) | Sniff's `png`, etc. are a separate format namespace. PDF totals are not `len(pages)`. Summary counts observations, not necessarily unique units. |
| Candidate | `{id,kind,page,priority,reasons}`; optional `decor`. Kind is `page|image`, priority `high|low`. PDF is `pN/page/N`; raster is `image` or `fN`, kind `image`, page `null`; embedded media is member/stream ID, kind `image`, page `null` (63–73, 419, 439–454, 883–895, 973–974) | `media` and `normal` are mdflow values, not core values. Candidate IDs need not be unique. |
| PDF evidence | `pages[].n`, not `pages[].page`; `bbox_pt`, `rotation`, `chars`, `nonspace_chars`, `unresolved_glyph_share`, `cid_count`, `replacement_count`, `private_use_count`, `vector_objects`, `image_area_ratio`, `image_count`, `images_truncated`, `images`; optional `text_sample` only with samples enabled (348–370) | Validate candidates against actual page numbers and total coverage. |
| Raster evidence | `{id,frame,px,mode,dpi_tag,exif_orientation,bytes}`; failed probe retains an `image` candidate with nullable evidence (431–485) | Frame number/orientation and probe failure require explicit rendering policy. |
| Media evidence | `{id,where,px,bytes,ext,decor,references}`; PPTX `where` may be `{slide:N}`; references are `{part,id}` (868–877). HWP also has `payload_sha256`, `payload_kind`, `stored_bytes`, `stored_sha256` (951–966) | Media rows can repeat per occurrence. HWP payload bytes and stored stream bytes can differ. |

### Vocabulary missing from the decision/handling table

Not every literal needs a separate routing row. Every literal does need an explicit preservation, visibility and execution policy; table 3.2 currently supplies none beyond verdict/count inference.

| Exact literal | Type and actual meaning | Required explicit policy |
|---|---|---|
| `scan_like` | Reason; high PDF candidate, or embedded image with document text under 30 nonspace chars (373–380, 887–895) | Preserve; apply format-specific mapping; never assume it means a PDF. |
| `suspect_text_layer` | Reason; high PDF candidate, including pages with no raster images (381–384) | Render the page; text presence does not exclude it. |
| `low_text_nonblank` | Reason; low PDF candidate based on image/vector evidence (373–378) | Preserve as low; default includes it, normal-only leaves an explicit pending marker. |
| `image_with_text_layer` | Reason; low PDF candidate despite at least 30 text glyphs (379–380) | Same low-priority policy; do not convert-only merely because text exists. |
| `embedded_image` | Reason; high or low Office candidate, low HWP candidate (887–895, 973) | Use actual candidate priority, payload and occurrence mapping. |
| `standalone_image` | Reason; high `image`/`fN` candidate (439–454) | Map every inventoried frame, not a fabricated single candidate. |
| `decor_media` | Reason plus `decor=true`; low candidate only for exclusive decorative references under complete coverage (814–885) | Preserve low priority and disclose whether included; decor is not proof of no text. |
| `external_media` | Issue; remote image deliberately not fetched; coverage becomes partial (555–559, 695–700) | Never fetch; expose unresolved media and incomplete coverage. |
| `unresolved_embed` | Issue; embedded relationship missing; partial (795–799) | Surface unresolved inventory, not merely a generic unknown verdict. |
| `zip_limit` | Issue; bounded Office/HWP inspection, not mdflow's archive error family (561–564, 656–657, 975–977) | Distinguish incomplete triage from container rejection; retain known candidates and unresolved remainder. |
| `page_cap` | Issue; PDF inspected at most 1000 pages; total remains available (404–421) | Report uninspected pages; never infer FULL from inspected count alone. |
| `frame_cap` | Issue; only first 100 frames inspected (435–463) | Report an unknown remainder; do not silently flatten. |
| `missing_dependency` | Issue; normal returned report, not necessarily a raised exception (387–396, 908–914) | Surface dependency diagnosis with UNKNOWN coverage; do not wait for `E_TRIAGE_FAIL`. |
| `unsupported_compression` | Issue; package member probing refused, partial coverage (566–573) | Retain refusal; do not silently decompress it later without an explicit bounded policy. |
| `image_probe_failed` | Issue; dimensions/frame inventory unavailable; candidates may remain and coverage need not become partial (464–485, 853–860) | Keep candidate; validate rendering; report unresolved failures independently of verdict. |
| `unsupported_media` | Issue; unsupported HWP/HWPX encoding; candidate retained (837–842, 945–950) | Pending unsupported format with visible unit accounting. |
| `encrypted` | Issue; PDF encryption detected by core, including encryption not requiring an opening password (400–424) | Map to protected handling even when Sniff opened it successfully. |
| `corrupt` | Issue; sometimes partial evidence survives (199–213, 425–428, 599–611, 658–660) | Define fatal/partial handling; preserve issue details and known inventory. |
| `too_large` | Issue; core limit 256 MiB, no hash/inspection (134–138) | Account for user raising mdflow's 200 MiB default above core's limit. |
| `media_not_inspected` | Issue; nonempty Markdown/HTML/XML/RTF; verdict unknown, coverage none (159–172) | Warning plus UNKNOWN need; never use as a coverage state. |
| `unsupported_format` | Issue; unknown input or unrecognized package (188–198, 646–652) | UNKNOWN/report policy using issue membership, not coverage equality. |
| `parser_image_payload` | `media[].payload_kind`; supported HWP parser payload, possibly decompressed (960–965; GUIDE formats) | Extract/verify payload bytes against `payload_sha256`. |
| `stored_ole_stream` | `media[].payload_kind`; retained unsupported stored HWP stream (960–965) | Do not mistake compressed/stored bytes for a sendable image; keep pending unless decoded under an explicit supported rule. |

The issue inventory is exactly 14 codes: `corrupt encrypted external_media frame_cap image_probe_failed media_not_inspected missing_dependency page_cap too_large unresolved_embed unsupported_compression unsupported_format unsupported_media zip_limit`. The two payload-kind values above are neither reasons nor issue codes.

### R3-01 — MAJOR
Location: `10_SPEC.md:3.2 rows 13–15; REQ-TRI-01/04; Objections 1`.
Defect: Rows 13/14 are unreachable for actual core output because they compare issue codes to coverage state. Deferred contract discovery contradicts R18's now-readable references. Returned core issues are not equivalent to engine exceptions.
Concrete fix text: “Validate core coverage against `{complete,partial,none,not_applicable}`. Detect `media_not_inspected` and `unsupported_format` in `triage.issues[].code`; preserve the raw report and derive separate mdflow issues. Replace Objection 1 with the pinned field/vocabulary contract and exhaustive handling matrix above.”

### R3-02 — BLOCKER
Location: `10_SPEC.md:3.1, 3.2 row 17; REQ-CLS-01`.
Defect: Sniff emits `png|jpeg|gif|bmp|tiff|webp`; row 17 requires `format == image`, which is core's namespace. Literal evaluation of a valid PNG report reaches row 23, `convert_only`, preventing planned OCR for all standalone image formats.
Concrete fix text: “Define `is_raster := sniff.format in {png,jpeg,gif,bmp,tiff,webp}`. Use `is_raster` in row 17; retain `triage.file.format == image` as a separately validated core fact.”

### R3-03 — BLOCKER
Location: `10_SPEC.md:REQ-RND-02/03, MAP-02, 5.1, 6.1; 3.2 row 17`.
Defect: Core returns `f1`,`f2`, etc. for multi-frame TIFF/GIF/WebP, not `image`. A two-frame TIFF probe returned two high candidates with null page fields. Single-unit rendering and first-frame embedded rendering lose text-bearing frames; caps/probe failures leave inventory unresolved.
Concrete fix text: “Map each standalone `rasters[].id` to a page unit whose page is its `frame`, preserving candidate ID; render that frame. Inventory embedded frames before planning and give each derived frame an occurrence/frame identity. Preserve `frame_cap`/probe-failure remainder as unresolved and never claim complete OCR coverage.”

### R3-04 — BLOCKER
Location: `10_SPEC.md:REQ-CLS-02, 5.1, MAP-03/07, 6.2; REQ-TRX-01`.
Defect: Core emits duplicate candidate IDs for repeated references. The probe returned two identical `word/media/image1.png` candidates. IDs alone cannot identify placement. MAP-07 promises one call, but Lookup precedes all calls, so identical misses remain scheduled twice unless explicitly coalesced; matching a link line also misses inline occurrences.
Concrete fix text: “Keep occurrence records keyed by source ID plus deterministic reference/occurrence index; map all image-link occurrences. Build a unique execution queue by full cache Key, then fan one result out to every occurrence. Report occurrence counts and unique request counts separately; apply MAP-07 only when the full Key matches.”

### R3-05 — BLOCKER
Location: `10_SPEC.md:MAP-05/06, REQ-RND-03, 3.2 row 21`.
Defect: HWP is OLE, not ZIP. MAP-05 specifies placement only; MAP-06 requires “member bytes.” Supported HWP payloads can differ from compressed stored streams, so this cannot produce the bytes core observed. `stored_ole_stream` is not a usable image by implication.
Concrete fix text: “For HWP5 obtain parser image payloads through the pinned core extraction path (`extract_media`, GUIDE); verify `payload_sha256` before normalization and retain `stored_sha256` as separate provenance. Do not ZIP-open HWP or send stored OLE bytes as an image. Unavailable/unsupported payloads remain counted pending units.”

## B. Decision-table totality and ordering

### R3-06 — MAJOR
Location: `10_SPEC.md:3.2 rows 12, 15, 17–23; REQ-CLS-01/05`.
Defect: First-match selection gives one selected row for well-formed tuples, but does not validate the tuple. `no_candidates/complete` with nonempty candidates is accepted as T; `ocr_recommended/future_state` with one PDF page is accepted as S; candidate `p99/page=99` against only page 1 is also accepted as S. Unknown kinds become media because of `kind!=page`. These bypass the advertised safe fallback.
Concrete fix text: “Before positive rows, validate required field types, known enums, candidate IDs/kinds/priorities and page ranges. Contradictory reports select UNKNOWN with `W_TRIAGE_INCONSISTENT`; unknown vocabulary selects UNKNOWN with `W_TRIAGE_UNKNOWN_VALUE`, without OCR. Normalize only `high→normal`, `low→low`; preserve original priority separately.”

### R3-07 — MAJOR
Location: `10_SPEC.md:3.2 P/K definitions, rows 18–21 and note; REQ-ASM-04`.
Defect: `P=len(pages)` counts inspected evidence. In the capped-parser probe, total=1001, P=K=1000, state=partial, reason=`suspect_text_layer`, issue=`page_cap`; row 18 labels FULL. Rows 17–21 ignore incomplete coverage. The folding note also conflicts with K's page-kind-only definition. Assembly's every-page anchors require a separate actual total.
Concrete fix text: “Use `coverage.pages_total` for PDF total, `pages[].n` for inspected inventory, and one documented candidate-page normalization. FULL requires complete validated inventory and all actual pages selected. Partial/none coverage yields UNKNOWN with known candidate units retained and an explicit uninspected remainder; actual PDF page count drives anchors.”

### R3-08 — MAJOR
Location: `10_SPEC.md:REQ-TRI-01, 3.1 G2, 3.2 row 9`.
Defect: Skipping all G2 triage labels Markdown/HTML/XML/EPUB/IPYNB/MSG as NONE/T without establishing media coverage. Core deliberately returns unknown/none with `media_not_inspected` for several of these. Even `.txt/.log` are only not_applicable after strict validation. This hides uncertainty despite F4 and R18.
Concrete fix text: “Run available plain-text/media-uninspected triage. Assign NONE only after validated not_applicable or complete no-candidate evidence. G2 formats without such evidence remain UNKNOWN/convert_only with an explicit media-not-inspected issue; `not_run` never proves NONE.”

### R3-09 — MAJOR
Location: `10_SPEC.md:3.2 rows 7/8/15/23; REQ-CTR-01/02; section 4`.
Defect: Row 7's ‘no zip bound issue’ still permits `E_ZIP_PATH`, then preempts row 8's ‘any E_ZIP_*’. Row 8 would stop a container for the member path error that CTR-01 says must allow siblings to continue. `E_SNIFF_IO` has no terminal classifier rule. Row 15 can discard surviving candidate inventory from a core fatal/partial report without unresolved-unit accounting.
Concrete fix text: “Separate member path errors from container bound errors. Container bounds select report_only before recurse; invalid members alone are rejected while siblings continue. Specify terminal Sniff IO handling before triage access. UNKNOWN preserves observed candidates as evidence/pending inventory and records why execution is unavailable. Call the table ordered first-match, not mutually exclusive predicates.”

### R3-10 — MAJOR
Location: `10_SPEC.md:REQ-SNF-03/04/05/07; 3.1A/B`.
Defect: Eight bytes cannot identify WebP's bytes 8–11. ZIP `mimetype` contents require more than the central directory; corruption validation requires reads excluded by SNF-07. OOXML sniff markers differ from core's exact `word/document.xml`, `ppt/presentation.xml`, `xl/workbook.xml`; HWPX core uses `Contents/content.hpf`. BigTIFF magic is omitted. Arbitrary CFB renamed `.docx` is not proof of encryption; normal ZIP ODT is routed CONTAINER before its LEGACY extension row.
Concrete fix text: “Permit a bounded 16-byte header plus enumerated bounded parser/member reads. Align package identity checks with the pinned core markers; add BigTIFF and explicit ODF/other ZIP-family precedence. Identify encrypted OOXML by its encrypted-package streams, not extension alone; carry actual encryption evidence and format disagreement.”

## C. Internal contracts, consent, durability and security

### R3-11 — BLOCKER
Location: `10_SPEC.md:REQ-PLN-01/02/05/07, 4, 5.1, 7.1, 10.1/10.4`.
Defect: Plan is PURE before Convert/Render/Lookup, yet contains raster hashes, media appearance order, source facts, cache hits and final send count unavailable in its inputs. No stage finalizes/rehashes after Lookup. `plan` both promises stages 1–8 (including Convert) and forbids Convert/writes. Plan/run cannot reliably yield the same approvable hash.
Concrete fix text: “Distinguish candidate selection from final Plan construction. Prepare local rasters, resolve inventory, perform cache lookup, then construct/hash the immutable executable Plan from explicit snapshot, unit and lookup inputs. `plan` performs the same local preparation without persistent writes or provider calls. Use stable ID ordering for Plan; assembly independently uses appearance order. Document the local-preparation refinement to R2.”

### R3-12 — BLOCKER
Location: `10_SPEC.md:REQ-PLN-02, REQ-APR-02, 7.1, 8.2/8.4`.
Defect: `destination` ambiguously means full URL in JSON but host in prose; command identifies only argv0. Changing `python script.py --endpoint A` to endpoint B leaves the command destination/hash unchanged. Runtime command/config identity is absent. No requirement binds later source reads/provider settings to the hashed snapshot. Consent can describe different work from execution.
Concrete fix text: “Hash the exact canonical scheme/host/port/path endpoint, full parsed command template, declared egress, nonsecret behavior-affecting configuration and all final request identities. Freeze the prepared bytes/configuration through execution; fail or replan on source/config changes. Verify approval against that final immutable object immediately before any request.”

### R3-13 — MAJOR
Location: `10_SPEC.md:REQ-PLN-01/05, REQ-APR-02/05/06, 7.1/7.2/7.4, 10.2; decisions R6`.
Defect: R6 requires an estimated cost cap; only a hint/estimate exists, with no request/retry cap budget. Unknown cost has no explicit approval treatment. One `--yes HASH` cannot approve multiple sensitive/large per-file Plans in one run. APR-06 says consent is never persisted while APR-05 and ledger require persistence.
Concrete fix text: “Include maximum permitted requests/retries and estimated cost ceiling, or explicit unknown-cost acknowledgement, in each approved Plan; stop before exceeding its request budget. Accept a set of per-file hashes or a hashed run manifest. Persist consent as audit evidence only; never reuse it as authorization. Include consent/null in the run-report schema.”

### R3-14 — MAJOR
Location: `10_SPEC.md:5.1 Key, REQ-LKP-01/04, 7.2, 8.2; decisions R4`.
Defect: Same raster/provider=`openai-compatible`/model/prompt/dpi hits the same cache after changing endpoint; `command` script/template changes also reuse stale results. `|` is unescaped in user-controlled model labels. Cache validation is unspecified beyond “malformed.” This can misattribute text/provenance without a new call.
Concrete fix text: “Namespace the R4 cache tuple by a canonical provider-configuration fingerprint, including endpoint or command identity. Serialize tuple components unambiguously as canonical JSON. Validate record version, derived key ID, raster digest, status/text/error shape and configuration namespace before accepting a hit; otherwise warn and miss.”

### R3-15 — MAJOR
Location: `10_SPEC.md:REQ-GEN-06, REQ-LKP-02/03, REQ-ASM-09, 6.4/6.5, 10.4`.
Defect: Unchanged reruns with `--force` or failed units must call again, contradicting the unconditional zero-call requirement. Provenance `at` is not tied to stored transcription time, so warm runs can change body hashes. ASM-09 trusts the existing claimed body hash and ignores changed required metadata, permitting stale headers or undetected body edits.
Concrete fix text: “Zero-call/no-rewrite applies after a fully successful warm run without force. Retry failed/unknown work under the documented consent rules. Reuse ledger creation time for OCR provenance; generated time changes only on write. Recompute the existing body's digest and compare all required semantic frontmatter excluding generated; define an explicit edited-output policy.”

### R3-16 — MAJOR
Location: `10_SPEC.md:REQ-GEN-05/09, REQ-CNV-03, REQ-TRX-02, section 4, SEC-04/09`.
Defect: Calling Core extract-media directly into the final media directory does not establish GEN-05 atomicity. Per-file replace does not make output plus media plus ledger transactional. SIGKILL cannot guarantee cleanup. Cache/write failures and rollback behavior are unspecified; PID temp names can collide for concurrent same-process writes.
Concrete fix text: “Stage Core output in a private directory; validate and atomically publish media before publishing Markdown that references it. Use exclusive unique temporary files with restrictive permissions; define file-level atomicity separately from crash durability. Specify cache-write failure reporting and stop policy. Cleanup is guaranteed on handled exits; recover stale temp state after uncatchable termination.”

### R3-17 — MAJOR
Location: `10_SPEC.md:REQ-TRX-02, section 4 Transcribe idempotency, 7.2; decisions R4/R13`.
Defect: A process can die after remote success but before ledger commit. An atomic cache write cannot close that external side-effect window; rerun repeats the request. “Idempotent via ledger” omits the uncertainty state and can conceal duplicate cost.
Concrete fix text: “Document successful committed rerun idempotency separately from crash recovery. Durably mark request identity in-flight before sending; use provider idempotency where supported. After an uncertain interruption, report an indeterminate unit and require explicit retry authorization. Extend ledger/report status contracts accordingly; do not promise exactly-once remote execution.”

### R3-18 — MAJOR
Location: `10_SPEC.md:REQ-CLS-02, REQ-RPT-02, 7.1–7.5, 8.1/8.2, SEC-07, header/Objections`.
Defect: Classification lacks `decision` required by Plan; Unit fields differ between 5.1 and 7.1; Plan example has batch=3 despite R17's 1 and counts that do not match its shown list. Report omits required consent. `E_PROVIDER_HTTP:exit=N` and SEC-07's unnamed warning violate the closed code list. Failed-unit/report shapes and non-native triage nullability lack a complete schema. Header still binds only R1–R14.
Concrete fix text: “Publish normative typed schemas with required/optional/null fields, counter invariants and examples that validate. Set batch=1; distinguish abbreviated examples from complete contracts. Add classification decision and report consent; encode child exit status as a separate numeric field and add a named truncation warning. Bind amendments R10/R15–R18 and remove resolved objections.”

### R3-19 — MAJOR
Location: `10_SPEC.md:REQ-CNV-01, REQ-RND-04, REQ-PLN-04, REQ-TRX-03, 8.1, 10.3`.
Defect: A conversion failure with no OCR units can write an empty file and exit 0: exit 2 covers report_only/write failures only. Render errors and oversize pending work have no exit mapping. Mid-run `E_PROVIDER_CONFIG` is exit 4 in TRX but “raising aborts the batch” in 8.1; config precedence 1 is startup-only. Failures are not reliably observable from CLI status.
Concrete fix text: “Define an exhaustive code/status-to-exit mapping. File conversion/render/plan-bound failures produce exit 2 unless a higher defined outcome applies; provider failures produce 4. Startup configuration produces 1; runtime adapter exceptions become per-unit failures and sibling processing continues. Test every closed error code, including cache/report-write failures.”

### R3-20 — MAJOR
Location: `10_SPEC.md:REQ-GEN-07, REQ-SNF-01, REQ-ASM-02, 3.3, 7.4`.
Defect: “Input root” is undefined for multiple roots or standalone files; overlapping inputs can duplicate reports/requests, and equal relative names can overwrite outputs. An output directory inside a recursively walked input can become input on rerun. ZIP duplicate/case-colliding names can collide with member/index paths. Count/report guarantees lack a source-identity rule.
Concrete fix text: “Define stable root IDs and virtual archive/member identities. Discover inputs before writes, exclude output/cache/temp roots, deduplicate overlapping inputs, and preflight output/media/index collisions using target-platform rules. Reject or deterministically namespace collisions; report each logical source once.”

### R3-21 — BLOCKER
Location: `10_SPEC.md:REQ-CNV-05, 3.1B/G2, SEC-08; GUIDE formats/install`.
Defect: Non-egress conversion is asserted solely because recognized audio routes are blocked. Extension-only G2 admits arbitrary binary bytes as `.txt`; core conversion may independently recognize a format, and GUIDE explicitly documents optional network audio transcription and URI fetching. No offline converter/plugin configuration is mandated, so routing alone does not prove zero egress.
Concrete fix text: “Run Core in an enforced offline configuration with network converters, remote clients and third-party plugins disabled. Pass validated local streams with authoritative format hints; never hand URI strings to conversion. Validate claimed plain text. Test renamed audio and URI-like inputs with network calls intercepted and forbidden, including when optional audio dependencies are installed.”

### R3-22 — BLOCKER
Location: `10_SPEC.md:8.2 openai-compatible/command, SEC-08; REQ-TRX-03`.
Defect: Requests always label bytes `image/png`, although Render preserves JPEG. Default urllib redirect/proxy behavior is not constrained to the approved endpoint and can send credentials to a different host. `shlex.split` lacks a Windows argument contract. Provider output/result bounds are checked only after unbounded capture.
Concrete fix text: “Use the unit's validated MIME in the data URI; reject unsupported accepts. Disable redirects or require new consent for destination changes and never forward credentials across origins; make proxy routing explicit. Specify a cross-platform argv-array representation and bounded streaming stdout/HTTP reads with timeout and per-unit errors.”

### R3-23 — BLOCKER
Location: `10_SPEC.md:REQ-CTR-02/04, REQ-SNF-03, REQ-RND-01/03, REQ-LKP-01, SEC-04/05`.
Defect: Archive protections apply to CONTAINER while Office packages bypass that route and still reach Convert after bounded/failed triage. Limits are not defined across nested archives, and division by zero for zero compressed size is unspecified. There is no decoded-pixel/per-page raster memory bound before Render/Lookup, so byte/unit limits do not bound expansion.
Concrete fix text: “Apply archive preflight/decompression/path budgets to every ZIP-family parser and extraction path before allocation, including Office. Define cumulative nested budgets and zero-compressed-size behavior; enforce actual streamed byte limits. Bound decoded dimensions/pixels and per-run raster memory before rendering, report rejected units, and validate each final media/output destination before publication.”

### R3-24 — MAJOR
Location: `10_SPEC.md:6.4–6.6, REQ-TRX-04, SEC-05/06`.
Defect: Raw OCR text can contain `<!-- /mdflow:ocr -->` and forged mdflow markers. Model/provider strings are not escaped; unit IDs only replace quotes, and `-->` still breaks comments. YAML quoting only colon/hash leaves values such as `null`, `true`, leading `*`, newlines or quotes ambiguous. Delimiters and metadata are not safe serialization boundaries.
Concrete fix text: “Serialize metadata with a defined YAML-safe scalar encoder. Escape all comment attributes and reserved marker sequences in rendered content while retaining original OCR text in the ledger. Specify lossless decode/round-trip rules and adversarial fixtures. Constrain paths using platform-aware containment and a no-link-swap publication policy; a prior string-prefix check alone is not race-safe.”

### R3-25 — MAJOR
Location: `10_SPEC.md:Conventions, REQ-TRI-04, 6.7 ASM-P2/P3, SEC-01/02/06, REQ-TRX-04`.
Defect: ASM-P2 forbids triage data except decision in output, yet headings use candidate IDs verbatim. “No usernames/secrets in output” conflicts with faithful source/OCR text. Universal redaction conflicts with verbatim triage/text when user content matches a secret value. “Rasters never placed in a prompt” contradicts the multimodal user prompt. All-paths-relative also conflicts with raw member IDs, absolute cache paths and security's home-prefix representation.
Concrete fix text: “Scope metadata privacy rules to engine-generated metadata/diagnostics, preserving intentional document content. Explicitly permit source/unit identity and derived classification/counts. Redact credentials before diagnostic serialization; specify behavior for raw reports containing sensitive identifiers. Treat raster content solely as untrusted image data, never instructions. Define path namespaces and serialization separately for logical source paths, raw member IDs and runtime configuration.”

## D. Testability and requirement traceability

### R3-26 — MAJOR
Location: `10_SPEC.md:REQ-GEN-04/07/09, REQ-SNF-03/07, REQ-CLS-01/05, REQ-PLN-01/02/05/06, REQ-ASM-01/06/08/09, REQ-RPT-02/03; SEC-01–09; 10.4`.
Defect: These requirements lack a consistent oracle until the preceding findings are fixed. In particular, 100% against unspecified labels can certify the erroneous table; cross-OS plan-hash stability contradicts Windows-only case-insensitive sensitive matching. Pure Approve produces `approved_at` without an explicit timestamp input. JSON/hash/text byte encodings and final plan inputs are incomplete. Several normative mapping/security rules also have MAP/SEC/ASM-P IDs despite the promised `REQ-<AREA>-<NN>` convention.
Concrete fix text: “Assign one stable traceable ID to every normative rule, retaining aliases for existing IDs. Supply a versioned fixture/oracle manifest covering every row plus overlapping, malformed and incomplete cases. Define UTF-8/LF hash bytes, canonical number rules rejecting NaN/infinity, path/glob/case normalization, explicit time inputs, status/counter equations, and platform-specific exceptions. State measurable assertions for each REQ and SEC rule, including denied-network, crash, cancellation and resource-bound cases.”

Additional acceptance oracles required before TDD:

| Requirement(s) | Missing or contradictory oracle to resolve |
|---|---|
| GEN-01/03, GEN-02 | Distinguish pure-Python mdflow source from native transitive dependencies; pin the lock and supported Core/rules-version compatibility cases across required Python/OS combinations (R10/R12/R18). |
| GEN-05/09, SEC-04 | Per-artifact atomic visibility versus multi-artifact consistency, crash durability, handled cancellation and uncatchable kill; subprocess lifecycle and cache IO failure. |
| GEN-06, LKP-02/03, ASM-09 | Successful warm run versus retry/force; provenance timestamp source; edited body and semantic-frontmatter comparison. |
| SNF-01/06, GEN-07, CTR-01/02 | Input-root definition, skips, duplicate roots/members, collision behavior, nested/global limits, exact reporting identity. |
| TRI-01/03, CLS-01/04/05 | Complete known-vocabulary fixture set; malformed schema-1 reports; explicit meaning of unknown coverage and normalized priority. |
| PLN-01/02/05/06, APR-01–06 | Final Plan inputs/time, deduplicated send count, per-run approval set, cost ceiling and OS-independent sensitive matching. |
| RND-01/02/03/04, ASM-04 | Frame/orientation policy, normalization/encoder options and versions, actual page total, supported payload extraction, deterministic render-failure accounting. |
| TRX-03/04, ASM-06/08, SEC-07 | Runtime error mapping; exact enclosing-fence/trailing-whitespace algorithm; truncation order and warning; UTF-8 body hash and escaped-marker serialization. |
| RPT-02/03, 7.1–7.5 | Executable schemas, units-versus-occurrences count equations, consent/null and unresolved remainder, every error's exit outcome. |
| SEC-01/02/05/06/08/09 | Diagnostic versus document redaction, redirects/proxies/offline Core, publication containment, reserved marker handling, cache permissions and supported OS behavior. |

Clean subareas, with evidence: all 74 defined REQ IDs are unique and every REQ reference resolves; verdict spellings and schema_version=1 match core; row 16 correctly precedes positive OCR rows for empty candidate lists; R17 output-extension retention and explicit DPI are reflected in ASM-02/CLI; `none` is consistently the default provider. These do not repair the failures above. R15 clean-room shell implementation and R16 README disclosures are outside this engine-spec audit; no compliance credit is inferred from silence.

## Completeness scores and verdict

Scores assess readiness of the written spec for implementation, not implementation quality. Ten equally weighted checks per requested area; only fully satisfied checks receive credit.

| Area | Completeness | Evidence / justification |
|---|---:|---|
| (a) Core fields/vocabulary | 30/100 | Pass: verdict spellings, schema version, PDF pN identity. Fail: state/issue separation, format/kind mapping, frame preservation, occurrence identity, HWP payload extraction, exhaustive reason handling, exhaustive issue handling (inventory; R3-01–05). |
| (b) Total decision function | 20/100 | Pass: declared first-match/fallback semantics; empty-candidate guard precedes OCR branches. Fail: raster reachability, known-state validation, candidate consistency, coverage/total accounting, G2 uncertainty, ZIP precedence, terminal error coverage, K/folding consistency (R3-02/06–10). |
| (c) Internal contracts/security | 30/100 | Pass: REQ uniqueness/reference resolution; default-none and explicit egress declaration; R17 naming/DPI and batch=1 prose. Fail: Plan lifecycle, consent identity/budget, wire/error consistency, cache/idempotency, atomicity/crash model, path/archive bounds, enforceable security/serialization (R3-11–25). |
| (d) Testability | 30/100 | Pass: numerical bounds; explicit primary output templates; finite row-coverage target. Fail: independent fixture oracle, PURE inputs, cross-OS determinism, complete schemas/counters, exit/error oracles, retry/crash semantics, security/privacy oracles (R3-26 and oracle table). |

Verdict: **REJECT**. The spec is not TDD-ready: valid core inputs can lose frames/occurrences, final consent does not yet bind executable work, and several determinism/security guarantees lack enforceable contracts.
