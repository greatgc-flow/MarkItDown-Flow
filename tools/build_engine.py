"""Build one pure mdflow wheel and the allowlisted engine ZIP from a frozen lock."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WHEEL = 'mdflow-2.0.0-py3-none-any.whl'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def zip_bytes(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2020, 2, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)

def build(output: Path, *, wheel_only=False):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if metadata.version('hatchling') != '1.33.0':
        raise ValueError('install the separately pinned requirements-build.txt first')
    wheel_dir = output / 'wheels'
    wheel_dir.mkdir(exist_ok=True)
    if (wheel_dir / WHEEL).exists():
        raise ValueError('refusing to replace an existing candidate wheel; choose an empty output directory')
    env = dict(os.environ, SOURCE_DATE_EPOCH='1580601600', PYTHONHASHSEED='0')
    subprocess.run([sys.executable, '-m', 'hatchling', 'build', '-t', 'wheel', '-d', str(wheel_dir)],
                   cwd=ROOT / 'engine', env=env, check=True)
    wheel = wheel_dir / WHEEL
    with zipfile.ZipFile(wheel) as archive:
        if any(n.endswith(('.so', '.pyd', '.dll', '.dylib', '.pyc')) for n in archive.namelist()):
            raise ValueError('mdflow wheel must be pure Python')
        wm = archive.read('mdflow-2.0.0.dist-info/WHEEL').decode()
        if 'Root-Is-Purelib: true' not in wm or 'Tag: py3-none-any' not in wm:
            raise ValueError('unexpected wheel metadata')
    if wheel_only:
        return wheel
    lock = (ROOT / 'engine/engine.lock').read_text(encoding='utf-8-sig')
    inventory = json.loads((ROOT / 'engine/lock-inventory.json').read_text(encoding='utf-8'))
    if inventory.get('unresolved'):
        raise ValueError(f"release lock incomplete: {inventory['unresolved']}")
    requirement = f'./wheels/{WHEEL} --hash=sha256:{digest(wheel)}'
    old = re.search(r'^\./wheels/[^\n]+', lock, re.M)
    if old and old[0] != requirement:
        raise ValueError('frozen engine wheel hash differs; review and refreeze the candidate lock')
    if not old:
        lock = requirement + '\n' + lock
    entries = {f'wheels/{WHEEL}': wheel.read_bytes(), 'engine.lock': lock.encode(),
               'BOOTSTRAP.md': (ROOT / 'engine/BOOTSTRAP.md').read_bytes(),
               'LICENSE': (ROOT / 'LICENSE').read_bytes(),
               'package-inventory.json': json.dumps(inventory, indent=2).encode()}
    notices = ['Package licenses are recorded verbatim from package metadata.']
    for package in inventory['packages']:
        notices.append(f"\n{package['name']}=={package['version']}\n{package['license']}")
    entries['NOTICE.txt'] = '\n'.join(notices).encode()
    (output / 'engine.lock').write_bytes(entries['engine.lock'])
    zip_bytes(output / 'engine.zip', entries)
    return wheel

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'build/engine')
    p.add_argument('--wheel-only', action='store_true')
    a = p.parse_args()
    print(build(a.output, wheel_only=a.wheel_only))

if __name__ == '__main__':
    main()
