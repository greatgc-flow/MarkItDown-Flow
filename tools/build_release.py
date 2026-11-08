"""Assemble, hash and verify one release candidate; never publish or rebuild in verify mode."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile
from build_engine import build

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ('main.js', 'manifest.json', 'styles.css', 'engine.zip', 'engine.lock')
SUBJECTS = (*ASSETS, 'SHA256SUMS')
COMMANDS = ('convert-file', 'convert-folder', 'convert-url', 'view-conversion-history',
            'open-log-folder', 'run-image-pipeline-selftest')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def versions(tag):
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8-sig'))
    shell = json.loads((ROOT / 'shell/package.json').read_text(encoding='utf-8-sig'))
    engine = tomllib.loads((ROOT / 'engine/pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    prior = json.loads((ROOT / 'versions.json').read_text(encoding='utf-8'))
    if not tag or tag.startswith('v') or not (tag == manifest['version'] == shell['version'] == engine == '2.0.0'):
        raise ValueError('tag must equal manifest/package/engine version 2.0.0 (no v prefix)')
    if manifest['id'] != 'markitdown-flow' or manifest['isDesktopOnly'] is not True:
        raise ValueError('wrong plugin identity/desktop flag')
    if prior.get(tag) != manifest['minAppVersion']:
        raise ValueError('versions.json must match the tested manifest minimum')
    description = manifest['description']
    if len(description) > 250 or not description.endswith('.') or re.search('azure|audio|youtube|fallback|—', description, re.I):
        raise ValueError('manifest description violates release checklist')

def verify(folder):
    folder = folder.resolve(strict=True)
    sums = {}
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        h, name = line.split('  ')
        if name not in ASSETS or name in sums or not re.fullmatch('[0-9a-f]{64}', h):
            raise ValueError('invalid checksum inventory')
        sums[name] = h
    if set(sums) != set(ASSETS):
        raise ValueError('missing checksum subject')
    for name, expected in sums.items():
        path = folder / name
        if path.is_symlink() or sha(path) != expected:
            raise ValueError(f'changed candidate bytes: {name}')
    with zipfile.ZipFile(folder / 'engine.zip') as z:
        if z.read('engine.lock') != (folder / 'engine.lock').read_bytes():
            raise ValueError('separate lock differs from ZIP lock')
        if any(re.search(r'(^|/)(venv|\.venv|cache|__pycache__|\.peerhub|data\.json)(/|$)|\.pyc$', n) for n in z.namelist()):
            raise ValueError('forbidden content in engine ZIP')
    candidate = json.loads((folder / 'release-candidate.json').read_text())
    if candidate['lock_sha256'] != sha(folder / 'engine.lock'):
        raise ValueError('candidate lock digest differs')
    versions(candidate['tag'])
    main = (folder / 'main.js').read_text(encoding='utf-8')
    if not (folder / 'styles.css').stat().st_size:
        raise ValueError('production stylesheet is empty')
    for command in COMMANDS:
        if not re.search(r"['\"]" + re.escape(command) + r"['\"]", main) or f'markitdown-flow:{command}' in main:
            raise ValueError(f'missing or prefixed command alias: {command}')
    if re.search('SampleModal|SampleSettingTab|open-sample-modal|sample-modal-simple|Sample Plugin', main):
        raise ValueError('retired sample implementation in production bundle')
    for subject in SUBJECTS:
        if candidate['draft_release']['assets'][list(SUBJECTS).index(subject)] != {'name': subject, 'sha256': sha(folder / subject)}:
            raise ValueError('candidate inventory differs from frozen subjects')
    return candidate

def assemble(folder, tag, commit, repo):
    versions(tag)
    if not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise ValueError('supply actual source commit and owner/repository')
    folder = folder.resolve()
    if folder.exists() and any(folder.iterdir()):
        raise ValueError('candidate directory must be empty; build once')
    folder.mkdir(parents=True, exist_ok=True)
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    for command in ([npm, 'ci'], [npm, 'run', 'typecheck'], [npm, 'run', 'build']):
        subprocess.run(command, cwd=ROOT / 'shell', check=True)
    for name in ('main.js', 'styles.css'):
        source = next((p for p in (ROOT / 'shell/dist' / name, ROOT / 'shell' / name) if p.is_file()), None)
        if not source:
            raise ValueError(f'production shell build did not produce {name}')
        shutil.copyfile(source, folder / name)
    shutil.copyfile(ROOT / 'manifest.json', folder / 'manifest.json')
    # Wheel is built once. Nothing in later jobs invokes a build command.
    build(folder)
    # The wheel is inside engine.zip; standard release attachments are allowlisted.
    # Retain the original wheel for audit. Publication allowlists attachments.
    (folder / 'SHA256SUMS').write_text(''.join(f'{sha(folder / name)}  {name}\n' for name in ASSETS), encoding='utf-8')
    candidate = {'repo': repo, 'commit': commit, 'tag': tag,
                 'signer_workflow': f'{repo}/.github/workflows/release.yml',
                 'lock_sha256': sha(folder / 'engine.lock'), 'required_jobs': [], 'shell_jobs': [],
                 'acceptance': {'gates': [], 'score': 'UNVERIFIED'},
                 'blockers': ['required CI, named reviews, desktop rehearsal and provenance verification pending'],
                 'rollback': {'tag': '1.0.8', 'artifacts_retained': False},
                 'draft_release': {'assets': [{'name': n, 'sha256': sha(folder / n)} for n in SUBJECTS]}}
    (folder / 'release-candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    verify(folder)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / 'build/candidate')
    p.add_argument('--tag', default=os.environ.get('GITHUB_REF_NAME', ''))
    p.add_argument('--commit', default=os.environ.get('GITHUB_SHA', ''))
    p.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', ''))
    p.add_argument('--verify', action='store_true')
    a = p.parse_args()
    if a.verify:
        verify(a.output)
    else:
        assemble(a.output, a.tag, a.commit, a.repo)

if __name__ == '__main__':
    main()
