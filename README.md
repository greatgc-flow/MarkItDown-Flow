# MarkItDown Flow 2.0.0

MarkItDown Flow converts local documents to Markdown and plans selective OCR for
pages and images. The engine uses `markitdown-gc` 0.3.5. The desktop Obsidian
shell uses an engine installed separately in a virtual environment. Release
verification is still pending; see [packaging verification](docs/renewal/PACKAGING_VERIFICATION.md).

## Setup

Download the standard plugin assets `main.js`, `manifest.json`, and `styles.css`
from the same release. Download and verify `engine.zip`, `engine.lock`, and
`SHA256SUMS` separately. Follow [BOOTSTRAP.md](engine/BOOTSTRAP.md) in your own
terminal, then select the absolute venv Python path in the plugin. The plugin
never installs Python or dependencies. Keep the venv at its original location.

## Network services and purpose

The default provider `none` performs local conversion and sends no document data.
Optional `openai-compatible` OCR sends selected page/image rasters and a prompt
to the endpoint configured through `MDFLOW_BASE_URL`, using `MDFLOW_MODEL` and
`MDFLOW_API_KEY`. The standard OpenAI endpoint is `https://api.openai.com/v1`.
Other endpoints must actually implement this protocol. Native Azure OpenAI,
Gemini and Anthropic APIs are not configured automatically; using a compatible
proxy or Ollama requires validating its protocol, destination and model before
approval. No compatibility test for those services is claimed here. Provider
privacy and retention follow the configured service's policies; consult
[OpenAI's data controls](https://platform.openai.com/docs/guides/your-data) when
using OpenAI. External bootstrap downloads assets from the release host and
wheels from the Python package index (PyPI). The CLI-only `command` provider
executes a user-specified program with its declared egress behavior; the shell
does not configure or execute command providers.

## Outside-vault access

The selected engine executable and venv, selected source documents, temporary
page rasters and transcription cache can be outside the vault. The engine reads
sources to classify/convert them, creates temporary rasters for selected units,
and reads the venv to execute dependencies. CLI cache defaults to
`~/.mdflow/cache`; plugin cache is `<plugin-dir>/cache`. Cache contains
transcriptions and is retained by default. Explicit clearing can cause paid
retranscription. Shell-selected output stays inside the vault. Sources and
outputs are preserved during upgrades and cleanup.

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

Plans show the per-file maximum request budget and estimated maximum cost, or
unknown cost when pricing is unavailable. These are planning limits, not a
billing cap. Interrupted requests, retry, force and concurrent cache misses can
incur additional charges. Forced cancellation may leave the provider processing
a request. CLI commands run with your user privileges. Review the selected
rasters, endpoint, model and costs before approving.

## Migration and operation

Create a separate venv for upgrades, validate it externally and then change the
selected interpreter; retain the previous venv for rollback. Six local command
aliases remain: `convert-file`, `convert-folder`, `convert-url`,
`view-conversion-history`, `open-log-folder`, and `run-image-pipeline-selftest`.
The URL alias displays removal guidance. Audio/YouTube, Azure fallback routing,
and inherited wrapper behavior are removed. Command providers are CLI-only.
Outputs use the fixed document Markdown/media naming defined in the v2 spec.

Migration drops removed settings and credentials and keeps a sanitized rollback
snapshot `data.v1.json.bak`. Old external backups can retain credentials. If a
migration write fails, the original secret-bearing disk file may remain: jobs
are blocked and you must remove its credentials manually before syncing. A
failed write does not prove sanitization. Disable the plugin before rollback;
preserve current settings/cache, restore verified 1.0.8 assets and the sanitized
v1 snapshot, and review v1 dependency/network behavior before re-enabling.
Never give schema-2 settings to v1 or restore removed secrets automatically.
Published assets stay immutable; public defects require a higher patch version.

## Development and license

See [25_PACKAGING](docs/renewal/25_PACKAGING.md) for release gates. Build with
`python tools/build_engine.py` and `python tools/build_release.py`; dependencies
are explicitly pinned, and missing wheel or review evidence blocks release.
Required CI targets are Windows x64, Ubuntu x64 and macOS Intel, Python 3.10 and
3.14; Python 3.15 is experimental. Python 3.11-3.13 need the install/classify
smokes before being advertised as verified.

MIT license; see [LICENSE](LICENSE). Historical MarkItDown Flow contributors and
Microsoft MarkItDown retain their respective credit and licenses. Third-party
package licenses and artifact origins are included in the engine inventory.
