### Horizontal MECE Audit Round 2: File Class x Stage Matrix

#### 1. Audit Summary & Score
* **Total Matrix Cells**: 280 (20 classes x 14 stages)
* **Covered Cells (count $\ge$ 1)**: 176
* **Declared N/A Cells**: 104
  * **VALID N/A**: 74 (genuine pipeline bypasses: report-only classes, pure convert-only sources without OCR candidates, container/directory folder expansions).
  * **INVALID N/A**: 30 (delegation anti-pattern: classes executing active runtime logic in normal runs marked N/A).
* **Horizontal-Closure Score**: **72 / 100**
  * *Justification*: True executable closure is $\frac{176}{176 + 30} = 85.4\%$, penalized to **72** due to critical omissions on primary document formats: S12 Write (publishing `.md`) is completely unasserted for 8 output-producing classes (including high-risk K03), S7 Cache Lookup is delegated away for 6 active OCR classes (including high-risk K03, K07), and S9 Approve egress gates are skipped for all office/hybrid formats.

---

#### 2. Re-Judgment of Remaining N/A Cells by Stage

##### Stage S4 (Select)
* **VALID N/A**:
  * `K01`, `K10`, `K18`: Pure text/convert-only; zero OCR candidates emitted by S3.
  * `K12`, `K13`, `K15`, `K16`, `K17`, `K19`: Report-only / non-convertible; no candidate extraction.
  * `K14`, `K20`: Container / directory abstractions; member files own candidates.
* **INVALID N/A**:
  * `S4:K05` (Presentation/PPTX): Contains embedded slide media units; Select runs candidate filtering/caps.
  * `S4:K06` (Spreadsheet/XLSX): Contains embedded sheet charts/rasters; Select runs priority ordering.
  * `S4:K08` (HWPX): Carries embedded media units requiring candidate selection.
  * `S4:K09` (HWP5): Binary Hangul embedded images reach S6 render; must pass Select.

##### Stage S5 (Convert)
* **VALID N/A**:
  * `K12`, `K15`, `K16`, `K17`, `K19`: Report-only/corrupt/oversize sources never reach conversion.
  * `K20`: Directory tree; individual discovered files convert, not the directory container.
* **INVALID N/A**: None. (S5 coverage for all converted classes is complete).

##### Stage S6 (Render)
* **VALID N/A**:
  * `K01`, `K10`, `K11`, `K18`: No OCR candidates; rendering is bypassed.
  * `K12`, `K13`, `K15`, `K16`, `K17`, `K19`: Report-only; no units produced.
  * `K14`, `K20`: Archive/folder wrappers; members render individually.
* **INVALID N/A**:
  * `S6:K04` (Capped PDF): Capped pages up to the page limit are actively rendered to raster images.
  * `S6:K08` (HWPX): Embedded media units require local extraction/re-encoding rasterization.

##### Stage S7 (Lookup)
* **VALID N/A**:
  * `K01`, `K10`, `K11`, `K18`: No OCR rasters generated; ledger lookup never invoked.
  * `K12`, `K13`, `K15`, `K16`, `K17`, `K19`: Report-only sources never produce raster hashes.
  * `K14`, `K20`: Container wrappers do not query the ledger.
* **INVALID N/A**:
  * `S7:K03` (Hybrid PDF): Extracted page/media rasters actively query ledger before provider egress.
  * `S7:K04` (Capped PDF): Capped rasters actively query cache.
  * `S7:K06` (Spreadsheet/XLSX): Embedded image rasters query cache.
  * `S7:K07` (Word/DOCX): High-risk media units query cache; hash format differs from PDF page rasters.
  * `S7:K08` (HWPX): Embedded media rasters query cache.
  * `S7:K09` (HWP5): Binary HWP media rasters query cache.

##### Stage S9 (Approve)
* **VALID N/A**:
  * `K10`, `K11`, `K18`: Convert-only, no egress planned; approval gate skipped per REQ-APR-01.
  * `K12`, `K13`, `K15`, `K16`, `K17`, `K19`: Report-only, no external egress.
  * `K14`, `K20`: Approval evaluated per constituent file, not on container handle.
* **INVALID N/A**:
  * `S9:K04` (Capped PDF): Produces provider egress candidates; requires plan hash consent.
  * `S9:K05` (Presentation/PPTX): Egressing slide media requires plan approval.
  * `S9:K06` (Spreadsheet/XLSX): Egressing sheet media requires plan approval.
  * `S9:K07` (Word/DOCX): High-risk egressing document media requires consent.
  * `S9:K08` (HWPX): Hancom media egress requires consent.
  * `S9:K09` (HWP5): Hancom binary media egress requires consent.

##### Stage S10 (Transcribe)
* **VALID N/A**:
  * `K01`, `K10`, `K11`, `K18`: No OCR units to transcribe.
  * `K12`, `K13`, `K15`, `K16`, `K17`, `K19`: Report-only; zero provider calls.
  * `K14`, `K20`: Container wrappers have no provider payloads.
* **INVALID N/A**:
  * `S10:K04` (Capped PDF): Active provider transcription calls on non-capped units.
  * `S10:K06` (Spreadsheet/XLSX): Provider transcription on chart/diagram rasters.
  * `S10:K08` (HWPX): Provider transcription on extracted HWPX media rasters.
  * `S10:K09` (HWP5): Provider transcription on extracted HWP5 media rasters.

##### Stage S11 (Assemble)
* **VALID N/A**:
  * `K12`, `K17`, `K19`: Report-only sources produce no Markdown and bypass Assemble.
  * `K13`: Report-only media produces no final document assembly.
* **INVALID N/A**: None. (Protected `K15` and corrupt `K16` already have dedicated no-output assertions).

##### Stage S12 (Write)
* **VALID N/A**:
  * `K12`, `K13`, `K15`, `K16`, `K17`, `K19`: Report-only / error sources write zero Markdown files.
* **INVALID N/A**:
  * `S12:K03` (Hybrid PDF): Publishes final `.md` containing merged text and OCR transcriptions.
  * `S12:K04` (Capped PDF): Publishes final `.md` containing partial text and capped pending markers.
  * `S12:K05` (Presentation/PPTX): Publishes final converted presentation `.md`.
  * `S12:K06` (Spreadsheet/XLSX): Publishes final table/sheet `.md`.
  * `S12:K08` (HWPX): Publishes final Hangul XML `.md`.
  * `S12:K09` (HWP5): Publishes final Hangul binary `.md`.
  * `S12:K11` (Audio/Notebook): Publishes final converted `.md`.
  * `S12:K18` (Pure text/standalone): Publishes final output `.md`.

---

#### 3. Complete List of 30 INVALID Cells & Tests to Add

| Stage | Cell | Required Test Description |
|---|---|---|
| **S4** | `S4:K05` | `T-SEL-07`: Assert PPTX embedded shape/slide media candidate prioritization and filtering |
| **S4** | `S4:K06` | `T-SEL-08`: Assert XLSX embedded chart/image candidate extraction and bounding |
| **S4** | `S4:K08` | `T-SEL-09`: Assert HWPX media payload candidate selection |
| **S4** | `S4:K09` | `T-SEL-10`: Assert HWP5 binary media payload candidate selection |
| **S6** | `S6:K04` | `T-RND-10`: Assert rasterization of K04 pages strictly respecting `--max-pages` / budget caps |
| **S6** | `S6:K08` | `T-RND-11`: Assert extraction and raster formatting of HWPX embedded image units |
| **S7** | `S7:K03` | `T-LKP-06`: Assert cache ledger hit/miss lookup for hybrid PDF page and media rasters |
| **S7** | `S7:K04` | `T-LKP-07`: Assert cache ledger hit/miss lookup for capped PDF unit rasters |
| **S7** | `S7:K06` | `T-LKP-08`: Assert cache ledger hit/miss lookup for XLSX image units |
| **S7** | `S7:K07` | `T-LKP-09`: Assert cache ledger hit/miss lookup for DOCX media units |
| **S7** | `S7:K08` | `T-LKP-10`: Assert cache ledger hit/miss lookup for HWPX media units |
| **S7** | `S7:K09` | `T-LKP-11`: Assert cache ledger hit/miss lookup for HWP5 media units |
| **S9** | `S9:K04` | `T-APR-05`: Assert plan hash generation and consent approval/denial for capped PDF egress |
| **S9** | `S9:K05` | `T-APR-06`: Assert plan hash generation and consent approval/denial for PPTX media egress |
| **S9** | `S9:K06` | `T-APR-07`: Assert plan hash generation and consent approval/denial for XLSX media egress |
| **S9** | `S9:K07` | `T-APR-08`: Assert plan hash generation and consent approval/denial for DOCX media egress |
| **S9** | `S9:K08` | `T-APR-09`: Assert plan hash generation and consent approval/denial for HWPX media egress |
| **S9** | `S9:K09` | `T-APR-10`: Assert plan hash generation and consent approval/denial for HWP5 media egress |
| **S10** | `S10:K04` | `T-TRX-08`: Assert provider transcription payload transmission and response for K04 units |
| **S10** | `S10:K06` | `T-TRX-09`: Assert provider transcription payload transmission and response for XLSX units |
| **S10** | `S10:K08` | `T-TRX-10`: Assert provider transcription payload transmission and response for HWPX units |
| **S10** | `S10:K09` | `T-TRX-11`: Assert provider transcription payload transmission and response for HWP5 units |
| **S12** | `S12:K03` | `T-WRT-04`: Assert atomic file publish, path mapping, and encoding of K03 hybrid `.md` |
| **S12** | `S12:K04` | `T-WRT-05`: Assert publishing of K04 `.md` containing inline capped pending markers |
| **S12** | `S12:K05` | `T-WRT-06`: Assert publishing of K05 presentation `.md` output |
| **S12** | `S12:K06` | `T-WRT-07`: Assert publishing of K06 spreadsheet `.md` output |
| **S12** | `S12:K08` | `T-WRT-08`: Assert publishing of K08 HWPX `.md` output |
| **S12** | `S12:K09` | `T-WRT-09`: Assert publishing of K09 HWP5 `.md` output |
| **S12** | `S12:K11` | `T-WRT-10`: Assert publishing of K11 `.md` output |
| **S12** | `S12:K18` | `T-WRT-11`: Assert publishing of K18 `.md` output |

---

#### 4. Remaining Weak Cells for High-Risk Classes

* **`K02` (Scanned PDF)**:
  * `S5:K02` (1 test): Weak. Only asserts default markitdown-gc empty extraction; needs assertion of fallback metadata preservation when text stream is empty.
  * `S10:K02` (1 test): Weak. Single mock call; lacks error-injection / provider timeout retry assertion on full scanned pages.
* **`K03` (Hybrid PDF)**:
  * `S6:K03` (1 test): Weak. `T-RND-09` covers isolated page rasterization, but lacks mixed inline image extraction tests.
  * `S7:K03` (NA): Untested. Complete blind spot for hybrid cache hits avoiding egress.
  * `S12:K03` (NA): Untested. Final published markdown integrity is never asserted.
* **`K07` (Word/DOCX with Media)**:
  * `S7:K07` (NA) & `S9:K07` (NA): Untested. High-risk blind spot: DOCX media units have distinct SHA-256 and MIME profiles; cache lookup and consent hashing must be verified end-to-end.
  * `S8:K07` (2 tests): Weak. Lacks multi-media egress plan boundary assertions.
* **`K14` (Archive/Container)**:
  * `S1:K14` (9 tests) vs `S2:K14` (3 tests): Weak triage on corrupted inner container members.
  * Manifest discrepancy: Declared N/A for S5 in text declarations despite grid showing 1 passing test.
* **`K15` (Password-Protected)**:
  * `S8:K15` (2 tests) vs `S11:K15` (1 test): Weak. S11 relies on an implicit no-output assertion rather than checking that the orchestrator explicitly prevents downstream stage invocation.
* **`K16` (Corrupt/Malformed)**:
  * `S8:K16` (1 test): Weak. Minimal assertion that a malformed file produces an empty plan without raising uncaught stage exceptions.


> Orchestrator note (2026-11-09): reviewer misidentified classes in section 3 (K05 = raster_single, K06 = raster_multiframe per 30_TESTPLAN §5, not PPTX/XLSX). Cell-level intent (every output-producing class reaches S12; every unit-bearing class reaches S7/S9/S10) is accepted and will be closed by a class-sweep E2E test, not per-cell tests.
