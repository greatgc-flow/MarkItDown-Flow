# Flow 2.1.0 post-release Linux smoke test

The public release passed a clean Linux engine install and document-processing smoke test on November 28, 2026. The owner desktop rehearsal (MAN-04) remains pending. The release acceptance score remains 99/100.

| Item | Observed result |
| --- | --- |
| Release identity | Tag `2.1.0` resolved to `dc067838e8f71ff5d3c07d18ab675eb89a5f7e71`. The existing Obsidian Community entry showed `2.1.0`. |
| Clean install | The public `mdflow-2.1.0-py3-none-any.whl` installed in a fresh Debian 13 x64 virtual environment with Python 3.12.14 and `markitdown-gc` 0.3.10. `pip check`, `mdflow selftest`, and the protocol 2 version probe passed. |
| Strict PDF conversion | A synthetic PDF with 99 text pages and one scanned final page was excluded as a whole. Dry-run inspected and measured all 100 pages, marked page 100 for OCR, and created no files. |
| Partial export and external OCR handoff | Explicit export retained 99 text pages and an omission marker. Handoff copied the original byte for byte and reused it on the next request. A changed original blocked the handoff and a user edit to the partial note survived a retry. The test used paths with spaces and Hangul. |
| Complete text conversion | A plain-text file produced a complete Markdown note. A warm rerun preserved its digest and modification time. |
| Optional ExifTool | With ExifTool 13.64, the engine returned the selected Make and ImageWidth fields. Artist appeared after an explicit request. GPS stayed out of both responses and the JPEG bytes stayed identical. |
| Rollback files | The public 1.0.8 tag, plugin bundle, manifest and stylesheet were reachable. The downloaded manifest declared plugin ID `markitdown-flow` and version `1.0.8`. |
| Linux desktop | The vendor Linux packages for Obsidian 1.14.4 and 1.15.1 matched their published SHA-256 digests. The isolated desktop launch stopped at local display socket creation with `EPERM`, leaving real-app checks pending. |

MAN-04 requires six owner desktop runs across Windows, macOS and Linux at the minimum and current Obsidian versions. Record a directory install, upgrade from 1.0.8, rollback, commands, English and Korean UI, and cancellation and restart in isolated vaults. Include the real Windows cancellation. Fill in the rehearsal template once the checks have been observed. [MAN-04 template](https://github.com/greatgc-flow/MarkItDown-Flow/blob/2.1.0/docs/renewal/manual-templates/release_rehearsal.yml)

[Flow 2.1.0 release](https://github.com/greatgc-flow/MarkItDown-Flow/releases/tag/2.1.0) · [Obsidian Community entry](https://community.obsidian.md/plugins/markitdown-flow) · [Release validation](https://github.com/greatgc-flow/MarkItDown-Flow/actions/runs/46093803133)
