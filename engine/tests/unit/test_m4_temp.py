"""Owned temporary rasters: live leases survive; abandoned owned trees are removed."""
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


@pytest.mark.req('REQ-GEN-09', 'REQ-RND-05')
@pytest.mark.cov('S0', 'FM7')
def test_T_GEN_93_m4_temp_recovery_preserves_live_and_unowned_trees(tmp_path):
    from mdflow import runtime_temp
    unrelated = tmp_path / 'mdflow-unowned'
    unrelated.mkdir()
    (unrelated / 'sentinel').write_bytes(b'keep')
    with runtime_temp.run_directory(tmp_path) as live:
        payload = live / 'raster.png'
        payload.write_bytes(b'private raster')
        assert runtime_temp.cleanup_stale(tmp_path) == 0
        assert payload.read_bytes() == b'private raster'
        assert (unrelated / 'sentinel').read_bytes() == b'keep'
    assert not live.exists()
    assert (unrelated / 'sentinel').read_bytes() == b'keep'


@pytest.mark.req('REQ-GEN-09', 'REQ-RND-05')
@pytest.mark.cov('S0', 'FM7')
@pytest.mark.parametrize('death', ['exit', 'kill'])
def test_T_GEN_94_m4_native_death_releases_temp_lease_and_next_run_recovers(
        tmp_path, cli_command, death):
    from mdflow import runtime_temp
    # Real process exit without context-manager unwinding, not a simulated stale flag.
    code = """
import os, sys, time
from pathlib import Path
from mdflow import runtime_temp
with runtime_temp.run_directory(Path(__import__('sys').argv[1])) as directory:
    (directory / 'raster.png').write_bytes(b'private raster')
    if sys.argv[2] == 'kill':
        print(str(directory), flush=True)
        while True:
            time.sleep(.1)
    os._exit(23)
"""
    flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    child = subprocess.Popen(cli_command(code=code) + [str(tmp_path), death],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
    try:
        if death == 'kill':
            # Read readiness from the child holding the OS lock, not a guessed delay.
            assert child.stdout.readline().strip()
            assert runtime_temp.cleanup_stale(tmp_path) == 0
            child.kill()
        stdout, stderr = child.communicate(timeout=30)
        assert child.returncode == 23 if death == 'exit' else child.returncode != 0
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
    abandoned, = [p for p in tmp_path.iterdir() if p.name.startswith('mdflow-')]
    assert (abandoned / 'raster.png').read_bytes() == b'private raster'
    with runtime_temp.run_directory(tmp_path) as fresh:
        assert not abandoned.exists()
        assert fresh.is_dir()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.req('REQ-GEN-09', 'REQ-RND-05')
@pytest.mark.cov('S0', 'FM9')
def test_T_GEN_95_m4_temp_recovery_never_follows_links_or_bad_owner_records(tmp_path):
    from mdflow import runtime_temp
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'sentinel'
    sentinel.write_bytes(b'keep')
    malformed = tmp_path / 'mdflow-malformed'
    malformed.mkdir()
    (malformed / runtime_temp.OWNER_FILE).write_text('{}', encoding='utf-8')
    link = tmp_path / 'mdflow-link'
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        # Real Windows reparse detection is also covered by the injected attribute control below.
        from types import SimpleNamespace
        original = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == malformed:
                return SimpleNamespace(st_mode=0o40700, st_file_attributes=0x400)
            return original(path, *args, **kwargs)
        from unittest.mock import patch
        with patch.object(Path, 'lstat', lstat):
            assert runtime_temp.cleanup_stale(tmp_path) == 0
    assert runtime_temp.cleanup_stale(tmp_path) == 0
    assert malformed.is_dir() and sentinel.read_bytes() == b'keep'
