# MarkItDown Flow | Product and engineering specification
**English pre-TDD handoff · Revision 1 · 28 November 2026**

**Product promise.** A user can point MarkItDown Flow at a folder, take the complete Markdown documents, and immediately find every source that needs external OCR. A document with 99 text pages and one scanned page produces no complete MD. On request, the user can inspect its composition or save its existing text as a clearly identified partial document. None of these three operations performs OCR.

**Design basis.** This specification develops the approved UX design of 28 November against [repository snapshot b9cc6355](https://github.com/greatgc-flow/MarkItDown-Flow/tree/b9cc63551e79e8ee0038fbadcdadd610f3206a65). Repository observations describe that snapshot. Requirements, wire examples, thresholds and fixtures below describe proposed behavior. The handoff ends before writing the first failing test.

## Reading guide

| If you own… | Start with |
|---|---|
| Product, UX or localization | §§1–4, 7–8 |
| Classification, PDF inspection or extraction | §§3, 5–6 |
| CLI, Obsidian integration or storage | §§8–11 |
| QA or release qualification | §§12–15 |

## 1. Decisions and boundaries

| ID | Decision | Observable consequence |
|---|---|---|
| D1 | One whole source is the unit of automatic conversion. A readable archive is an enumeration boundary. | One regular document or archive member receives one outcome. A container summary never increases the document total. |
| D2 | Default to local conversion of verified OCR-free files. Use positive evidence for both completeness and OCR need. | Mixed and scanned files go into the same OCR-required list. Uncertain files have their own reason. |
| D3 | Make composition preview and partial-text export explicit, independent operations. | The user can preview before running, export without previewing, and return to the original exclusion after either action. |
| D4 | Offer four levels of external handoff. | Inspect the list, open one original, export references, or copy selected originals. The user chooses the external tool and initiates any upload. |
| D5 | Treat photo metadata as a separate, optional action. | An installed ExifTool does not change conversion eligibility or silently add GPS to Markdown. |
| D6 | Retain useful existing protections. | Isolated interpreter, vault-contained shell output, bounded archive reads, edited-note protection and checked writes apply to the new routes. |
| D7 | Start with PDF for detailed composition and partial text. | Other formats may expose reliable structural counts. Each format advertises its supported actions. Missing capabilities have an explanation. |
| D8 | Keep the public 2.0.2 review candidate separate from this behavioral change. | Version and qualify the new policy separately. Do not reuse acceptance receipts bound to the old candidate. |

**Assumptions selected for TDD.** “Text” means usable text encoded in the source, including an existing text layer when its quality and correspondence can be verified. A photo or decorative logo by itself does not establish an OCR requirement. An uncertain inference never qualifies a document for automatic conversion. Desktop Obsidian and the local CLI are the two supported entry points. External transcription completion is owned by the user. The copy action creates copies, never relocates originals.

## 2. Current implementation and change impact

| Current evidence | Change needed | Reuse |
|---|---|---|
| The coordinator executes a remote plan/consent workflow when a provider is selected. Keeping OCR pending can produce notes containing pending markers. | Default entry points must call the strict operation even when settings contain an old provider. | Entry-point routing, busy reservation, cancellation, destination revalidation. |
| Classification expresses route, need, label, action, candidates and coverage. Some unknown or uninspected cases still take the conversion path. | Evaluate file eligibility before content conversion, raster generation, cache lookup for output, or publication. | Sniff, triage envelope validation, coverage, reasons and source hashing. |
| The engine's plan-only branch can still execute conversion and render before it returns. | Give preview an inspection path with its own effect boundary. | Read-only snapshot discovery and structural inspection. |
| Existing release output, report and progress types describe legacy OCR units. The result view derives status from errors and pending units. | Introduce explicit file outcomes and per-action results. An expected exclusion must display as such. | Existing JSON framing, version probe and result localization patterns. |
| Direct image conversion may invoke ExifTool automatically. Existing cache keys and note content can reflect that. | Start photo metadata reads only from the user's field-selection flow. Isolate new output/cache identities. | Absolute executable resolution, capability diagnostics and timeouts. |
| Recent history stores summaries. A forced cancellation can end without a final job report. | Persist per-file results for durable jobs and reconcile interrupted writes. | Existing file protections, cancellation UI, diagnostic redaction and history access. |

Source references: [classification](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/src/mdflow/classify.py), [pipeline](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/src/mdflow/orchestrate.py), [conversion](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/src/mdflow/convert.py), [coordinator](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/shell/src/ui/coordinator.ts), [results](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/shell/src/ui/results-modal.ts), [history](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/shell/src/pure/history.ts).

## 3. Classification, scope and accounting

### 3.1 Ordered file decision

Apply the following rows in order. Capture a primary reason for display and retain supporting evidence separately. Input identity and readability take precedence over content judgments about a stale or inaccessible source.

| Priority | Condition | Terminal outcome or next step | Complete output |
|---|---|---|---|
| 1 | Repeated selection of the same logical source, hidden entry under the active policy, linked directory, output/cache/work folder | Discovery skip with reason. Do not create a second work item. | None |
| 2 | Readable, permitted container | Enumerate bounded members. A blocked container with no accessible members has one exclusion record explaining the boundary. | No container MD |
| 3 | Identified protection, corruption, disallowed format, legacy conversion requirement or configured hard size limit | Excluded with the specific known reason. An unexpected read error or lost permission on a previously accessible original is a failure with retry guidance. | None |
| 4 | At least one reliable, located OCR-needed page or object | Excluded, OCR required. Stop further classification when the adapter allows it. A known candidate is sufficient even if later pages are uninspected. | None |
| 5 | No confirmed OCR need, but coverage is incomplete, a required dependency is unavailable, or material is unresolved | Excluded, undetermined. Keep the evidence and the missing scope. | None |
| 6 | Valid input with no document content | Excluded, empty. A valid blank page inside a document remains an inspected page. | None for a wholly empty document |
| 7 | All applicable content inspected, usable direct text/content, no OCR-required or unresolved material | Eligible. Convert the same snapshot. Post-check and commit the output. | One complete MD only on success; associated media if required by the converter |
| 8 | Eligible conversion yields unexpected emptiness, incomplete output, a write error or protected user edit | Failed with a specific corrective action. An identical verified result may instead be reused and counted as complete. | No replacement of an existing valid document |

A visually blank input is “empty” only when that conclusion is reliable. A damaged font map, an unavailable layout measure or an image showing a white sheet does not establish emptiness. A Core low-priority candidate needs an interpretation: confirmed meaningful image text goes to OCR required, positively identified decoration can pass, ambiguity goes to undetermined. A request limit, priority filter or warmed OCR cache cannot remove the exclusion.

### 3.2 Format matrix

| Family | Evidence needed for complete MD | Preview / partial behavior for the first implementation |
|---|---|---|
| TXT, LOG, CSV, TSV, JSON | Supported encoding and structure, decodable complete input, no material loss. Check legacy-encoded text for decoding failure. | Structural counts where available. Empty input gets the empty outcome. |
| PDF | Whole applicable page/object coverage, reliable text layer, no unresolved regions. Material embedded imagery with unknown content blocks eligibility. | Page and area preview; explicit partial export for mixed documents. |
| DOCX, PPTX, XLSX, supported HWP/HWPX | All applicable document parts, including embedded media, inspected under a supported adapter. Missing parts or unsupported embeds go to undetermined. | Known paragraphs/slides/sheets/images with units. Disable partial export until the adapter preserves positions and omissions. |
| MD, HTML, XML, EPUB and other compound formats | Apply existing input exclusions for generated files. Explicit sources need evidence about referenced or embedded material. A T label with an uninspected-media warning is insufficient. | Reliable structural fields only. If the adapter cannot establish completeness, exclude. |
| Standalone image, multi-frame image | A known OCR-needed image is excluded. Ambiguous image content is undetermined. No metadata-only “complete” note. | External handoff. Optional metadata for supported standalone JPG/JPEG/PNG. |
| Protected, unsupported, legacy or archive | Explain known barriers. A legacy derived copy alone cannot establish fidelity to the whole original. Apply size, nesting, member and path limits to archives. | Original location or archive member identity. A block never becomes a partial-export shortcut. |

### 3.3 Counts

For a stable enumeration: **admitted documents = complete + excluded + failed + unfinished**. OCR-required is a subset of excluded. Discovery skips, container rollups, reused outputs, copies and partial exports each have their own counts. If discovery is interrupted, show “discovered so far” and keep total unknown. Example: 100 processed = 68 complete + 30 excluded + 2 failed. Of the 30, 24 need OCR, four are undetermined and two are locked. Copying five or extracting partial text from one changes no term in that equation.

## 4. User journeys and UI behavior

| Entry or state | Primary action | Details and recovery |
|---|---|---|
| First use | Select interpreter, check connection, run two examples | Show OS-specific offline/online setup instructions, shell/engine paths and capability status. A text PDF and a mixed PDF must produce exactly one complete MD. API keys and optional tools are unnecessary. |
| Start a run | Add files or folders, review recursive scope and destination, then “Classify and convert” | Ribbon, palette, context menu and optional drop use one coordinator. Retain the current recursive default and display it. Restrict conversion drops to the job view so ordinary note attachments remain available. |
| Before saving | “Preview composition” | Open read-only view directly. Show detected format, coverage, page counts, area estimates where supported, and limitations. Closing it discards ephemeral results. |
| Work in progress | Reopen job or stop | Show discovery count before total is known. Once known, show inspected count, terminal counts and cancellation behavior. Closing a normal job window leaves it running. |
| Complete | Open MD or output location | Reused MD is labeled. A protected edit offers keep/open or save a distinct copy. |
| Excluded | Select reason, then source | OCR-required view offers open, reveal, copy paths, CSV, copy originals, preview and supported text-only extraction. Undetermined, protected and unsupported each have their own explanation and plausible next action. |
| Returned later | Open the recent run | Restore filters and results against the recorded source snapshot; check freshness before acting. Missing external originals offer locate-and-verify by digest. |
| Large selection | Select visible page or all matching | Display intended scope and selected count before copy/export. Filter changes clear a selection whose scope would become ambiguous. Show expected bytes where known. |
| Keyboard or localized UI | Use the same actions without a mouse | Provide text labels, keyboard focus and cancel, meaningful screen-reader status and full relative paths on demand. English and Korean resources use the same reason keys. Preserve filenames and literal source text. |

The primary result line for the canonical mixed PDF reads **“Excluded · OCR required”**. A detail may read “First confirmed at page 37; inspection stopped.” Do not infer that page 37 is the only scanned page. If a complete preview later establishes a specific count, display it with its own coverage.

## 5. Read-only composition preview

**Contract.** Inspect only. No complete MD, partial MD, page rasters for OCR, original copy, persistent report, content cache, saved job or provider request. The engine may use bounded private scratch for a parser and must clean it on normal exit or cancellation. The shell must use an ephemeral reader for large responses, not quietly persist the old run spool. One page summary at a time is adequate. Caller-directed stdout redirection is external to this operation.

### 5.1 Page composition

For each inspected PDF page, emit one of: text only, mixed, OCR only, blank, or other/undetermined. Determine blank only with reliable coverage. Known text plus known OCR gives mixed; text with unresolved material is undetermined unless both types are already established. Report unresolved detail separately. Totals for these five classes equal inspected pages. Report uninspected pages separately when the document total is known. Show both counts and denominator; when there are no inspected pages, display “unavailable.”

### 5.2 Surface-area composition

Use the visible, rotated crop area in common page coordinates. Divide it into four disjoint classes: displayed text blocks, placed images/photos, unoccupied page background, and other/unknown. This measures layout coverage rather than character ink, semantic importance or transcription effort. White pixels inside a scanned image count as image. Invisible text adds no visible text area. Visible front objects own overlaps; ambiguous clipping, transparency and unresolvable paint order go into other. Vectors and unresolved annotations go to other. A page-wide opaque background object confidently identified as page background may be counted as background; uncertain fills go to other.

For each measurable page accumulate raw areas. For class k, percentage = 100 × sum of class-k area / sum of measured visible page area. Aggregate raw areas before rounding to one decimal. Render ordinary rounding differences with an approximation label. When coordinates or coverage are unreliable for a whole page, omit that page from the area denominator and show how many pages were measurable. When no page is measurable, display null/unavailable for every area percentage. Keep page inspection coverage and area measurement coverage independent.

**Worked oracle.** Consider two fully measured pages with crop areas 100 and 300 square units. The first contains 40 units of text and 60 of background. The second contains 120 units of image and 180 of background. Report text 10%, image 30%, background 60%, other 0%. If the second page cannot be measured, report the first page’s 40%/60% and “area measured on 1 of 2 pages.” Do not extrapolate to the missing page.

**Feasibility decision.** Start with a PDF adapter behind a geometry interface using the already declared PDF dependency where practical. First test the crop/rotation and overlapping-object fixtures against the supported dependency range. If the backend cannot resolve a region, return other/unknown; if it cannot support a dependable page measurement, return unavailable. A package addition, whole-document rasterization or conversion to PDF for non-PDF formats requires separate evaluation. Benchmarks must record which provider of geometry produced the result. [Declared dependencies](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/pyproject.toml)

### 5.3 Limits

Default conversion may stop at the first confirmed OCR need. Detailed preview scans to completion within existing resource bounds; interruption or a cap yields partial coverage. Never relabel a partial preview as complete. A directory preview aggregates file dispositions and per-file measurements; whole-batch area is optional only when every included denominator is explicitly described. Initial UI shows per-file percentages only. An image-area percentage never acts as an eligibility threshold.

## 6. Optional text-only extraction

**Trigger and scope.** Off by default. Explicit invocation per file or confirmed selection. PDF is the initial adapter. A previous early exclusion establishes OCR need; the partial action then walks the complete document to find usable existing text, including text on mixed pages. Verify the source snapshot before extraction. All-scan input with no usable text yields “No extractable text”, no file. Protected, damaged or unsupported input yields the specific barrier. An unexpected read error, incomplete traversal or cancellation discards staged output.

**Reading order and omissions.** Preserve physical page order, 1-based page numbers, Unicode, meaningful paragraph breaks and reliable within-page reading order. Use an existing verified PDF text layer without invoking an OCR engine. Exclude unusable/garbled layers; never synthesize text. Preserve extracted numerals and CJK text. If columns or table ordering cannot be established, retain only reliable blocks with an ordering warning or mark the region omitted. Use a single page-level marker when coordinates are unreliable. Merge adjacent missing spans only if the source locations stay unambiguous. A legitimately blank page is labeled blank, not “OCR required.”

**Output contract.** Store separately from complete output using a dedicated subtree, e.g. `Partial/<root alias>/<relative source>.text-only.md`. Localize the display label independently of the stable on-disk directory name. The first visible line identifies a partial extraction. Include source identity/digest, extraction policy version, extraction time and inspected range. Any metadata encoding must escape user-controlled names. Reuse the same collision, containment and edited-note rules as complete output. Example visible content:

> Partial text extraction — OCR-required content omitted  
> Source: Statements.pdf · pages inspected: 1–100  
> Page 36 — [existing readable text]  
> Page 37 — OCR-required page omitted  
> Page 38 — [existing readable text]

The operation returns a secondary result (saved, reused, no usable text, unsupported, failed or cancelled). It leaves the source in the OCR-required result and never increments complete conversions. The user can still copy the original. Preserve the existing complete MD and any edited partial MD.

## 7. External handoff and optional photo metadata

| Desired artifact | UI and transfer rule | Failure behavior |
|---|---|---|
| None | Keep a persistent filterable run result. No extra folders or placeholder notes. | A missing source remains visible with a reason. |
| Open original | Open or reveal one file through the OS; a member reveals its containing archive and its internal location. | If the source changed, show reclassification before export. Never open a different file solely on a filename match. |
| References | Copy absolute local paths to the clipboard, with clear labeling. Export selected rows as UTF-8 CSV with root alias, relative source path, member path where applicable and reason. Full paths are opt-in for CSV. | CSV must round-trip Unicode, commas, quotes and embedded line breaks. A member is represented by container path plus member field. For names containing a line break, offer CSV instead of ambiguous newline clipboard output. |
| Original bytes | Pick a destination and show count and estimated bytes. Preserve root aliases and relative structure. Copy only selected originals or safely extract the selected archive members. | Same destination/same digest counts as reused. Different bytes require a distinct name. If changed, missing, unsafe, over limit or out of space, record the item and continue when safe. |

Keep output, work, cache, partials and known copy destinations out of subsequent ordinary discovery. Compare canonical destinations, reject same-file copies, and preserve case/normalization collisions as explicit outcomes. Each copy ends as new, reused, conflict, failed or unfinished. An externally processed item does not need a second in-app “transcription complete” workflow.

**ExifTool.** For a supported standalone photo, expose “Copy photo information” on explicit selection. Show installed/absent/too old/unusable/no metadata states. Read locally with bounded subprocess output and timeout. Present actual fields with GPS, author and device identifiers deselected. Copy only checked values; preserve unspecified time zones and missing fields. Allow batch selection only with a preview of field coverage and affected file count. Installation, failure, key selection or metadata copying never affects eligibility, Markdown counts or source bytes. The original photo can still carry its own metadata when the user attaches it externally. ExifTool metadata does not silently enter prompts, cached Markdown, logs or exported reference lists.

## 8. Engine, shell and CLI contracts

### 8.1 Ownership and sequencing

| Boundary | Owns | Must not infer |
|---|---|---|
| Discovery / source reader | Root labels, containment, archive limits, stable identity, immutable input bytes or equivalent verified snapshot | OCR need from extension |
| Classifier / eligibility policy | Direct-text suitability, confirmed OCR evidence, missing coverage, ordered decision, one primary reason | Completeness from zero *selected* OCR units |
| Inspect adapter | Page roles, measured region classes, counts, coverage, provenance of estimates | Text semantics from visible area |
| Text adapter and publisher | Reliable source text, ordered blocks, omission locations, validated atomic writes | Full success from a file's presence |
| Engine command boundary | Mode-specific capabilities, schema-versioned results, progress, exit semantics | Permission to call a provider from legacy settings |
| Shell and local run store | Selection, user action, localization, history, retry, filters, export selection | Eligibility from warning strings, output counts or CLI exit alone |

**Sequence for automatic conversion.** Discover → identify immutable input → classify → stop on exclusion → convert eligible source → validate output against snapshot/policy → publish → record outcome. Branch before selection, rendering, approval, OCR ledger lookup and provider construction. Core may inspect more than one page internally. The early-stop requirement applies to avoiding remaining work where the adapter supports short-circuiting; do not advertise measured time savings until verified.

**Preview.** Discover and inspect → emit bounded per-file records → present → discard ephemeral data. **Partial export.** Resolve selected source → check identity → extract supported text with omission markers → validate → commit to the partial subtree. **Handoff.** Resolve the recorded source → verify it still identifies the classified bytes → copy references or bytes. Use a shared resolver for ZIP member identity in all four flows.

### 8.2 Proposed command surface and migration semantics

The names below are proposed for the new behavior-changing release. They are not commands promised by the 2.0.2 candidate.

| Invocation | Defined behavior |
|---|---|
| `mdflow run <inputs...> -o <dir>` | Strict automatic conversion. A completed OCR exclusion is a normal file result. |
| `mdflow run --dry-run <inputs...>` | Read-only composition preview. Reject output, persistent report, force-write, approval, provider and copy flags in this mode. |
| `mdflow extract-text <inputs...> -o <dir>` | Explicit partial export. Accept a verified mixed PDF; for fully text-only input return “Use standard conversion”; for an all-scan input return “No extractable text”. |
| `--input-list <json-file>` on these operations | Alternative to positional paths for large selections. UTF-8 JSON array of absolute paths; allow exactly one input source. Preserve order and support embedded newlines. Reject malformed arrays before processing. Under the shell, any transient input list belongs to a private temporary directory. |
| `mdflow version` / `selftest` | Preserve diagnostic purpose. Version advertises policy, report schema and available adapters. Self-test covers local operation without account credentials. |

The new shell passes the proposed selector `--policy strict-v1` when launching a job, in addition to checking the version/capabilities. An old engine must refuse that selector. A legacy shell and a new engine must fail the old protocol gate before normal work. Use a distinct negotiated major protocol for this behavior change; reserve its numeric value after checking the registry. Keep existing automation that requires the historical selective-OCR behavior on its pinned engine or an explicitly named legacy entry point. New strict commands reject legacy provider/approval options and must not silently reinterpret them. Publish an old-to-new CLI migration note, including how to retrieve exclusions and how to request a partial. Preserve any already-published release artifacts.

**Process contract.** Retain isolated interpreter launch, fixed working directory and credential redaction. New modes receive no provider credentials or provider config through the launcher. Reject incompatible command combinations at startup. In strict modes use exit 0 for completed valid work including expected exclusions/no-text, 1 for invalid invocation or incompatible runtime, 2 for one or more operational failures, 130 for cancellation. Cancellation wins for the process outcome; already known per-file errors are preserved. Validate this proposed mapping separately from historic OCR/approval exit codes. Parse structured diagnostics; never create a complete row because a process returned 0.

### 8.3 Result shape and identities

Use the existing transport's separation between stdout results and stderr progress. Add a new negotiated report envelope; keep old decoders bound to their own protocol. For high volume, the new protocol streams versioned JSON records (header, per-file results, footer). The shell can render and journal completed files before the footer. Split oversized detail into ordered page chunks with the same source ID. Never place full text or raster data in progress. Sample per-file record within a proposed strict result stream:

```json
{
  "kind": "file",
  "mode": "run",
  "source": {
    "root": "inbox",
    "relativePath": "April/statement.pdf",
    "memberPath": null,
    "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "outcome": "excluded",
  "reason": "ocr_required",
  "coverage": {"inspectedPages": 37, "totalPages": 100, "complete": false},
  "evidence": [{"page": 37, "kind": "ocr_needed"}],
  "outputs": []
}
```

| Record | Required semantics and validation |
|---|---|
| Header/footer | Schema major, operation, run ID and policy version. Final record contains process status and count reconciliation. A missing footer makes the session interrupted. Never synthesize successful results for trailing inputs. |
| Source | Stable logical identity is root plus normalized relative path and archive member chain, encoded as separate fields with reversible escaping. Digest identifies source revision. Matching bytes at two logical paths preserve two rows. Nested archives carry a sequence of containers/members, not an ambiguous slash-joined string. |
| Strict file result | Outcome, reason when relevant, location or explanation where available, coverage, diagnostic codes, actual outputs. Only verified complete/reused results can reference complete output. |
| Preview file / page details | Format, supported measures, inspected and total pages (null when unavailable), class counts, measured-area page count, raw area totals, percentages or null, early-stop/limit flags and reason codes. A measurable 0 differs from an unavailable value. |
| Partial result | Original identity, action status, extraction extent and skipped locations, output reference only on successful save/reuse. Parent strict outcome is immutable. |
| Events | Monotonic sequence within a run; include logical file ID, stage, status and counts. Unknown optional fields are ignored under the same major version. Unknown critical values, malformed counts, duplicate conflicting results or an incompatible major produce a visible protocol error. |

Use reason tokens independent of UI language. Minimum vocabulary for policy tests: `ocr_required`, `undetermined`, `protected`, `corrupt`, `unsupported`, `legacy`, `limit`, `empty`, `source_changed`, `read_failed`, `write_failed`, `edited_output`, `no_usable_text`, `measurement_unavailable`. Keep native diagnostic codes as secondary details. Bind the new schema’s actions to an allowlist rather than exposing arbitrary command names through report data.

## 9. Persistence, recovery and concurrency

**Storage decision.** Reuse existing settings and short history for preferences and run summaries. Store durable per-file results for regular jobs in a separate bounded local job store outside the synced vault by default, namespaced by vault and run. The shell owns the Obsidian job store. The standalone CLI emits records to the caller and owns its local resume record only for durable CLI runs. Select one journal owner per execution. Use an append-only journal with checkpoints for the first implementation.

- A job header captures root aliases, scope and resolved destinations, mode, engine/adapter identity and policy version. Each file record captures source identity, result, output and its hash when available. A local per-device binding maps root aliases to actual roots. CSV exports omit local absolute roots by default.
- Admit one active job per shell instance, as today. Separate CLI/shell instances may target the same destination. Acquire a destination claim before replacing/publishing and recheck actual content under that claim. Use a no-clobber strategy for new names and recoverable claims for interrupted writers. Order locks consistently for a document's MD and media.
- Write the generated files into private staging on the target volume. Publish referenced media first; then atomically publish the MD as the visibility boundary. Keep user-edited files protected. Track owned staged files for repair. A durable “complete” row is recorded only after validated publication.
- If the process dies after publishing MD but before journaling completion, recover only after matching source, policy, output digest and referenced media. A stray filename is insufficient. If any check fails, reprocess or surface a conflict. An interrupted journal tail may be discarded only back to its last complete validated record.
- Resume starts with previous terminal records and revalidates source and output identities. Changed input, adapter or policy reopens the file; deleted output can be restored. A changed source that now requires OCR is excluded; preserve and label its previous MD as an earlier result. Cancellation retains completed work and marks the current item unfinished. Unknown discovery totals stay unknown.
- Cache keys distinguish strict/partial operations and include source, engine, parser/policy and output-relevant options. Do not reuse existing OCR-enriched or EXIF-bearing bodies when creating strict/partial outputs. Preview and clipboard metadata operations have no persistent content cache. Copy reuse compares original bytes, not Markdown cache entries.
- Generated outputs, journals, caches, partial folders and copy destinations are discovery exclusions after canonical path resolution. Preserve existing hidden/symlink checks and archive budgets. Rank collision keys using the destination filesystem's normalization rules and serialize same-destination publication. Retain provenance of multiple source roots.
- Cleanup shows which category will be cleared and its size. Clearing run history or cache must preserve sources, complete documents, edited notes, partial exports and independently copied originals. Existing 100-entry summary retention must not silently erase a resumable active run. Keep device-local paths out of shared diagnostics unless the user explicitly includes them.

## 10. Installation, updates and operational failure

| Situation | User-visible outcome | Engineering acceptance |
|---|---|---|
| Fresh machine | OS-specific instructions, verified local wheel or normal installation path, interpreter picker, connection and destination test | Supported desktop OSes run the two-document smoke. Offline installation instructions list required local wheels. Avoid global Python mutation. |
| Compatible existing environment | Show engine path, version and capabilities for strict conversion, preview, partial export and optional tools | Reuse a compatible environment; display degraded optional actions without blocking basic work. |
| New shell / old engine or opposite | Explain which component to update and how to select the previous compatible pair | No fallback to partial or provider workflows. Retain compatible settings, originals, previous outputs and sanitized migration backup. |
| Update interrupted | Previous working environment remains selectable | Prepare and self-test a separate venv before switching. Do not switch underneath an active job. |
| Optional dependency missing | Disable only the affected action and show why | No API key for core functions, no ExifTool requirement for conversion or handoff, no LibreOffice requirement for native formats. |
| Corrupt history, incompatible data schema or unexpected permission error | Show precise diagnostic, recovery location and available read-only actions | Do not rewrite unknown schemas; recover valid records where safe. Preserve edits and sources before repair. |
| Diagnostic sharing | Show destination and what the copy includes | Redact credentials and sensitive local paths from routine diagnostic exports. Keep source content, full EXIF and OCR images out of logs. |

Production upgrade and rollback remain separate from product acceptance. In particular, a green unit suite does not prove that a release tag, reviewed commit, attached wheel, shell bundle and release evidence all match. Requalify the chosen release commit using the repository’s existing packaging process. [Release workflow](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/.github/workflows/release.yml)

## 11. Performance and capacity

First support 1,000 and 10,000 mixed logical sources including nested folders and named ZIP members. Exercise small, medium and single-large files separately. Preserve configured per-file, archive and parser bounds. Batch the work list, stream results, render a bounded window of rows, and avoid passing thousands of paths via an OS argument string. Use a single processing worker initially; increase concurrency only after measuring memory and correctness. Classifying with certainty, PDF layout accounting, and exporting a copy have different costs; record them separately.

Proposed interactive acceptance on a recorded reference desktop: first progress indicator within one second of admission, user feedback on cancel within one second, and first visible result rows rendered within one second of receiving a result chunk. These are UI targets, not promises about parser termination. Measure worker stop latency separately on each OS, including forced termination on Windows. Record elapsed time, peak parent and worker memory, time to first item, files per second, durable journal size and restart time. For a scaled set of equally sized files verify that live document payloads are bounded by the worker count, never the total number of inputs. Record machine, OS, Python, engine, fixture manifest, cold/warm cache and source size profile. Set throughput and memory budgets from measured baselines before promising them to users.

### Delivery defaults for a reproducible first implementation

| Decision | Default and acceptance oracle |
|---|---|
| Source of truth for classification | Translate the pinned Core decision, priority, reason and coverage into **confirmed OCR / verified direct / unresolved** at one boundary. Do not classify on the number of candidates left after filtering. For the initial PDF adapter, a validated scan-like or image-with-text-layer/suspect-text signal whose underlying evidence is ambiguous stays unresolved; a fixture with a known scan and affirmative OCR evidence is confirmed. Text selection alone cannot establish that a pre-existing layer faithfully represents the page. |
| Missing adapter capability | Strict conversion requires a declared format-specific whole-file inspection capability. Preview may independently advertise page roles, page areas or structural counts. Partial PDF requires reliable positioned text and omission reporting. Feature detection in the version response precedes every operation; a missing optional flag disables only its action. |
| Page details at boundaries | Zero-page/invalid PDF receives the parser's empty/corrupt reason, with no ratios. An inspected blank page with known geometry has 100% visible background. A confidently scanned page filled by a single image has 100% image area even if most pixels are white. Counts remain available when trustworthy geometry is unavailable. |
| Dry-run completion status | Report complete, limited or cancelled. For a deliberately bounded preview with useful output, return a completed invocation and record limited coverage. Cancellation returns 130 and presents the validated in-memory prefix with a cancellation label. Normal close discards this view. |
| Partial ordering and identity | Use source physical page indices throughout. On a mixed page, include each trusted block once and locate omitted material by page and, if reliable, block position. Source page labels may be shown alongside physical indices. Empty/no-text and unsupported action results produce zero output; operational failures remain retryable. |
| Entry-point consistency | Menu, ribbon and drop use the same include-subfolders, scope exclusions, naming, edit protection and policy version as the CLI for equivalent inputs. Mobile clients remain outside the declared desktop shell scope. |
| Durability and privacy | A strict or partial job may persist status and output identity. Preview and photo-info reads are ephemeral. Do not log selected EXIF values. Internal paths used to reopen work remain local. Exports carry only fields selected for that export. |
| First implementation ownership | Place policy and adapters in the Python engine. The shell presents typed results and performs explicit clipboard/open/save interactions. Share file resolution, bounds and safe-copy primitives for handoff; establish equivalent logical identity for archive members and normal files. The shell never reparses a PDF to decide eligibility. |

## 12. Fixture catalog and expected results

Use generated, redistributable fixtures with known page layouts. Store the generator revision, hashes and an independently specified manifest of expected outcomes, visible text, omissions and areas. Include Korean and mixed Korean/English paths, spaces, numerals, mixed scripts and meaningful tables. Compare area results to authored geometry, never to the same measurement routine used by production.

| Fixture | Construction | Expected observation |
|---|---|---|
| F01 Text-only | 100 PDF pages with known, visible numbered text | Complete 1, excluded 0. Stored Markdown preserves all expected page sentinels. |
| F02 Mixed page sequence | Insert a full-page scan into a 100-page file at page 1, 37 or 100, leaving 99 text pages | Strict excludes once in all variants; no partial artifacts. Preview identifies 99 text-only and 1 OCR-only page on full inspection. Partial preserves 99 page sentinels and the exact omission. |
| F03 Mixed within one page | Visible paragraph and scanned table on one page; separate decorative-logo control | First file excluded, partial includes paragraph once and omission once. Known decoration alone does not create a false OCR claim. |
| F04 All scan / image | Image-only PDF and standalone photo with and without GPS | No usable partial text. Handoff succeeds. Only explicitly selected EXIF fields are copied. |
| F05 Ambiguous | Broken or mismatched hidden text layer, unresolved embedded media, partial-coverage cap, uninspected HTML media | Positive OCR evidence or undetermined as specified per fixture; no false complete output. Known-good matching text-layer control can qualify. |
| F06 Geometry | Two unequal crop areas from §5, rotated/clipped objects, overlap, standalone vector, hidden layer, blank page and white scanned image | Arithmetic and reported coverage match independent expectations. Unresolved geometry goes to other or null at the correct scope. |
| F07 Paths / archives | Two roots with same basename, casing and Unicode variants, nested ZIP members, an output/copy directory inside discovery scope | Distinct logical rows, deterministic mapping, no duplicate re-ingestion, safe member handoff. |
| F08 Recovery | Changed input, user-edited MD, deleted output, interrupted write before/after publication, denied writes, full target volume | No original loss, partial final output or silent overwrite. Per-file outcomes and resume reconciliation match §9. |
| F09 Environment | Old/new shell and engine, absent ExifTool, offline venv, old OCR settings and legacy cache | Strict effect boundary holds; incompatible pair blocks with recovery guidance. |
| F10 Scale | Seeded 1k/10k mixture of known complete, OCR, unknown, blocked and failure cases | Exact counts, bounded presentation, resume without duplicate writes. |
| F11 Format and text quality | UTF-8/legacy text, empty source, valid TSV and CJK table, Office with embedded raster, unsupported compound layout | File policy follows actual coverage. Structural counts use named units, area can be null. |
| F12 Transport and UI | Malformed/truncated stream, duplicate records, unsupported major, newline-bearing paths, UTF-8 CSV round-trip | No fabricated success, preserved valid prefix on interruption, unambiguous identifiers, keyboard-accessible selection. |

### Smallest test oracles for ambiguous cases

| Authored observation | Expected policy | Independent assertion |
|---|---|---|
| Inspected text page contains selectable text and a confirmed scanned table | OCR required | Full run emits no output even if the table is the lowest-priority unit. A partial includes the text once. |
| Source has a clean text paragraph and a verified decorative logo | Eligible if remaining coverage is complete | A nonzero image-area estimate does not change eligibility. |
| HTML has a text body and a referenced image whose content cannot be inspected | Undetermined | The legacy T label cannot cause a complete write; do not fetch the remote image. |
| PDF reports a hidden layer with contradictory or unreadable glyph mapping and no affirmative evidence that resolves it | Undetermined | Neither a nonempty text string nor a nearly full image area constitutes independent proof. |
| A protected ZIP has no accessible members | Excluded, protected | One barrier record, zero fictitious member rows, zero copies. |
| A file becomes inaccessible between inspection and export | Secondary action failed or source changed | Earlier classification and counts remain intact. A reclassification of new bytes belongs to a new revision. |
| A limited preview inspects 20/100 pages and measures 18 | Limited | Five page classes sum to 20. Area denominator is the visible area of the 18 measured pages; 80 uninspected pages and 2 unmeasured inspected pages are explicit. |

## 13. Requirement-to-acceptance trace

The following are **design identifiers** for handoff. Map them to the repository's registered requirement/test identifiers before adding tests. The final column specifies the smallest boundary capable of proving the behavior. Cross-layer cases also require one real entry-point pass.

| ID | Requirement / testable assertion | Fixture(s) | First test boundary |
|---|---|---|---|
| A01 | Strict eligibility accepts a complete directly readable source. It rejects uncertain coverage even with label T or zero selected units. | F01, F05, F11 | Pure classification |
| A02 | Any confirmed OCR evidence excludes the whole source; first/middle/last scan yield the same single outcome. | F02–03 | Engine policy + CLI filesystem |
| A03 | Unknown, empty, blocked, failed and unfinished have distinct actions and reconciled totals. | F05, F08, F10–11 | Report projection |
| A04 | Strict and preview paths never invoke approve/transcribe/provider; excluded sources never publish text or use an old enriched body. | F02, F04, F09 | Stage-call spies + output inventory |
| A05 | Preview has no durable effects and reports trustworthy coverage after cancellation or cap. | F02, F05–06 | CLI scratch/output diff |
| A06 | Area is the union of clipped, visible disjoint classes, aggregated by measured area; null differs from zero. | F06 | Geometry fixtures |
| A07 | Partial stores real text, original order and omissions, produces zero output for all-scan inputs, never alters complete counts. | F02–05 | Text adapter + publisher |
| A08 | CLI/shell entry points give equivalent strict decisions; unsupported modes/options are rejected visibly. | F01–02, F09, F12 | Subprocess + Jest replay |
| A09 | Open/reveal, reference export and original-copy actions select only intended sources; identical copies are reused. | F04, F07, F12 | Handoff layer |
| A10 | Metadata stays opt-in and field-scoped; failure leaves the primary workflow usable. | F04, F09 | ExifTool stub + UI |
| A11 | Source replacement, relative-path collisions, nested members, inside-input output and edited MD remain safe. | F07–08 | Filesystem integration |
| A12 | Pause/cancel, process death and retry preserve valid items and reconcile published output; concurrent writers cannot clobber. | F08, F10 | Fault-injected job/publisher integration |
| A13 | Version negotiation, migration, offline startup, update failure and rollback preserve prior data and disable invalid routes. | F09 | Version-gate + installation smoke |
| A14 | Scaled input is bounded; selection, counts, keyboard navigation and reopen work for all matching rows. | F10, F12 | UI + benchmark |
| A15 | Classification can report known evidence early, while a full preview may add inspected details without changing the earlier strict result. | F02, F05 | Cross-mode integration |
| A16 | Per-format capability display and optional tools match what the local adapter can actually deliver. | F04–06, F09, F11 | Capability decode + settings |
| A17 | Summary/report schema distinguishes discovery skip, source disposition, secondary action and process outcome, including missing footer. | F07–08, F12 | Producer/consumer contract |
| A18 | End-to-end demo produces a single complete MD for the text/mixed pair. Preview produces none; explicit partial produces exactly one separately identifiable partial MD. | F01–02 | Real installed engine + desktop rehearsal |

## 14. Order of the first failing tests

| Slice | First red assertion | Implementation seam / existing suite to extend | Exit before next slice |
|---|---|---|---|
| 1 · Strict decision | A verified text source qualifies; one scan or uninspected media prevents complete output. | classify.py, existing pure classification tests | Decision table green including precedence, no CLI effects yet. |
| 2 · Enforce at runtime | Running the canonical pair publishes exactly one MD with zero calls to OCR/provider; legacy cache cannot bypass the gate. | orchestrate.py, cli.py, step7 orchestration and CLI tests | Real files, output inventory and reason codes match A01–04. |
| 3 · Negotiate and present | New shell rejects an incapable engine and displays OCR-required as an expected exclusion. | launcher/version gate, protocol decoder, coordinator, results modal; JT-09/11/12/17 | UI and CLI agree; old settings cannot select remote work. |
| 4 · Preview and geometry | Read-only preview of F02 has correct coverage and zero durable files. F06 produces 10/30/60/0. | triage/inspection adapter and CLI fixtures; shell stream replay | Partial/null measurements, cancellation and resource bounds pass. |
| 5 · Optional partial | F03 exports only its genuine paragraph with a location marker. All-scan input creates no file. | PDF adapter, assembly and writer; existing convert/write tests | Ordering, empty case, conflicts and no accidental full output pass. |
| 6 · Handoff and EXIF | Filtering 24 OCR-required rows excludes four unknown and two locked rows; copying five reports four new and one reused. | results, source resolver, safe writer, existing R31 metadata cases | All four handoff paths, ZIP identity and field-level opt-in pass. |
| 7 · Durable jobs and volume | Inject process death after file publication but before success journaling. Reopen and converge without duplicate output. | job journal, existing cancellation tests and spool boundaries | Concurrent writers, disk failures, 1k/10k and accessibility coverage recorded. |
| 8 · Installed upgrade rehearsal | In a fresh compatible environment the canonical pair passes. Old/new combinations block safely; previous pair can be selected. | setup, package verification and desktop/manual rehearsal | Required platforms recorded; limitations and release evidence tied to the chosen commit. |

Starter references: [pure classification tests](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/tests/unit/test_core_classify.py), [orchestration tests](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/tests/stage_io/step7/test_orchestrate.py), [write tests](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/tests/stage_io/test_write_io.py), [ExifTool tests](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/engine/tests/stage_io/test_r31_exiftool.py), [shell contract replay](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/shell/test/jt-11-contract-replay.test.ts), [version gate tests](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/shell/test/jt-17-version-gate.test.ts), [trace registry](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc6355/tools/trace.py).

## 15. Handoff checklist and remaining evidence

**Ready for the first red test:** the approved use case, effect boundaries, precedence, representative fixtures, output counts, compatibility decisions, observable error handling and owning seams are specified. Start at slice 1 with F01/F02/F05; the most important regression is a mixed or uninspected source silently becoming a complete MD. Preserve existing test registrations and historic receipts; update the repository's canonical specification, requirement registry and trace map for the new candidate as part of implementation.

**Evidence still to collect in TDD:** independently generated fixture bytes and hashes, actual geometry support by dependency version, text-layer quality on genuine multi-column/CJK files, cross-platform publish/recovery behavior, benchmark results, screen-reader/keyboard walkthroughs, and real-app install/update/rollback results. Risk-driven fallback is defined: incomplete classification means undetermined, missing geometry means unavailable, unreliable text is omitted with provenance or produces no partial, and incompatible runtimes block with a recovery path.

**First acceptance walkthrough:** install → process the text/mixed pair → open the only complete MD → filter the excluded original → preview all 100 pages → explicitly export existing text → copy the original for external OCR → reopen results. Expected inventory is one complete MD, one optional partial MD under its separate subtree and one optional original copy. Preview contributes zero files; the original mixed source remains a single exclusion throughout.