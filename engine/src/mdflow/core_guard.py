"""Reject the upstream distribution sharing the fork's import namespace."""
from importlib import metadata
from contextlib import contextmanager, redirect_stdout, redirect_stderr
import os
import sys
import threading

_OUTPUT_LOCK = threading.RLock()


@contextmanager
def quiet_output():
    """Keep third-party Python/native diagnostics outside the JSON protocol.

    Native libraries (notably ONNX device discovery during Core import) write
    directly to file descriptors, bypassing Python's redirect_stderr. Restore
    both descriptors even when Core raises or a cancellation interrupts it.
    """
    with _OUTPUT_LOCK, open(os.devnull, 'w', encoding='utf-8') as sink:
        saved = []
        try:
            for stream in (sys.stdout, sys.stderr):
                stream.flush()
            for fd in (1, 2):
                saved.append((fd, os.dup(fd)))
                os.dup2(sink.fileno(), fd)
            with redirect_stdout(sink), redirect_stderr(sink):
                yield
        finally:
            sink.flush()
            for fd, original in reversed(saved):
                os.dup2(original, fd)
                os.close(original)


class CoreConflict(RuntimeError):
    """A broken environment, independent of any document's contents."""


def check() -> None:
    # Core owns both co-install and loaded-code/metadata mismatch detection.
    # Missing Core remains the version gate's responsibility (including `version`).
    try:
        metadata.version('markitdown-gc')
    except metadata.PackageNotFoundError:
        return
    with quiet_output():
        from markitdown._installation import installation_conflict
        message = installation_conflict()
    if message:
        raise CoreConflict('E_CORE_CONFLICT: ' + message)
