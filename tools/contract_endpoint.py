"""Run newest-Core contract, visibly reusing the successful identical minimum endpoint."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--suite', required=True)
    p.add_argument('--pytest', choices=('pytest',), default='pytest')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    version = importlib.metadata.version('markitdown-gc')
    print('importlib.metadata markitdown-gc:', version)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    if version == '0.3.7':
        # contract-max depends on contract-min's success, so this is an identical endpoint.
        a.output.with_suffix('.json').write_text(json.dumps(
            {'version': version, 'deduplicated_with': 'contract-min', 'reason': 'same exact Core distribution/version'}) + '\n')
        print('Newest public Core equals 0.3.7; contract-min already tested this endpoint.')
        return 0
    return subprocess.call([sys.executable, '-I', '-m', a.pytest, a.suite, '-q', '--junitxml=' + str(a.output)])

if __name__ == '__main__':
    raise SystemExit(main())
