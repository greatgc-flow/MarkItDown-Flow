"""Step 7 RED: sequential pipeline integration (SPEC section 4)."""

from datetime import datetime
from pathlib import Path
from typing import Sequence


def run(roots: Sequence[Path], options: dict, *, provider=None,
        now: datetime | None = None) -> dict:
    """Run discovered sources; provider/now permit deterministic integration probes."""
    raise NotImplementedError("Step 7: orchestrator")
