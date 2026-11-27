"""Explicit actions on a selected, digest-bound original or archive member."""
import hashlib
import os
from pathlib import Path

from . import exiftool, orchestrate, sniff_io
from .strict_workflow import LIMIT, barrier, digest, publish

PHOTO_FIELDS = ("DateTimeOriginal", "ImageWidth", "ImageHeight", "Make", "Model",
                "GPSLatitude", "GPSLongitude", "Artist", "SerialNumber")


def selected(path, sha, original_sha, member):
    original = sniff_io.sniff(path, logical=path.name)
    if path.is_symlink() or original["sha256"] != original_sha:
        raise ValueError("source_changed")
    data = orchestrate._source_bytes(path, original, LIMIT)
    if member:
        if original["route"] != "CONTAINER":
            raise ValueError("unsupported")
        archive = sniff_io.expand_container(data, logical=path.name)
        matches = [m for m in archive["members"] if m["logical"] == path.name + "/" + member]
        if archive["issues"] or len(matches) != 1 or barrier(matches[0]["sniff"]):
            raise ValueError("unsupported")
        data = matches[0]["data"]
        sniff = matches[0]["sniff"]
    else:
        sniff = original
    if hashlib.sha256(data).hexdigest() != sha:
        raise ValueError("source_changed")
    return data, sniff


def action(args):
    path = args.path.absolute()
    try:
        data, sniff = selected(path, args.sha256, args.original_sha256, args.member)
        if args.command_name == "handoff-copy":
            relative = Path(args.relative or path.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("unsupported")
            target = relative / args.member if args.member else relative
            if args.member and Path(args.member).is_absolute():
                raise ValueError("unsupported")
            if digest(path) != args.original_sha256:
                raise ValueError("source_changed")
            mount = hashlib.sha256(os.fsencode(str(path.parent))).hexdigest()[:12]
            status, output = publish(args.out, Path("External-OCR", mount) / target, data)
            return {"status": status, "output": output}
        if sniff["format"] not in {"jpeg", "png"}:
            raise ValueError("unsupported")
        tool = exiftool.detect(exiftool.CONVERT_TIMEOUT_S)
        if not tool["available"]:
            return {"status": tool["status"], "fields": {}}
        from markitdown.photo_metadata import read_photo_info
        return read_photo_info(data, fields=args.field, executable=tool["path"], timeout=exiftool.CONVERT_TIMEOUT_S)
    except (OSError, TimeoutError):
        return {"status": "read_failed"}
    except (ValueError, KeyError, IndexError) as exc:
        known = {"source_changed", "unsupported"}
        return {"status": str(exc) if str(exc) in known else "unusable"}
