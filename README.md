# MarkItDown Flow 2.0.0

MarkItDown Flow converts local documents to Markdown and plans selective OCR for
pages and images. The engine (`mdflow`, a Python CLI) uses `markitdown-gc`
0.3.7 (published on PyPI). The desktop Obsidian shell drives an engine installed separately in a
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

The plugin always launches that interpreter in isolated mode
(`python -I -X utf8 -m mdflow ...`) with the venv directory as working
directory, not the vault or the plugin folder (if you created the venv inside
your vault, that venv directory is the working directory; it is still not on
the import path). Isolated mode ignores `PYTHONPATH`, the user site-packages
and the current directory, so files inside a vault (including a synced or
downloaded vault) can never be imported in place of the engine or its
libraries. Use the same `-I` form in your own scripts.

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
accepted for `localhost`, `127.0.0.1` and `[::1]` spelled exactly that way,
and the settings tab refuses other `http` values, loopback aliases such as
`127.1` or `0x7f000001`, credentials, query strings and fragments up front,
the same rule the engine applies)
requires validating its protocol, destination and model before approval. No compatibility test for those services
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

Two optional programs on your machine can also be started by the engine. If
`exiftool` is found (on PATH or via `EXIFTOOL_PATH`), the engine runs it on
standalone `png`, `jpg` and `jpeg` sources and writes the metadata lines it
reports (for example `GPSPosition`, `Author` or `Artist`) into the converted
note, so a note can contain location or author data the image carried. Only if
you turn on "Legacy formats (LibreOffice)", the engine runs your own LibreOffice
(`soffice` on PATH or `SOFFICE_PATH`) in a private profile with macros and link
updates disabled to convert legacy `.doc`, `.ppt`, `.rtf` and HWP sources; it
reads the source and writes a temporary converted copy that is not kept. The
plugin itself never runs either program.

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
informational and need no approval. The default button, "Keep OCR pending",
converts everything that needs no OCR right away and leaves the OCR parts as
pending markers without contacting the provider; convert the same files again
later to review and approve them. Closing the dialog converts nothing. These
are planning limits, not a billing
cap. Interrupted requests, retry, force and concurrent cache misses can incur
additional charges. A Cancel button stays visible in the status bar for the
whole job (planning, approval, conversion). On macOS and Linux, Cancel first
asks the engine to stop cooperatively and forces termination after five
seconds; on Windows every Cancel is a forced termination, because the plugin
cannot deliver a console control event to the engine. A forced termination may
leave the provider processing a request, produces no conversion report, and can
leave the engine's temporary raster folder (`mdflow-*` under the OS temporary
directory) behind; delete such folders if they accumulate. CLI commands run
with your user privileges. Review the selected rasters, endpoint, model and
costs before approving.

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
standard file dialog of the desktop app; an empty selection is reported rather
than ignored. The optional drop handler is off by default: when enabled, every
local file dropped anywhere in the workspace is converted instead of being
attached to the note, after a confirmation that lists the files. The
context-menu, drop and language settings take effect after the plugin is
reloaded. Run options (render DPI, minimum OCR priority, maximum units per
file, approval threshold, sensitive path globs) are editable in the settings
tab. A value a text field refuses (a relative interpreter path, an output path
outside the vault, a Base URL the engine would reject, a non-integer bound) is
not saved: a notice says so and the field shows the saved value again. A
relative interpreter path found in a hand-edited or synced settings file is
likewise reset and never launched.

Legacy `.doc`, `.ppt`, `.rtf` and pre-5.0 HWP files are reported, not
converted, unless you turn on "Legacy formats (LibreOffice)" in the Conversion
section (off by default). The plugin then passes `--preconvert-legacy` to the
engine, which converts each such file with your own LibreOffice (`soffice` on
PATH or `SOFFICE_PATH`; the plugin never installs it) in a private profile with
macros and link updates disabled, and marks the result as derived from the converted
copy: the result list shows "derived · LibreOffice <version>", the note's
frontmatter carries `fidelity: DERIVED` with the original and derived SHA-256
values, and the report carries `W_PRECONVERTED`. The setting's description and
the setup diagnostics show which LibreOffice and exiftool the engine detected;
`EXIFTOOL_PATH` and `SOFFICE_PATH` are forwarded to the engine. If the engine
venv also contains the upstream `markitdown` package, the version check is
blocked with `E_CORE_CONFLICT` and the setup diagnostics show the exact
`pip uninstall -y markitdown` command for the selected interpreter.

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
(`<venv>/bin/python -I -m mdflow ...`, or `<venv>\Scripts\python.exe -I -m mdflow ...`
on Windows; `-I` keeps the current directory off the import path). The
authoritative contract is [10_SPEC section 10](docs/renewal/10_SPEC.md#10-cli-surface).

```text
python -I -m mdflow run  <PATH>... -o OUT_DIR [--provider none|openai-compatible|command] [--model NAME] [--progress jsonl]
python -I -m mdflow plan <PATH>... [options]          # prints one Plan JSON per file; no provider call, nothing written
python -I -m mdflow classify <PATH>                   # sniff/triage/classification only
python -I -m mdflow version | selftest | providers | cache (stats|clear) [--cache DIR]
```

Legacy `.doc`, `.ppt`, `.rtf` and pre-5.0 HWP conversion is opt-in: add
`--preconvert-legacy` to `run`, `plan` or `classify` (programmatic setting
`preconvert_legacy=True`). Install LibreOffice yourself and put `soffice` on
PATH or set `SOFFICE_PATH` to its executable. Each conversion uses a private
profile with macros and link updates disabled; the default 60-second deadline
(`--preconvert-timeout-s`) kills the entire child tree. Core owns conversion, process cleanup and intermediate files. mdflow inspects
the returned Markdown and extracted media. Markdown retains original and returned-Markdown
SHA-256 values (`derived_format: markdown`) and `fidelity: DERIVED`; the report includes `W_PRECONVERTED`
with the LibreOffice version. Failed conversions leave no Markdown and siblings
continue. Other legacy formats still require manual conversion. In the plugin
the same option is the "Legacy formats (LibreOffice)" toggle (see "Migration
and operation").

CSV/TSV/JSON classify as T. Markdown/HTML/XML/EPUB classify as T with
`W_MEDIA_NOT_INSPECTED`; embedded media in those formats is not inspected.
A venv containing both upstream `markitdown` and `markitdown-gc` is refused
with `E_CORE_CONFLICT` on every entry point, including `version` and `selftest`;
remove upstream `markitdown` or use a dedicated venv.

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
