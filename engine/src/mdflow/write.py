"""Stage 12: Write (SPEC 2.9 REQ-WRT-*, REQ-GEN-05, REQ-SEC-05/09).

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

import itertools
import os
import posixpath
import shutil
import stat
from pathlib import Path
from typing import Mapping, TypedDict

from .contracts import Issue

_SEQUENCE = itertools.count(1)
_COMPARE_CHUNK = 1 << 20
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class WriteResult(TypedDict):
    ok: bool
    written: list[str]
    unchanged: list[str]
    issues: list[Issue]


class _Containment(OSError):
    """The target would leave out_dir or pass through a link."""


def _same_bytes(path: str, data: bytes) -> bool:
    try:
        if os.stat(path).st_size != len(data):
            return False
        with open(path, "rb") as handle:
            offset = 0
            while offset < len(data):
                chunk = handle.read(_COMPARE_CHUNK)
                if not chunk or chunk != data[offset:offset + len(chunk)]:
                    return False
                offset += len(chunk)
            return handle.read(1) == b""
    except OSError:
        return False


def _ensure_directory(directory: str, dir_mode: int | None) -> None:
    if dir_mode is None:
        os.makedirs(directory, exist_ok=True)
        return
    missing: list[str] = []
    current = directory
    while current and not os.path.isdir(current):
        missing.append(current)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    for path in reversed(missing):
        try:
            os.mkdir(path, dir_mode)
        except FileExistsError:
            if not os.path.isdir(path):
                raise
        try:
            os.chmod(path, dir_mode)
        except OSError:
            pass


def atomic_write(target: str | Path, data: bytes, *, dir_mode: int | None = None) -> bool:
    destination = os.fspath(target)
    _ensure_directory(os.path.dirname(os.path.abspath(destination)), dir_mode)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    temp = ""
    descriptor = -1
    for _ in range(100):
        temp = f"{destination}.tmp-{os.getpid()}-{next(_SEQUENCE)}"
        try:
            descriptor = os.open(temp, flags, 0o600)
            break
        except FileExistsError:
            continue
    else:
        raise FileExistsError("no free temporary file name")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if os.path.isfile(destination) and _same_bytes(destination, data):
            os.unlink(temp)
            return False
        os.replace(temp, destination)
        return True
    except OSError:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def _is_link(path: str) -> bool:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return True
    return bool(getattr(info, "st_file_attributes", 0) & _REPARSE_POINT)


def _checked_target(out_dir: str, relative: str) -> str:
    """Return the write path for ``relative`` or raise _Containment (lstat walk at write time)."""
    if not relative or os.path.isabs(relative) or os.path.splitdrive(relative)[0]:
        raise _Containment("target is not relative")
    root_real = os.path.normcase(os.path.realpath(out_dir))
    lexical = os.path.normpath(os.path.join(out_dir, relative))
    real = os.path.normcase(os.path.realpath(lexical))
    if real != root_real and not real.startswith(root_real.rstrip(os.sep) + os.sep):
        raise _Containment("target leaves the output directory")
    parts = os.path.relpath(lexical, out_dir).split(os.sep)
    if parts[0] == os.pardir:
        raise _Containment("target leaves the output directory")
    current = out_dir
    for part in parts:
        current = os.path.join(current, part)
        try:
            linked = _is_link(current)
        except FileNotFoundError:
            break
        if linked:
            raise _Containment("link inside the output directory")
    return lexical


def _failure(result: WriteResult, exc: BaseException) -> WriteResult:
    result["ok"] = False
    result["issues"].append({"code": "E_OUTPUT_IO", "message": f"output could not be written ({type(exc).__name__})"})
    return result


def publish_source(
    out_dir: str | Path,
    md_rel: str,
    md_bytes: bytes,
    media: Mapping[str, str | Path] | None = None,
) -> WriteResult:
    result: WriteResult = {"ok": True, "written": [], "unchanged": [], "issues": []}
    root = os.fspath(out_dir)
    folder = posixpath.dirname(md_rel.replace("\\", "/"))
    artifacts: list[tuple[str, str, bytes | Path]] = []
    for name, source in (media or {}).items():
        artifacts.append((posixpath.join(folder, "media", name), name, Path(source)))
    artifacts.append((md_rel, "", md_bytes))
    try:
        for relative, media_name, payload in artifacts:
            if media_name and (media_name != os.path.basename(media_name) or media_name in (".", "..")):
                raise _Containment("media name is not a plain file name")
            path = _checked_target(root, relative)
            content = payload if isinstance(payload, bytes) else payload.read_bytes()
            changed = atomic_write(path, content)
            (result["written"] if changed else result["unchanged"]).append(posixpath.normpath(relative))
    except (OSError, ValueError) as exc:
        return _failure(result, exc)
    return result


def _remove_readonly(function, path, _excinfo) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


def clear_cache(cache_dir: str | Path) -> int:
    root = os.fspath(cache_dir)
    if not os.path.isdir(root):
        return 0
    removed = 0
    for entry in os.listdir(root):
        path = os.path.join(root, entry)
        if os.path.isdir(path) and not _is_link(path):
            removed += sum(len(files) for _, _, files in os.walk(path))
            try:
                shutil.rmtree(path, onexc=_remove_readonly)
            except TypeError:  # Python < 3.12 has only onerror
                shutil.rmtree(path, onerror=_remove_readonly)
        else:
            try:
                os.unlink(path)
            except PermissionError:
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)
            removed += 1
    return removed
