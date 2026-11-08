"""Stage 12: Write (SPEC 2.9 REQ-WRT-*, REQ-GEN-05, REQ-SEC-05/09). RED-PHASE STUB.

All modules reach the OS through ``os.open``, ``os.fsync`` and ``os.replace`` *module attributes*
(tests patch them).

* ``atomic_write(target, data, *, dir_mode=None) -> bool``: temp ``<target>.tmp-<pid>-<seq>`` in the same
  directory (``O_CREAT|O_EXCL``, mode 0o600), fsync, byte-compare with an existing target (identical ->
  delete temp, leave target untouched, return False), ``os.replace`` (return True). Missing parent
  directories are created with ``dir_mode`` when given. OSError propagates.
* ``publish_source(out_dir, md_rel, md_bytes, media=None) -> WriteResult``: containment (realpath inside
  out_dir and no symlink/junction between out_dir and the target, lstat walk at write time), media files
  (``media`` maps name -> source path) published to ``<dirname(md_rel)>/media/<name>`` BEFORE the ``.md``.
  Failures never raise: ``ok False`` and ``E_OUTPUT_IO`` (message without absolute paths).
* ``clear_cache(cache_dir) -> int``: removes everything under the cache dir (including stale ``*.tmp-*``)
  and leaves the directory itself, empty.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, TypedDict

from .contracts import Issue


class WriteResult(TypedDict):
    ok: bool
    written: list[str]
    unchanged: list[str]
    issues: list[Issue]


def atomic_write(target: str | Path, data: bytes, *, dir_mode: int | None = None) -> bool:
    raise NotImplementedError("Step 6 green: atomic write")


def publish_source(
    out_dir: str | Path,
    md_rel: str,
    md_bytes: bytes,
    media: Mapping[str, str | Path] | None = None,
) -> WriteResult:
    raise NotImplementedError("Step 6 green: publish")


def clear_cache(cache_dir: str | Path) -> int:
    raise NotImplementedError("Step 6 green: cache clear")
