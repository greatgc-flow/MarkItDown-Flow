# MarkItDown Flow 2.1

Convert local documents to Markdown in Obsidian Desktop. Flow saves a complete note only when the document qualifies for direct text conversion. A PDF with 99 text pages and a single scanned page stays in the external OCR queue. You can inspect the original, extract its existing text to a separate partial note, or hand it to a transcription tool of your choice.

## Setup

Use an isolated Python environment and the matching desktop plugin bundle. The 2.1 candidate requires markitdown-gc 0.3.10 or newer in the 0.3 series. Under Settings → MarkItDown Flow, enter the absolute path to the environment's Python and choose an output directory relative to the vault. Setup checks the interpreter, dependencies and protocol. The desktop plugin uses isolated Python and an argument array. Installation, upgrade and rollback instructions are in [BOOTSTRAP.md](engine/BOOTSTRAP.md).

## Convert, inspect or hand off

| Action | How to use it | Result |
|---|---|---|
| Convert a folder | Run **Convert folder to Markdown**, or use the ribbon, context menu or confirmed drop | Qualified sources create notes under `Complete/`. Each excluded original has its own reason. |
| Inspect composition | Run **Inspect document composition** or choose **Inspect** in the results | Shows how many pages were inspected and measured, their roles, and estimated text, image, background and other area. Preview writes no note. |
| Save partial text | Choose **Extract existing text** for a mixed PDF | Creates a separate `Partial/*.text-only.md` with page locations and omission markers. The source remains excluded. |
| Hand off to another tool | Filter results by **External OCR needed** | Reveal the original, copy the list as CSV or make a byte-identical copy under `External-OCR/`. |
| Copy photo information | Select a standalone JPG/JPEG/PNG and choose **Photo information** | If ExifTool is available, copy selected fields. GPS, author and device identifiers require explicit selection. |
| Retry or inspect a conflict | Review the per-file result and rerun after correcting the cause | Identical output can be reused. A note with different bytes is preserved and reported as a conflict. |

## Command-line usage

```sh
mdflow run ./inbox -o ./notes
mdflow run --dry-run ./paper.pdf
mdflow extract-text ./mixed.pdf -o ./notes
mdflow run --input-list paths.json -o ./notes
mdflow version
mdflow selftest
```

The input list is a UTF-8 JSON array of absolute paths. The output stream uses JSON Lines with a header, file results and a footer. Exit 0 includes expected exclusions, 1 indicates invalid usage or an incompatible runtime, and 2 indicates an operational failure. An interrupted stream without a footer has incomplete results.

For a selected source, use `handoff-copy` or `photo-info` with its path, `--sha256` and `--original-sha256` from the file record. Add `--member` for an archive member. A changed digest blocks the action. Metadata requires one or more explicit `--field` choices.

## Network services and purpose

Strict conversion, inspection, partial export, handoff and photo metadata are local operations. The user chooses any external transcription tool and initiates uploads separately. Installing a package or downloading a plugin release requires the selected package registry or GitHub. Open external documentation links only when you choose to do so.

## Outside-vault access

The desktop plugin launches the configured virtual-environment interpreter, reads selected files and folders, and stages transient parser data or large input selections in private temporary directories. The optional ExifTool process receives a private copy of the selected image for a bounded, field-scoped read. Local original copies preserve the source file's own metadata.

## Telemetry

Flow disables ONNX Runtime telemetry for engine operations. Diagnostics and composition previews contain no transcribed page text. Source paths appear in results so you can reopen the original. Exporting a list or copying metadata to the clipboard is an explicit action.

## Account, API key and cost

The strict workflow requires no API key or paid transcription provider. Prior selective-OCR CLI automations can explicitly use `mdflow legacy-run` on the new engine. That entry point can contact a configured provider and incur charges under its historical approval and cache policy. The legacy plan and provider commands are intended for those callers. [Historical CLI and provider disclosures](https://github.com/greatgc-flow/MarkItDown-Flow/blob/b9cc63551e79e8ee0038fbadcdadd610f3206a65/README.md)

## Migration and limits

Install the shell and engine as a matched pair. A 2.0 environment uses the old protocol. Keep its environment and plugin assets together for rollback. Reliable page geometry and partial export are available for PDF. Missing evidence, ambiguous media, unreadable text layers and limited inspection produce a separate outcome. The preview shows measured-page coverage so missing pages do not inflate area estimates.

The [English product specification](docs/strict-markdown/PRE_TDD_SPEC_EN.md) records the acceptance criteria. The [packaging verification guide](docs/renewal/PACKAGING_VERIFICATION.md) describes the evidence required before distribution.

## Development and license

Use Python for the engine and Node 24 for the shell. Run pytest under `engine/` and run `npm ci`, `npm run typecheck`, `npm test` and `npm run build` under `shell/`. See [LICENSE](LICENSE).
