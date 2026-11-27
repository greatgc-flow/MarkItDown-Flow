"""Local-only conversion and independent, read-only inspection."""
import csv
import hashlib
import io
import json
import os
import tempfile
import unicodedata
import uuid
from collections import Counter
from pathlib import Path

from . import classify, convert, core_guard, orchestrate, sniff_io, triage
from .sniff_pure import OFFICE, RASTERS

LIMIT = sniff_io.DEFAULT_MAX_BYTES
POLICY = "strict-v1"
SCHEMA = 2
BARRIERS = {
    "E_SNIFF_IO": "read_failed", "E_CORRUPT": "corrupt", "E_TOO_LARGE": "limit",
    "E_ENCRYPTED": "protected", "E_OUTPUT_COLLISION": "edited_output",
    "E_ZIP_PATH": "unsupported", "E_ZIP_BOMB": "limit", "E_ZIP_DEPTH": "limit",
    "E_ZIP_ENTRIES": "limit", "E_ZIP_TOTAL": "limit",
}
ROUTES = {"PROTECTED": "protected", "LEGACY": "legacy", "UNSUPPORTED": "unsupported"}
FAILURES = {"read_failed", "source_changed", "write_failed", "edited_output", "conversion_failed"}


def barrier(sniff):
    if sniff["route"] == "PROTECTED":
        return "protected"
    for issue in sniff["issues"]:
        if issue["code"].startswith("E_"):
            return BARRIERS.get(issue["code"], "undetermined")
    return ROUTES.get(sniff["route"])


def digest(path):
    with path.open("rb") as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def publish(base, relative, payload):
    """Install a fully written sibling with an exclusive claim. Preserve user edits."""
    base = base.absolute()
    dest = base / relative
    if relative.is_absolute() or ".." in relative.parts or dest.resolve() != dest:
        return "write_failed", None
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dest.parent, prefix=".mdflow-", delete=False) as staged:
            temp = Path(staged.name)
            try:
                staged.write(payload)
                staged.flush()
                os.fsync(staged.fileno())
            except BaseException:
                staged.close()
                temp.unlink(missing_ok=True)
                raise
        try:
            os.link(temp, dest)
        except FileExistsError:
            if dest.is_symlink() or not dest.is_file() or digest(dest) != hashlib.sha256(payload).hexdigest():
                return "edited_output", None
            return "reused", str(dest)
        finally:
            temp.unlink(missing_ok=True)
    except OSError:
        return "write_failed", None
    return "saved", str(dest)


def plain(data, fmt):
    try:
        encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        body = data.decode(encoding)
        if any(ord(c) < 32 and c not in "\n\r\t\f" for c in body):
            return "undetermined", None, {}
        if not body.strip():
            return "empty", None, {}
        if fmt == "json":
            json.loads(body)
            # A fence longer than any run in the input always closes correctly.
            import re
            fence = chr(96) * max(3, 1 + max(map(len, re.findall(chr(96) + "+", body)), default=0))
            body = f"{fence}json\n{body.rstrip()}\n{fence}"
        if fmt in {"csv", "tsv"}:
            rows = csv.reader(io.StringIO(body, newline=""), delimiter="," if fmt == "csv" else "\t", strict=True)
            result = []
            columns = None
            for row in rows:
                if columns is None:
                    columns = len(row)
                if not columns or len(row) != columns:
                    return "undetermined", None, {}
                cells = [s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                          .replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "<br>")
                          .replace("\n", "<br>").replace("\r", "<br>") for s in row]
                result.append("| " + " | ".join(cells) + " |")
                if len(result) == 1:
                    result.append("| " + " | ".join(["---"] * columns) + " |")
            return "direct", "\n".join(result), {"rows": len(result) - 1, "columns": columns}
        return "direct", body, {"lines": len(body.splitlines())}
    except (UnicodeError, RecursionError):
        return "undetermined", None, {}
    except (ValueError, csv.Error):
        return "corrupt", None, {}


def inspect_source(data, sniff, mode, work):
    fmt = sniff["format"]
    if fmt in {"txt", "log", "csv", "tsv", "json"}:
        return plain(data, fmt)
    if fmt == "pdf":
        with core_guard.quiet_output():
            from markitdown.document_inspection import inspect_pdf
            facts = inspect_pdf(data, measure=mode == "preview", include_text=mode == "extract-text",
                                stop_at_ocr=mode == "run")
        return facts["reason"], None, facts
    if fmt not in OFFICE | RASTERS:
        return "undetermined", None, {}
    snapshot = work / ("source." + fmt)
    snapshot.write_bytes(data)
    evidence = triage.run_triage(snapshot, sniff)
    decision = classify.classify(dict(sniff, issues=sniff["issues"] + evidence["issues"]), evidence["report"])
    if evidence["report"] is None:
        return "undetermined", None, {}
    facts = dict(evidence["report"].get("summary", {}))
    if evidence["report"].get("issues"):
        return "undetermined", None, facts
    if decision["need"] in {"PARTIAL", "FULL"}:
        confirmed = any(c["priority"] == "normal" for c in decision["candidates_unique"])
        return ("ocr_required" if confirmed else "undetermined"), None, facts
    if (fmt in OFFICE and decision["coverage_state"] == "complete" and decision["need"] == "NONE"
            and not decision["issues"] and not facts.get("image_occurrences")):
        return "direct", None, facts
    return "undetermined", None, facts


def partial_body(facts, source_hash):
    pages = facts.get("pages", [])
    if not facts.get("complete") or not any(p.get("text", "").strip() for p in pages):
        return None
    lines = ["# Partial text extraction", "", f"Source SHA-256: {source_hash}",
             f"Policy: {POLICY} · Pages inspected: {len(pages)}", ""]
    for page in pages:
        lines.extend([f"## Page {page['number']}", ""])
        if page.get("text"):
            lines.extend([page["text"], ""])
        if page["role"] in {"mixed", "ocr", "undetermined"}:
            lines.extend(["[Visual or unresolved content omitted.]", ""])
    return "\n".join(lines)


def process(data, sniff, mode, base, relative, original, original_hash, expected=None):
    source = {"path": str(original), "relativePath": sniff["path"], "sha256": sniff["sha256"],
              "originalSha256": original_hash, "root": sniff["root"], "format": sniff["format"]}
    row = {"kind": "file", "source": source, "mode": mode}
    reason = barrier(sniff)
    if expected and expected != sniff["sha256"]:
        reason = "source_changed"
    facts = {}
    body = None
    with tempfile.TemporaryDirectory(prefix="mdflow-inspect-") as folder:
        work = Path(folder)
        if not reason:
            try:
                reason, body, facts = inspect_source(data, sniff, mode, work)
            except (ValueError, RuntimeError):
                reason = "undetermined"
        row.update(reason=reason, outcome="eligible" if reason == "direct" and mode == "preview"
                   else "complete" if reason == "direct" and mode == "run"
                   else "failed" if reason in FAILURES else "excluded")
        if mode == "extract-text":
            if reason == "direct":
                row.update(outcome="eligible", action="use_standard_conversion")
            elif reason == "ocr_required" and sniff["format"] == "pdf":
                body = partial_body(facts, sniff["sha256"])
                row["action"] = "no_usable_text" if facts.get("complete") else "limited"
            else:
                body = None
                row["action"] = "unavailable"
        if mode == "preview":
            row["inspection"] = facts
            return row
        partial = mode == "extract-text" and reason == "ocr_required" and bool(body)
        if not partial and not (mode == "run" and reason == "direct"):
            return row
        if body is None:
            result = convert.convert_source(data, sniff=sniff, action="convert_only", run_temp=work)
            if result["issues"] or result["media"] or not result["body"].strip():
                row.update(outcome="failed", reason="conversion_failed")
                return row
            body = result["body"]
        if original.is_symlink() or digest(original) != original_hash:
            row.update(outcome="failed", reason="source_changed")
            return row
        dest = Path("Partial" if partial else "Complete") / relative
        dest = dest.with_name(dest.name + (".text-only.md" if partial else ".md"))
        status, output = publish(base, dest, (body.rstrip("\r\n") + "\n").encode("utf-8"))
        row["action"] = status
        if output:
            row["output"] = output
        elif not partial:
            row.update(outcome="failed", reason=status)
    return row


def run(paths, *, mode, out, emit, expected=None, exclude=(), member=None):
    run_id = str(uuid.uuid4())
    common = dict(schema=SCHEMA, policy=POLICY, mode=mode, run_id=run_id)
    emit(dict(kind="header", **common))
    found = sniff_io.discover(paths, exclude=[*(exclude or ()), *([out] if out else [])])
    counts = Counter()
    errors = 0
    seen = set()
    for skipped in found["skipped"]:
        emit(dict(kind="skip", **skipped))
    for entry in found["files"]:
        path = Path(entry["path"])
        sn = sniff_io.sniff(path, logical=entry["logical"], root=entry["root"])
        original_hash = sn["sha256"]
        try:
            data = b"" if barrier(sn) else orchestrate._source_bytes(path, sn, LIMIT)
            items = [(sn, data)]
            if sn["route"] == "CONTAINER" and not barrier(sn):
                expanded = sniff_io.expand_container(data, logical=sn["path"], root=sn["root"])
                if expanded["issues"] or not expanded["members"]:
                    sn["issues"] += expanded["issues"]
                    items = [(dict(sn, route="UNSUPPORTED"), b"")]
                else:
                    items = [(m["sniff"], m["data"]) for m in expanded["members"]
                             if m["sniff"]["route"] != "CONTAINER" or barrier(m["sniff"])]
                    emit(dict(kind="container", path=sn["path"], members=len(items)))
            if member:
                selected = [(s, d) for s, d in items if s["path"] == sn["path"] + "/" + member]
                if len(selected) != 1:
                    raise OSError("Selected member disappeared")
                items = selected
            for item, payload in items:
                root = Path(paths[entry["root"]]).absolute()
                folder = root if root.is_dir() else root.parent
                alias = (folder.name or "root") + "-" + hashlib.sha256(os.fsencode(str(folder))).hexdigest()[:12]
                relative = Path(alias, item["path"])
                key = unicodedata.normalize("NFC", str(relative)).casefold()
                if key in seen:
                    item["issues"].append({"code": "E_OUTPUT_COLLISION"})
                seen.add(key)
                try:
                    row = process(payload, item, mode, out, relative, path, original_hash, expected)
                except OSError:
                    row = dict(kind="file", reason="read_failed", outcome="failed",
                               source=dict(path=str(path), relativePath=item["path"], sha256=item["sha256"]))
                row["source"]["originalRelative"] = sn["path"]
                row["source"]["member"] = (item["path"][len(sn["path"]) + 1:]
                                           if item["path"] != sn["path"] else None)
                counts[row["outcome"]] += 1
                errors += row["outcome"] == "failed" or row.get("action") in FAILURES
                emit(row)
        except OSError:
            counts["failed"] += 1
            errors += 1
            emit(dict(kind="file", reason="read_failed", outcome="failed",
                      source=dict(path=str(path), relativePath=sn["path"], sha256=original_hash)))
    status = 2 if errors else 0
    emit(dict(kind="footer", counts=dict(counts), files=sum(counts.values()), exit=status, **common))
    return status
