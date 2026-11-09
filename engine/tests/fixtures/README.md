# Fixture provenance

All fixtures are generated at test time by `gen_core.py` / `gen_io.py` from own deterministic recipes, except the binaries listed below.

PNG recipes write RGB scanlines with filter 0 and explicit uncompressed DEFLATE blocks, using only integer CRC-32 and Adler-32 checksums. No Pillow encoder or native compression library chooses the bytes. ZIP recipes store members with fixed metadata, avoiding zlib-version differences in Office/archive source hashes. Goldens are regenerated with reference Core 0.3.7 and retain full report equality in CT-03. FX-46 remains a frozen compressed archive so its compression-ratio rejection is exercised.

`.gitattributes` disables newline conversion for sealed goldens, binary inputs and FX-71 replay files. Their hashes cover the exact committed bytes even on Windows checkouts.

`hwp5_bytes()` freezes the original own-work PNG/raw-DEFLATE and body-record payloads as small hex literals, then builds the CFB with integer operations. It reproduces FX-24 exactly; FX-27 changes only the encryption property. Pillow/zlib upgrades cannot choose new bytes, and existing goldens remain sealed without regeneration (T-GEN-57).

| File | Bytes | SHA-256 | Provenance |
|---|---|---|---|
| `FX-46.zip` | 11335 | `2ca96972d495cbcc53d1b59fadd556099a47736d445597ab01877631d45876d5` | Own work. Frozen on 2026-11-09 from the original `zip_bytes([("zeros.txt", b"\0" * (11 * 1024**2))])` recipe (Pillow 13.0.0 environment, Python 3.15.2 on Windows). One DEFLATE member, fixed 1980 timestamp and Unix mode 0600; synthetic zeros only. Preserve these bytes across native compressor upgrades. |
| `FX-24.hwp` | 3072 | `01cd148a7c6145a645db19f3cd20e81932136f590bfaf4131d8b3fb9c661fecd` | Own work. Materialized by the orchestrator on 2026-11-09 from `gen_core.hwp5_bytes()` (recipe written for this project: synthetic 200x200 solid PNG made by Pillow, raw-deflate stored; text "Own deterministic HWP fixture"; no third-party document content). Reverified with release baseline markitdown-gc 0.3.6 (0.3.5 reports remain byte-identical): converts to the text above; `--ocr-report` = `review`/`complete`, candidates `BinData/BIN0001.png`, `BinData/BIN0002.wmf` (issue `unsupported_media`). Re-generate and compare: the recipe must reproduce identical bytes. |
