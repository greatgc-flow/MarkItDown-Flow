### 1. N/A Declarations Audit

#### VALID N/A Cells (106 cells)
* **Unreachable by Contract / Route:**
  * **S4 (Select):** `K01`, `K10`, `K11`, `K18` (zero OCR candidates); `K12`, `K13`, `K15`, `K16`, `K17`, `K19` (`report_only` stops at S3); `K20` (directory expanded at S1).
  * **S5 (Convert):** `K12`, `K15`, `K16`, `K17`, `K19` (`report_only`); `K14` (archive unpacked at S1); `K20` (directory tree discovered at S1).
  * **S6 (Render):** `K01`, `K10`, `K11`, `K18` (no OCR units); `K12`, `K13`, `K15`, `K16`, `K17`, `K19` (`report_only`); `K14`, `K20` (unpacked/expanded earlier).
  * **S7 (Lookup):** `K01`, `K10`, `K11`, `K12`, `K13`, `K15`, `K16`, `K17`, `K18`, `K19` (no units to query); `K14`, `K20` (container-level).
  * **S9 (Approve):** `K10`, `K11`, `K12`, `K13`, `K15`, `K16`, `K17`, `K18`, `K19` (no external egress/units, consent bypassed); `K14`, `K20` (container-level).
  * **S10 (Transcribe):** `K01`, `K10`, `K11`, `K12`, `K13`, `K15`, `K16`, `K17`, `K18`, `K19` (no units to transcribe); `K14`, `K20` (container-level).
  * **S12 (Write):** `K12`, `K13`, `K15`, `K16`, `K17`, `K19` (`report_only` emits no Markdown publication).
* **Format-Agnostic Owner Plausible:**
  * **S4 (Select):** `K05`, `K06`, `K08`, `K09`, `K14` (candidate prioritization contract `{id, kind, page, priority}` exercised at `S4:K02`/`S4:K07`).
  * **S6 (Render):** `K08`, `K09` (HWPX/HWP5 media raster rendering matches Office media path at `S6:K07`).
  * **S7 (Lookup):** `K03`, `K04`, `K05`, `K06`, `K07`, `K08`, `K09` (lookup key is hash `{raster_sha256, provider_fingerprint, dpi}`; input document class is erased, owner `S7:K02` is sufficient).
  * **S9 (Approve):** `K04`, `K05`, `K06`, `K07`, `K08`, `K09` (approval evaluates `plan_hash` over Plan; format-independent, owner `S9:K02` is sufficient).
  * **S10 (Transcribe):** `K04`, `K05`, `K06`, `K08`, `K09` (unit rasters passed individually to provider; owner `S10:K03`/`S10:K07` is plausible).
  * **S12 (Write):** `K03`, `K04`, `K05`, `K06`, `K08`, `K09`, `K10`, `K11`, `K18` (atomic filesystem sink takes `(path, bytes)`; format-independent IO, owner `S12:K02` is sufficient).

---

#### INVALID N/A Cells (11 cells)
1. **`S5:K01` (pdf_text x Convert)**
   * *Why:* Native text PDF reaches Convert in every normal run. Core native extraction is completely distinct from mixed/scanned PDF handling; owner `S5:K03` does not verify native text extraction.
   * *Test to add:* `T-CNV-06` — Convert native text PDF through Core, asserting text fidelity, table preservation, and absence of OCR fallbacks.
2. **`S5:K02` (pdf_scan x Convert)**
   * *Why:* Pure scan PDF reaches S5 before OCR; Core must run cleanly without throwing or emitting corrupted text tokens before handing off.
   * *Test to add:* `T-CNV-07` — Convert scanned PDF fixture via Core, asserting clean execution and empty/placeholder baseline output.
3. **`S5:K04` (pdf_capped x Convert)**
   * *Why:* Capped PDF passes through Convert; conversion must handle page cap boundaries without out-of-bounds page slicing.
   * *Test to add:* `T-CNV-08` — Convert capped PDF, asserting page slicing respects `--max-pages`.
4. **`S5:K05` (raster_single x Convert)**
   * *Why:* Standalone raster files reach S5; Core executes metadata/EXIF extraction and image wrapping distinct from PDF conversion.
   * *Test to add:* `T-CNV-09` — Convert PNG/JPEG via Core, asserting metadata extraction into Markdown.
5. **`S5:K06` (raster_multiframe x Convert)**
   * *Why:* Multiframe rasters (TIFF/ICO) reach S5; multi-frame handling in Core is unverified by PDF owner `S5:K03`.
   * *Test to add:* `T-CNV-10` — Convert multipage TIFF via Core, asserting frame extraction.
6. **`S5:K11` (g2b x Convert)**
   * *Why:* Tabular/structured formats (CSV, TSV, JSON, HTML, EPUB, XLS) reach S5; Core uses tabular parsers (pandas/bs4/json) completely distinct from PDF. Delegating to `S5:K03` is invalid.
   * *Test to add:* `T-CNV-11` — Convert CSV/HTML/JSON fixtures through Core, asserting table formatting and structural markdown.
7. **`S5:K18` (ext_mismatch x Convert)**
   * *Why:* Mismatched files reach S5; tests whether Convert dispatches based on sniffed MIME type rather than file extension (e.g., PDF renamed to `.docx`).
   * *Test to add:* `T-CNV-12` — Convert extension-mismatched file, asserting parser dispatch follows sniffed MIME.
8. **`S4:K03` (pdf_mixed x Select)**
   * *Why:* Mixed PDF reaches S4; candidate selection must selectively filter scanned pages from native text pages. Owner `S4:K02` (all scanned) never tests mixed selection logic.
   * *Test to add:* `T-SEL-03` — Select candidates on mixed PDF, asserting exclusion of text pages and inclusion of scan pages.
9. **`S4:K04` (pdf_capped x Select)**
   * *Why:* Capped PDF reaches S4; candidate selection must truncate candidate units according to cap budget. Owner `S4:K02` has no cap limits.
   * *Test to add:* `T-SEL-04` — Select candidates on capped PDF, asserting candidate list truncation at budget limit.
10. **`S6:K03` (pdf_mixed x Render)**
    * *Why:* Mixed PDF reaches S6; Render must selectively rasterize only candidate pages, skipping native text pages. Owner `S6:K02` renders all pages unconditionally.
    * *Test to add:* `T-RND-07` — Render mixed PDF, asserting rasters are emitted exclusively for selected candidate pages.
11. **`S10:K02` (pdf_scan x Transcribe)**
    * *Why:* `K02` is the primary scan benchmark and high-risk class. Delegating pure scan transcription to mixed PDF `S10:K03` leaves the primary OCR ingestion target without dedicated verification.
    * *Test to add:* `T-TRX-05` — Transcribe unit rasters from pure scan PDF fixture, asserting provider invocation and transcription return.

---

### 2. WEAK Cells (High-Risk Classes: K02, K03, K07, K14, K15, K16)

* **`S10:K03` (count = 1):** Mixed PDF transcription has only 1 test. Fails to cover boundary conditions like partial provider failures across mixed page layouts.
* **`S10:K07` (count = 1):** Office embedded media transcription has only 1 test. Inadequate coverage for diverse embedded media types (diagrams, inline photos, logos).
* **`S12:K07` (count = 1):** Office output write has only 1 test. Fails to cover collision/pathing edge cases with complex embedded asset names.
* **`S8:K14` (count = 1):** Zip container planning has only 1 test (inherited blanket `T-PLN-01`). No dedicated test for archive member budget estimation or recursion planning.
* **`S12:K14` (count = 1):** Zip container output emission has only 1 test. High risk for nested relative path traversal and atomic directory write collisions.
* **`S8:K15` (count = 1):** Protected file planning relies exclusively on blanket `T-PLN-01`. Missing dedicated check asserting that zero-cost plan is produced without probing encrypted contents.
* **`S11:K15` (count = 1):** Protected file assembly relies exclusively on blanket `T-ASM-06`. Lacks dedicated verification of protected/error status marker formatting.
* **`S8:K16` (count = 1):** Corrupt/unreadable file planning relies solely on blanket `T-PLN-01`. No dedicated validation that zero-cost bypass plan is generated for corrupted payloads.
* **`S11:K16` (count = 1):** Corrupt file assembly relies solely on blanket `T-ASM-06`. Lacks dedicated assertion for corruption placeholder marker injection into Markdown report.

---

### 3. Horizontal-Closure Score: 68 / 100

**Justification:**
* **False Closure via N/A Abuse (-18):** 11 cells across stages S4, S5, S6, and S10 are falsely declared N/A. Most critically, Stage S5 (Convert) evades testing the primary conversion paths for native PDF (`K01`), scanned PDF (`K02`), tabular/markup data (`K11`), and extension mismatch (`K18`) by claiming delegation to mixed PDF (`K03`).
* **Critical Missing Primary Target (-8):** Pure scan transcription (`S10:K02`), the core reason for MarkItDown-Flow's existence, has zero direct tests in S10 and is marked N/A.
* **Blanket Smoke Masking High-Risk Classes (-6):** 6 of the 9 weak cells (`S8` and `S11` across `K14`, `K15`, `K16`) only pass because of the broad `fx("all")` markers (`T-PLN-01`, `T-ASM-06`). They lack dedicated negative, security, or boundary assertions for zip bombs, password-protected files, or corrupted streams.
