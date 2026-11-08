"""Step 7 RED: report and progress publication (SPEC 7.3/7.4)."""

from pathlib import Path
from typing import Mapping, TextIO


def emit_progress(event: dict, stream: TextIO, *,
                  env: Mapping[str, str] | None = None, home: str | None = None) -> None:
    raise NotImplementedError("Step 7: JSONL progress")


def publish(value: dict, *, stdout: TextIO, report_path: Path | None = None) -> None:
    raise NotImplementedError("Step 7: run report")
