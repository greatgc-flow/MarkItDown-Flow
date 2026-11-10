"""Install the verified release wheel under its declared dependency policy, outside sources."""
from __future__ import annotations
import argparse
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from build_release import verify, WHEEL

def install(bundle, venv, current=False):
    verify(bundle)
    root = bundle.parent / ('engine install 한글 ' + venv.name)
    root.mkdir(parents=True, exist_ok=True)
    if current:
        python = Path(sys.executable)
    else:
        if venv.exists():
            raise ValueError('fresh venv required')
        subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True)
        python = venv.resolve() / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    report = bundle.parent / 'trace' / f'install-{sys.platform}-py{sys.version_info.major}.{sys.version_info.minor}-{venv.name}.json'
    report.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '--only-binary=:all:',
                    '--index-url', 'https://pypi.org/simple', '--report', str(report),
                    str(bundle / WHEEL), 'markitdown-gc>=0.3.8,<0.4'],
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
        subprocess.run([str(python), '-I', '-m', 'mdflow', 'selftest'], cwd=cwd, check=True)
        if a.command == 'smoke':
            source = cwd / 'local sample.txt'
            source.write_text('Local classification smoke.\n' * 40, encoding='utf-8')
            subprocess.run([str(python), '-I', '-m', 'mdflow', 'classify', str(source)], cwd=cwd, check=True)
            target = os.environ.get('MDFLOW_CI_TARGET')
            if target:
                receipt = a.bundle.resolve().parent / 'trace' / f'smoke-{target}-py{sys.version_info.major}.{sys.version_info.minor}.json'
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(json.dumps(dict(commit=os.environ.get('GITHUB_SHA'), exit=0)), encoding='utf-8')

if __name__ == '__main__':
    main()
