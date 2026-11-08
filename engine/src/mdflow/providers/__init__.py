"""Providers (SPEC 8).

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

import math
import os
import urllib.parse
from typing import Mapping, Sequence

from ._errors import ProviderConfigError

NAMES = ("none", "openai-compatible", "command")
DEFAULT_TIMEOUT_S = 120.0

__all__ = ["NAMES", "ProviderConfigError", "build_provider"]


def _timeout(env: Mapping[str, str]) -> float:
    raw = env.get("MDFLOW_TIMEOUT_S")
    if raw is None or raw == "":
        return DEFAULT_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError:
        raise ProviderConfigError("MDFLOW_TIMEOUT_S must be a positive number") from None
    if not math.isfinite(value) or value <= 0:
        raise ProviderConfigError("MDFLOW_TIMEOUT_S must be a positive number")
    return value


def _proxy(env: Mapping[str, str]) -> str | None:
    raw = (env.get("MDFLOW_PROXY") or "").strip()
    if not raw:
        return None
    try:
        parts = urllib.parse.urlsplit(raw)
        parts.port  # noqa: B018 - validates the port
    except ValueError:
        raise ProviderConfigError("MDFLOW_PROXY is not a valid proxy URL") from None
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname or '@' in parts.netloc:
        raise ProviderConfigError("MDFLOW_PROXY is not a valid proxy URL")
    return raw


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
    settings: Mapping[str, str] = os.environ if env is None else env
    if name == "none":
        from .none import NoneProvider

        provider = NoneProvider()
        if cost_hint is not None:
            provider.meta['cost_hint'] = cost_hint
        return provider
    if name == "openai-compatible":
        from .openai_compat import DEFAULT_BASE_URL, OpenAICompatProvider

        api_key = settings.get("MDFLOW_API_KEY") or ""
        if not api_key:
            raise ProviderConfigError("MDFLOW_API_KEY is required for provider openai-compatible")
        if not model:
            raise ProviderConfigError("--model is required for provider openai-compatible")
        return OpenAICompatProvider(
            api_key=api_key, base_url=settings.get("MDFLOW_BASE_URL") or DEFAULT_BASE_URL, model=model,
            timeout_s=_timeout(settings), cost_hint=cost_hint, proxy=_proxy(settings))
    if name == "command":
        from .command import CommandProvider

        if not command:
            raise ProviderConfigError("--command is required for provider command")
        if not trust_command:
            raise ProviderConfigError("--trust-command is required for provider command")
        if not isinstance(command_egress, bool):
            raise ProviderConfigError("--command-egress true|false is required for provider command")
        if not model:
            raise ProviderConfigError("--model <label> is required for provider command")
        names = [item for item in command_env if item]
        if any("=" in item for item in names):
            raise ProviderConfigError("--command-env takes variable names, not assignments")
        return CommandProvider(
            command=command, egress=command_egress, env_names=names, model=model,
            timeout_s=_timeout(settings), cost_hint=cost_hint)
    raise ProviderConfigError(f"unknown provider (expected one of {', '.join(NAMES)})")
