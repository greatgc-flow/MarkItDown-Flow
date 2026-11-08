"""Provider ``none`` (SPEC 8.2). RED-PHASE STUB.

egress False, destination None, retries 0, cost_hint "0", model "". ``transcribe`` is never called.
"""

from __future__ import annotations

from ..contracts import ProviderMeta


class NoneProvider:
    meta: ProviderMeta

    def __init__(self) -> None:
        raise NotImplementedError("Step 6 green: none provider")

    def transcribe(self, unit, raster, prompt):
        raise NotImplementedError("Step 6 green: none provider")
