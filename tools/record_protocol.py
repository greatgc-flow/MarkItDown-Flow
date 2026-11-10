"""Record FX-71 protocol streams from REAL ``python -m mdflow`` runs (stdlib only).

    python -I tools/record_protocol.py            # installed wheel; record + derive into shell/test/fixtures/fx71/
    python -I tools/record_protocol.py --verify   # hashes match manifest; derived == transform(parent)

Provenance rules (30_TESTPLAN FX-71, 90_ACCEPTANCE G-12):

* ``kind: recorded``  bytes exactly as the child process wrote them. Nothing is
  hand-typed. Streams carry real timestamps, so a re-record changes them; the
  manifest's sha256 detects hand edits.
* ``kind: derived``   deterministic byte transform of ONE recorded parent
  (split chunks, CRLF, unknown events, oversize lines, truncation, version
  variants, extra triage fields). ``--verify`` recomputes each from its parent.
  Derived streams are labelled and never presented as engine output.

Inputs come from ``engine/tests/fixtures/gen_core.py`` generators and are always
passed as relative paths, so no machine path enters a recording (checked).
The only credential used is a fixed dummy sentinel, and it must never appear in
any recording (REQ-SEC-01).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
OUT_DEFAULT = REPO / "shell/test/fixtures/fx71"
WORK_DEFAULT = REPO / "build/trace/fx71-work"
SENTINEL = "sk-fx71-dummy-sentinel-0000"  # not a credential; must never be recorded
LINE_LIMIT = 64 * 1024
MODEL = "gpt-4.1-mini"
PLACEHOLDER = "<WORK>"  # stands for the recording work directory wherever the engine printed it absolutely
LARGE_PAGES = 200  # the pretty Plan stdout must exceed the 64 KiB progress-line limit
ABSOLUTE_PATH = re.compile(rb"""(?<![A-Za-z0-9])[A-Za-z]:[\\/]|(?<![\w\x80-\xff~:/\\])/(?!/)[^/\\\s"'<>:{}|]+(?:/|(?=[\s"'\\]|$))""")


def check_portable(name: str, data: bytes) -> None:
    """Check bytes, including JSON-escaped paths; never rely on known host roots."""
    if ABSOLUTE_PATH.search(data.replace(b"\\/", b"/")):
        raise SystemExit(f"{name}: recording leaks an absolute path")
    if SENTINEL.encode() in data:
        raise SystemExit(f"{name}: recording leaks the credential sentinel")


def load_gen():
    spec = importlib.util.spec_from_file_location("fx71_gen_core", REPO / "engine/tests/fixtures/gen_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- byte helpers

def lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def lines_of(data: bytes) -> list[bytes]:
    text = lf(data)
    return (text[:-1] if text.endswith(b"\n") else text).split(b"\n")


def join_lines(lines: list[bytes]) -> bytes:
    return b"".join(line + b"\n" for line in lines)


def objects(data: bytes) -> list:
    """Consecutive JSON values (pretty Plans, or one report)."""
    text, decoder, values = data.decode("utf-8"), json.JSONDecoder(), []
    while text.strip():
        value, end = decoder.raw_decode(text.lstrip())
        values.append(value)
        text = text.lstrip()[end:]
    return values


def jline(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def multibyte_starts(data: bytes) -> list[int]:
    return [i for i, b in enumerate(data) if b >= 0xC0]


# ----------------------------------------------------------- derived transforms
# Each takes the parent's bytes and returns the derived bytes: pure, deterministic.
# Line-oriented transforms work on the LF-normalised parent (Windows stdout is CRLF).

def t_crlf(parent: bytes) -> bytes:
    return lf(parent).replace(b"\n", b"\r\n")


def _cuts(data: bytes) -> list[int]:
    cuts = {1}
    for start in multibyte_starts(data)[:3]:  # inside the first multibyte sequences
        cuts.update({start + 1, start + 2} if data[start] >= 0xE0 else {start + 1})
    for position in [i for i, b in enumerate(data) if b == 0x0A][:3]:
        cuts.update({position, position + 1})  # before and after the line break
        if position and data[position - 1] == 0x0D:
            cuts.add(position - 1)  # between CR and LF
    cuts.update(range(1024, len(data), 1024))
    return sorted(c for c in cuts if 0 < c < len(data))


def _split_json(data: bytes) -> bytes:
    cuts = _cuts(data)
    chunks = [data[a:b] for a, b in zip([0, *cuts], [*cuts, len(data)])]
    return (json.dumps({
        "rule": "cuts at byte 1; inside the first 3 multibyte UTF-8 sequences; before/after (and between CR and LF "
                "of) the first 3 line breaks; then every 1024 bytes. Concatenating chunks_b64 gives the stream.",
        "cuts": cuts,
        "chunks_b64": [base64.b64encode(c).decode("ascii") for c in chunks],
    }, indent=1) + "\n").encode("utf-8")


def t_split(parent: bytes) -> bytes:
    return _split_json(lf(parent))


def t_split_crlf(parent: bytes) -> bytes:
    return _split_json(t_crlf(parent))


def t_unknown_events(parent: bytes) -> bytes:
    lines = lines_of(parent)
    inserts = [{"ev": "heartbeat"}, {"ev": "x_vendor_event", "file": "보고서/3분기 결산.pdf", "detail": "한국어 payload"},
               {"ev": "future_stage_detail", "nested": {"a": [1, 2, {"b": None}]}}]
    out, count = [], 0
    for index, line in enumerate(lines):
        event = json.loads(line)
        # A known event with an extra additive field: consumers ignore unknown fields.
        out.append(jline(dict(event, future_field=[1, "x", None])) if index == 1 else line)
        if index % 3 == 0:
            out.append(jline(dict(inserts[count % len(inserts)], v=1, ts=event["ts"])))
            count += 1
    return join_lines(out)


def _padded_warning(ts: str, size: int) -> bytes:
    base = {"v": 1, "ev": "warning", "ts": ts, "file": "x.pdf", "code": "W_MEDIA_UNMAPPED", "message": ""}
    pad = size - len(jline(base))
    assert pad >= 0
    line = jline(dict(base, message="x" * pad))
    assert len(line) == size
    return line


def _with_inserted_line(parent: bytes, size: int) -> bytes:
    lines = lines_of(parent)
    return join_lines([*lines[:2], _padded_warning(json.loads(lines[1])["ts"], size), *lines[2:]])


def t_line_exact_limit(parent: bytes) -> bytes:
    return _with_inserted_line(parent, LINE_LIMIT)  # the allowed boundary


def t_line_over_limit(parent: bytes) -> bytes:
    return _with_inserted_line(parent, LINE_LIMIT + 1)  # first rejected size


def t_unterminated_oversize(parent: bytes) -> bytes:
    lines = lines_of(parent)
    return join_lines(lines[:2]) + _padded_warning(json.loads(lines[1])["ts"], 70000)  # no newline


def _truncate(parent: bytes, percent: int) -> bytes:
    """Cut at ``percent`` and one byte into the next multibyte sequence (invalid UTF-8 tail) when present."""
    cut = len(parent) * percent // 100
    starts = [i for i in multibyte_starts(parent) if i >= cut]
    return parent[:starts[0] + 1] if starts else parent[:cut]


def t_truncate_report(parent: bytes) -> bytes:
    return _truncate(parent, 60)


def t_truncate_plan(parent: bytes) -> bytes:
    return _truncate(parent, 55)


def t_triage_extra(parent: bytes) -> bytes:
    report = json.loads(parent)
    for entry in report["files"]:
        if isinstance(entry.get("triage"), dict):
            entry["triage"]["future_core_field"] = {"kept": "verbatim", "ko": "한국어"}
    return (json.dumps(report, ensure_ascii=False) + "\n").encode("utf-8")


VERSION_KEYS = ("mdflow", "markitdown-gc", "pypdfium2", "pillow", "python", "platform", "protocol", "triage_schema")
VERSION_VARIANTS = ["protocol-2", "schema-2", "wrong-pillow", "wrong-renderer", "core-out-of-range",
                    "core-unavailable", "python-3.15",
                    "protocol-string", "unknown-optional-field", *[f"missing-{k}" for k in VERSION_KEYS]]


def version_variant(name: str, parent: bytes) -> bytes:
    data = json.loads(parent)
    if name == "protocol-2":
        data["protocol"] = 2
    elif name == "schema-2":
        data["triage_schema"] = 2
    elif name == "wrong-pillow":
        # First excluded versions, independent of the resolved supported endpoint.
        data["pillow"] = "14.0.0"
    elif name == "wrong-renderer":
        data["pypdfium2"] = "6.0.0"
    elif name == "core-out-of-range":
        data["markitdown-gc"] = "0.4.0"
    elif name == "core-unavailable":
        data["markitdown-gc"] = "unavailable"
    elif name == "python-3.15":
        data["python"] = "3.15.2"
    elif name == "protocol-string":
        data["protocol"] = str(data["protocol"])
    elif name == "unknown-optional-field":
        data["future_optional"] = {"ignored": True}
    elif name.startswith("missing-"):
        del data[name.removeprefix("missing-")]
    else:
        raise KeyError(name)
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# name -> (parent, transform name, transform, description)
DERIVED: dict[str, tuple[str, str, object, str]] = {}


def _derive(name, parent, fn, description):
    DERIVED[name] = (parent, fn.__name__, fn, description)


_AP = "approve-required.progress.jsonl"
_derive("approve-required.crlf.jsonl", _AP, t_crlf, "LF to CRLF")
_derive("approve-required.split.json", _AP, t_split, "UTF-8 / line-break split chunks (LF)")
_derive("approve-required.crlf.split.json", _AP, t_split_crlf, "UTF-8 / CR|LF split chunks (CRLF)")
_derive("approve-required.unknown-events.jsonl", _AP, t_unknown_events, "unknown ev values + additive field inserted")
_derive("approve-required.line-65536.jsonl", _AP, t_line_exact_limit, "one valid line of exactly 65536 bytes (allowed)")
_derive("approve-required.line-65537.jsonl", _AP, t_line_over_limit, "one line of 65537 bytes (over the limit)")
_derive("approve-required.unterminated-70000.jsonl", _AP, t_unterminated_oversize, "70000-byte unterminated tail line")
_derive("plan-mixed.split.json", "plan-mixed.stdout.json", t_split, "split chunks of pretty Plan stdout")
_derive("plan-mixed.truncated.stdout.json", "plan-mixed.stdout.json", t_truncate_plan, "truncated plan stdout")
_derive("run-mixed.truncated.stdout.json", "run-mixed.stdout.json", t_truncate_report, "truncated run report")
_derive("run-corrupt.triage-extra.stdout.json", "run-corrupt.stdout.json", t_triage_extra,
        "unknown Core field added inside files[].triage")


def _variant(variant):
    def transform(parent: bytes) -> bytes:
        return version_variant(variant, parent)
    transform.__name__ = "version_variant:" + variant
    return transform


for _variant_name in VERSION_VARIANTS:
    _derive(f"version.{_variant_name}.json", "version.json", _variant(_variant_name),
            f"version response variant: {_variant_name}")


# ------------------------------------------------------------------- recording

class Recorder:
    def __init__(self, out: Path, work: Path):
        self.out, self.work = out, work
        self.entries: dict[str, dict] = {}
        self.gen = load_gen()
        # HOME is the work dir itself: the engine reports out/cache as absolute paths but shortens the home prefix
        # to "~", so reports read "~/out-mixed" instead of a machine path.
        home, tmp = work, work / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        base = {k: v for k, v in os.environ.items()
                if not k.upper().startswith("MDFLOW_") and k.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
        # Use the selected interpreter's installed engine, never a source-tree injection.
        base.update(HOME=str(home), USERPROFILE=str(home), TMP=str(tmp), TEMP=str(tmp),
                    PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        # Resolve the command scenario under HOME too: its destination must not expose this interpreter's path.
        bin_dir = work / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            (bin_dir / "python.cmd").write_text('@echo off\n"' + sys.executable.replace('%', '%%') + '" %*\n',
                                                encoding="utf-8")
        else:
            shim = bin_dir / "python"
            shim.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n', encoding="utf-8")
            shim.chmod(0o755)
        base["PATH"] = str(bin_dir) + os.pathsep + base.get("PATH", "")
        self.env = base
        self.version = None

    # inputs ---------------------------------------------------------------
    def put(self, root: str, rel: str, fx: str, **kwargs) -> None:
        generated = self.gen.generate(fx, self.work / "scratch", **kwargs)
        target = self.work / root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated, target)

    def put_bytes(self, root: str, rel: str, data: bytes) -> None:
        target = self.work / root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    # process --------------------------------------------------------------
    def portable(self, data: bytes) -> tuple[bytes, int]:
        """Replace any remaining absolute work-dir prefix by PLACEHOLDER (the leak check still runs afterwards)."""
        count = 0
        for spelling in sorted({str(self.work), self.work.as_posix(), json.dumps(str(self.work))[1:-1]},
                               key=len, reverse=True):
            raw = spelling.encode("utf-8")
            count += data.count(raw)
            data = data.replace(raw, PLACEHOLDER.encode("ascii"))
        return data, count

    def save(self, name: str, data: bytes, *, argv, exit_code, stream, env_names, note=""):
        data, replaced = self.portable(data)
        check_portable(name, data)
        entry = {"kind": "recorded", "stream": stream, "argv": argv, "exit": exit_code, "env_names": env_names,
                 "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                 "eol": "crlf" if b"\r\n" in data else "lf"}
        if replaced:
            entry["placeholder_replacements"] = replaced
        if note:
            entry["note"] = note
        self.entries[name] = entry
        (self.out / name).write_bytes(data)

    def record(self, label: str, args, *, expect, stdout: str | None, progress: str | None = None,
               env: dict | None = None, note: str = ""):
        """``expect``: an exit code or a collection of acceptable codes (plan may announce missing consent: 0 or 3)."""
        argv = [sys.executable, "-I", "-m", "mdflow", *map(str, args)]
        proc = subprocess.run(argv, cwd=self.work, env=dict(self.env, **(env or {})), capture_output=True, timeout=900)
        if proc.returncode not in ({expect} if isinstance(expect, int) else set(expect)):
            raise SystemExit(f"{label}: exit {proc.returncode}, expected {expect}\n"
                             f"stdout={proc.stdout[:400]!r}\nstderr={proc.stderr[:2000]!r}")
        shown, names = ["python", "-I", "-m", "mdflow", *map(str, args)], sorted((env or {}).keys())
        for stream, name, data in (("stdout", stdout, proc.stdout), ("stderr", progress, proc.stderr)):
            if name:
                self.save(name, data, argv=shown, exit_code=proc.returncode, stream=stream, env_names=names, note=note)
            elif data.strip():
                raise SystemExit(f"{label}: unexpected {stream}: {data[:500]!r}")

    def entry_bytes(self, name: str) -> bytes:
        return (self.out / name).read_bytes()

    def write_yes(self, name: str, plans: list):
        text = "# fx71 approval file (hashes taken from the preceding `plan` stdout, as the shell does)\n\n" + "".join(
            f"{p['plan_hash']}\n" for p in plans) + "\n# end\n"
        (self.work / name).write_text(text, encoding="utf-8", newline="\n")
        (self.out / name).write_text(text, encoding="utf-8", newline="\n")
        data = text.encode("utf-8")
        self.entries[name] = {"kind": "recorded", "stream": "input-file", "argv": None, "exit": None, "env_names": [],
                              "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "eol": "lf",
                              "note": "yes-file passed to the next run"}

    # scenarios ------------------------------------------------------------
    def build_inputs(self):
        self.put("inputs", "sub/a.pdf", "FX-03")
        self.put("inputs", "보고서/3분기 결산.pdf", "FX-02", pages=3)
        self.put("inputs", "b c.docx", "FX-16")
        self.put("inputs", "memo.txt", "FX-28")
        self.put_bytes("inputs", ".DS_Store", b"\x00\x00\x00\x01Bud1")
        self.put("bad", "broken.pdf", "FX-06")
        self.put("bad", "empty.pdf", "FX-40")
        # mdflow's Sniff rejects garbage PDFs itself (E_CORRUPT, Triage never runs). To record a *Core* triage report
        # with a `corrupt` issue the file must pass Sniff: a valid zip/docx whose relationships XML is truncated.
        # Core then reports corrupt "Package XML could not be inspected." (ocr_triage_0.3.5 _Package.xml).
        generated = self.gen.generate("FX-16", self.work / "scratch")
        with zipfile.ZipFile(generated) as archive:
            members = {name: archive.read(name) for name in archive.namelist()}
        rels = "word/_rels/document.xml.rels"
        members[rels] = members[rels][:len(members[rels]) // 2]
        self.put_bytes("bad", "garbled.docx", self.gen.zip_bytes(sorted(members.items())))
        self.put("large", "긴 문서.pdf", "FX-02", pages=LARGE_PAGES)
        (self.work / "ocr_echo.py").write_text(
            "import sys\nsys.stdout.reconfigure(encoding='utf-8')\nprint('모의 OCR 텍스트 (fx71)')\n", encoding="utf-8")

    def scenarios(self):
        key = {"MDFLOW_API_KEY": SENTINEL}
        remote = ["--provider", "openai-compatible", "--model", MODEL]
        self.record("version", ["version"], expect=0, stdout="version.json")
        self.version = json.loads(self.entry_bytes("version.json"))
        self.record("providers", ["providers"], expect=0, stdout="providers.json")
        self.record("selftest", ["selftest"], expect=0, stdout="selftest.json")
        self.record("usage-error", ["run", "inputs", "-o", "out-usage", "--no-such-flag"], expect=1, stdout=None,
                    progress="usage-error.stderr.json")

        self.record("plan-mixed", ["plan", "inputs", "--cache", "cache-plan", *remote], expect=(0, 3), env=key,
                    stdout="plan-mixed.stdout.json",
                    note="openai-compatible Plans (egress true); plan opens no socket and writes nothing")
        self.record("plan-none", ["plan", "inputs", "--cache", "cache-plan"], expect=0, stdout="plan-none.stdout.json")
        self.record("plan-large", ["plan", "large", "--cache", "cache-plan", *remote], expect=(0, 3), env=key,
                    stdout="plan-large.stdout.json",
                    note=f"one {LARGE_PAGES}-page file: the full Plan exceeds 64 KiB, valid only as plan stdout")
        self.record("run-mixed", ["run", "inputs", "bad", "-o", "out-mixed", "--cache", "cache-mixed",
                                  "--progress", "jsonl"], expect=2,
                    stdout="run-mixed.stdout.json", progress="run-mixed.progress.jsonl",
                    note="provider none; hidden file skipped; corrupt and empty PDFs; exit 2")
        self.record("run-corrupt", ["run", "bad", "-o", "out-corrupt", "--cache", "cache-corrupt",
                                    "--progress", "jsonl"], expect=2,
                    stdout="run-corrupt.stdout.json", progress="run-corrupt.progress.jsonl")
        self.record("run-approve", ["run", "inputs", "large", "-o", "out-approve", "--cache", "cache-approve",
                                    "--progress", "jsonl", *remote], expect=3, env=key,
                    stdout="approve-required.stdout.json", progress="approve-required.progress.jsonl",
                    note="no --yes: one approve_required summary event per file needing consent; exit 3")

        # Engine-driven consent flow via the command provider (declared egress, no network).
        command = ["--provider", "command", "--command", "python ocr_echo.py {input}", "--command-egress", "true",
                   "--trust-command", "--model", "fx71-echo", "--cache", "cache-cmd"]
        self.record("cmd-plan", ["plan", "inputs", *command], expect=(0, 3), stdout="consent-1-plan.stdout.json")
        plans = {p["approved"]["file"]["path"]: p for p in objects(self.entry_bytes("consent-1-plan.stdout.json"))}
        needing = [p for p in plans.values() if p["status"]["requests_to_send"] > 0]
        assert len(needing) >= 2, "need two files requiring consent"
        # The docx has rasters distinct from the PDFs, so approving it first leaves the PDFs pending (exit 3)
        # instead of being satisfied from the shared ledger.
        first = next(p for p in needing if p["approved"]["file"]["format"] == "docx")
        self.write_yes("consent-yes-1.txt", [first])
        self.record("cmd-run-pending", ["run", "inputs", "-o", "out-cmd", *command, "--progress", "jsonl"], expect=3,
                    stdout="consent-2-pending.stdout.json", progress="consent-2-pending.progress.jsonl")
        self.record("cmd-run-partial", ["run", "inputs", "-o", "out-cmd", *command, "--progress", "jsonl",
                                        "--yes-file", "consent-yes-1.txt", "--approved-by", "plugin:modal"], expect=3,
                    stdout="consent-3-partial.stdout.json", progress="consent-3-partial.progress.jsonl",
                    note="one file approved and executed; the rest stay pending (exit 3)")
        self.record("cmd-plan-warm", ["plan", "inputs", *command], expect=(0, 3), stdout="consent-4-plan-warm.stdout.json")
        warm = {p["approved"]["file"]["path"]: p for p in objects(self.entry_bytes("consent-4-plan-warm.stdout.json"))}
        for path, plan in plans.items():
            assert warm[path]["plan_hash"] == plan["plan_hash"], f"plan_hash changed after cache warming: {path}"
        assert warm[first["approved"]["file"]["path"]]["status"]["requests_to_send"] == 0, "cache was not warmed"
        self.write_yes("consent-yes-2.txt", needing)
        self.record("cmd-run-all", ["run", "inputs", "-o", "out-cmd", *command, "--progress", "jsonl",
                                    "--yes-file", "consent-yes-2.txt", "--approved-by", "plugin:modal"], expect=0,
                    stdout="consent-5-approved.stdout.json", progress="consent-5-approved.progress.jsonl")
        self.record("cmd-run-warm", ["run", "inputs", "-o", "out-cmd", *command, "--progress", "jsonl"], expect=0,
                    stdout="consent-6-warm.stdout.json", progress="consent-6-warm.progress.jsonl",
                    note="warm rerun without --yes: no approve_required, provider_calls 0")

    def derive(self):
        for name, (parent, transform_name, fn, description) in DERIVED.items():
            data = fn(self.entry_bytes(parent))
            (self.out / name).write_bytes(data)
            self.entries[name] = {"kind": "derived", "derived_from": parent, "transform": transform_name,
                                  "description": description, "bytes": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest()}

    def check_recordings(self):
        paths = [str(self.work), self.work.as_posix(), str(REPO), REPO.as_posix(), str(Path.home()), Path.home().as_posix()]
        # JSON-escaped spellings too (backslashes are doubled inside recorded JSON text).
        forbidden = [SENTINEL, *paths, *(json.dumps(p)[1:-1] for p in paths)]
        for name, entry in self.entries.items():
            if entry["kind"] == "recorded":
                check_portable(name, self.entry_bytes(name))
                text = self.entry_bytes(name).decode("utf-8")
                for bad in forbidden:
                    if bad and bad in text:
                        raise SystemExit(f"{name}: recording leaks {bad!r}")
                if name.endswith(".progress.jsonl"):
                    for line in lines_of(self.entry_bytes(name)):
                        assert len(line) <= LINE_LIMIT, f"{name}: real stderr line over 64 KiB"
                        event = json.loads(line)
                        assert event["v"] == 1 and "ev" in event
        required = [e for e in map(json.loads, lines_of(self.entry_bytes(_AP))) if e["ev"] == "approve_required"]
        assert len(required) >= 3 and all("units" not in e for e in required), "approve_required events missing/leaky"
        large = self.entry_bytes("plan-large.stdout.json")
        assert len(large) > LINE_LIMIT, "large Plan stdout is not > 64 KiB"
        assert objects(large)[0]["approved"]["units_total"] == LARGE_PAGES
        corrupt = objects(self.entry_bytes("run-corrupt.stdout.json"))[0]
        assert any(i.get("code") == "corrupt" for f in corrupt["files"] if isinstance(f["triage"], dict)
                   for i in f["triage"].get("issues", [])), "no raw Core triage with a `corrupt` issue was recorded"
        assert objects(self.entry_bytes("run-mixed.stdout.json"))[0]["skipped"], "no skipped entries recorded"

    def manifest(self):
        data = {
            "v": 1,
            "fixture": "FX-71",
            "generator": "tools/record_protocol.py",
            "inputs": "engine/tests/fixtures/gen_core.py generators (FX-02, FX-03, FX-06, FX-16, FX-28, FX-40); "
                      "relative paths with Korean/space names and a hidden file; the command provider is "
                      "`python ocr_echo.py {input}` (no network)",
            "recording_host": {"platform": platform.platform(), "python": platform.python_version()},
            "engine": self.version,
            "placeholder": {PLACEHOLDER: "recording work directory; HOME was set to it, so the engine prints `~/...`; "
                                         "any other absolute spelling was replaced by this token (see "
                                         "`placeholder_replacements` per file)"},
            "note": "recorded = verbatim child output (except the placeholder) (real timestamps; re-recording changes the bytes; stdout/stderr "
                    "newlines are those of the recording host, see `eol`). derived = deterministic transform of one "
                    "recorded parent, never engine output. Check with: python tools/record_protocol.py --verify",
            "files": dict(sorted(self.entries.items())),
        }
        (self.out / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(out: Path, work: Path) -> None:
    out, work = out.resolve(), work.resolve()
    if not work.is_relative_to(REPO / "build") or not out.is_relative_to(REPO):
        raise SystemExit("--work must be under build/ and --out inside the repository")
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    recorder = Recorder(out, work)
    recorder.build_inputs()
    recorder.scenarios()
    recorder.derive()
    recorder.check_recordings()
    recorder.manifest()
    recorded = sum(e["kind"] == "recorded" for e in recorder.entries.values())
    print(f"recorded={recorded} derived={len(recorder.entries) - recorded} -> {out.relative_to(REPO).as_posix()}")


def verify(out: Path) -> int:
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    problems = []
    on_disk = {p.name for p in out.iterdir() if p.name != "manifest.json"}
    for name in sorted(on_disk ^ set(manifest["files"])):
        problems.append(f"file/manifest mismatch: {name}")
    for name, entry in manifest["files"].items():
        path = out / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        if entry["kind"] == "recorded":
            try:
                check_portable(name, data)
            except SystemExit as exc:
                problems.append(str(exc))
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
            problems.append(f"hash mismatch (edited?): {name}")
        if entry["kind"] == "derived":
            parent, _, fn, _ = DERIVED[name]
            if entry["derived_from"] != parent or fn((out / parent).read_bytes()) != data:
                problems.append(f"derived != transform(parent): {name}")
    for problem in problems:
        print(problem)
    print(f"verify {'FAILED' if problems else 'ok'}: {len(manifest['files'])} files")
    return int(bool(problems))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--work", type=Path, default=WORK_DEFAULT)
    parser.add_argument("--verify", action="store_true", help="check manifest hashes and derived == transform(parent)")
    args = parser.parse_args(argv)
    if args.verify:
        return verify(args.out.resolve())
    record(args.out, args.work)
    return verify(args.out.resolve())


if __name__ == "__main__":
    sys.exit(main())
