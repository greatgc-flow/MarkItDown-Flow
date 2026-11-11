"""MAN-04 rehearsal kit: automates the mechanical part of one owner run (one OS x one Obsidian channel).

    python tools/man04_kit.py run --channel minimum|current [--repo OWNER/REPO] [--assets DIR] [--work DIR]
    python tools/man04_kit.py validate release_rehearsal.yml --commit CANDIDATE_SHA

``run`` downloads the release assets, verifies them against SHA256SUMS, installs the plugin into a throwaway
vault, builds a fresh venv exactly as BOOTSTRAP.md says (pip check, selftest, version) and writes the mechanical
fields of this OS/channel into the record. Every human observation stays ``TODO``: the kit never writes PASS.
The record is JSON, which is valid YAML. ``validate`` runs the real gate (``trace.py attest MAN-04``); it proves
the file shape, not that a human saw anything.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from build_engine import ASSETS, SUBJECTS, WHEEL, digest, read_sums  # noqa: E402
import release_evidence  # noqa: E402

ROOT = TOOLS.parent
TEMPLATE = ROOT / 'docs/renewal/manual-templates/release_rehearsal.yml'
TAG = '2.0.0'
PLUGIN_ID = 'markitdown-flow'
OS_NAMES = {'Windows': 'windows', 'Darwin': 'macos', 'Linux': 'linux'}


class KitError(Exception):
    pass


def verify_assets(folder: Path) -> dict[str, str]:
    """SHA-256 of every subject; raises KitError if one is missing or differs from SHA256SUMS."""
    missing = [name for name in SUBJECTS if not (folder / name).is_file()]
    if missing:
        raise KitError(f'missing release assets: {", ".join(missing)}')
    try:
        listed = read_sums(folder)
    except ValueError as error:
        raise KitError(f'SHA256SUMS: {error}') from None
    actual = {name: digest(folder / name) for name in SUBJECTS}
    bad = [name for name in ASSETS if listed[name] != actual[name]]
    if bad:
        raise KitError(f'SHA256SUMS mismatch for: {", ".join(bad)}')
    return actual


def install_plugin(folder: Path, vault: Path) -> Path:
    """Copy main.js/manifest.json/styles.css into <vault>/.obsidian/plugins/<id>; keeps any data.json."""
    target = vault / '.obsidian' / 'plugins' / PLUGIN_ID
    target.mkdir(parents=True, exist_ok=True)
    for name in ('main.js', 'manifest.json', 'styles.css'):
        shutil.copyfile(folder / name, target / name)
    listing = vault / '.obsidian' / 'community-plugins.json'
    enabled = json.loads(listing.read_text(encoding='utf-8')) if listing.is_file() else []
    if PLUGIN_ID not in enabled:
        listing.write_text(json.dumps([*enabled, PLUGIN_ID]), encoding='utf-8')
    return target


def _run(python: Path, args: list[str], log: Path, cwd: Path, timeout=1800) -> str:
    # -I ignores PYTHON* variables, so UTF-8 mode is requested with -X (still honoured under -I).
    done = subprocess.run([str(python), '-I', '-X', 'utf8', *args], cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)
    log.write_text(f'$ {" ".join(args)}\nexit {done.returncode}\n{done.stdout}{done.stderr}', encoding='utf-8')
    if done.returncode:
        raise KitError(f'step failed (exit {done.returncode}); see {log}')
    return done.stdout


def provision_engine(folder: Path, work: Path, base_python: str) -> dict:
    """BOOTSTRAP.md in a fresh venv. Runs with -I so nothing in the downloaded folder is imported."""
    venv = work / f'venv-{TAG}'
    if venv.exists():
        if not (venv / 'pyvenv.cfg').is_file():
            raise KitError(f'{venv} exists but is not a venv; remove it yourself')
        shutil.rmtree(venv)
    logs = work / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    subprocess.run([base_python, '-I', '-m', 'venv', str(venv)], check=True, timeout=600)
    python = venv / ('Scripts/python.exe' if platform.system() == 'Windows' else 'bin/python')
    _run(python, ['-m', 'pip', 'install', '--only-binary=:all:', '--index-url', 'https://pypi.org/simple',
                  str(folder / WHEEL), 'markitdown-gc>=0.3.9,<0.4'], logs / '1-install.txt', work)
    _run(python, ['-m', 'pip', 'check'], logs / '2-pip-check.txt', work)
    _run(python, ['-m', 'mdflow', 'selftest'], logs / '3-selftest.txt', work)
    _run(python, ['-m', 'mdflow', 'version'], logs / '4-version.txt', work)
    meta = _run(python, ['-c', 'import importlib.metadata as m, platform; '
                         'print(platform.python_version(), m.version("mdflow"), m.version("markitdown-gc"))'],
                logs / '5-versions.txt', work).split()
    return {'python': meta[0], 'engine': meta[1], 'core': meta[2], 'enginePython': str(python), 'logs': str(logs)}


def update_record(record: dict, *, os_name: str, channel: str, hashes: dict[str, str], engine: dict) -> dict:
    """Fill only mechanical fields of the (os, channel) run. Human fields (incl. obsidian_version) stay untouched."""
    runs = [r for r in record['runs'] if r.get('os') == os_name and r.get('obsidian_channel') == channel]
    if len(runs) != 1 or not isinstance(runs[0].setdefault('checks', {}), dict):
        raise KitError(f'record has no unique run with a checks mapping for {os_name}/{channel}')
    run = runs[0]
    run.update(python=engine['python'], engine=engine['engine'], core=engine['core'],
               downloads=[{'asset': name, 'sha256': hashes[name]} for name in SUBJECTS])
    for check in sorted(release_evidence.REHEARSAL):
        run['checks'].setdefault(check, 'TODO')
    return record


def validate(record_path: Path, commit: str) -> list[str]:
    """The real MAN-04 gate: trace.py attest (top-level checks/inputs/evidence/commit + validate_rehearsal)."""
    spec = importlib.util.spec_from_file_location('mdflow_trace_kit', TOOLS / 'trace.py')  # not stdlib `trace`
    trace = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trace)
    if record_path.name != trace.MANUAL_FILES['MAN-04']:
        return [f'record must be named {trace.MANUAL_FILES["MAN-04"]}']
    return trace.attest(ROOT, 'MAN-04', record_path.parent, commit)


def run(args, provision=provision_engine) -> int:
    os_name = OS_NAMES.get(platform.system())
    if not os_name:
        raise KitError(f'unsupported OS: {platform.system()}')
    work = args.work or Path.home() / 'mdflow-man04' / f'{os_name}-{args.channel}'
    work.mkdir(parents=True, exist_ok=True)
    if args.assets:
        folder = args.assets
    else:
        folder = work / 'downloads'
        command = ['gh', 'release', 'download', TAG, '--dir', str(folder), '--clobber']
        command += ['--repo', args.repo] if args.repo else []
        subprocess.run(command, check=True, timeout=600, cwd=ROOT)
    hashes = verify_assets(folder)
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('id'), manifest.get('version')) != (PLUGIN_ID, TAG):
        raise KitError(f'manifest.json is {manifest.get("id")!r} {manifest.get("version")!r}, '
                       f'expected {PLUGIN_ID} {TAG}')
    vault = work / 'vault'
    plugin = install_plugin(folder, vault)
    engine = provision(folder, work, args.python)
    record_path = args.record or Path.cwd() / 'release_rehearsal.yml'
    record = release_evidence.read_record(record_path if record_path.is_file() else TEMPLATE)
    update_record(record, os_name=os_name, channel=args.channel, hashes=hashes, engine=engine)
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str) + '\n', encoding='utf-8')
    print(f'SHA256SUMS verified for {len(ASSETS)} assets; plugin installed in {plugin}')
    print(f'Engine {engine["engine"]} / Core {engine["core"]} / Python {engine["python"]}: pip check, selftest, version OK')
    print(f'Settings -> enginePython: {engine["enginePython"]}')
    if args.channel == 'minimum':
        print(f'Use Obsidian {manifest["minAppVersion"]} (manifest minAppVersion) and record the version you ran.')
    print(f'Open {vault} in Obsidian {args.channel} ({os_name}); logs: {engine["logs"]}')
    print(f'Record updated: {record_path}')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='kind', required=True)
    step = commands.add_parser('run', help='download, verify, install and probe for this OS/channel')
    step.add_argument('--channel', choices=('minimum', 'current'), required=True)
    step.add_argument('--repo', help='OWNER/REPO for gh (default: the repo of this checkout)')
    step.add_argument('--assets', type=Path, help='use an already downloaded asset folder instead of gh')
    step.add_argument('--work', type=Path,
                      help='folder for vault/venv/logs (default: ~/mdflow-man04/<os>-<channel>)')
    step.add_argument('--record', type=Path,
                      help='release_rehearsal.yml to create/update (default: ./release_rehearsal.yml)')
    step.add_argument('--python', default=sys.executable, help='interpreter used to create the venv')
    check = commands.add_parser('validate', help='run trace.py attest MAN-04 on a completed record')
    check.add_argument('record', type=Path)
    check.add_argument('--commit', required=True, help='candidate commit SHA the record must bind')
    args = parser.parse_args(argv)
    try:
        if args.kind == 'run':
            return run(args)
        problems = validate(args.record, args.commit)
        print('\n'.join(problems) if problems else 'Schema valid; claims require independent verification.')
        return int(bool(problems))
    except (KitError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
        print(f'man04_kit: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
