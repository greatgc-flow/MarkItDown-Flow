"""Provider ``none`` (SPEC 8.2).

egress False, destination None, retries 0, cost_hint "0", model "". ``transcribe`` is never called.
"""

from __future__ import annotations

from ..contracts import ProviderMeta, UnitResult


class NoneProvider:
    meta: ProviderMeta

    DEFAULT_META = {
        "name": "none", "model": "", "egress": False, "cost_hint": "0", "max_batch": 1, "retries": 0,
        "destination": None, "command_env_names": [], "accepts": ["image/png", "image/jpeg"],
    }

    def __init__(self) -> None:
        from copy import deepcopy
        self.meta = deepcopy(self.DEFAULT_META)

    def transcribe(self, unit, raster, prompt) -> UnitResult:
        # Defensive: the pipeline never sends anything to this provider.
        return {
            "status": "failed", "text": None, "duration_ms": 0,
            "error": {"code": "E_PROVIDER_CONFIG", "message": "provider none does not transcribe", "exit": None},
        }
