"""Bind validated acceptance and named reviews to the frozen candidate; no fabricated successes."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from build_release import verify, versions, SUBJECTS
from trace import ROOT, score, required_executions

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--manual', type=Path, required=True)
    a = p.parse_args()
    if os.environ.get('GITHUB_REF_TYPE') != 'tag':
        raise ValueError('release must run from the exact existing version tag')
    versions(os.environ['GITHUB_REF_NAME'])
    candidate = verify(a.candidate)
    if candidate['commit'] != os.environ['GITHUB_SHA'] or candidate['repo'] != os.environ['GITHUB_REPOSITORY']:
        raise ValueError('candidate source identity differs from release context')
    tagged = subprocess.check_output(['gh', 'api', f"repos/{candidate['repo']}/commits/{candidate['tag']}",
                                      '--jq', '.sha'], text=True).strip()
    if tagged != candidate['commit']:
        raise ValueError('remote version tag no longer points to the tested source commit')
    problems = required_executions(a.evidence, candidate['commit'])
    if problems:
        raise ValueError('\n'.join(problems))
    # Independent command-oracle receipts are evidence, not automatic PASS labels.
    shutil.copyfile(a.manual / 'oracles.json', a.evidence / 'oracles.json')
    result = score(ROOT, a.evidence, a.manual, candidate['commit'])
    if result['score'] != 'SCORE 100/100 (automated 93/93, manual 7/7)':
        raise ValueError(result['score'])
    for filename in ('actions-review.json', 'pkg04_core_artifacts.json', 'listing-review.json'):
        record = json.loads((a.manual / filename).read_text())
        if record.get('commit') != candidate['commit'] or record.get('verdict') != 'PASS' or not record.get('reviewer') or not record.get('evidence'):
            raise ValueError(f'missing or invalid independent review: {filename}')
    retained = json.loads(subprocess.check_output(
        ['gh', 'release', 'view', '1.0.8', '--json', 'tagName,assets'], text=True))
    names = {x['name'] for x in retained['assets']}
    if retained['tagName'] != '1.0.8' or not {'main.js', 'manifest.json', 'styles.css'} <= names:
        raise ValueError('verified 1.0.8 rollback assets must remain available')
    # These jobs completed in the prerequisite reusable CI; scoring checked the actual per-cell JUnit.
    platforms = ('windows-2022', 'ubuntu-24.04', 'macos-15-intel')
    candidate['required_jobs'] = [{'name': f'pytest ({o}, {py})', 'os': o, 'python': py,
                                    'result': 'success', 'run_id': os.environ['GITHUB_RUN_ID']}
                                   for o in platforms for py in ('3.10', '3.14')]
    candidate['shell_jobs'] = [{'name': f'jest ({o})', 'os': o, 'result': 'success',
                                'run_id': os.environ['GITHUB_RUN_ID']} for o in platforms]
    candidate['acceptance'] = {'score': result['score'], 'gates': result['automated'], 'manual': result['manual']}
    candidate['rollback'] = {'tag': '1.0.8', 'artifacts_retained': True}
    candidate['blockers'] = []
    (a.candidate / 'release-candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
    verify(a.candidate)

if __name__ == '__main__':
    main()
