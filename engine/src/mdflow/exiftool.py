"""exiftool discovery (SPEC REQ-CNV-06, R31).

markitdown-gc extracts image/audio EXIF metadata only when it is handed an ``exiftool_path``. Its own probing finds
``EXIFTOOL_PATH`` and a few well-known directories but not a user-installed tool elsewhere on ``PATH``, and it raises on
a configured-but-broken path. ``mdflow`` therefore decides itself and always passes Core an explicit value (the empty
string disables Core's probing).

* order: ``EXIFTOOL_PATH`` (non-empty; never silently replaced by ``PATH`` when unusable), then ``PATH``;
* the candidate must print a version ``>= 12.24`` for ``-ver`` (older releases carry CVE-2021-22204);
* ``detect()`` never raises: it returns ``available``, ``path``, ``version``, ``source`` (``EXIFTOOL_PATH|PATH|None``) and
  ``status`` (``ok|not_found|too_old|unusable``); results are cached per (``EXIFTOOL_PATH``, ``PATH``, deadline);
* the ``-ver`` deadline is ``VERSION_TIMEOUT_S`` for the ``version``/``selftest`` diagnostics (SPEC 10.1 M6 budget) and
  ``CONVERT_TIMEOUT_S`` when an image conversion needs the tool (a Perl cold start can exceed 0.5 s);
* exiftool is optional enrichment for standalone images; it is never started for any other format. An image conversion
  with a found/configured but unusable tool (``too_old|unusable``) records ``W_EXIFTOOL_UNUSABLE`` (``unusable_issues``).
"""

from __future__ import annotations

import functools
import os
import re
import shutil

from . import core_guard, runtime_temp

MIN_VERSION = (12, 24)
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})  # the extensions Core's image converter accepts
_VERSION = re.compile(r"\d+(?:\.\d+)*")
VERSION_TIMEOUT_S = 0.5  # `version` diagnostics: each optional tool's deadline (SPEC 10.1 M6, T-CLI-87/88)
CONVERT_TIMEOUT_S = 3.0  # image conversions: bounded like the 3 s healthy-machine `version` target


def _result(status: str, *, path: str | None = None, version: str | None = None, source: str | None = None) -> dict:
    return dict(available=status == "ok", path=path if status == "ok" else None, version=version, source=source,
                status=status)


def _probe(candidate: str, source: str, timeout_s: float) -> dict:
    try:
        # Reuse Core's bounded capture and descendant cleanup. In particular,
        # killing a Windows .cmd alone leaves inherited PIPE readers alive.
        with core_guard.quiet_output():
            from markitdown import _libreoffice as lo
        with runtime_temp.run_directory() as work:
            text = lo._execute([candidate, "-ver"], cwd=work, timeout_s=timeout_s,
                               output=work / 'version.log').strip()
    except Exception:
        return _result("unusable", source=source)
    if not _VERSION.fullmatch(text):
        return _result("unusable", source=source)
    if tuple(int(part) for part in text.split(".")) < MIN_VERSION:
        return _result("too_old", version=text, source=source)
    return _result("ok", path=candidate, version=text, source=source)


@functools.lru_cache(maxsize=16)
def _detect(explicit: str, search_path: str, timeout_s: float) -> dict:
    if explicit:
        found = shutil.which(explicit) if not os.path.isabs(explicit) else (explicit if os.path.isfile(explicit) else None)
        return _probe(found, "EXIFTOOL_PATH", timeout_s) if found else _result("unusable", source="EXIFTOOL_PATH")
    found = shutil.which("exiftool", path=search_path)
    return _probe(os.path.abspath(found), "PATH", timeout_s) if found else _result("not_found")


def detect(timeout_s: float = VERSION_TIMEOUT_S) -> dict:
    """The current environment's exiftool state (see the module docstring); never raises."""
    return dict(_detect(os.environ.get("EXIFTOOL_PATH", "").strip(), os.environ.get("PATH", ""), timeout_s))


def reset() -> None:
    """Forget cached detections (tests and long-lived hosts that change the environment)."""
    _detect.cache_clear()


def for_extension(ext: str) -> dict | None:
    """The usable exiftool (``path`` and ``version``) for a conversion with this extension hint, else ``None``."""
    if ext.lower() not in IMAGE_EXTENSIONS:
        return None
    found = detect(CONVERT_TIMEOUT_S)
    return found if found["available"] else None


def unusable_issues(ext: str) -> list[dict]:
    """``[W_EXIFTOOL_UNUSABLE]`` when this image conversion skipped a found/configured but unusable exiftool, else ``[]``."""
    if ext.lower() not in IMAGE_EXTENSIONS:
        return []
    found = detect(CONVERT_TIMEOUT_S)
    if found["status"] not in ("too_old", "unusable"):
        return []
    return [{"code": "W_EXIFTOOL_UNUSABLE",
             "message": f"exiftool from {found['source']} is {found['status'].replace('_', ' ')} "
                        "(needs a working version >= 12.24); image metadata was skipped."}]
