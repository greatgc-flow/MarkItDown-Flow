"""Command-line protocol (SPEC section 10); no engine configuration files."""

import argparse
from decimal import Decimal, InvalidOperation
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys
import tempfile
import zlib

from . import approve, assemble, classify, convert, exiftool, orchestrate, providers, report, sniff_io, transcribe, triage, write

_DISCLOSURE = ("Duplicate remote charges are possible if a run dies between a response and its ledger write. "
               "A trusted command runs with your privileges on every OCR unit.")


class UsageError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs['allow_abbrev'] = False
        super().__init__(*args, **kwargs)

    def error(self, message):
        # argparse's raw message may echo an unrecognised credential argument.
        raise UsageError("Invalid command or option; use --help for the supported syntax.")


def _nonnegative(text: str) -> int:
    number = int(text)
    if number < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return number


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="mdflow", description="Local document conversion and selective OCR.", epilog=_DISCLOSURE)
    commands = parser.add_subparsers(dest="command_name", required=True)
    for name in ("run", "plan"):
        cmd = commands.add_parser(name, description=_DISCLOSURE)
        cmd.add_argument("paths", nargs="+", type=Path)
        cmd.add_argument("-o", "--out", type=Path, required=name == "run")
        cmd.add_argument("--provider", choices=providers.NAMES, default="none")
        cmd.add_argument("--model")
        cmd.add_argument("--dpi", type=int, choices=(200, 300), default=200)
        cmd.add_argument("--prompt-version", default="p1")
        cmd.add_argument("--yes", nargs="?", const=True, action="append", default=[])
        cmd.add_argument("--yes-file", type=Path, action="append", default=[])
        cmd.add_argument("--approved-by", default="cli:--yes")
        cmd.add_argument("--sensitive", action="append", default=[])
        cmd.add_argument("--min-priority", choices=("low", "normal"), default="low")
        for option in ("approve_threshold", "max_units", "max_bytes", "max_pixels", "zip_depth", "zip_entries", "zip_total_bytes"):
            cmd.add_argument("--" + option.replace("_", "-"), type=_nonnegative, default=orchestrate.DEFAULTS[option])
        cmd.add_argument("--force", action="store_true")
        cmd.add_argument("--cache", type=Path, default=Path.home() / ".mdflow/cache")
        cmd.add_argument("--progress", choices=("none", "jsonl"), default="none")
        cmd.add_argument("--report", type=Path)
        cmd.add_argument("--command")
        cmd.add_argument("--command-egress", choices=("true", "false"))
        cmd.add_argument("--command-env", action="append", default=[])
        cmd.add_argument("--trust-command", action="store_true",
                         help="The command runs with your privileges on every OCR unit.")
        cmd.add_argument("--cost-hint")
    cmd = commands.add_parser("classify")
    cmd.add_argument("path", type=Path)
    for name in ("version", "providers", "selftest"):
        commands.add_parser(name)
    cmd = commands.add_parser("cache")
    cmd.add_argument("operation", choices=("stats", "clear"))
    cmd.add_argument("--cache", type=Path, default=Path.home() / ".mdflow/cache")
    return parser


def _check_core() -> None:
    try:
        version = metadata.version("markitdown-gc")
    except metadata.PackageNotFoundError:
        raise RuntimeError("markitdown-gc is not installed") from None
    match = re.fullmatch(r"0\.3\.(\d+)(.*)", version)
    if not match or int(match[1]) < 5 or (int(match[1]) == 5 and match[2] and
                                        not match[2].startswith((".post", "+"))):
        raise RuntimeError("markitdown-gc must be >=0.3.5,<0.4")


def _print(value: object, *, pretty: bool = False) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2 if pretty else None) + "\n")
    sys.stdout.flush()


def _error(code: str, message: str) -> int:
    value = report.diagnostics({"code": code, "message": message})
    sys.stderr.write(json.dumps({"error": value}, ensure_ascii=False) + "\n")
    return 1


def _options(args: argparse.Namespace) -> dict:
    opts = vars(args).copy()
    if opts['provider'] != 'command' and (
            opts['command'] is not None or opts['command_egress'] is not None or
            opts['command_env'] or opts['trust_command']):
        raise UsageError('Command options require --provider command.')
    if opts["max_bytes"] > 268435456:
        raise UsageError("--max-bytes exceeds Core's 256 MiB cap.")
    try:
        transcribe.load_prompt(opts["prompt_version"])
    except LookupError:
        raise UsageError("Unknown --prompt-version.") from None
    if opts["cost_hint"] is not None:
        try:
            cost = Decimal(opts["cost_hint"])
        except InvalidOperation:
            raise UsageError("--cost-hint must be a finite nonnegative decimal.") from None
        if not cost.is_finite() or cost < 0:
            raise UsageError("--cost-hint must be a finite nonnegative decimal.")
    opts["yes_hashes"] = [value for value in opts["yes"] if isinstance(value, str)]
    opts["yes"] = any(value is True for value in opts["yes"])
    for path in opts.pop("yes_file"):
        try:
            opts["yes_hashes"].extend(approve.parse_yes_lines(path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError):
            raise UsageError("The approval hash file could not be read.") from None
    if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in opts["yes_hashes"]):
        raise UsageError("Approval hashes must be 64 lowercase hexadecimal characters.")
    if opts["command_egress"] is not None:
        opts["command_egress"] = opts["command_egress"] == "true"
    return opts


def _classification(path: Path, *, logical: str | None = None) -> dict:
    sniff = sniff_io.sniff(path, logical=logical or path.name)
    if sniff['route'] == 'NATIVE' and not any(i['code'].startswith('E_') for i in sniff['issues']):
        try:
            data = orchestrate._source_bytes(path, sniff, 268435456)
        except OSError:
            sniff['issues'].append({'code': 'E_SNIFF_IO', 'message': 'Source changed or could not be read after Sniff.'})
            outcome = triage.run_triage(path, sniff)
        else:
            with tempfile.TemporaryDirectory(prefix='mdflow-classify-') as work:
                snapshot = Path(work) / ('source.' + sniff['format'])
                snapshot.write_bytes(data)
                outcome = triage.run_triage(snapshot, sniff)
    else:
        outcome = triage.run_triage(path, sniff)
    decision = classify.classify(dict(sniff, issues=[*sniff["issues"], *outcome["issues"]]), outcome["report"])
    return dict(sniff=sniff, triage=outcome["report"], classification=decision)


def _selftest_documents() -> dict[str, bytes]:
    """Bundled smoke fixtures encoded using stdlib only; no test-tree dependency."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    scan = b"".join(b"\0" + bytes((i * 37 + row * 11) % 256 for i in range(96)) for row in range(32))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 32, 32, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(scan)) + chunk(b"IEND", b"")
    text = ("Bundled local conversion selftest text. " * 20).encode("ascii")
    stream = b"BT /F1 10 Tf 20 500 Td (" + text + b") Tj ET\n"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 612] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
               b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream"]
    pdf, offsets = b"%PDF-1.4\n", [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(f"{n:010} 00000 n \n".encode() for n in offsets[1:])
    pdf += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return {"smoke.pdf": pdf, "smoke.png": png}


def _exiftool_versions() -> dict:
    """`version` fields for the optional exiftool helper (R31); absence is a normal state, never an error."""
    found = exiftool.detect()
    return dict(exiftool=found["version"] if found["available"] else "unavailable",
                exiftool_status=found["status"], exiftool_source=found["source"])


def _selftest_exiftool(png: bytes) -> dict:
    """Informational only: does the detected exiftool actually yield metadata for the bundled PNG?"""
    found = exiftool.detect()
    metadata = False
    if found["available"]:
        try:
            metadata = "ImageSize:" in convert.core_convert(png, ".png", exiftool_path=found["path"])
        except Exception:
            metadata = False
    return dict(status=found["status"], version=found["version"], metadata=metadata)


def _selftest() -> int:
    expected = {
        "pdf": dict(route="NATIVE", need="NONE", label="T", action="convert_only", decision="no_candidates",
                    coverage_state="complete", candidates_unique=[], uninspected_pages=0, reasons=[], issues=[]),
        "png": dict(route="NATIVE", need="FULL", label="S", action="convert_and_ocr", decision="ocr_recommended",
                    coverage_state="complete", candidates_unique=[dict(id="image", kind="image", page=None,
                    priority="normal", priority_core="high", refs=1)], uninspected_pages=0,
                    reasons=["cand:standalone_image"], issues=[]),
    }
    matched = True
    documents = _selftest_documents()
    with tempfile.TemporaryDirectory(prefix="mdflow-selftest-") as folder:
        for name, data in documents.items():
            path = Path(folder) / name
            path.write_bytes(data)
            value = _classification(path)
            matched = (value["classification"] == expected[path.suffix[1:]]) and matched
    _print({"ok": matched, "exiftool": _selftest_exiftool(documents["smoke.png"])})
    return 0 if matched else 2


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        args = _parser().parse_args(argv)
        if args.command_name == "version":
            _print(dict(orchestrate.tools(), python=platform.python_version(), platform=platform.platform(),
                        protocol=1, triage_schema=1, **_exiftool_versions()))
            return 0
        try:
            _check_core()
        except RuntimeError as exc:
            return _error("E_CORE_VERSION", str(exc))
        if args.command_name == "providers":
            _print(providers.describe())
            return 0
        if args.command_name == "selftest":
            return _selftest()
        if args.command_name == "classify":
            value = _classification(args.path)
            _print(report.diagnostics(value))
            return assemble.exit_code([i["code"] for i in value["classification"]["issues"]])
        if args.command_name == "cache":
            cache = args.cache.expanduser()
            if args.operation == "clear":
                _print({"removed": write.clear_cache(cache)})
            else:
                files = [p for p in cache.rglob("*") if p.is_file() and not p.is_symlink()] if cache.exists() else []
                _print({"files": len(files), "bytes": sum(p.stat().st_size for p in files)})
            return 0
        opts = _options(args)
        provider = providers.build_provider(opts["provider"], **{k: opts[k] for k in
            ("model", "cost_hint", "command", "command_egress", "command_env", "trust_command")})
        if args.command_name == "plan":
            opts.update(_plan_only=True, _on_plan=lambda value: _print(value, pretty=True))
        terminal = []
        if args.command_name == 'run':
            opts['_on_run_end'] = terminal.append
        value = orchestrate.run(args.paths, opts, provider=provider)
        if args.command_name == "run":
            if args.report is not None:
                try:
                    write.atomic_write(args.report, (report._json(value) + '\n').encode('utf-8'))
                except OSError:
                    issue = {'code': 'E_OUTPUT_IO', 'message': 'Run report could not be written.'}
                    if value['files']:
                        value['files'][0]['issues'].append(issue)
                    else:
                        value.setdefault('issues', []).append(issue)
                    value['exit'] = assemble.exit_code(['E_OUTPUT_IO'], cancelled=value['exit'] == 130)
                    if args.progress == 'jsonl':
                        report.emit_progress(dict(v=1, ev='error', ts=value['finished'], file=None, **issue), sys.stderr)
            if args.progress == 'jsonl':
                event = terminal[0]
                failed = sum(bool(assemble.exit_code([i['code'] for i in f['issues']])) for f in value['files'])
                event.update(exit=value['exit'], files_failed=failed, files_ok=len(value['files']) - failed)
                report.emit_progress(event, sys.stderr)
            report.publish(value, stdout=sys.stdout)
        return value["exit"]
    except UsageError as exc:
        return _error("E_USAGE", str(exc))
    except providers.ProviderConfigError as exc:
        return _error("E_PROVIDER_CONFIG", str(exc))
    except (OSError, ValueError) as exc:
        return _error("E_USAGE", f"Command could not complete ({type(exc).__name__}).")
    except SystemExit as exc:
        return int(exc.code or 0)
