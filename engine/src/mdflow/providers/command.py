"""Provider ``command`` (SPEC 8.2).

``shlex.split(template, posix=True)``, placeholders ``{input}`` (temp raster path) and ``{mime}``
substituted argument-wise, ``subprocess.run(argv, shell=False, env=<allowlist + command_env>)`` looked up
as the ``subprocess.run`` module attribute. The child env is exactly ``ALLOWED_ENV`` plus the
``--command-env`` names that exist in the parent environment.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
import time
from typing import Sequence

from ..contracts import ProviderMeta, UnitResult
from ._errors import ProviderConfigError

ALLOWED_ENV = frozenset(
    {"PATH", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "HOME", "USERPROFILE", "TEMP", "TMP", "LANG", "LC_ALL"}
)
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_SUFFIXES = {"image/png": ".png", "image/jpeg": ".jpg"}


def canonical_destination(argv_template: Sequence[str]) -> str:
    return "command:" + json.dumps(list(argv_template), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _failed(code: str, message: str, started: float, exit_status: int | None = None) -> UnitResult:
    return {
        "status": "failed", "text": None, "duration_ms": int((time.monotonic() - started) * 1000),
        "error": {"code": code, "message": message, "exit": exit_status},
    }


class CommandProvider:
    meta: ProviderMeta

    def __init__(self, *, command: str, egress: bool, env_names=(), model: str, timeout_s: float = 120.0,
                 cost_hint: str | None = None) -> None:
        try:
            template = shlex.split(command, posix=True)
        except ValueError:
            raise ProviderConfigError("command template cannot be parsed") from None
        if not template:
            raise ProviderConfigError("command template is empty")
        self._template = template
        self._env_names = sorted(set(env_names))
        self._timeout_s = timeout_s
        self.meta = {
            "name": "command", "model": model, "egress": bool(egress), "cost_hint": cost_hint, "max_batch": 1,
            "retries": 0, "destination": canonical_destination(template),
            "command_env_names": list(self._env_names), "accepts": ["image/png", "image/jpeg"],
        }

    def __repr__(self) -> str:
        return f"CommandProvider(model={self.meta['model']!r}, egress={self.meta['egress']!r})"

    def _child_env(self) -> dict[str, str]:
        wanted = ALLOWED_ENV | set(self._env_names)
        return {name: value for name, value in os.environ.items() if name in wanted}

    def transcribe(self, unit, raster, prompt) -> UnitResult:
        started = time.monotonic()
        mime = unit.get("mime") or "image/png"
        raster_path = output_path = ""
        try:
            handle, raster_path = tempfile.mkstemp(prefix="mdflow-", suffix=_SUFFIXES.get(mime, ".bin"))
            with os.fdopen(handle, "wb") as raster_file:
                raster_file.write(raster)
            handle, output_path = tempfile.mkstemp(prefix="mdflow-out-", suffix=".txt")
            argv = [word.replace("{input}", raster_path).replace("{mime}", mime) for word in self._template]
            try:
                with os.fdopen(handle, "wb") as sink:
                    completed = subprocess.run(
                        argv, shell=False, env=self._child_env(), stdin=subprocess.DEVNULL, stdout=sink,
                        stderr=subprocess.DEVNULL, timeout=self._timeout_s, check=False)
            except subprocess.TimeoutExpired:
                return _failed("E_PROVIDER_TIMEOUT", "command exceeded the time limit", started)
            except OSError as exc:
                return _failed("E_PROVIDER_CONFIG", f"command could not be started ({type(exc).__name__})", started)
            if completed.returncode != 0:
                return _failed("E_PROVIDER_HTTP", f"command exited with status {completed.returncode}", started,
                               completed.returncode)
            with open(output_path, "rb") as produced:
                payload = produced.read(MAX_OUTPUT_BYTES + 1)
            if len(payload) > MAX_OUTPUT_BYTES:
                return _failed("E_PROVIDER_OUTPUT", "command output exceeds 4 MiB", started)
            text = payload.decode("utf-8", errors="replace")
            if not text.strip():
                return _failed("E_PROVIDER_OUTPUT", "command produced no output", started)
            return {"status": "ok", "text": text, "error": None, "duration_ms": int((time.monotonic() - started) * 1000)}
        except OSError as exc:
            return _failed("E_PROVIDER_CONFIG", f"command input could not be prepared ({type(exc).__name__})", started)
        finally:
            for leftover in (raster_path, output_path):
                if leftover:
                    try:
                        os.unlink(leftover)
                    except OSError:
                        pass
