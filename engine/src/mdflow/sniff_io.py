"""Stage 1 IO: discovery, Sniff, zip containers (SPEC 2.1, 2.11). RED-PHASE STUB.

Binding API (the red tests in engine/tests/stage_io pin it):

* ``discover(roots, *, exclude=()) -> Discovery`` walks input roots (REQ-SNF-01/01b).
  Paths in ``Discovery`` are logical POSIX paths; ``files[].path`` is the absolute runtime path.
  ``skipped`` holds ``{"path": <logical>, "code": W_SKIPPED_HIDDEN|W_SKIPPED_SYMLINK|W_DUPLICATE_INPUT}``.
  A second logical source whose output path (``logical + ".md"``) collides after ``casefold()`` gets
  ``E_OUTPUT_COLLISION`` in ``files[].issues`` (row 0c).
* ``sniff(path, *, logical, root=0, max_bytes=..., zip_entries=..., zip_total_bytes=...) -> SniffResult``
  (REQ-SNF-02..08). ``ext`` is lower-case without the dot. ``reasons`` vocabulary used by the tests:
  ``pdf_password``, ``pdf_encrypt_trailer``, ``zip_flag_bit``, ``cfb_encrypted_package``,
  ``hwp5_encrypted``, ``media_out_of_scope``, ``unsupported_format``. Read failure never raises:
  it yields ``E_SNIFF_IO`` and route ``UNSUPPORTED``. Core must never be imported or called.
* ``read_member(zip_path, name, *, max_bytes, total_remaining=None) -> bytes`` streams a member in
  64 KiB chunks and raises ``ZipReadError(code="E_ZIP_BOMB")`` when the real decompressed size exceeds
  the declared size, ``max_bytes`` or ``total_remaining`` (REQ-SNF-09). ``name`` is the verbatim
  (``orig_filename``) member name.
* ``expand_container(source, *, logical, max_bytes=..., zip_depth=3, zip_entries=1000,
  zip_total_bytes=...) -> Container`` reads zip members in memory (never by name on disk), flattens
  nested zips (top-level zip is depth 1) and applies cumulative budgets (REQ-CTR-01..04).
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, TypedDict

from .contracts import Issue, SniffResult

DEFAULT_MAX_BYTES = 209715200
DEFAULT_ZIP_DEPTH = 3
DEFAULT_ZIP_ENTRIES = 1000
DEFAULT_ZIP_TOTAL_BYTES = 1073741824


class DiscoveredFile(TypedDict):
    path: str
    logical: str
    root: int
    issues: list[Issue]


class Skipped(TypedDict):
    path: str
    code: str


class Discovery(TypedDict):
    files: list[DiscoveredFile]
    skipped: list[Skipped]


class Member(TypedDict):
    logical: str
    member: str
    depth: int
    data: bytes
    sniff: SniffResult


class Container(TypedDict):
    logical: str
    issues: list[Issue]
    members: list[Member]


class ZipReadError(Exception):
    """Raised by read_member; ``code`` is a closed-list code such as E_ZIP_BOMB."""

    code: str = "E_ZIP_BOMB"


def discover(roots: Sequence[str | Path], *, exclude: Sequence[str | Path] = ()) -> Discovery:
    raise NotImplementedError("Step 5 green: discovery")


def sniff(
    path: str | Path,
    *,
    logical: str,
    root: int = 0,
    max_bytes: int = DEFAULT_MAX_BYTES,
    zip_entries: int = DEFAULT_ZIP_ENTRIES,
    zip_total_bytes: int = DEFAULT_ZIP_TOTAL_BYTES,
) -> SniffResult:
    raise NotImplementedError("Step 5 green: sniff")


def read_member(
    zip_path: str | Path, name: str, *, max_bytes: int, total_remaining: int | None = None
) -> bytes:
    raise NotImplementedError("Step 5 green: streamed member read")


def expand_container(
    source: str | Path | bytes,
    *,
    logical: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    zip_depth: int = DEFAULT_ZIP_DEPTH,
    zip_entries: int = DEFAULT_ZIP_ENTRIES,
    zip_total_bytes: int = DEFAULT_ZIP_TOTAL_BYTES,
) -> Container:
    raise NotImplementedError("Step 5 green: container expansion")
