"""The complete collection is produced independently of execution selectors."""
import json
import os
import subprocess

import pytest


@pytest.mark.req('REQ-PKG-10', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_T_META_96_m4_restricted_collection_cannot_define_the_complete_inventory(
        trace_module, repo_root, tmp_path, monkeypatch):
    # Actual pytest collection of one known parameter. Its independent companion
    # must still contain every class, not the restricted caller's item list.
    filename = 'junit-restricted.xml'
    target = next(row['nodeid'] for row in trace_module.discover_tests(repo_root) if row['tid'] == 'T-GEN-85')
    env = dict(os.environ, GITHUB_SHA='a' * 40, PYTEST_ADDOPTS='-k K01')
    done = subprocess.run([__import__('sys').executable, '-B', '-I', '-m', 'pytest',
        target + '[K01]', '--collect-only', '-q', '-p', 'no:cacheprovider',
        '--junitxml=' + str(tmp_path / filename)], cwd=repo_root, env=env,
        capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert done.returncode == 0, done.stdout + done.stderr
    registry = json.loads(trace_module.execution_registry_path(tmp_path, filename).read_text())
    assert len(registry['tests']) == 1
    complete = json.loads(trace_module.collection_path(tmp_path, filename).read_text())
    cases = [row['nodeid'] for row in complete['tests'] if row['tid'] == 'T-GEN-85']
    assert len(cases) == 20 and any(node.endswith('[K09]') for node in cases)
    assert complete['commit'] == 'a' * 40
    refused = subprocess.run([__import__('sys').executable, '-B', '-I', '-m', 'pytest',
        target + '[K01]', '--collect-only', '-q', '-p', 'no:cacheprovider',
        '--mdflow-collection-output=' + str(tmp_path / 'not-canonical.json')],
        cwd=repo_root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert refused.returncode != 0 and 'requires the full engine/tests root' in refused.stderr
    assert not (tmp_path / 'not-canonical.json').exists()
    release = (repo_root / '.github/workflows/release.yml').read_text(encoding='utf-8')
    assert 'build/trace/registry-release-*.json' in release
    assert 'build/trace/collection-release-*.json' in release
