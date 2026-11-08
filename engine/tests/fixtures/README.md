# Fixture provenance

All fixtures are generated at test time by `gen_core.py` / `gen_io.py` from own deterministic recipes, except:

| File | Bytes | SHA-256 | Provenance |
|---|---|---|---|
| `FX-24.hwp` | 3072 | `01cd148a7c6145a645db19f3cd20e81932136f590bfaf4131d8b3fb9c661fecd` | Own work. Materialized by the orchestrator on 2026-11-09 from `gen_core.hwp5_bytes()` (recipe written for this project: synthetic 200x200 solid PNG made by Pillow, raw-deflate stored; text "Own deterministic HWP fixture"; no third-party document content). Verified with markitdown-gc 0.3.5: converts to the text above; `--ocr-report` = `review`/`complete`, candidates `BinData/BIN0001.png`, `BinData/BIN0002.wmf` (issue `unsupported_media`). Re-generate and compare: the recipe must reproduce identical bytes. |
