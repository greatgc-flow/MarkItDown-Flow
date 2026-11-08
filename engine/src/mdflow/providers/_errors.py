"""Provider configuration error, kept apart so submodules can import it without a cycle."""

from __future__ import annotations


class ProviderConfigError(Exception):
    """Startup configuration error (exit 1); the message never carries secrets or absolute paths."""

    code = "E_PROVIDER_CONFIG"
