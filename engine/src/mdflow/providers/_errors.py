"""Provider configuration error and failed-unit result, kept apart so submodules can import them without a cycle."""

from __future__ import annotations

import time

from ..contracts import UnitResult


class ProviderConfigError(Exception):
    """Startup configuration error (exit 1); the message never carries secrets or absolute paths."""

    code = "E_PROVIDER_CONFIG"


def failed(code: str, message: str, started: float, exit_status: int | None = None) -> UnitResult:
    return {
        "status": "failed", "text": None, "duration_ms": int((time.monotonic() - started) * 1000),
        "error": {"code": code, "message": message, "exit": exit_status},
    }
