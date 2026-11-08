"""Provider ``command`` (SPEC 8.2). RED-PHASE STUB.

``shlex.split(template, posix=True)``, placeholders ``{input}`` (temp raster path) and ``{mime}``
substituted argument-wise, ``subprocess.run(argv, shell=False, env=<allowlist + command_env>)`` looked up
as the ``subprocess.run`` module attribute. The child env is exactly ``ALLOWED_ENV`` plus the
``--command-env`` names that exist in the parent environment.
"""

from __future__ import annotations

from ..contracts import ProviderMeta

ALLOWED_ENV = frozenset(
    {"PATH", "SYSTEMROOT", "SYSTEMDRIVE", "COMSPEC", "HOME", "USERPROFILE", "TEMP", "TMP", "LANG", "LC_ALL"}
)


class CommandProvider:
    meta: ProviderMeta

    def __init__(self, *, command: str, egress: bool, env_names=(), model: str, timeout_s: float = 120.0) -> None:
        raise NotImplementedError("Step 6 green: command provider")

    def transcribe(self, unit, raster, prompt):
        raise NotImplementedError("Step 6 green: command provider")
