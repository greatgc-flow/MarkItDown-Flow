# Command provider adapters

The engine passes one prepared raster to an external command and reads its UTF-8 transcription from stdout. This supports local tools and external services without adding a built-in Azure or peerhub provider. The command must write only transcription to stdout, return nonzero on failure, and finish before `MDFLOW_TIMEOUT_S`. Diagnostics belong on stderr; do not print credentials.

A local adapter can use this Python script, saved as `ocr_adapter.py`:

```python
from pathlib import Path
import sys

image = Path(sys.argv[1])  # prepared PNG/JPEG, not the original document
# Replace this example text with your local OCR library's result for image.
sys.stdout.reconfigure(encoding="utf-8")
print("Example transcription")
```

Preview it with the same interpreter and script paths you will use for the run:

```text
mdflow plan scan.pdf --provider command --command "python ocr_adapter.py {input}" --command-egress false --trust-command --model adapter-v1
mdflow run scan.pdf -o output --provider command --command "python ocr_adapter.py {input}" --command-egress false --trust-command --model adapter-v1
```

`{input}` and `{mime}` are substituted in individual arguments after POSIX-style splitting; no shell is invoked. Quote paths with spaces inside the template, using forward slashes for Windows paths. Use an absolute interpreter/script path when the working directory or PATH is uncertain. The example emits a placeholder transcription; it is an adapter skeleton, not an OCR implementation.

Use `--command-egress true` for any adapter that sends rasters to a remote service. Inspect the resulting Plan and approve its file hashes with `--yes-file` before running. Set `--trust-command` only for a command you reviewed: the engine cannot enforce the command's egress declaration or constrain its subprocesses. Only the documented environment allowlist and explicit `--command-env NAME` names reach the child. Keep keys in environment variables and allowlist their names; never put keys on argv or in the model label. Output is capped at 4 MiB and the direct child is killed/reaped on timeout; adapters must manage their own descendants.

The archived [Core guide](../renewal/ref/markitdown-gc_GUIDE_0.3.5.md) documents `markitdown-gc -d -e ENDPOINT` for Azure Document Intelligence and the `peerhub ask` workflow. Those commands are not drop-in raster adapters. An Azure adapter must accept the prepared raster, obtain service credentials from an explicitly forwarded environment variable, submit it, wait within the deadline and emit only extracted text. Azure CU needs its own adapter with the same contract. A peerhub adapter must arrange for the peer to read the provided raster path, collect the completed transcription and strip peerhub progress/envelope output; peerhub has no attachment flag. External-service setup and human verification remain outside the engine. Do not claim local egress for either remote workflow.

The cache fingerprint includes the command template, model label and environment **names**, but not script contents or environment values. Change `--model` when adapter behavior changes, or use `--force`, to avoid reusing old transcriptions.

The release/reference baseline is Core0.3.6; the archived 0.3.5 guide retains stable references. See the [Core reference note](../renewal/ref/README.md).
