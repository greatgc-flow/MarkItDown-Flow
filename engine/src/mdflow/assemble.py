"""PURE assembly, provider-text normalization and exit decisions."""
import json
import posixpath
import re
from .contracts import EXIT_CODE_MAP, STARTUP_EXIT_CODE_MAP, EXIT_PRECEDENCE
from .hashing import sha256

_ANCHOR = re.compile(r"^<!-- mdflow:page ([1-9]\d*) -->[ \t]*(?:\n|$)", re.M)
_LINK = re.compile(r"!?\[[^\]\n]*\]\(\s*<?(media/[^<>\s)]+)>?(?:\s+[^)]*)?\)")
_RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", re.I)


def _linked(line: str, units: list) -> list:
    linked = []
    for match in _LINK.finditer(line):
        target = match[1]
        stem = posixpath.splitext(posixpath.basename(target))[0]
        extension = posixpath.splitext(target)[1].casefold()
        for unit in units:
            media_file = unit.get("media_file")
            if not media_file or unit["kind"] != "media":
                continue
            media_stem = posixpath.splitext(posixpath.basename(media_file))[0]
            if stem == media_stem and extension == posixpath.splitext(media_file)[1].casefold() and unit["source_id"] not in linked:
                linked.append(unit["source_id"])
    return linked


def _entry(unit: dict, entries: dict) -> dict | None:
    direct = entries.get(unit["source_id"])
    if direct is not None:
        return direct
    identity = unit.get("key_id")
    if identity is not None:
        return entries.get(identity)
    # The IO orchestrator may supply entries keyed by the normative ledger key_id.
    matches = [e for e in entries.values() if isinstance(e, dict)
               and e.get("key", {}).get("raster_sha256") == unit.get("raster_sha256")
               and e.get("key", {}).get("dpi") == unit.get("dpi")]
    return matches[0] if len(matches) == 1 else None


def _block(unit: dict, entry: dict | None, meta: dict) -> str:
    identity = unit["source_id"]
    if unit["status"] in {"eligible", "cached"} and entry and entry.get("status") == "ok":
        provider, model = meta.get("provider", "none"), meta.get("model", "")
        at = entry["created"]
        attributes = dict(unit=identity, key=entry["key_id"][:16], provider=provider, model=model,
                          prompt=meta.get("prompt_version", "p1"), dpi=str(unit["dpi"]), at=at)
        comment = "<!-- mdflow:ocr " + " ".join(f'{name}="{esc_attr(value)}"' for name, value in attributes.items()) + " -->"
        heading_id = ("media " if unit["kind"] == "media" else "") + esc_head(identity)
        heading = f"## OCR {heading_id} ({esc_head(provider)}, {esc_head(model)}, {at[:10]})"
        return comment + "\n" + heading + "\n" + esc_text(entry["text"]) + "\n<!-- /mdflow:ocr -->"
    statuses = {"skipped_low_priority": "low_priority", "oversize": "oversize",
                "render_failed": "render_failed", "unsupported_media_format": "unsupported_media_format"}
    reason = statuses.get(unit["status"], meta.get("pending_reason", "no_provider"))
    if unit["status"] in {"eligible", "cached"} and entry and entry.get("status") == "failed":
        reason = "provider_failed:" + entry["error"]["code"]
    return f'<!-- mdflow:pending unit="{esc_attr(identity)}" reason="{esc_attr(reason)}" -->'


def assemble(base_body: str, units: list, ledger_entries: dict,
             meta: dict) -> tuple[str, dict]:
    placements = {u["source_id"]: 0 for u in units}
    by_id = {u["source_id"]: u for u in units}
    entries = {u["source_id"]: _entry(u, ledger_entries) for u in units}

    def block(identity):
        placements[identity] += 1
        return _block(by_id[identity], entries[identity], meta)

    fmt = meta["format"]
    if fmt == "pdf" or fmt in {"png", "jpeg", "gif", "bmp", "tiff", "webp"}:
        anchors = list(_ANCHOR.finditer(base_body))
        page_text = {}
        for i, anchor in enumerate(anchors):
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(base_body)
            page_text[int(anchor[1])] = base_body[anchor.end():end].rstrip("\n")
        if not anchors and base_body:
            page_text[1] = base_body.rstrip("\n")
        total = meta.get("pages_total") if fmt == "pdf" else meta.get("frames_total")
        if total is None:
            total = max([0, *page_text, *[u["page"] for u in units if u.get("page") is not None]])
        sections = []
        for number in range(1, total + 1):
            section = f"<!-- mdflow:page {number} -->"
            if page_text.get(number):
                section += "\n" + page_text[number]
            blocks = [block(u["source_id"]) for u in units if u["kind"] == "page" and u["page"] == number]
            if blocks:
                section += ("\n\n" if page_text.get(number) else "\n") + "\n\n".join(blocks)
            sections.append(section)
        body = "\n\n".join(sections) + ("\n" if sections else "")
    else:
        parts = []
        for line in base_body.splitlines(keepends=True):
            parts.append(line)
            linked = _linked(line, units)
            if linked:
                if not line.endswith("\n"):
                    parts.append("\n")
                parts.append("\n" + "\n\n".join(block(identity) for identity in linked) + "\n\n")
        body = "".join(parts)
        unmapped = sorted((u for u in units if u["kind"] == "media" and not placements[u["source_id"]]), key=lambda u: u["source_id"])
        if unmapped:
            separator = "" if not body or body.endswith("\n\n") else "\n" if body.endswith("\n") else "\n\n"
            body += separator + "## OCR media (unmapped)\n\n" + "\n\n".join(block(u["source_id"]) for u in unmapped) + "\n"
    counts = dict(total=len(units), done=0, pending=0, failed=0)
    for unit in units:
        e = entries[unit["source_id"]]
        outcome = e.get("status") if e and unit["status"] in {"eligible", "cached"} else None
        counts["done" if outcome == "ok" else "failed" if outcome == "failed" else "pending"] += 1
    header = dict(mdflow=2)
    for name in ("source", "sha256", "bytes", "format", "route", "need", "label", "triage_decision", "coverage_state"):
        header[name] = meta[name]
    if meta.get('fidelity') == 'DERIVED':
        for name in ('fidelity', 'original_sha256', 'derived_sha256'):
            header[name] = meta[name]
    header["units"] = counts
    if units:
        for name in ("provider", "model", "prompt_version"):
            header[name] = meta[name]
    if fmt == "pdf":
        header["dpi"] = meta.get("dpi", 200)
    tools = {name: meta["tools"][name] for name in ("mdflow", "markitdown-gc", "pypdfium2", "pillow", "exiftool")
             if name in meta["tools"]}
    if meta.get('fidelity') == 'DERIVED':
        tools['LibreOffice'] = meta['version']
    header.update(tools=tools, generated=meta["now"], content_sha256=sha256(body.encode("utf-8")))

    def scalar(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)

    def yaml_value(value):
        if isinstance(value, dict):
            return "{" + ", ".join(name + ": " + scalar(item) for name, item in value.items()) + "}"
        return scalar(value)

    frontmatter = "---\n" + "".join(name + ": " + yaml_value(value) + "\n" for name, value in header.items()) + "---\n"
    return frontmatter + body, placements


def output_path(logical_path: str) -> str:
    parts = logical_path.split("/")
    return "/".join(("_" if _RESERVED.fullmatch(part.split(".", 1)[0]) else "") + part for part in parts) + ".md"


def media_issues(base_body: str, units: list) -> list[dict]:
    """PURE warning derivation; assembly inputs are never mutated."""
    seen = {identity for line in base_body.splitlines() for identity in _linked(line, units)}
    return [dict(code="W_MEDIA_UNMAPPED", message="Media has no matching body link.")
            for unit in units if unit["kind"] == "media" and unit["source_id"] not in seen]


def esc_text(text: str) -> str:
    return text.replace("<!--", "<!- -").replace("-->", "-- >")


def esc_attr(text: str) -> str:
    return esc_text(text).replace('"', "_").replace("--", "__").replace("\n", " ")


def esc_head(text: str) -> str:
    return esc_text(text).replace("\n", " ")


def postprocess_text(text: str) -> tuple[str, list]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    last = len(lines) - 1
    while last >= 0 and lines[last] == "":
        last -= 1
    if lines and re.fullmatch(r"```[A-Za-z0-9_-]*", lines[0]) and last > 0 and lines[last] == "```":
        lines = lines[1:last] + lines[last + 1:]
    lines = [line.rstrip() for line in lines]
    while lines and not lines[-1]:
        lines.pop()
    text = "\n".join(lines)
    if len(text) > 200000:
        return text[:200000] + "\n<!-- mdflow:truncated -->", [dict(code="W_OUTPUT_TRUNCATED", message="Provider text exceeded 200000 characters.")]
    return text, []


def _parse_output(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("Missing generated frontmatter")
    frontmatter, body = text[4:].split("---\n", 1)
    header = {}
    for line in frontmatter.splitlines():
        name, separator, value = line.partition(": ")
        if not separator or name in header:
            raise ValueError("Invalid generated frontmatter")
        if value.startswith("{"):
            value = re.sub(r'([{,]\s*)([A-Za-z0-9_-]+)\s*:', r'\1"\2":', value)
        header[name] = json.loads(value)
    return header, body


def publication_decision(existing: str, new: str, *, force: bool = False) -> dict:
    """Return {write, issues}; caller owns filesystem access."""
    if force:
        return dict(write=True, issues=[])
    try:
        old_header, old_body = _parse_output(existing)
        new_header, _ = _parse_output(new)
        old_hash = sha256(old_body.encode("utf-8"))
        if old_hash != old_header["content_sha256"]:
            raise ValueError("Output body was edited")
    except (ValueError, KeyError, TypeError):
        return dict(write=False, issues=[dict(code="W_OUTPUT_EDITED", message="Existing output was edited; use force to replace it.")])
    comparable = lambda h: {k: v for k, v in h.items() if k not in {"generated", "tools"}}
    identical = old_hash == new_header["content_sha256"] and comparable(old_header) == comparable(new_header)
    return dict(write=not identical, issues=[])


def exit_code(codes: list[str], *, startup: bool = False,
              cancelled: bool = False) -> int:
    if cancelled:
        return 130
    contributions = {STARTUP_EXIT_CODE_MAP.get(code, EXIT_CODE_MAP[code]) if startup else EXIT_CODE_MAP[code] for code in codes}
    return next((code for code in EXIT_PRECEDENCE if code in contributions), 0)
