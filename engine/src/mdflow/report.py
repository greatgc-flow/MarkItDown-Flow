"""JSON report publication and bounded, redacted progress (SPEC 7.3/7.4)."""

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Mapping, TextIO

from . import redact, write


def diagnostics(value: object, *, env: Mapping[str, str] | None = None,
                home: str | None = None) -> object:
    """Copy diagnostics, leaving document data and Core's triage subtree verbatim."""
    settings = os.environ if env is None else env
    prefix = str(Path.home()) if home is None else home
    if isinstance(value, dict):
        return {key: deepcopy(child) if key == "triage" else
                redact.redact(child, settings, prefix) if key == "message" and isinstance(child, str) else
                diagnostics(child, env=settings, home=prefix) for key, child in value.items()}
    if isinstance(value, list):
        return [diagnostics(child, env=settings, home=prefix) for child in value]
    return value


def _json(value: object, *, pretty: bool = False) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      indent=2 if pretty else None, separators=None if pretty else (",", ":"))


def emit_progress(event: dict, stream: TextIO, *,
                  env: Mapping[str, str] | None = None, home: str | None = None) -> None:
    value = diagnostics(event, env=env, home=home)
    if "sensitive_hits" in value:
        value["sensitive_hits"] = value["sensitive_hits"][:20]
    if value.get("ev") == "approve_required":
        value.pop("units", None)
    line = _json(value)
    # Pattern strings can themselves be very long. Preserve valid JSON and the
    # summary's scalar facts while reducing only its informational strings.
    while len(line.encode("utf-8")) > 65535:
        hits = value.get("sensitive_hits", [])
        if hits:
            value["sensitive_hits"] = hits[:-1]
        else:
            strings = [(key, child) for key, child in value.items()
                       if isinstance(child, str) and key not in {"ev", "code", "ts", "plan_hash"}]
            if not strings:
                raise ValueError("progress event exceeds 64 KiB")
            key, child = max(strings, key=lambda pair: len(pair[1]))
            if not child:
                raise ValueError("progress event exceeds 64 KiB")
            value[key] = child[:len(child) // 2]
        line = _json(value)
    stream.write(line + "\n")
    stream.flush()


def publish(value: dict, *, stdout: TextIO, report_path: Path | None = None) -> None:
    text = _json(value) + "\n"
    if report_path is not None:
        write.atomic_write(report_path, text.encode("utf-8"))
    stdout.write(text)
    stdout.flush()
