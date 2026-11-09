# Engine bootstrap

Download the release wheel `mdflow-2.0.0-py3-none-any.whl`, `BOOTSTRAP.md`,
`NOTICE.txt`, `LICENSE`, `SHA256SUMS` and provenance bundles from the same release
host. Verify SHA-256 and attestations before installation. The commands below
use the Python package index (PyPI) https://pypi.org/simple and download dependency
wheels over the network. Execute commands in your own terminal from the wheel’s
download directory. The Obsidian plugin never downloads or installs Python,
dependencies or updates.

Install a supported Python with venv support yourself: [Windows/macOS downloads](https://www.python.org/downloads/),
or [Ubuntu Python documentation](https://documentation.ubuntu.com/ubuntu-for-developers/howto/python-setup/).
Use Python 3.10-3.14 after the corresponding release target checks pass; 3.15 is
experimental. Only x64 targets are claimed by this baseline. On Ubuntu, install
the matching venv prerequisite through your OS administrator/package manager.

Windows PowerShell (replace both quoted directory paths):

```powershell
Set-Location -LiteralPath 'C:\Downloads\mdflow-2.0.0-engine'
py -3.14 -m venv 'C:\mdflow-venvs\2.0.0'
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -m pip install --only-binary=:all: --index-url https://pypi.org/simple './mdflow-2.0.0-py3-none-any.whl' 'markitdown-gc>=0.3.5,<0.4'
if ($LASTEXITCODE -ne 0) { throw 'Wheel install failed' }
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -I -m mdflow selftest
if ($LASTEXITCODE -ne 0) { throw 'Engine selftest failed' }
& 'C:\mdflow-venvs\2.0.0\Scripts\python.exe' -I -m mdflow version
if ($LASTEXITCODE -ne 0) { throw 'Engine version check failed' }
```

Ubuntu/macOS POSIX shell:

```sh
set -e
cd '/path/to/mdflow-2.0.0-engine'
python3.14 -m venv '/path/to/mdflow-venvs/2.0.0'
'/path/to/mdflow-venvs/2.0.0/bin/python' -m pip install --only-binary=:all: --index-url https://pypi.org/simple './mdflow-2.0.0-py3-none-any.whl' 'markitdown-gc>=0.3.5,<0.4'
'/path/to/mdflow-venvs/2.0.0/bin/python' -m pip check
'/path/to/mdflow-venvs/2.0.0/bin/python' -I -m mdflow selftest
'/path/to/mdflow-venvs/2.0.0/bin/python' -I -m mdflow version
```

Set `enginePython` to the resulting absolute `Scripts/python.exe` or `bin/python`
path. Activation is unnecessary. Keep the venv at its creation location; recreate
it after moving it or removing its base interpreter. Create another venv for an
upgrade and retain the previous one for rollback. Do not use global fallback
packages. The mdflow wheel is pure Python; dependencies can contain native code. Its metadata declares Core >=0.3.5,<0.4, pypdfium2 >=5,<6 and Pillow >=11,<14, matching the released shell gate. Core may impose tighter constraints; pip check and selftest verify the resolved environment.

## Optional remote OCR

Provider `none` requires no key. For remote OCR, fully quit Obsidian first, then
set `MDFLOW_API_KEY` in the terminal and launch your actual installed executable.
The following paths are examples; verify the installed path yourself. Desktop
launch/inheritance results remain pending the named per-OS rehearsal.

PowerShell: `$env:MDFLOW_API_KEY = '<your key>'`, then
`& "$env:LOCALAPPDATA\Obsidian\Obsidian.exe"` (or your actual installed path).

macOS: `export MDFLOW_API_KEY='<your key>'`, then
`'/Applications/Obsidian.app/Contents/MacOS/Obsidian'`.

Linux: `export MDFLOW_API_KEY='<your key>'`, then
`'/path/to/Obsidian.AppImage'` (or the actual installed executable).

Do not save the key in settings, command arguments or a checked-in file. Finder,
Dock and shortcut launches may not inherit the terminal environment. A running
Obsidian instance will not gain variables by activating an engine venv. The UI
shows presence only. Read the README network and cost disclosures before consent.

## Reference reproduction (Linux x64 / CPython 3.14 only)

CI generates one `reference-requirements.txt` with pip-tools, including Core 0.3.6, the exact wheel hash and resolved dependency hashes. Verify it alongside
the wheel; in a new venv on that target, from the download directory, run:

```sh
'/path/to/reference-venv/bin/python' -m pip install --require-hashes --only-binary=:all: --index-url https://pypi.org/simple -r reference-requirements.txt
'/path/to/reference-venv/bin/python' -m pip check
'/path/to/reference-venv/bin/python' -I -m mdflow selftest
```

This reference does not promise identical versions on other targets. Ordinary
installs resolve the wheel’s supported dependency range; CI checks all advertised
OS/Python targets separately. Exact installed tool versions appear in `version`
and output provenance. Keep each venv at its creation path for rollback.
