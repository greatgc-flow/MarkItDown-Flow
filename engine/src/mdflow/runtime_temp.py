"""Private run directories with OS-released leases for recovery after native death.

Only marked mdflow directories of the current user are recovered. An unmarked
legacy directory is left alone; a name prefix is never deletion authority.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

OWNER_FILE = '.mdflow-owner-v1'


def _plain(path: Path, *, directory: bool) -> bool:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        return False
    if hasattr(os, 'getuid') and info.st_uid != os.getuid():
        return False
    return stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)


def _lock(stream) -> None:
    stream.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def cleanup_stale(root: Path | None = None) -> int:
    """Remove abandoned, recognized owned trees, never live or linked directories.

    Failures leave the directory for a later start. Cleanup does not turn an
    otherwise valid conversion into an error, nor inspect arbitrary temp files.
    """
    root = Path(root if root is not None else tempfile.gettempdir()).resolve()
    removed = 0
    try:
        candidates = list(root.glob('mdflow-*'))
    except OSError:
        return 0
    for directory in candidates:
        try:
            marker = directory / OWNER_FILE
            if not _plain(directory, directory=True) or not _plain(marker, directory=False):
                continue
            if directory.resolve().parent != root:
                continue
            # Locks are released by the OS even when finally/__exit__ never run.
            with marker.open('r+b', buffering=0) as lease:
                _lock(lease)
                raw = lease.read(4097)
                if len(raw) > 4096:
                    continue
                owner = json.loads(raw)
                if owner != {'v': 1, 'directory': directory.name}:
                    continue
            # Legitimate runs never reopen an existing lease/name. Closing the
            # lease first permits Windows to remove its file and directory.
            if _plain(directory, directory=True) and directory.resolve().parent == root:
                shutil.rmtree(directory)
                removed += 1
        except (OSError, ValueError, TypeError):
            continue
    return removed


@contextmanager
def run_directory(root: Path | None = None):
    """Hold a non-inheritable lease until normal/handled cancellation cleanup."""
    root = Path(root if root is not None else tempfile.gettempdir()).resolve()
    cleanup_stale(root)
    with tempfile.TemporaryDirectory(prefix='mdflow-', dir=root) as name:
        directory = Path(name)
        marker = directory / OWNER_FILE
        # Write a byte before locking: Windows range locks require a real byte.
        descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        with os.fdopen(descriptor, 'r+b', buffering=0) as lease:
            lease.write(b' ')
            _lock(lease)
            lease.seek(0)
            lease.write(json.dumps({'v': 1, 'directory': directory.name}).encode('utf-8'))
            lease.truncate()
            yield directory
