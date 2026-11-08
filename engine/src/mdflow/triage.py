"""Stage 2: Triage wrapper (SPEC 2.2).

``run_triage(path, sniff)`` calls ``markitdown.ocr_triage.triage(path)`` in-process with default
options. The Core function is looked up at call time (``importlib.import_module``), never bound
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

import importlib
from pathlib import Path
from typing import TypedDict

from .contracts import Issue, SniffResult

NOT_RUN = "not_run"
_BLOCKING = frozenset(
    "E_SNIFF_IO E_TOO_LARGE E_CORRUPT E_ZIP_ENTRIES E_ZIP_TOTAL E_ZIP_BOMB E_ZIP_PATH E_ZIP_DEPTH "
    "E_OUTPUT_COLLISION".split()
)


class TriageOutcome(TypedDict):
    ran: bool
    report: dict | None
    coverage_state: str
    issues: list[Issue]


def _outcome(ran: bool, report: dict | None, state: str, issues: list[Issue]) -> TriageOutcome:
    return {"ran": ran, "report": report, "coverage_state": state, "issues": issues}


def run_triage(path: str | Path, sniff: SniffResult) -> TriageOutcome:
    if sniff["route"] != "NATIVE" or any(issue["code"] in _BLOCKING for issue in sniff["issues"]):
        return _outcome(False, None, NOT_RUN, [])
    try:
        core = importlib.import_module("markitdown.ocr_triage")
        report = core.triage(str(path))
    except Exception as exc:  # any Core failure is a verdict input, never a crash
        message = f"Core triage failed ({type(exc).__name__})"
        return _outcome(True, None, NOT_RUN, [{"code": "E_TRIAGE_FAIL", "message": message}])
    version = report.get("schema_version") if isinstance(report, dict) else None
    if not isinstance(report, dict) or type(version) is not int or version != 1:
        return _outcome(True, None, NOT_RUN, [{"code": "E_TRIAGE_SCHEMA", "message": "Core report has no schema_version 1"}])
    coverage = report.get("coverage")
    state = coverage.get("state") if isinstance(coverage, dict) else None
    return _outcome(True, report, state if isinstance(state, str) else NOT_RUN, [])
