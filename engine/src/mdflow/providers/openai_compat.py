"""Provider ``openai-compatible`` (SPEC 8.2, 7.1 destination rules). RED-PHASE STUB.

POST ``<base_url>/chat/completions`` through ``urllib.request`` with an opener that has no
``HTTPRedirectHandler`` (3xx -> ``E_PROVIDER_HTTP``) and ``ProxyHandler({})`` unless a proxy is set.
Retries (HTTP 429/5xx only) back off with ``time.sleep(2)`` then ``time.sleep(8)`` -- always through the
``time`` module attribute so tests can observe the sleeps.
"""

from __future__ import annotations

from ..contracts import ProviderMeta


class OpenAICompatProvider:
    meta: ProviderMeta

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_s: float = 120.0,
                 cost_hint: str | None = None, proxy: str | None = None) -> None:
        raise NotImplementedError("Step 6 green: openai-compatible provider")

    def transcribe(self, unit, raster, prompt):
        raise NotImplementedError("Step 6 green: openai-compatible provider")
