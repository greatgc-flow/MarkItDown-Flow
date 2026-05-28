# MarkItDown Flow

An Obsidian plugin that converts documents, images, archives, audio and more
into structured Markdown via Microsoft's
[MarkItDown](https://github.com/microsoft/markitdown) library, with a
four-phase conversion pipeline that falls back from offline parsing to AI
vision, Azure Document Intelligence, and Azure Content Understanding only
when needed.

Forked from
[`ethanolivertroy/obsidian-markitdown`](https://github.com/ethanolivertroy/obsidian-markitdown)
v2.1.0 — the TypeScript surface is largely inherited; the Python engine is
substantially rebuilt. See [`CHANGELOG.md`](CHANGELOG.md) for the full
divergence.

## How it differs from the upstream template

| Capability                                | Upstream template | MarkItDown Flow |
|-------------------------------------------|-------------------|-----------------|
| Direct `MarkItDown.convert()`             | ✓                 | ✓ (Phase 1)     |
| Multi-client AI vision fallback (OpenAI / Anthropic / Gemini) | —                 | ✓ (Phase 2)     |
| Azure Document Intelligence 4.0 GA (API `2024-11-30`) | env-var only      | ✓ direct SDK, model selectable (Phase 3) |
| Azure Content Understanding (`2025-05-01-preview`) | —                 | ✓ (Phase 4)     |
| Inline base64 asset extraction with sanitised paths | images only       | ✓ images + HTML `<img>` data URIs |
| Recursive archive (zip/tar) extraction    | —                 | ✓               |
| EXIF + GPS reverse geocoding              | —                 | ✓               |
| Output document i18n (en, ko, ja, zh, hi, fr, es, ar) | —                 | ✓ via `output_lang` |
| Timezone-aware timestamps                 | —                 | ✓ via `timezone_offset` |
| Detailed logs (`~/omnidata_logs/`)        | —                 | ✓ with secret-masking |
| Zero-loss virtual base64 fallback         | —                 | ✓ when all phases empty |

## Requirements

- Obsidian v0.15.0 or higher (desktop only — see notes below)
- Python 3.10 or higher
- `pip install markitdown[all]` (the plugin can do this for you on first run)

Optional, only if you want the corresponding phase active:

```bash
# Phase 2 — pick whichever LLM clients you intend to use
pip install openai anthropic google-genai

# Phase 3 — Azure Document Intelligence 4.0 GA
pip install "azure-ai-documentintelligence>=1.0.0"

# Phase 4 — Azure Content Understanding
pip install azure-ai-contentunderstanding

# EXIF GPS reverse geocoding
pip install Pillow geopy
```

### Desktop-only

This plugin shells out to a Python subprocess and so cannot run on Obsidian
Mobile (iOS / Android). `isDesktopOnly: true` is set in `manifest.json`.

## Installation

For now, MarkItDown Flow is distributed manually (not yet on the Obsidian
Community Plugins browser).

1. Download or build `main.js`, `manifest.json`, `styles.css`, and the
   `python/` directory.
2. Copy them into `<your-vault>/.obsidian/plugins/markitdown-flow/`.
3. Enable **MarkItDown Flow** in Obsidian → Settings → Community plugins.
4. Open the plugin's settings tab and either point it at your Python
   executable or click **Install Markitdown** to install the package.

## Usage

Same surface as the upstream template:

- Ribbon icon → file conversion modal
- Command palette:
  - **Convert file to Markdown**
  - **Convert folder to Markdown**
  - **Convert URL to Markdown**
  - **View conversion history**
- Right-click on a supported file in the file explorer → **Convert to Markdown**
- Drag a supported file from Finder/Explorer into an open note — it is
  converted and a wiki-link is inserted at the drop position.

## Configuration

Settings live under **Settings → Community plugins → MarkItDown Flow**.

| Setting                          | Notes |
|----------------------------------|-------|
| **Python path**                  | Path to the Python executable. Auto-detection covers Homebrew, Framework, AppData, Microsoft Store and `python3` fallback. |
| **Output folder**                | Vault-relative; defaults to `markitdown-output`. |
| **Output filename template**     | `{filename}`, `{ext}`, `{date}`, `{datetime}`. |
| **Extract assets**               | When on, inline base64 images / HTML `<img data:>` are decoded into a sibling folder and the markdown is rewritten to reference them. |
| **Asset subfolder**              | Template for that folder, default `{filename}-assets`. |
| **Recursive folder conversion**  | Include subfolders by default. |
| **Show batch progress**          | Progress bar for folder conversions. |
| **Context menu**                 | Right-click action on convertible files. |
| **Drag and drop**                | Auto-convert dropped files. |
| **Auto frontmatter / Auto tags** | YAML post-processing. |
| **Enable Markitdown plugins**    | Third-party MarkItDown plugins (entry points). |
| **Plugin arguments**             | Key-value editor for parameters routed to either the MarkItDown constructor, its `convert()` call, or this plugin's engine config (see `ConfigManager.PARAM_SPEC` in the wrapper). |
| **Azure Document Intelligence endpoint** | Set this to enable Phase 3. Pair with a `docintel_credential` plugin argument. |

### Plugin argument reference (engine parameters)

These keys (set via **Plugin arguments** in settings) flow into
`OmniDataPipeline` and `MarkItDown`. Defaults shown.

```jsonc
{
  // Engine
  "output_lang": "en",            // en | ko | ja | zh | hi | fr | es | ar
  "timezone_offset": null,        // null → system local; e.g. 9.0 for KST
  "exhaustive_mode": false,       // force every phase to run even on success
  "extract_archives": false,      // recurse into zip/tar contents
  "max_recursion_depth": 5,

  // Phase 2 — AI vision (zero or more clients, tried in order)
  "ai_target_mimes": ["image/", "audio/", "video/"],
  "ai_clients": [
    { "client_type": "openai",    "api_key": "sk-…",   "model": "gpt-4o" },
    { "client_type": "anthropic", "api_key": "sk-ant-…", "model": "claude-sonnet-4-5" },
    { "client_type": "gemini",    "api_key": "AIza…",   "model": "gemini-2.0-flash" }
  ],
  "llm_prompt": "Analyze this file in extreme detail.",

  // Phase 3 — Azure Document Intelligence (4.0 GA)
  "docintel_target_mimes": ["application/pdf", "application/vnd.", "image/"],
  "docintel_endpoint": "https://<resource>.cognitiveservices.azure.com/",
  "docintel_credential": "<key>",
  "docintel_api_version": "2024-11-30",
  "docintel_model_id": "prebuilt-layout",  // -read | -invoice | -receipt | -contract | …

  // Phase 4 — Azure Content Understanding
  "content_understanding_endpoint": "https://<resource>.cognitiveservices.azure.com/",
  "content_understanding_credential": "<key>",
  "content_understanding_api_version": "2025-05-01-preview",
  "content_understanding_analyzer_id": "prebuilt-documentAnalyzer",
  "content_understanding_target_mimes": ["application/pdf", "image/", "video/", "audio/"],

  // MarkItDown core — pass-through (unknown keys are forwarded automatically)
  "pdf_layout": true,
  "pdf_dpi": 300,
  "keep_data_uris": true
}
```

API key console links:

- OpenAI — https://platform.openai.com/api-keys
- Anthropic — https://console.anthropic.com/settings/keys
- Google AI Studio — https://aistudio.google.com/app/apikey
- Azure (Document Intelligence / Content Understanding) — https://portal.azure.com/

## Security

**Never paste API keys into files that get committed** — that includes
`README.md`, sample configs, and request screenshots. Enter them through the
Obsidian settings UI; they are stored in
`<vault>/.obsidian/plugins/markitdown-flow/data.json`, which the plugin
tells the vault's `.gitignore` to ignore by default (Obsidian's `.obsidian/`
is typically already gitignored).

If a key has ever been pushed to a public repository, rotate it
immediately in the issuing console.

## Logs

The engine writes detailed, secret-masked logs to:

```
~/omnidata_logs/engine_YYYYMMDD.log
```

(`~` resolves to your OS home directory on every platform.)

A command palette entry **MarkItDown Flow: Open log folder** opens that
directory in your OS file manager.

## Self-test

A built-in diagnostic runs the image pipeline against four bundled fixtures
(clean document, skewed document, ruled table, photo) and reports
classification + confidence + AI-escalation decision per case. Use it to
confirm the engines you have installed are actually picked up and behaving:

- **Command palette → "MarkItDown Flow: Run image pipeline self-test"**
- **Settings → MarkItDown Flow → Image pipeline → "Run self-test"**

The modal also writes an optional `.md` report to your output folder so you
can share results when reporting issues. Fixtures and the driver scripts
live under [`tests/`](tests/README.md).

## Development

```bash
git clone https://github.com/greatgc-flow/MarkItDown-Flow.git
cd MarkItDown-Flow
npm install
npm run dev      # esbuild in watch mode
npm run build    # tsc -noEmit + esbuild production bundle
npm test         # jest
```

## Credits

- [Microsoft MarkItDown](https://github.com/microsoft/markitdown) — the
  conversion engine.
- [`ethanolivertroy/obsidian-markitdown`](https://github.com/ethanolivertroy/obsidian-markitdown)
  — TypeScript surface (commands, modals, settings, drag-and-drop, history,
  Python discovery) inherited from this excellent upstream template.

## License

MIT — see [LICENSE](LICENSE).
