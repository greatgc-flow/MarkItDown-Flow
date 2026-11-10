"""Provider ``openai-compatible`` (SPEC 8.2, 7.1 destination rules).

POST ``<base_url>/chat/completions`` through ``urllib.request`` with an opener that has no
``HTTPRedirectHandler`` (3xx -> ``E_PROVIDER_HTTP``) and ``ProxyHandler({})`` unless a proxy is set.
Retries (HTTP 429/5xx only) back off with ``time.sleep(2)`` then ``time.sleep(8)`` -- always through the
``time`` module attribute so tests can observe the sleeps.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

from ..contracts import ProviderMeta, UnitResult
from ._errors import ProviderConfigError, failed as _failed

DEFAULT_BASE_URL = "https://api.openai.com/v1"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
BACKOFF_SECONDS = (2, 8)
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_DEFAULT_PORTS = {"http": 80, "https": 443}
_READ_CHUNK = 65536


def canonical_destination(base_url: str) -> str:
    """Return the canonical chat-completions endpoint (7.1) or raise ProviderConfigError."""
    invalid = ProviderConfigError("MDFLOW_BASE_URL is not a valid endpoint (https URL without credentials, query or fragment)")
    text = base_url.strip()
    if not text or any(ord(char) < 33 or ord(char) == 127 for char in text):
        raise invalid
    try:
        parts = urllib.parse.urlsplit(text)
        port = parts.port
    except ValueError:
        raise invalid from None
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if scheme not in _DEFAULT_PORTS or not host or "@" in parts.netloc or parts.query or parts.fragment:
        raise invalid
    if "?" in text or "#" in text:
        raise invalid
    if scheme == "http" and host not in _LOCAL_HOSTS:
        raise invalid
    shown_host = f"[{host}]" if ":" in host else host
    authority = shown_host if port is None or port == _DEFAULT_PORTS[scheme] else f"{shown_host}:{port}"
    path = parts.path.rstrip("/")
    return f"{scheme}://{authority}{path}/chat/completions"


class _NoRedirectOpener:
    """OpenerDirector without HTTPRedirectHandler; proxies come only from the explicit setting."""

    @staticmethod
    def build(proxy: str | None) -> urllib.request.OpenerDirector:
        opener = urllib.request.OpenerDirector()
        proxies = {"http": proxy, "https": proxy} if proxy else {}
        for handler in (
            urllib.request.ProxyHandler(proxies),
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(),
            urllib.request.HTTPDefaultErrorHandler(),
            urllib.request.HTTPErrorProcessor(),
        ):
            opener.add_handler(handler)
        return opener


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    return isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, TimeoutError)


class OpenAICompatProvider:
    meta: ProviderMeta
    DEFAULT_META = dict(name='openai-compatible', model='', egress=True, cost_hint=None, max_batch=1,
                        retries=2, destination=canonical_destination(DEFAULT_BASE_URL), command_env_names=[],
                        accepts=['image/png', 'image/jpeg'])

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_s: float = 120.0,
                 cost_hint: str | None = None, proxy: str | None = None) -> None:
        if not api_key or any(ord(char) < 32 or ord(char) == 127 for char in api_key):
            raise ProviderConfigError("MDFLOW_API_KEY is missing or malformed")
        if not model:
            raise ProviderConfigError("a model is required")
        if cost_hint is not None:
            try:
                if Decimal(cost_hint) < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                raise ProviderConfigError("cost hint must be a non-negative decimal number") from None
        destination = canonical_destination(base_url)
        self._api_key = api_key
        self._timeout_s = timeout_s
        self.proxy = proxy
        self.requests_sent = 0
        self._opener = _NoRedirectOpener.build(proxy)
        from copy import deepcopy
        self.meta = dict(deepcopy(self.DEFAULT_META), model=model, cost_hint=cost_hint, destination=destination)

    def __repr__(self) -> str:
        return f"OpenAICompatProvider(model={self.meta['model']!r}, destination={self.meta['destination']!r})"

    __str__ = __repr__

    def _request_body(self, unit, raster: bytes, prompt) -> bytes:
        encoded = base64.b64encode(raster).decode("ascii")
        payload = {
            "model": self.meta["model"],
            "temperature": 0,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt.user},
                    {"type": "image_url", "image_url": {"url": f"data:{unit['mime']};base64,{encoded}"}},
                ]},
            ],
        }
        return json.dumps(payload).encode("utf-8")

    def _post_once(self, body: bytes) -> tuple[str, object]:
        """('ok', raw bytes) | ('retry', status) | ('http', status) | ('timeout', None) | ('output', None)."""
        deadline = time.monotonic() + self._timeout_s
        self.requests_sent += 1
        request = urllib.request.Request(
            self.meta["destination"], data=body, method="POST",
            headers={
                "Content-Type": "application/json", "Accept": "application/json",
                "Authorization": "Bearer " + self._api_key,
            })
        try:
            response = self._opener.open(request, timeout=self._timeout_s)
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            return ("retry" if status == 429 or status >= 500 else "http", status)
        except Exception as exc:
            if _is_timeout(exc):
                return "timeout", None
            return "http", type(exc).__name__
        try:
            with response:
                status = getattr(response, "status", 200)
                if not 200 <= status < 300:
                    return "http", status
                data = bytearray()
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return 'timeout', None
                    # HTTPResponse.read1 makes at most one underlying read. Refresh
                    # the socket timeout against the same monotonic deadline.
                    raw = getattr(getattr(response, 'fp', None), 'raw', None)
                    sock = getattr(raw, '_sock', None)
                    if sock is not None:
                        sock.settimeout(remaining)
                    chunk = getattr(response, 'read1', response.read)(_READ_CHUNK)
                    if time.monotonic() >= deadline:
                        return 'timeout', None
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > MAX_RESPONSE_BYTES:
                        return "output", None
                return "ok", bytes(data)
        except Exception as exc:
            if _is_timeout(exc):
                return "timeout", None
            return "http", type(exc).__name__

    @staticmethod
    def _extract(raw: bytes) -> str | None:
        try:
            content = json.loads(raw)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            return None
        if not isinstance(content, str) or not content.strip():
            return None
        return content

    def transcribe(self, unit, raster, prompt) -> UnitResult:
        started = time.monotonic()
        body = self._request_body(unit, raster, prompt)
        attempts = 1 + self.meta["retries"]
        for attempt in range(attempts):
            kind, detail = self._post_once(body)
            if kind == "ok":
                text = self._extract(detail)  # type: ignore[arg-type]
                if text is None:
                    return _failed("E_PROVIDER_OUTPUT", "response has no usable text content", started)
                return {"status": "ok", "text": text, "error": None, "duration_ms": int((time.monotonic() - started) * 1000)}
            if kind == "retry" and attempt + 1 < attempts:
                time.sleep(BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)])
                continue
            if kind == "timeout":
                return _failed("E_PROVIDER_TIMEOUT", "provider did not answer within the time limit", started)
            if kind == "output":
                return _failed("E_PROVIDER_OUTPUT", "response exceeds 4 MiB", started)
            label = f"HTTP status {detail}" if isinstance(detail, int) else f"request failed ({detail})"
            return _failed("E_PROVIDER_HTTP", label, started)
        return _failed("E_PROVIDER_HTTP", "request failed", started)
