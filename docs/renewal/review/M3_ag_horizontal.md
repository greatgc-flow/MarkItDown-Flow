### RECURSIVE MECE AUDIT Round 3 — HORIZONTAL (File Class × Stage)

#### 1. Audit Summary
- **Total matrix cells**: 280 (20 classes × 14 stages)
- **Covered cells (count ≥ 1 in grid)**: 207
- **Grid N/A cells**: 73
- **Valid N/A cells**: 67
- **Invalid N/A cells (unclosed delegation gaps)**: 6
- **Stale TOML declarations (covered in grid, but declared N/A)**: 4

---

#### 2. Re-judgment of Remaining N/A Cells

##### A. VALID N/A (67 cells)
1. **Report-only classes** (K12, K13, K15, K16, K17, K19 never reach S4–S12 except S8 Plan / S13 Report):
   - **K12** (8 cells): S4, S5, S6, S7, S9, S10, S11, S12
   - **K13** (7 cells): S4, S6, S7, S9, S10, S11, S12 *(S5 covered with 2 in grid)*
   - **K15** (7 cells): S4, S5, S6, S7, S9, S10, S12 *(S11 covered with 1 in grid)*
   - **K16** (7 cells): S4, S5, S6, S7, S9, S10, S12 *(S11 covered with 1 in grid)*
   - **K17** (8 cells): S4, S5, S6, S7, S9, S10, S11, S12
   - **K19** (8 cells): S4, S5, S6, S7, S9, S10, S11, S12
2. **Text / Data classes with no OCR units** (no S4, S6, S7, S9, S10):
   - **K10** (5 cells): S4, S6, S7, S9, S10
   - **K11** (4 cells): S6, S7, S9, S10 *(S4 covered with 1 in grid)*
3. **Convert-only native text / mismatch formats** (no OCR units):
   - **K01** (4 cells): S4, S6, S7, S10
   - **K18** (5 cells): S4, S6, S7, S9, S10
4. **Structural / container boundaries**:
   - **K20** (3 cells): S4, S5, S6 (directory tree boundary; files processed individually)
   - **K14** (1 cell): S6 (ZIP container itself has no rasters to render)

---

##### B. INVALID N/A (6 cells in grid)
The following 6 cells are unit-bearing candidate/render stages that actually occur in the pipeline but were improperly declared N/A by delegation to K02:
1. **S4:K05** (*raster_single*): Single image carries an OCR candidate; delegation to `S4:K02` is invalid.
2. **S4:K06** (*raster_multiframe*): Multi-frame GIF/TIFF carries multiple candidate frames requiring selection/ordering; delegation to `S4:K02` is invalid.
3. **S4:K08** (*hwpx*): Media-bearing document carries embedded image candidates; delegation to `S4:K02` is invalid.
4. **S4:K09** (*hwp5*): Media-bearing document carries embedded image candidates; delegation to `S4:K02` is invalid.
5. **S4:K14** (*zip container*): Container member expansion yields candidate sets; delegation to `S4:K02` is invalid.
6. **S6:K04** (*pdf_capped*): Capped PDF (>1000 pages) renders pages 1..1000 to rasters; delegation to `S6:K02` is invalid.

---

##### C. Stale TOML N/A Declarations (4 cells covered in Grid)
These cells are tested and covered in the grid, yet remain declared under `[[class_stage]]`:
- **S6:K08** (Grid count: 1; TOML declared N/A via `S6:K07`)
- **S6:K09** (Grid count: 3; TOML declared N/A via `S6:K07`)
- **S5:K14** (Grid count: 1; TOML declared N/A via `S1:K14`)
- **S4:K11** (Grid count: 1; TOML declared N/A in Block 2)

---

#### 3. Horizontal-Closure Score
- **Closed cells**: 274 / 280 (207 covered + 67 valid N/A)
- **Remaining gaps**: 6 invalid N/A cells (`S4:K05`, `S4:K06`, `S4:K08`, `S4:K09`, `S4:K14`, `S6:K04`)
- **Score**: **98 / 100** *(97.9% closed; 100 cannot be awarded while 6 invalid delegation gaps remain)*
