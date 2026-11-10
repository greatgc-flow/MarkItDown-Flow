"""JSON report publication and bounded, redacted progress (SPEC 7.3/7.4)."""

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Mapping, TextIO

from . import redact


def home_relative(path: str) -> str:
    """Shorten only a complete home prefix, preserving the rest of the path."""
    home = str(Path.home())
    return "~" + path[len(home):] if path == home or path.startswith(home + os.sep) else path


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
            strings = []
            containers = []
            def visit(node):
                if isinstance(node, dict):
                    for key, child in node.items():
                        if isinstance(child, str) and child and key not in {'ev', 'code', 'ts', 'plan_hash'}:
                            strings.append((node, key, child))
                        elif isinstance(child, (dict, list)):
                            visit(child)
                elif isinstance(node, list):
                    if len(node) > 1:
                        containers.append(node)
                    for key, child in enumerate(node):
                        if isinstance(child, str) and child:
                            strings.append((node, key, child))
                        elif isinstance(child, (dict, list)):
                            visit(child)
            visit(value)
            if not strings:
                if not containers:
                    raise ValueError('progress fixed fields exceed 64 KiB')
                container = max(containers, key=len)
                del container[len(container) // 2:]
            else:
                parent, key, child = max(strings, key=lambda pair: len(pair[2].encode('utf-8')))
                parent[key] = child[:len(child) // 2]
        line = _json(value)
    stream.write(line + "\n")
    stream.flush()


def publish(value: dict, *, stdout: TextIO) -> None:
    text = _json(value) + "\n"
    stdout.write(text)
    stdout.flush()
