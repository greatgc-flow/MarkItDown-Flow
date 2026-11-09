"""Stage 1 IO: discovery, Sniff, zip containers (SPEC 2.1, 2.11).

Binding API (the stage_io tests pin it):

* ``discover(roots, *, exclude=()) -> Discovery`` walks input roots (REQ-SNF-01/01b).
  Paths in ``Discovery`` are logical POSIX paths; ``files[].path`` is the absolute runtime path.
  ``skipped`` holds ``{"path": <logical>, "code": W_SKIPPED_HIDDEN|W_SKIPPED_SYMLINK|W_DUPLICATE_INPUT}``.
  A second logical source whose output path (``logical + ".md"``) collides after ``casefold()`` gets
  ``E_OUTPUT_COLLISION`` in ``files[].issues`` (row 0c).
* ``sniff(path, *, logical, root=0, max_bytes=..., zip_entries=..., zip_total_bytes=...) -> SniffResult``
  (REQ-SNF-02..08). ``ext`` is lower-case without the dot. ``reasons`` vocabulary:
  ``pdf_password``, ``pdf_encrypt_trailer``, ``zip_flag_bit``, ``cfb_encrypted_package``,
  ``hwp5_encrypted``, ``media_out_of_scope``, ``unsupported_format``. Read failure never raises:
  it yields ``E_SNIFF_IO`` and route ``UNSUPPORTED``. Core is never imported or called.
* ``read_member(zip_path, name, *, max_bytes, total_remaining=None) -> bytes`` streams a member in
  64 KiB chunks and raises ``ZipReadError(code="E_ZIP_BOMB")`` when the real decompressed size exceeds
  the declared size, ``max_bytes`` or ``total_remaining`` (REQ-SNF-09). ``name`` is the verbatim
  (``orig_filename``) member name.
* ``expand_container(source, *, logical, max_bytes=..., zip_depth=3, zip_entries=1000,
  zip_total_bytes=...) -> Container`` reads zip members in memory (never by name on disk), flattens
  nested zips (top-level zip is depth 1) and applies cumulative budgets (REQ-CTR-01..04).
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import stat
import struct
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Sequence, TypedDict

from .contracts import Issue, SniffResult
from .sniff_pure import (by_extension as _by_extension, magic_format as _magic_format,
                         zip_format as _zip_format, zip_route as _zip_route, expected_exts as _expected_exts)

DEFAULT_MAX_BYTES = 209715200
DEFAULT_ZIP_DEPTH = 3
DEFAULT_ZIP_ENTRIES = 1000
DEFAULT_ZIP_TOTAL_BYTES = 1073741824

_CHUNK = 65536
_MIB = 1048576
_CFB_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_ZIP_FAMILY_NATIVE = frozenset({"docx", "pptx", "xlsx", "hwpx", "epub"})
_ZIP_FAMILY_LEGACY = frozenset({"odt", "odp", "ods"})
_ENCRYPTED_OFFICE_EXTS = frozenset({"docx", "xlsx", "pptx"})
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


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

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message or (code or self.code))
        if code is not None:
            self.code = code


def _issue(code: str, message: str) -> Issue:
    return {"code": code, "message": message}


# ---------------------------------------------------------------------------------------------
# discovery


def _real(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(os.fspath(path)))


def _is_link(path: str) -> bool:
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction and isjunction(path):
        return True
    try:
        return bool(getattr(os.lstat(path), 'st_file_attributes', 0) &
                    getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))
    except FileNotFoundError:
        return False


def _inside(candidate: str, folder: str) -> bool:
    return candidate == folder or candidate.startswith(folder.rstrip(os.sep) + os.sep)


def _walk(directory: str, prefix: str, excluded: list[str], found: list[tuple[str, str]], skipped: list[Skipped]) -> None:
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        found.append((prefix.rstrip('/') or os.path.basename(directory.rstrip('/\\')), directory))
        return
    for name in names:
        full = os.path.join(directory, name)
        logical = f"{prefix}{name}"
        if name.startswith("."):
            skipped.append({"path": logical, "code": "W_SKIPPED_HIDDEN"})
            continue
        if _is_link(full):
            skipped.append({"path": logical, "code": "W_SKIPPED_SYMLINK"})
            continue
        real = _real(full)
        if any(_inside(real, folder) for folder in excluded):
            continue
        if os.path.isdir(full):
            _walk(full, logical + "/", excluded, found, skipped)
        else:
            found.append((logical, full))


def discover(roots: Sequence[str | Path], *, exclude: Sequence[str | Path] = ()) -> Discovery:
    excluded = [_real(path) for path in exclude]
    files: list[DiscoveredFile] = []
    skipped: list[Skipped] = []
    seen_real: set[str] = set()
    seen_output: set[str] = set()
    seen_roots: set[str] = set()
    for index, root in enumerate(roots):
        root_text = os.fspath(root)
        name = os.path.basename(os.path.abspath(root_text)) or root_text
        if name.startswith('.'):
            skipped.append({'path': name, 'code': 'W_SKIPPED_HIDDEN'})
            continue
        if _is_link(root_text):
            skipped.append({'path': name, 'code': 'W_SKIPPED_SYMLINK'})
            continue
        real_root = _real(root_text)
        if any(_inside(real_root, folder) for folder in excluded):
            continue
        if real_root in seen_roots:
            skipped.append({'path': name, 'code': 'W_DUPLICATE_INPUT'})
            continue
        seen_roots.add(real_root)
        if os.path.isdir(root_text):
            found: list[tuple[str, str]] = []
            _walk(root_text, "", excluded, found, skipped)
            found.sort(key=lambda item: item[0])
        else:
            found = [(os.path.basename(root_text.rstrip("/\\")) or root_text, root_text)]
        for logical, full in found:
            real = _real(full)
            if real in seen_real:
                skipped.append({"path": logical, "code": "W_DUPLICATE_INPUT"})
                continue
            seen_real.add(real)
            issues: list[Issue] = []
            output_key = (logical + ".md").casefold()
            if output_key in seen_output:
                issues.append(_issue("E_OUTPUT_COLLISION", "output path collides with an earlier source (case-insensitive)"))
            else:
                seen_output.add(output_key)
            files.append({"path": os.path.abspath(full), "logical": logical, "root": index, "issues": issues})
    return {"files": files, "skipped": skipped}


# ---------------------------------------------------------------------------------------------
# CFB (OLE2) structure: header, FAT, directory, first bytes of a stream


class _CfbError(Exception):
    pass


class _Cfb:
    _END = 0xFFFFFFFE
    _MAX_REG = 0xFFFFFFFA

    def __init__(self, fp: BinaryIO, size: int) -> None:
        self.fp = fp
        fp.seek(0)
        header = fp.read(512)
        if len(header) < 512 or header[:8] != _CFB_SIGNATURE:
            raise _CfbError("header")
        shift = struct.unpack_from("<H", header, 0x1E)[0]
        if shift not in (9, 12):
            raise _CfbError("sector shift")
        self.sector_size = 1 << shift
        self.sector_count = max(0, -(-(size - self.sector_size) // self.sector_size))
        fat_count, first_dir = struct.unpack_from("<II", header, 0x2C)
        self.mini_cutoff, first_minifat, minifat_count = struct.unpack_from("<III", header, 0x38)
        first_difat, difat_count = struct.unpack_from("<II", header, 0x44)
        difat = list(struct.unpack_from("<109I", header, 0x4C))
        if fat_count > self.sector_count or difat_count > self.sector_count:
            raise _CfbError("counts")
        per_sector = self.sector_size // 4
        sector = first_difat
        for _ in range(difat_count):
            if sector > self._MAX_REG:
                break
            raw = self._sector(sector)
            entries = struct.unpack("<%dI" % per_sector, raw)
            difat.extend(entries[:-1])
            sector = entries[-1]
        fat_sectors = [s for s in difat if s <= self._MAX_REG][:fat_count]
        if len(fat_sectors) < fat_count:
            raise _CfbError("fat")
        self.fat: list[int] = []
        for fat_sector in fat_sectors:
            self.fat.extend(struct.unpack("<%dI" % per_sector, self._sector(fat_sector)))
        self.first_minifat = first_minifat
        self.minifat_count = minifat_count
        self.entries = self._read_directory(first_dir)

    def _sector(self, number: int) -> bytes:
        if number >= self.sector_count:
            raise _CfbError("sector out of range")
        self.fp.seek((number + 1) * self.sector_size)
        raw = self.fp.read(self.sector_size)
        if not raw:
            raise _CfbError("sector out of range")
        return raw.ljust(self.sector_size, b"\x00")

    def _chain(self, start: int) -> list[int]:
        chain: list[int] = []
        seen: set[int] = set()
        sector = start
        while sector != self._END:
            if sector > self._MAX_REG or sector >= len(self.fat) or sector in seen:
                raise _CfbError("broken chain")
            seen.add(sector)
            chain.append(sector)
            sector = self.fat[sector]
            if len(chain) > self.sector_count:
                raise _CfbError("chain too long")
        return chain

    def _read_directory(self, first_dir: int) -> list[dict]:
        entries: list[dict] = []
        for sector in self._chain(first_dir):
            raw = self._sector(sector)
            for offset in range(0, self.sector_size, 128):
                entry = raw[offset:offset + 128]
                kind = entry[66]
                if kind == 0:
                    continue
                name_len = struct.unpack_from("<H", entry, 64)[0]
                name = entry[:max(0, min(name_len, 64) - 2)].decode("utf-16-le", "replace")
                start = struct.unpack_from("<I", entry, 116)[0]
                stream_size = struct.unpack_from("<Q", entry, 120)[0]
                if self.sector_size == 512:
                    stream_size &= 0xFFFFFFFF
                entries.append({"name": name, "type": kind, "start": start, "size": stream_size})
        if not entries:
            raise _CfbError("empty directory")
        return entries

    def stream_names(self) -> set[str]:
        return {entry["name"] for entry in self.entries if entry["type"] in (1, 2)}

    def read_head(self, name: str, count: int) -> bytes:
        entry = next((e for e in self.entries if e["type"] == 2 and e["name"] == name), None)
        if entry is None:
            raise _CfbError("no such stream")
        want = min(count, entry["size"])
        if entry["size"] >= self.mini_cutoff:
            data = bytearray()
            for sector in self._chain(entry["start"]):
                data += self._sector(sector)
                if len(data) >= want:
                    break
            return bytes(data[:want])
        root = self.entries[0]
        root_chain = self._chain(root["start"])
        minifat: list[int] = []
        per_sector = self.sector_size // 4
        for sector in self._chain(self.first_minifat):
            minifat.extend(struct.unpack("<%dI" % per_sector, self._sector(sector)))
        data = bytearray()
        mini = entry["start"]
        seen: set[int] = set()
        while len(data) < want:
            if mini > self._MAX_REG or mini >= len(minifat) or mini in seen:
                raise _CfbError("broken mini chain")
            seen.add(mini)
            offset = mini * 64
            index, within = divmod(offset, self.sector_size)
            if index >= len(root_chain):
                raise _CfbError("mini sector out of range")
            data += self._sector(root_chain[index])[within:within + 64]
            mini = minifat[mini]
        return bytes(data[:want])


# ---------------------------------------------------------------------------------------------
# sniff


def _ext_of(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).suffix.lstrip(".").lower()


def _zip_preflight(infos: Sequence[zipfile.ZipInfo], zip_entries: int, zip_total_bytes: int) -> list[Issue]:
    issues: list[Issue] = []
    if len(infos) > zip_entries:
        issues.append(_issue("E_ZIP_ENTRIES", f"archive has {len(infos)} entries, bound is {zip_entries}"))
    if sum(info.file_size for info in infos) > zip_total_bytes:
        issues.append(_issue("E_ZIP_TOTAL", f"declared uncompressed size exceeds {zip_total_bytes} bytes"))
    for info in infos:
        packed, size = info.compress_size, info.file_size
        if size > 10 * _MIB and (packed == 0 or size > 100 * packed):
            issues.append(_issue("E_ZIP_BOMB", "archive member has a suspicious compression ratio"))
            break
    return issues


def _check_pdf(fp: BinaryIO, size: int) -> tuple[list[str], bool]:
    """(protection reasons, corrupt)."""
    reasons: list[str] = []
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return reasons, False
    fp.seek(0)
    try:
        document = pdfium.PdfDocument(fp)
    except Exception as exc:  # pdfium reports every open failure as PdfiumError
        if getattr(exc, "err_code", None) == 4 or "password" in str(exc).lower():
            if "pdf_password" not in reasons:
                reasons.insert(0, "pdf_password")
            return reasons, False
        return reasons, True
    try:
        if pdfium.raw.FPDF_GetSecurityHandlerRevision(document) >= 0:
            reasons.append('pdf_encrypt_trailer')
        document.close()
    except Exception:
        pass
    return reasons, False


def _result(
    logical: str, root: int, size: int, sha: str, ext: str, head: bytes,
    fmt: str, route: str, reasons: list[str], issues: list[Issue],
) -> SniffResult:
    return {
        "path": logical, "root": root, "bytes": size, "sha256": sha, "ext": ext, "magic": head.hex(),
        "format": fmt, "route": route, "reasons": reasons, "issues": issues,
    }  # type: ignore[return-value]


def _analyze(
    fp: BinaryIO, size: int, sha: str, *, logical: str, root: int, ext: str,
    max_bytes: int, zip_entries: int, zip_total_bytes: int,
) -> SniffResult:
    fp.seek(0)
    head = fp.read(16)
    issues: list[Issue] = []
    reasons: list[str] = []
    too_large = size > max_bytes
    if too_large:
        issues.append(_issue("E_TOO_LARGE", f"size {size} exceeds the bound of {max_bytes} bytes"))
    if size == 0:
        issues.append(_issue("E_CORRUPT", "file is empty"))
        fmt, route, reasons = _by_extension(ext)
        return _result(logical, root, size, sha, ext, head, fmt, route, reasons, issues)

    magic = _magic_format(head)
    if magic is None:
        fmt, route, reasons = _by_extension(ext)
        return _result(logical, root, size, sha, ext, head, fmt, route, reasons, issues)

    fmt, route = magic, "NATIVE"
    if magic == "pdf":
        if not too_large:
            protection, corrupt = _check_pdf(fp, size)
            if corrupt:
                issues.append(_issue("E_CORRUPT", "PDF could not be opened"))
            if protection:
                route, reasons = "PROTECTED", protection
    elif magic == "zip":
        fp.seek(0)
        try:
            archive = zipfile.ZipFile(fp)
            infos = archive.infolist()
        except Exception:
            fmt = ext if ext in (_ZIP_FAMILY_NATIVE | _ZIP_FAMILY_LEGACY) else "zip"
            route = _zip_route(fmt)
            issues.append(_issue("E_CORRUPT", "zip central directory is unreadable"))
        else:
            fmt = _zip_format({info.orig_filename for info in infos}, ext)
            route = _zip_route(fmt)
            if not too_large:
                issues.extend(_zip_preflight(infos, zip_entries, zip_total_bytes))
            if any(info.flag_bits & 0x1 for info in infos):
                route, reasons = "PROTECTED", ["zip_flag_bit"]
    elif magic == "cfb":
        try:
            cfb = _Cfb(fp, size)
        except (_CfbError, struct.error, OSError):
            fmt, route = "cfb", "UNSUPPORTED"
            issues.append(_issue("E_CORRUPT", "CFB directory is unreadable"))
        else:
            names = cfb.stream_names()
            if {"EncryptionInfo", "EncryptedPackage"} <= names:
                fmt = ext if ext in _ENCRYPTED_OFFICE_EXTS else "cfb"
                route, reasons = "PROTECTED", ["cfb_encrypted_package"]
            elif "FileHeader" in names and ext == "hwp":
                fmt = "hwp"
                try:
                    props = cfb.read_head("FileHeader", 40)
                except OSError:
                    raise
                except (_CfbError, struct.error):
                    props = b''
                    issues.append(_issue('E_CORRUPT', 'HWP FileHeader is unreadable'))
                if len(props) < 40 and not any(i['code'] == 'E_CORRUPT' for i in issues):
                    issues.append(_issue('E_CORRUPT', 'HWP FileHeader is truncated'))
                if len(props) >= 37 and (props[36] >> 1) & 1:
                    route, reasons = "PROTECTED", ["hwp5_encrypted"]
            elif ext in ("xls", "msg"):
                fmt = ext
            elif ext in ("doc", "ppt"):
                fmt, route = ext, "LEGACY"
            else:
                fmt, route, reasons = "cfb", "UNSUPPORTED", ["unsupported_format"]
    elif magic == "rtf":
        route = "LEGACY"

    # extension disagreement: the magic of table 3.1A always wins (REQ-SNF-03)
    if ext and fmt != "cfb" and ext not in _expected_exts(fmt) and not any(i["code"] == "E_CORRUPT" for i in issues):
        issues.append(_issue("W_EXT_MISMATCH", f"extension .{ext} does not match detected format {fmt}"))
    return _result(logical, root, size, sha, ext, head, fmt, route, reasons, issues)


def sniff(
    path: str | Path,
    *,
    logical: str,
    root: int = 0,
    max_bytes: int = DEFAULT_MAX_BYTES,
    zip_entries: int = DEFAULT_ZIP_ENTRIES,
    zip_total_bytes: int = DEFAULT_ZIP_TOTAL_BYTES,
) -> SniffResult:
    ext = _ext_of(os.fspath(path))
    try:
        with open(path, "rb") as fp:
            digest = hashlib.sha256()
            size = 0
            while True:
                chunk = fp.read(_CHUNK)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
            return _analyze(
                fp, size, digest.hexdigest(), logical=logical, root=root, ext=ext,
                max_bytes=max_bytes, zip_entries=zip_entries, zip_total_bytes=zip_total_bytes)
    except OSError as exc:
        try:
            size = os.stat(path).st_size
        except OSError:
            size = 0
        message = f"file could not be read ({type(exc).__name__})"
        return _result(logical, root, size, "", ext, b"", "unknown", "UNSUPPORTED", [], [_issue("E_SNIFF_IO", message)])


# ---------------------------------------------------------------------------------------------
# streamed member reads (REQ-SNF-09)


def _check_limits(produced: int, declared: int, max_bytes: int, total_remaining: int | None) -> None:
    if produced > declared:
        raise ZipReadError("member inflates beyond its declared size", code="E_ZIP_BOMB")
    if produced > max_bytes:
        raise ZipReadError("member exceeds the byte bound", code="E_ZIP_BOMB")
    if total_remaining is not None and produced > total_remaining:
        raise ZipReadError("member exceeds the remaining archive budget", code="E_ZIP_BOMB")


def _stream_member(
    fp: BinaryIO, archive: zipfile.ZipFile, info: zipfile.ZipInfo, *, max_bytes: int, total_remaining: int | None,
) -> bytes:
    if info.flag_bits & 0x1:
        raise ZipReadError("member is encrypted", code="E_ENCRYPTED")
    declared = info.file_size
    if declared > max_bytes:
        raise ZipReadError("member exceeds the byte bound", code="E_ZIP_BOMB")
    out = bytearray()
    crc = 0
    try:
        if info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            fp.seek(info.header_offset)
            local = fp.read(30)
            if len(local) < 30 or local[:4] != b"PK\x03\x04":
                raise ZipReadError("local header is unreadable", code="E_CORRUPT")
            name_len, extra_len = struct.unpack("<HH", local[26:30])
            fp.seek(info.header_offset + 30 + name_len + extra_len)
            left = info.compress_size
            if info.compress_type == zipfile.ZIP_STORED:
                while left > 0:
                    piece = fp.read(min(_CHUNK, left))
                    if not piece:
                        raise ZipReadError("member is truncated", code="E_CORRUPT")
                    left -= len(piece)
                    out += piece
                    crc = zlib.crc32(piece, crc)
                    _check_limits(len(out), declared, max_bytes, total_remaining)
            else:
                inflater = zlib.decompressobj(-15)
                pending = b""
                while not inflater.eof:
                    if not pending:
                        if left <= 0:
                            break
                        pending = fp.read(min(_CHUNK, left))
                        if not pending:
                            raise ZipReadError("member is truncated", code="E_CORRUPT")
                        left -= len(pending)
                    piece = inflater.decompress(pending, _CHUNK)
                    pending = inflater.unconsumed_tail
                    if piece:
                        out += piece
                        crc = zlib.crc32(piece, crc)
                        _check_limits(len(out), declared, max_bytes, total_remaining)
                while not inflater.eof:
                    piece = inflater.decompress(b"", _CHUNK)
                    if not piece:
                        break
                    out += piece
                    crc = zlib.crc32(piece, crc)
                    _check_limits(len(out), declared, max_bytes, total_remaining)
                if not inflater.eof:
                    raise ZipReadError("deflate stream is truncated", code="E_CORRUPT")
            if len(out) != declared or (crc & 0xFFFFFFFF) != info.CRC:
                raise ZipReadError("member does not match its directory entry", code="E_CORRUPT")
        else:
            with archive.open(info) as handle:
                while True:
                    piece = handle.read(_CHUNK)
                    if not piece:
                        break
                    out += piece
                    _check_limits(len(out), declared, max_bytes, total_remaining)
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, EOFError) as exc:
        raise ZipReadError(f"member is unreadable ({type(exc).__name__})", code="E_CORRUPT") from None
    return bytes(out)


def read_member(
    zip_path: str | Path, name: str, *, max_bytes: int, total_remaining: int | None = None
) -> bytes:
    with open(zip_path, "rb") as fp:
        try:
            archive = zipfile.ZipFile(fp)
        except zipfile.BadZipFile:
            raise ZipReadError("zip central directory is unreadable", code="E_CORRUPT") from None
        info = next((i for i in archive.infolist() if i.orig_filename == name), None)
        if info is None:
            raise KeyError(name)
        return _stream_member(fp, archive, info, max_bytes=max_bytes, total_remaining=total_remaining)


def read_member_bytes(
    data: bytes, name: str, *, max_bytes: int = DEFAULT_MAX_BYTES, total_remaining: int | None = None
) -> bytes:
    """Like :func:`read_member` for an in-memory archive (used by Render for Office media fallback)."""
    fp = io.BytesIO(data)
    try:
        archive = zipfile.ZipFile(fp)
    except zipfile.BadZipFile:
        raise ZipReadError("zip central directory is unreadable", code="E_CORRUPT") from None
    info = next((i for i in archive.infolist() if i.orig_filename == name), None)
    if info is None:
        raise KeyError(name)
    return _stream_member(fp, archive, info, max_bytes=max_bytes, total_remaining=total_remaining)


# ---------------------------------------------------------------------------------------------
# containers


def _unsafe_name(name: str) -> bool:
    if name.startswith(("/", "\\")) or "\\" in name or _WINDOWS_DRIVE.match(name):
        return True
    return ".." in name.split("/")


class _Expansion:
    def __init__(self, *, max_bytes: int, zip_depth: int, zip_entries: int, zip_total_bytes: int, root: int) -> None:
        self.max_bytes = max_bytes
        self.zip_depth = zip_depth
        self.zip_entries = zip_entries
        self.zip_total_bytes = zip_total_bytes
        self.root = root
        self.entries = 0
        self.total = 0
        self.issues: list[Issue] = []
        self.members: list[Member] = []

    def sniff_bytes(self, data: bytes, logical: str, ext: str) -> SniffResult:
        return _analyze(
            io.BytesIO(data), len(data), hashlib.sha256(data).hexdigest(), logical=logical, root=self.root, ext=ext,
            max_bytes=self.max_bytes, zip_entries=self.zip_entries, zip_total_bytes=self.zip_total_bytes)

    def stub(self, logical: str, ext: str, declared: int, issues: list[Issue], route: str | None = None,
             reasons: list[str] | None = None) -> SniffResult:
        fmt, ext_route, ext_reasons = _by_extension(ext)
        return _result(
            logical, self.root, declared, "", ext, b"", fmt, route or ext_route,
            list(reasons) if reasons is not None else ext_reasons, issues)

    def expand(self, fp: BinaryIO, prefix: str, depth: int) -> bool:
        """Append members of one archive; False when a container-level bound was exceeded."""
        if depth > self.zip_depth:
            self.issues.append(_issue('E_ZIP_DEPTH', 'Archive exceeds the depth bound'))
            return False
        fp.seek(0)
        try:
            archive = zipfile.ZipFile(fp)
            infos = archive.infolist()
        except Exception:
            self.issues.append(_issue("E_CORRUPT", "zip central directory is unreadable"))
            return False
        self.entries += len(infos)
        if self.entries > self.zip_entries:
            self.issues.append(_issue("E_ZIP_ENTRIES", f"archives hold more than {self.zip_entries} entries"))
            return False
        total_before = self.total
        self.total += sum(info.file_size for info in infos)
        if self.total > self.zip_total_bytes:
            self.issues.append(_issue("E_ZIP_TOTAL", f"declared uncompressed size exceeds {self.zip_total_bytes} bytes"))
            return False
        for info in infos:
            packed, size = info.compress_size, info.file_size
            if size > 10 * _MIB and (packed == 0 or size > 100 * packed):
                self.issues.append(_issue("E_ZIP_BOMB", "archive member has a suspicious compression ratio"))
                return False
        seen_folded: set[str] = set()
        for info in infos:
            name = info.orig_filename
            folded = name.casefold()
            duplicate = folded in seen_folded
            seen_folded.add(folded)
            if info.is_dir():
                continue
            logical = f"{prefix}/{name}"
            ext = _ext_of(name)
            if info.flag_bits & 0x1:
                sniffed = self.stub(logical, ext, info.file_size, [], route="PROTECTED", reasons=["zip_flag_bit"])
                data = b""
            elif info.file_size > self.max_bytes:
                sniffed = self.stub(logical, ext, info.file_size, [
                    _issue("E_TOO_LARGE", f"size {info.file_size} exceeds the bound of {self.max_bytes} bytes")])
                data = b""
            else:
                try:
                    data = _stream_member(
                        fp, archive, info, max_bytes=self.max_bytes, total_remaining=self.zip_total_bytes - total_before)
                except ZipReadError as exc:
                    data = b""
                    sniffed = self.stub(logical, ext, info.file_size, [_issue(exc.code, str(exc))])
                else:
                    sniffed = self.sniff_bytes(data, logical, ext)
            if duplicate or _unsafe_name(name):
                sniffed["issues"].append(_issue("E_ZIP_PATH", "member name is unsafe or duplicates an earlier member"))
            self.members.append({"logical": logical, "member": name, "depth": depth, "data": data, "sniff": sniffed})
            blocking = {"E_CORRUPT", "E_TOO_LARGE", "E_ZIP_ENTRIES", "E_ZIP_TOTAL", "E_ZIP_BOMB", "E_ZIP_PATH", "E_ENCRYPTED"}
            package_bounds = [i for i in sniffed['issues'] if i['code'] in {'E_ZIP_ENTRIES', 'E_ZIP_TOTAL', 'E_ZIP_BOMB'}]
            if sniffed['format'] in _ZIP_FAMILY_NATIVE | _ZIP_FAMILY_LEGACY and package_bounds:
                self.issues.extend(package_bounds)
                return False
            if sniffed['format'] in _ZIP_FAMILY_NATIVE | _ZIP_FAMILY_LEGACY and not any(i['code'] in blocking for i in sniffed['issues']):
                with zipfile.ZipFile(io.BytesIO(data)) as package:
                    internal = package.infolist()
                self.entries += len(internal)
                self.total += sum(item.file_size for item in internal)
                code = 'E_ZIP_ENTRIES' if self.entries > self.zip_entries else 'E_ZIP_TOTAL' if self.total > self.zip_total_bytes else None
                if code:
                    problem = _issue(code, 'Nested package exceeds the cumulative archive budget')
                    sniffed['issues'].append(problem)
                    self.issues.append(problem)
                    return False
            if sniffed["route"] == "CONTAINER" and not any(i["code"] in blocking for i in sniffed["issues"]):
                if depth + 1 > self.zip_depth:
                    sniffed["issues"].append(_issue("E_ZIP_DEPTH", f"nested archive exceeds depth {self.zip_depth}"))
                elif not self.expand(io.BytesIO(data), logical, depth + 1):
                    return False
        return True


def expand_container(
    source: str | Path | bytes,
    *,
    logical: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    zip_depth: int = DEFAULT_ZIP_DEPTH,
    zip_entries: int = DEFAULT_ZIP_ENTRIES,
    zip_total_bytes: int = DEFAULT_ZIP_TOTAL_BYTES,
    root: int = 0,
) -> Container:
    state = _Expansion(
        max_bytes=max_bytes, zip_depth=zip_depth, zip_entries=zip_entries, zip_total_bytes=zip_total_bytes, root=root)
    try:
        if isinstance(source, (bytes, bytearray)):
            ok = state.expand(io.BytesIO(bytes(source)), logical, 1)
        else:
            with open(source, "rb") as fp:
                ok = state.expand(fp, logical, 1)
    except OSError as exc:
        state.issues.append(_issue("E_SNIFF_IO", f"archive could not be read ({type(exc).__name__})"))
        ok = False
    # container-level bounds are evaluated cumulatively; nothing is processed once one trips
    if not ok:
        for member in state.members:
            member['sniff']['issues'].extend(i for i in state.issues if i not in member['sniff']['issues'])
    return {"logical": logical, "issues": state.issues, "members": state.members}
