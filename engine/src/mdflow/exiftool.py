"""exiftool discovery (SPEC REQ-CNV-06, R31).

markitdown-gc extracts image/audio EXIF metadata only when it is handed an ``exiftool_path``. Its own probing finds
``EXIFTOOL_PATH`` and a few well-known directories but not a user-installed tool elsewhere on ``PATH``, and it raises on
a configured-but-broken path. ``mdflow`` therefore decides itself and always passes Core an explicit value (the empty
string disables Core's probing).

* order: ``EXIFTOOL_PATH`` (non-empty; never silently replaced by ``PATH`` when unusable), then ``PATH``;
* the candidate must print a version ``>= 12.24`` for ``-ver`` (older releases carry CVE-2021-22204);
* ``detect()`` never raises: it returns ``available``, ``path``, ``version``, ``source`` (``EXIFTOOL_PATH|PATH|None``) and
  ``status`` (``ok|not_found|too_old|unusable``); results are cached per (``EXIFTOOL_PATH``, ``PATH``) value pair;
* exiftool is optional enrichment for standalone images; it is never started for any other format.
"""

from __future__ import annotations

import functools
import os
import re
import shutil

from . import core_guard, runtime_temp
from .executable import resolve_executable

MIN_VERSION = (12, 24)
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})  # the extensions Core's image converter accepts
_VERSION = re.compile(r"\d+(?:\.\d+)*")
_TIMEOUT_S = 0.5


def _result(status: str, *, path: str | None = None, version: str | None = None, source: str | None = None) -> dict:
    return dict(available=status == "ok", path=path if status == "ok" else None, version=version, source=source,
                status=status)


def _probe(candidate: str, source: str) -> dict:
    try:
        # Reuse Core's bounded capture and descendant cleanup. In particular,
        # killing a Windows .cmd alone leaves inherited PIPE readers alive.
        with core_guard.quiet_output():
            from markitdown import _libreoffice as lo
        with runtime_temp.run_directory() as work:
            text = lo._execute([candidate, "-ver"], cwd=work, timeout_s=_TIMEOUT_S,
                               output=work / 'version.log').strip()
    except Exception:
        return _result("unusable", source=source)
    if not _VERSION.fullmatch(text):
        return _result("unusable", source=source)
    if tuple(int(part) for part in text.split(".")) < MIN_VERSION:
        return _result("too_old", version=text, source=source)
    return _result("ok", path=candidate, version=text, source=source)


@functools.lru_cache(maxsize=16)
def _detect(explicit: str, search_path: str) -> dict:
    if explicit:
        if os.path.isabs(explicit):
            found = explicit if os.path.isfile(explicit) else None
        else:  # a bare name is looked up like PATH; a relative path with a folder is the user's explicit choice
            found = shutil.which(explicit) if os.path.dirname(explicit) else resolve_executable(explicit, search_path)
        return _probe(found, "EXIFTOOL_PATH") if found else _result("unusable", source="EXIFTOOL_PATH")
    found = resolve_executable("exiftool", search_path)  # never the current folder (security review C1)
    return _probe(found, "PATH") if found else _result("not_found")


def detect() -> dict:
    """The current environment's exiftool state (see the module docstring); never raises."""
    return dict(_detect(os.environ.get("EXIFTOOL_PATH", "").strip(), os.environ.get("PATH", "")))


def reset() -> None:
    """Forget cached detections (tests and long-lived hosts that change the environment)."""
    _detect.cache_clear()


def for_extension(ext: str) -> dict | None:
    """The usable exiftool (``path`` and ``version``) for a conversion with this extension hint, else ``None``."""
    if ext.lower() not in IMAGE_EXTENSIONS:
        return None
    found = detect()
    return found if found["available"] else None
