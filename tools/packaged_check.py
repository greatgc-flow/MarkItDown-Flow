"""Exercise a candidate lock in a fresh, fixed-location environment outside sources."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from build_release import verify

def install(bundle, venv, current=False):
    verify(bundle)
    root = bundle.parent / ('engine extract 한글 ' + venv.name)
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(bundle / 'engine.zip') as z:
        for name in z.namelist():
            p = root / name
            if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
                raise ValueError('unsafe ZIP member')
        z.extractall(root)
    if current:
        python = Path(sys.executable)
    else:
        if venv.exists():
            raise ValueError('fresh venv required')
        subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
        python = venv.resolve() / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:',
                    '--index-url', 'https://pypi.org/simple', '--find-links', './wheels', '-r', './engine.lock'],
                   cwd=root, check=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
    return python

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('install', 'install-current', 'smoke'))
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--venv', type=Path, default=Path('build/current-env'))
    a = p.parse_args()
    python = install(a.bundle.resolve(), a.venv.resolve(), a.command == 'install-current')
    with tempfile.TemporaryDirectory(prefix='mdflow smoke 한글 ') as temp:
        cwd = Path(temp)
        subprocess.run([str(python), '-I', '-m', 'mdflow', 'version'], cwd=cwd, check=True)
        if a.command == 'smoke':
            source = cwd / 'local sample.txt'
            source.write_text('Local classification smoke.\n' * 40, encoding='utf-8')
            subprocess.run([str(python), '-I', '-m', 'mdflow', 'classify', str(source)], cwd=cwd, check=True)

if __name__ == '__main__':
    main()
