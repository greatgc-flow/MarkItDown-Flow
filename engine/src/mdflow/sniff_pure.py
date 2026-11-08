"""PURE sniff decisions; structural evidence is supplied by the IO stage."""
from .hashing import sha256

RASTERS = frozenset("png jpeg gif bmp tiff webp".split())
OFFICE = frozenset("docx pptx xlsx hwp hwpx".split())
G2A = frozenset("txt log".split())
G2B = frozenset("csv tsv json md markdown xml html htm ipynb epub msg xls".split())
LEGACY = frozenset("doc ppt rtf odt odp ods pages key numbers".split())
MEDIA = frozenset("mp3 wav m4a flac ogg mp4 mov mkv avi webm".split())


def _route(fmt: str) -> str:
    if fmt in RASTERS | OFFICE | G2A | G2B | {"pdf"}:
        return "NATIVE"
    if fmt == "zip":
        return "CONTAINER"
    return "LEGACY" if fmt in LEGACY else "UNSUPPORTED"


def detect_format(header: bytes, ext: str, *, members: tuple = (),
                  streams: tuple = (), encrypted: bool = False) -> dict:
    ext = ext.lower().lstrip(".")
    normalized = {"jpg": "jpeg", "jpe": "jpeg", "tif": "tiff"}.get(ext, ext)
    magic, fmt = "unknown", normalized
    signatures = ((b"%PDF-", "pdf"), (b"\x89PNG\r\n\x1a\n", "png"),
        (b"\xff\xd8\xff", "jpeg"), (b"GIF87a", "gif"), (b"GIF89a", "gif"),
        (b"BM", "bmp"), (b"II*\0", "tiff"), (b"MM\0*", "tiff"),
        (b"II+\0", "tiff"), (b"MM\0+", "tiff"), (b"{\\rtf", "rtf"),
        (b"PK\x03\x04", "zip"), (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "cfb"))
    for signature, name in signatures:
        if header.startswith(signature):
            magic = fmt = name
            break
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        magic = fmt = "webp"
    if magic == "zip":
        for marker, name in (("word/document.xml", "docx"), ("ppt/presentation.xml", "pptx"),
                             ("xl/workbook.xml", "xlsx"), ("Contents/content.hpf", "hwpx")):
            if marker in members:
                fmt = name
                break
        if fmt == "zip" and "META-INF/container.xml" in members and ext == "epub":
            fmt = "epub"
        if fmt == "zip" and "META-INF/manifest.xml" in members and ext in {"odt", "odp", "ods"}:
            fmt = ext
    if magic == "cfb":
        if {"EncryptionInfo", "EncryptedPackage"} <= set(streams):
            encrypted = True
            fmt = ext if ext in {"docx", "xlsx", "pptx"} else "cfb"
        elif "FileHeader" in streams and ext == "hwp":
            fmt = "hwp"
        elif ext in {"xls", "msg", "doc", "ppt"}:
            fmt = ext
    route = "PROTECTED" if encrypted else _route(fmt)
    reasons, issues = [], []
    if route == "UNSUPPORTED":
        reasons.append("media_out_of_scope" if ext in MEDIA else "unsupported_format")
    if encrypted:
        reasons.append("encrypted")
    if magic != "unknown" and fmt != normalized:
        issues.append(dict(code="W_EXT_MISMATCH", message="File signature differs from its extension."))
    if not header:
        issues.append(dict(code="E_CORRUPT", message="Empty input."))
    return dict(ext=ext, magic=magic, format=fmt or "unknown", route=route, reasons=reasons, issues=issues)


def sniff_result(data: bytes, path: str, root: str, detection: dict) -> dict:
    return dict(path=path, root=root, bytes=len(data), sha256=sha256(data),
                **{k: detection[k] for k in ("ext", "magic", "format", "route")},
                reasons=list(detection.get("reasons", [])), issues=[dict(i) for i in detection.get("issues", [])])
