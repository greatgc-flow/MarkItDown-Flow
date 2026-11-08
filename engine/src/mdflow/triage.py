"""Stage 2: Triage wrapper (SPEC 2.2). RED-PHASE STUB.

``run_triage(path, sniff)`` calls ``markitdown.ocr_triage.triage(path)`` in-process with default
options. The Core function MUST be looked up at call time (``importlib.import_module``), never bound
at import time, so tests can substitute ``sys.modules['markitdown.ocr_triage']``.

* Core is called only when ``sniff["route"] == "NATIVE"`` and ``sniff["issues"]`` holds none of
  ``E_SNIFF_IO E_TOO_LARGE E_CORRUPT E_ZIP_ENTRIES E_ZIP_TOTAL E_ZIP_BOMB E_ZIP_PATH E_ZIP_DEPTH
  E_OUTPUT_COLLISION`` (archive preflight happens before Core touches the bytes, REQ-SNF-08).
  Otherwise ``ran`` is False, ``report`` None, ``coverage_state`` "not_run", no issues.
* Any exception from Core -> ``E_TRIAGE_FAIL`` (ran True, report None, coverage_state "not_run").
* A report that is not a dict with ``schema_version`` equal to the int 1 (``True`` and ``"1"`` do not
  count) -> ``E_TRIAGE_SCHEMA`` before any other field is read.
* The report is returned verbatim, unmodified. ``coverage_state`` is Core's ``coverage.state`` when
  present else ``"not_run"``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from .contracts import Issue, SniffResult


class TriageOutcome(TypedDict):
    ran: bool
    report: dict | None
    coverage_state: str
    issues: list[Issue]


def run_triage(path: str | Path, sniff: SniffResult) -> TriageOutcome:
    raise NotImplementedError("Step 5 green: triage wrapper")
