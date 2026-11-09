# MarkItDown Flow 2.0.0

MarkItDown Flow converts local documents to Markdown and plans selective OCR for
pages and images. The engine (`mdflow`, a Python CLI) uses `markitdown-gc`
0.3.5. The desktop Obsidian shell drives an engine installed separately in a
virtual environment. Release verification is still pending; see
[packaging verification](docs/renewal/PACKAGING_VERIFICATION.md).

## Setup

Download the standard plugin assets `main.js`, `manifest.json`, and `styles.css`
from the same release. Download and verify `mdflow-2.0.0-py3-none-any.whl`, `BOOTSTRAP.md`, and
`SHA256SUMS` separately. Follow [BOOTSTRAP.md](engine/BOOTSTRAP.md) in your own
terminal, then enter the absolute venv Python path in the plugin settings
("Engine interpreter"; the value is saved when you leave the field or press
Enter). The plugin never installs Python or dependencies and never probes a
partially typed path. Keep the venv at its original location.

## Network services and purpose

The default provider `none` performs local conversion and sends no document data.
Optional `openai-compatible` OCR sends selected page/image rasters and a fixed
prompt to the endpoint configured by the plugin setting "Base URL" (default
`https://api.openai.com/v1`, passed to the engine as `MDFLOW_BASE_URL`; the
setting wins over a value in the launch environment) with the model from the
"Model" setting and the key from `MDFLOW_API_KEY`. The engine posts to
`<Base URL>/chat/completions` and shows that destination in the approval dialog.
Other endpoints must actually implement this protocol. Native Azure OpenAI,
Gemini and Anthropic APIs are not configured automatically; using a compatible
proxy or Ollama (for example `http://127.0.0.1:11434/v1`; plain `http` is
accepted for loopback addresses only) requires validating its protocol,
destination and model before approval. No compatibility test for those services
is claimed here. Provider privacy and retention follow the configured service's
policies; consult
[OpenAI's data controls](https://platform.openai.com/docs/guides/your-data) when
using OpenAI. External bootstrap downloads assets from the release host and
wheels from the Python package index (PyPI). The CLI-only `command` provider
executes a user-specified program with its declared egress behavior; the shell
does not configure or execute command providers.

## Outside-vault access

The selected engine executable and venv, selected source documents and
temporary page rasters can be outside the vault. The engine reads sources to
classify/convert them, creates temporary rasters for selected units under the
OS temporary directory, and reads the venv to execute dependencies. Output
selected through the shell stays inside the vault. Sources and outputs are
preserved during upgrades and cleanup.

The CLI cache defaults to `~/.mdflow/cache`. The plugin keeps its cache,
transient report spool, one-run consent files and redacted logs inside the
vault under `.obsidian/plugins/markitdown-flow/` (`cache/`, `spool/`,
`consent/`, `logs/`). The cache contains OCR transcriptions and is retained by
default; if your vault or its plugin folder is synchronized (Obsidian Sync with
installed community plugins enabled, or a cloud-synced vault), those
transcriptions and logs are replicated too. Exclude the folder from sync or
clear the cache (`mdflow cache clear --cache <plugin-dir>/cache`) if that is not
acceptable. Explicit clearing can cause paid retranscription.

## Telemetry

There is no client telemetry. Local diagnostic logs help identify failures and
can include document names; review them before sharing. This statement describes
the client only: configured OCR providers have their own logging, retention and
privacy rules. Approval identifies the provider destination and selected data.
Offline operation with provider `none` requires no provider account or key.

## Account, API key and cost

Remote OCR can require an account and API key and incur charges. Supply
`MDFLOW_API_KEY` only through the launch environment; the shell reports key
presence and does not persist credentials. Fully quit Obsidian, set the variable
in your own terminal and launch the actual installed executable from that
terminal. See [terminal launch instructions](engine/BOOTSTRAP.md#optional-remote-ocr).
Activating a venv does not change an already running app's environment.
Optional `MDFLOW_TIMEOUT_S` and `MDFLOW_PROXY` are forwarded from the same
environment; the Base URL comes from the plugin setting.

Before any remote work the plugin runs `mdflow plan` and shows one approval
dialog for the whole selection: per file the destination, model, selected
units, DPI, the per-file maximum request budget and estimated maximum cost (or
unknown cost when pricing is unavailable), threshold and sensitive-pattern
notices. Files with nothing left to send (already cached) are listed as
informational and need no approval. These are planning limits, not a billing
cap. Interrupted requests, retry, force and concurrent cache misses can incur
additional charges. A Cancel button stays visible in the status bar for the
whole job (planning, approval, conversion); forced cancellation may leave the
provider processing a request. CLI commands run with your user privileges.
Review the selected rasters, endpoint, model and costs before approving.

## Migration and operation

Create a separate venv for upgrades, validate it externally and then change the
selected interpreter; retain the previous venv for rollback. Six local command
aliases remain: `convert-file`, `convert-folder`, `convert-url`,
`view-conversion-history`, `open-log-folder`, and `run-image-pipeline-selftest`.
The URL alias displays removal guidance; the self-test alias explains that the
old image-pipeline router was retired and runs the engine's offline self-test.
Audio/YouTube, Azure fallback routing, and inherited wrapper behavior are
removed. Command providers are CLI-only. Outputs use the fixed document
Markdown/media naming defined in the v2 spec. File and folder selection uses the
standard file dialog of the desktop app; a drop of local files shows the list
for confirmation before any work. Run options (render DPI, minimum OCR
priority, maximum units per file, approval threshold, sensitive path globs) are
editable in the settings tab.

Migration drops removed settings and credentials and keeps a sanitized rollback
snapshot `data.v1.json` next to `data.json`. Old external backups can retain
credentials. If a migration write fails, or the settings file was written by a
newer plugin version, settings are read-only and jobs are blocked; nothing is
written back. After a failed migration the original secret-bearing disk file
may remain: remove its credentials manually before syncing. A failed write does
not prove sanitization. Disable the plugin before rollback; preserve current
settings/cache, restore verified 1.0.8 assets and the sanitized v1 snapshot, and
review v1 dependency/network behavior before re-enabling. Never give schema-2
settings to v1 or restore removed secrets automatically. Published assets stay
immutable; public defects require a higher patch version.

## Command-line usage

The engine works without Obsidian from the venv created in Setup
(`<venv>/bin/python -m mdflow ...`, or `<venv>\Scripts\python.exe -m mdflow ...`
on Windows). The authoritative contract is [10_SPEC section 10](docs/renewal/10_SPEC.md#10-cli-surface).

```text
python -m mdflow run  <PATH>... -o OUT_DIR [--provider none|openai-compatible|command] [--model NAME] [--progress jsonl]
python -m mdflow plan <PATH>... [options]          # prints one Plan JSON per file; no provider call, nothing written
python -m mdflow classify <PATH>                   # sniff/triage/classification only
python -m mdflow version | selftest | providers | cache (stats|clear) [--cache DIR]
```

Remote OCR needs consent per file: `run` stops with exit 3 and an
`approve_required` event for each file, and `plan` prints the full Plan with its
`plan_hash`. Rerun the identical invocation with `--yes HASH` (repeatable) or
`--yes-file FILE` (one hash per line, `#` comments allowed), optionally
`--approved-by TEXT`. Hashes exclude cache state, so an approval stays valid
while other files fill the cache. The `command` provider requires
`--command "<template>" --command-egress true|false --trust-command --model <label>`
and runs the program with your privileges on every unit.

## Development and license

See [25_PACKAGING](docs/renewal/25_PACKAGING.md) for release gates. Build with
`python tools/build_engine.py` and `python tools/build_release.py`; dependencies
are explicitly pinned, and missing wheel or review evidence blocks release.
Required CI targets are Windows x64, Ubuntu x64 and macOS Intel, Python 3.10 and
3.14; Python 3.15 is experimental. Python 3.11-3.13 need the install/classify
smokes before being advertised as verified. Shell: `cd shell && npm ci && npm run typecheck && npm test && npm run build`.

MIT license; see [LICENSE](LICENSE). Historical MarkItDown Flow contributors and
Microsoft MarkItDown retain their respective credit and licenses. Third-party
package licenses and artifact origins are included in the engine inventory.
