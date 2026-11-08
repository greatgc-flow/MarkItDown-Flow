"""Stage 10: Transcribe (SPEC 2.8, 8.3). RED-PHASE STUB.

The ledger store is owned by another worktree, so the stage receives a ``publish`` callable.

``run_transcribe(jobs, provider, *, prompt, force, max_requests, consent, tools, now, publish,
postprocess) -> TranscribeResult``

* ``jobs``: one ``KeyJob`` per distinct Key (units sharing a Key are listed in ``units``; the first is
  the representative handed to the provider). ``hit`` is the Lookup result; hits are skipped unless
  ``force``. With ``provider.meta["egress"] is False`` and name ``none`` nothing is sent.
* Before each request the raster file is read into memory and re-hashed against
  ``key["raster_sha256"]``; a mismatch -> issue ``E_APPROVAL_DENIED`` + key id in ``denied``, nothing is
  sent, no entry is published (REQ-APR-07).
* A unit mime outside ``provider.meta["accepts"]`` -> failed entry ``E_PROVIDER_CONFIG``, no call.
* ``provider.transcribe(unit, raster, prompt)`` raising ``Exception`` -> failed ``E_PROVIDER_CONFIG`` for
  that Key, later Keys still run. ``BaseException`` (crash, KeyboardInterrupt) propagates untouched.
* ``postprocess(text) -> (text, issues)`` is the REQ-TRX-04 pipeline (owned by the assemble worktree).
* Every result (ok or failed) is turned into a ledger entry (SPEC 7.2) and handed to ``publish`` BEFORE
  the next request starts. ``created`` is ``now.isoformat(timespec="seconds")``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping, Sequence, TypedDict

from .contracts import Consent, Issue, LedgerEntry, Unit


@dataclass(frozen=True)
class Prompt:
    version: str
    system: str
    user: str


class KeyJob(TypedDict):
    key_id: str
    key: dict
    units: list[Unit]
    raster_path: str
    hit: bool


class TranscribeResult(TypedDict):
    entries: dict[str, LedgerEntry]
    sent: int
    ok: int
    failed: int
    denied: list[str]
    issues: list[dict]


def load_prompt(version: str) -> Prompt:
    """Return the packaged prompt; unknown versions raise LookupError."""
    raise NotImplementedError("Step 6 green: packaged prompt")


def run_transcribe(
    jobs: Sequence[KeyJob],
    provider: object,
    *,
    prompt: Prompt,
    force: bool,
    max_requests: int,
    consent: Consent | None,
    tools: Mapping[str, str],
    now: datetime,
    publish: Callable[[LedgerEntry], None],
    postprocess: Callable[[str], tuple[str, list[Issue]]],
) -> TranscribeResult:
    raise NotImplementedError("Step 6 green: transcribe")
