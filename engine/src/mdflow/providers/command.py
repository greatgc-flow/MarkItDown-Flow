"""Provider ``command`` (SPEC 8.2).

``shlex.split(template, posix=True)``, placeholders ``{input}`` (temp raster path) and ``{mime}``
substituted argument-wise, ``subprocess.Popen(argv, shell=False, env=<allowlist + command_env>)`` with
bounded pipe capture. The child env is exactly ``ALLOWED_ENV`` plus the
``--command-env`` names that exist in the parent environment.
"""

from __future__ import annotations

import json
from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import time
from typing import Sequence

from ..contracts import ProviderMeta, UnitResult
from ..executable import resolve_executable
from ..report import home_relative
from ._errors import ProviderConfigError

ALLOWED_ENV = frozenset(
    {"PATH", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "HOME", "USERPROFILE", "TEMP", "TMP", "LANG", "LC_ALL"}
)
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_SUFFIXES = {"image/png": ".png", "image/jpeg": ".jpg"}


def _read_ready(pipe) -> bytes | None:
    """One unbuffered read only when ready; None means poll again, b'' is EOF.

    There is one owner and no reader thread/locked buffered close. Windows
    anonymous pipes are not selectable; PeekNamedPipe also supports Python 3.10.
    Microsoft Learn: PeekNamedPipe (Win32 anonymous pipes).
    """
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        peek = kernel.PeekNamedPipe
        peek.argtypes = (wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                         wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID)
        peek.restype = wintypes.BOOL
        available = wintypes.DWORD()
        if not peek(msvcrt.get_osfhandle(pipe.fileno()), None, 0, None, ctypes.byref(available), None):
            error = ctypes.get_last_error()
            if error == 109:  # ERROR_BROKEN_PIPE: every writer closed
                return b''
            raise ctypes.WinError(error)
        return os.read(pipe.fileno(), min(65536, available.value)) if available.value else None
    import select
    return os.read(pipe.fileno(), 65536) if select.select([pipe], [], [], 0)[0] else None


def canonical_destination(argv_template: Sequence[str]) -> str:
    return "command:" + json.dumps([home_relative(word) for word in argv_template],
                                  sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _failed(code: str, message: str, started: float, exit_status: int | None = None) -> UnitResult:
    return {
        "status": "failed", "text": None, "duration_ms": int((time.monotonic() - started) * 1000),
        "error": {"code": code, "message": message, "exit": exit_status},
    }


class CommandProvider:
    meta: ProviderMeta
    DEFAULT_META = dict(name='command', model='', egress=True, cost_hint=None, max_batch=1,
                        retries=0, destination=None, command_env_names=[], accepts=['image/png', 'image/jpeg'])

    def __init__(self, *, command: str, egress: bool, env_names=(), model: str, timeout_s: float = 120.0,
                 cost_hint: str | None = None) -> None:
        try:
            template = shlex.split(command, posix=True)
        except ValueError:
            raise ProviderConfigError("command template cannot be parsed") from None
        if not template:
            raise ProviderConfigError("command template is empty")
        if not os.path.dirname(template[0]):
            # Pin the vouched-for program; destination shortens only its home prefix, retaining program identity
            # in the plan hash/cache fingerprint. Unresolved names are refused in _capture (never a cwd lookup).
            template[0] = resolve_executable(template[0], os.environ.get("PATH", "")) or template[0]
        self._template = template
        self._env_names = sorted(set(env_names))
        self._timeout_s = timeout_s
        from copy import deepcopy
        self.meta = dict(deepcopy(self.DEFAULT_META), model=model, egress=bool(egress), cost_hint=cost_hint,
                         destination=canonical_destination(template), command_env_names=list(self._env_names))

    def __repr__(self) -> str:
        return f"CommandProvider(model={self.meta['model']!r}, egress={self.meta['egress']!r})"

    def _child_env(self) -> dict[str, str]:
        wanted = ALLOWED_ENV | set(self._env_names)
        return {name: value for name, value in os.environ.items() if name in wanted}

    def transcribe(self, unit, raster, prompt) -> UnitResult:
        started = time.monotonic()
        mime = unit.get("mime") or "image/png"
        parent = Path(unit['_raster_path']).parent if unit.get('_raster_path') else None
        try:
            with tempfile.TemporaryDirectory(prefix='mdflow-command-', dir=parent) as work:
                raster_path = Path(work) / ('input' + _SUFFIXES.get(mime, '.bin'))
                # This is the verified in-memory payload, never a second read of mutable source data.
                with open(raster_path, 'xb') as stream:
                    stream.write(raster)
                argv = [word.replace('{input}', str(raster_path)).replace('{mime}', mime) for word in self._template]
                return self._capture(argv, started)
        except OSError as exc:
            return _failed('E_PROVIDER_CONFIG', f'command input could not be prepared ({type(exc).__name__})', started)

    def _capture(self, argv, started) -> UnitResult:
        child = None
        deadline = started + self._timeout_s
        if not os.path.dirname(argv[0]):
            return _failed('E_PROVIDER_CONFIG', 'command program was not found on PATH', started)
        try:
            child = subprocess.Popen(argv, shell=False, env=self._child_env(), stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
            payload = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return _failed('E_PROVIDER_TIMEOUT', 'command exceeded the time limit', started)
                chunk = _read_ready(child.stdout)
                if chunk is None:
                    time.sleep(min(.01, remaining))
                    continue
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > MAX_OUTPUT_BYTES:
                    return _failed('E_PROVIDER_OUTPUT', 'command output exceeds 4 MiB', started)
            try:
                code = child.wait(timeout=max(.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                return _failed('E_PROVIDER_TIMEOUT', 'command exceeded the time limit', started)
            if code != 0:
                return _failed('E_PROVIDER_HTTP', f'command exited with status {code}', started, code)
            text = payload.decode('utf-8', errors='replace')
            if not text.strip():
                return _failed('E_PROVIDER_OUTPUT', 'command produced no output', started)
            return dict(status='ok', text=text, error=None, duration_ms=int((time.monotonic() - started) * 1000))
        except OSError as exc:
            return _failed('E_PROVIDER_CONFIG', f'command could not be started ({type(exc).__name__})', started)
        finally:
            if child is not None:
                if child.poll() is None:
                    child.kill()
                child.wait()
                child.stdout.close()
