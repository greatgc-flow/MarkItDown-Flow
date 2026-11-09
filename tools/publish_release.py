"""Create a draft release from verified bytes and compare every downloaded attachment."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from build_release import SUBJECTS, sha, verify, versions
from trace import publication_problems

def gh(*args, **kwargs):
    return subprocess.run(['gh', *map(str, args)], check=True, **kwargs)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path, required=True)
    a = p.parse_args()
    folder = a.candidate.resolve()
    candidate = verify(folder)
    tag, repo, commit = candidate['tag'], candidate['repo'], candidate['commit']
    versions(os.environ['GITHUB_REF_NAME'])
    if candidate['blockers'] or publication_problems(candidate['acceptance']):
        raise ValueError('acceptance must pass before release creation')
    gh('--version')
    for name in SUBJECTS:
        gh('attestation', 'verify', folder / name, '--repo', repo, '--bundle', folder / (name + '.sigstore.json'),
           '--signer-workflow', candidate['signer_workflow'], '--source-digest', commit)
    # Release metadata is supplemental; attested subjects are never changed here.
    version = subprocess.check_output(['gh', '--version'], text=True).splitlines()[0]
    candidate['verifier'] = {'gh': version, 'source_digest': commit, 'signer_workflow': candidate['signer_workflow']}
    (folder / 'release-candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    notes = ('MarkItDown Flow 2.0.0\n\nMajor-version migration: install the engine externally in a new venv '
             'using the release wheel and BOOTSTRAP.md, then choose its interpreter. Audio/YouTube, Azure fallback '
             'routing and old wrapper settings are removed; review README disclosures before OCR. '
             'Keep 1.0.8 assets and the sanitized v1 settings snapshot for rollback. '
             'Never pass schema-2 settings to v1. Published assets are immutable.\n')
    with tempfile.TemporaryDirectory(prefix='mdflow-release-') as temp:
        work = Path(temp)
        body = work / 'notes.md'
        body.write_text(notes, encoding='utf-8')
        assets = [folder / name for name in SUBJECTS]
        assets += [folder / (name + '.sigstore.json') for name in SUBJECTS]
        assets.append(folder / 'release-candidate.json')
        # Existing releases/tags are never overwritten or retagged.
        gh('release', 'create', tag, *assets, '--repo', repo, '--verify-tag', '--target', commit,
           '--draft', '--title', 'MarkItDown Flow ' + tag, '--notes-file', body)
        remote = work / 'downloaded'
        remote.mkdir()
        gh('release', 'download', tag, '--repo', repo, '--dir', remote)
        for path in assets:
            if sha(path) != sha(remote / path.name):
                raise ValueError(f'remote release asset differs: {path.name}; draft remains unpublished')
    print('Draft release uploaded and digests compared. MAN-04 deferred: post-release (R35); failure requires REQ-PKG-20 rollback.')

if __name__ == '__main__':
    main()
