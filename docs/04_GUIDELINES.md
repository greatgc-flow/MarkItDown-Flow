# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace overview

This is a multi-project workspace containing:

| Project | Type | Purpose |
|---|---|---|
| `markitdown/` | Python library | Microsoft's file-to-Markdown converter (PDF, DOCX, PPTX, XLSX, HTML, etc.) |
| `obsidian-markitdown/` | TypeScript Obsidian plugin | Bridges Obsidian vault to `markitdown` via Python subprocess |
| `obsidian-sample-plugin/` | TypeScript Obsidian plugin | Official Obsidian plugin reference template |
| `MarkItDown-Flow/` | Placeholder | Early-stage experimental fork (minimal content) |

---

## markitdown (Python)

**Requirements:** Python 3.10+, `hatch`

```bash
cd markitdown/packages/markitdown
pip install hatch
hatch shell          # Activate virtual environment
hatch test           # Run test suite
pre-commit run --all-files  # Run lint/format checks
```

**Architecture:** The package lives under `packages/markitdown/src/markitdown/`. Conversion logic is split into `converters/` — one module per format (PDF, PPTX, DOCX, XLSX, HTML, images, audio, etc.). A plugin system lets 3rd-party packages register additional converters. Optional heavy dependencies (azure-ai-*, pdfminer, python-pptx, etc.) are declared as extras in `pyproject.toml` and are not required for basic use. The `markitdown-mcp/` and `markitdown-ocr/` packages are separate installable packages under `packages/`.

---

## obsidian-markitdown (TypeScript)

**Requirements:** Node.js 18+, npm, Python 3.8+ (runtime, not build-time)

```bash
cd obsidian-markitdown
npm install
npm run dev      # Watch mode (esbuild)
npm run build    # Production bundle
npm test         # Jest tests
```

**Install for manual testing:** Copy `main.js`, `manifest.json`, `styles.css` to `<Vault>/.obsidian/plugins/obsidian-markitdown/`, then enable in Obsidian **Settings → Community plugins**.

**Architecture:** TypeScript Obsidian plugin that shells out to a bundled Python wrapper (`python/markitdown_wrapper.py`). Key layers:

- `src/converter/MarkitdownConverter.ts` — orchestrates subprocess calls; always builds args as a string array (never string interpolation)
- `src/modals/` — UI dialogs (File, Folder, URL, Preview, History, BatchProgress, Setup)
- `src/settings/` — settings persistence via Obsidian's `loadData()`/`saveData()`
- `src/utils/` — Python detection, path resolution, file type list, conversion history
- `python/` — bundled Python scripts called at runtime; `markitdown_wrapper.py` handles all conversion via the `markitdown` library

---

## obsidian-sample-plugin (TypeScript)

**Requirements:** Node.js 18+, npm

```bash
cd obsidian-sample-plugin
npm install
npm run dev      # Watch mode
npm run build    # Production bundle
npm run lint     # ESLint (run eslint on src/ or main.ts)
```

**Architecture:** Minimal Obsidian plugin template demonstrating the full plugin API. `src/main.ts` handles only lifecycle (onload/onunload). Settings are in `src/settings.ts`.

---

## Obsidian plugin conventions (applies to both plugin projects)

**Release artifacts:** Only `main.js`, `manifest.json`, and `styles.css` are needed. Never commit `node_modules/` or release build artifacts to the repository.

**Listener cleanup:** Always use `this.registerEvent(...)`, `this.registerDomEvent(...)`, and `this.registerInterval(...)` so Obsidian cleans up on unload.

**TypeScript:** Both projects use `"strict": true`. `obsidian-sample-plugin` additionally enables `noUncheckedIndexedAccess`.

**manifest.json rules:**
- Never change `id` after release
- `version` must be SemVer without a leading `v`
- GitHub release tag must exactly match `manifest.json`'s `version`
- Update `versions.json` to map plugin version → minimum app version

**Settings pattern:**
```ts
this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
```

**Command IDs:** Stable once released — never rename a command's `id` after publishing.

**Desktop-only APIs:** Set `isDesktopOnly: true` in `manifest.json` when using Node.js/Electron APIs. `obsidian-markitdown` requires this because it uses `child_process` for Python subprocess calls.
