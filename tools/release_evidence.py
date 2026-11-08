"""Release-evidence validators and the cleanup tool (REQ-PKG-18, -19, -20, -21). RED STUBS.

Step 11 (red): every function raises ``NotImplementedError``; ``engine/tests/packaging`` (PT-18..PT-21)
pins the schemas and behavior. The green step replaces the bodies. A passing schema check proves a
named person supplied a well-formed record, not that the recorded property is true.

Validators return a list of human-readable problems; ``[]`` means schema-valid.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


class CleanupRefused(Exception):
    """Cleanup was refused: not verified, inside the rollback window, or a path is not owned/contained."""


def validate_rehearsal(data: dict) -> list[str]:
    """PT-18 / MAN-04 release rehearsal record (see PT-18 test for the exact schema)."""
    raise NotImplementedError("REQ-PKG-18 rehearsal validator")


def validate_postdeploy(data: dict) -> list[str]:
    """PT-19 post-deploy report (see PT-19 test for the exact schema)."""
    raise NotImplementedError("REQ-PKG-19 post-deploy validator")


def validate_rollback(data: dict) -> list[str]:
    """PT-20 rollback rehearsal record (see PT-20 test for the exact schema)."""
    raise NotImplementedError("REQ-PKG-20 rollback validator")


def plan_cleanup(plugin_dir: Path, owned: list[str], *, verified_at: datetime | None, now: datetime,
                 live: frozenset[str] = frozenset()) -> list[Path]:
    """Dry run: the exact resolved owned paths a cleanup would remove (REQ-PKG-21). Removes nothing.

    ``owned`` are names relative to ``plugin_dir``. Raises ``CleanupRefused`` when ``verified_at`` is None, when
    ``now < verified_at + 7 days``, or for any target that is not an owned artifact class located directly in
    ``plugin_dir`` (stale ``transport-*.tmp``, retired generated ``wrapper.*``): absolute paths, ``..``, symlinks
    leaving ``plugin_dir`` and protected content (settings, snapshot, locks, logs, cache) are all refused.
    Names in ``live`` (process still running) are retained, not planned."""
    raise NotImplementedError("REQ-PKG-21 cleanup dry-run")


def execute_cleanup(plugin_dir: Path, plan: list[Path], *, log: Path) -> dict:
    """Remove exactly ``plan``; write ``log`` listing removed and retained; return {removed, retained}."""
    raise NotImplementedError("REQ-PKG-21 cleanup execution")
