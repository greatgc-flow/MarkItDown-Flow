# Changelog

## 0.1.0 — Initial fork

First release of **MarkItDown Flow**, an Obsidian plugin that exposes the full
power of Microsoft's [MarkItDown](https://github.com/microsoft/markitdown)
library through a four-phase conversion pipeline.

Forked from [`ethanolivertroy/obsidian-markitdown`](https://github.com/ethanolivertroy/obsidian-markitdown)
v2.1.0. The TypeScript layer (commands, modals, settings, drag-and-drop,
context menu, history, Python detection) is inherited largely intact; the
Python wrapper has been replaced with a substantially more capable engine.

### Added

- **Four-phase conversion pipeline** in `python/markitdown_wrapper.py`:
  1. **Offline** — direct `MarkItDown.convert()`.
  2. **AI (Vision/Audio)** — fallback through a configured client array
     (OpenAI, Anthropic, Google Gemini), each with optional custom endpoint
     for Azure OpenAI / proxies.
  3. **Azure Document Intelligence** — pinned to 4.0 GA (API `2024-11-30`),
     model selectable (default `prebuilt-layout`), native Markdown output.
  4. **Azure Content Understanding** — API `2025-05-01-preview`, analyzer
     selectable (default `prebuilt-documentAnalyzer`).
  Phases gate on each other: AI/DocIntel/CU run only when an earlier phase
  produces empty output, when the MIME type matches `*_target_mimes`, or
  when `exhaustive_mode=true`.
- **i18n** for output document UI in 8 languages: en, ko, ja, zh, hi, fr, es,
  ar (controlled by `output_lang`).
- **Timezone-aware timestamps** — `timezone_offset` parameter; falls back to
  system local timezone.
- **EXIF + GPS reverse geocoding** for image inputs.
- **Recursive archive extraction** — `extract_archives=true` recurses into
  zip/tar contents and inlines their conversions under the parent node.
- **Inline base64 asset extraction** — matches both Markdown
  `![](data:...)` and HTML `<img src="data:...">`, decodes to physical
  files under a sanitised, recursively-created path, replaces with relative
  URLs.
- **Zero-loss virtual base** — if every phase produces empty output, the
  source is base64-embedded into the markdown so no information is lost.
- **Detailed logging** to `~/omnidata_logs/engine_YYYYMMDD.log` with
  secret-masking for API keys and credentials.
- **Self-test command** (`MarkItDown Flow: Run image pipeline self-test`)
  runs the SmartImageRouter against four bundled synthetic fixtures and
  reports per-case classification + confidence + escalation decision. Also
  available as a "Run self-test" button in the Image Pipeline settings
  section. Optional markdown report saved to the output folder.

### Changed

- `--extract-images` / `--image-dir` CLI flags renamed to
  `--extract-assets` / `--asset-dir`. Settings keys
  `imageExtractionEnabled` / `imageSubfolderTemplate` renamed to
  `assetExtractionEnabled` / `assetSubfolderTemplate`. Default subfolder
  template is now `{filename}-assets`.
- Plugin id changed to `markitdown-flow` (was `markitdown` in the upstream
  template). Users of the upstream template must reinstall under the new
  id; existing settings are not automatically migrated.
- Version reset to `0.1.0` to mark the new lineage.
- Author and author URL updated to point at this fork.

### Deferred to later milestones

- Input Base Path UI for structured output paths.
- MECE settings reorganisation.
- TypeScript-side i18n (the engine output is already localised; the
  plugin UI itself is still English-only).
- Mobile / Android / iOS support (blocked by the desktop-only Python
  subprocess requirement).
- Updating `src/utils/bundledScripts.ts` with the full new wrapper string
  for community-store distribution. Local installs ship and use the
  on-disk `python/markitdown_wrapper.py` directly.

### Security note

Never paste API keys (Azure DocIntel, OpenAI, Anthropic, Google) into any
file that gets committed. Enter them through the Obsidian settings UI; the
plugin persists them only inside the vault's local `data.json`, which is
ignored by `.gitignore`.
