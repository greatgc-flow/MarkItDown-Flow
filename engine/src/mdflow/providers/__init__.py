"""Providers (SPEC 8). RED-PHASE STUB.

``build_provider(name, *, model=None, env=None, cost_hint=None, command=None, command_egress=None,
command_env=(), trust_command=False) -> Provider``

* ``env`` is the only source of ``MDFLOW_API_KEY``, ``MDFLOW_BASE_URL``, ``MDFLOW_TIMEOUT_S`` and
  ``MDFLOW_PROXY`` (``None`` means ``os.environ``). There is deliberately no key parameter (REQ-SEC-01).
* Startup configuration errors raise ``ProviderConfigError`` (``code == "E_PROVIDER_CONFIG"``, exit 1 at
  startup); messages never contain secrets or absolute paths.
* Providers expose ``meta`` (``contracts.ProviderMeta``) and ``transcribe(unit, raster, prompt)`` which
  returns a ``contracts.UnitResult`` and never raises for provider-side failures.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from ..contracts import ProviderMeta, UnitResult

NAMES = ("none", "openai-compatible", "command")


class ProviderConfigError(Exception):
    code = "E_PROVIDER_CONFIG"


def build_provider(
    name: str,
    *,
    model: str | None = None,
    env: Mapping[str, str] | None = None,
    cost_hint: str | None = None,
    command: str | None = None,
    command_egress: bool | None = None,
    command_env: Sequence[str] = (),
    trust_command: bool = False,
):
    raise NotImplementedError("Step 6 green: provider factory")
