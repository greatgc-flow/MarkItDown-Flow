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


def expected_exts(fmt: str) -> frozenset[str]:
    return {'jpeg': frozenset({'jpg','jpeg'}), 'tiff': frozenset({'tif','tiff'})}.get(fmt, frozenset({fmt}))


def by_extension(ext: str) -> tuple[str, str, list[str]]:
    if ext in G2A | (G2B - {'epub', 'msg', 'xls'}):
        return ext, 'NATIVE', []
    if ext in {'pages', 'key', 'numbers'}:
        return ext, 'LEGACY', []
    return ext or 'unknown', 'UNSUPPORTED', ['media_out_of_scope' if ext in MEDIA else 'unsupported_format']


def magic_format(header: bytes) -> str | None:
    signatures = ((b'%PDF-', 'pdf'), (b'PK\x03\x04', 'zip'),
        (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 'cfb'), (b'\x89PNG\r\n\x1a\n', 'png'),
        (b'\xff\xd8\xff', 'jpeg'), (b'GIF87a', 'gif'), (b'GIF89a', 'gif'), (b'BM', 'bmp'),
        (b'II*\0', 'tiff'), (b'MM\0*', 'tiff'), (b'II+\0', 'tiff'), (b'MM\0+', 'tiff'), (b'{\\rtf', 'rtf'))
    for signature, fmt in signatures:
        if header.startswith(signature): return fmt
    return 'webp' if header.startswith(b'RIFF') and header[8:12] == b'WEBP' else None


def zip_format(names: set[str], ext: str) -> str:
    for marker, fmt in (('word/document.xml', 'docx'), ('ppt/presentation.xml', 'pptx'),
                        ('xl/workbook.xml', 'xlsx'), ('Contents/content.hpf', 'hwpx')):
        if marker in names: return fmt
    if 'META-INF/container.xml' in names and ext == 'epub': return 'epub'
    if 'META-INF/manifest.xml' in names and ext in {'odt', 'odp', 'ods'}: return ext
    return 'zip'


def zip_route(fmt: str) -> str:
    return 'LEGACY' if fmt in {'odt', 'odp', 'ods'} else 'CONTAINER' if fmt == 'zip' else 'NATIVE'


def detect_format(header: bytes, ext: str, *, members: tuple = (),
                  streams: tuple = (), encrypted: bool = False) -> dict:
    ext = ext.lower().lstrip(".")
    magic = magic_format(header) or 'unknown'
    fmt = magic if magic != 'unknown' else by_extension(ext)[0]
    if magic == 'zip':
        fmt = zip_format(set(members), ext)
    if magic == "cfb":
        if {"EncryptionInfo", "EncryptedPackage"} <= set(streams):
            encrypted = True
            fmt = ext if ext in {"docx", "xlsx", "pptx"} else "cfb"
        elif "FileHeader" in streams and ext == "hwp":
            fmt = "hwp"
        elif ext in {"xls", "msg", "doc", "ppt"}:
            fmt = ext
    route = 'PROTECTED' if encrypted else by_extension(ext)[1] if magic == 'unknown' else _route(fmt)
    reasons, issues = [], []
    if route == "UNSUPPORTED":
        reasons.append("media_out_of_scope" if ext in MEDIA else "unsupported_format")
    if encrypted:
        reasons.append("encrypted")
    if magic != "unknown" and ext and ext not in expected_exts(fmt):
        issues.append(dict(code="W_EXT_MISMATCH", message="File signature differs from its extension."))
    if not header:
        issues.append(dict(code="E_CORRUPT", message="Empty input."))
    return dict(ext=ext, magic=magic, format=fmt or "unknown", route=route, reasons=reasons, issues=issues)


def sniff_result(data: bytes, path: str, root: str, detection: dict) -> dict:
    return dict(path=path, root=root, bytes=len(data), sha256=sha256(data),
                **{k: detection[k] for k in ("ext", "magic", "format", "route")},
                reasons=list(detection.get("reasons", [])), issues=[dict(i) for i in detection.get("issues", [])])
