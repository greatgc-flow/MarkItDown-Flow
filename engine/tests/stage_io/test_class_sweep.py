"""M2-H horizontal class sweep (MECE round 2): one representative fixture per class K01..K20 through the REAL CLI.

``plan`` -> unconsented ``run`` -> ``run --yes-file`` -> rerun, always in a fresh isolated interpreter (the shared
``cli_command`` launcher, HOME/TEMP isolated, sockets blocked except the loopback mock provider FX-62). Per class the
test asserts exactly what the SPEC says the class reaches, from the progress events and the report fields:

* output-producing classes reach S12 Write (the ``.md`` exists, matches ``files[].outputs``, is byte-stable on rerun);
* unit-bearing classes reach S7 Lookup (miss first, ``cached`` on rerun with 0 provider calls), S9 Approve
  (``consent.plan_hash`` is the Plan's, nothing is sent and no socket is opened without it) and S10 Transcribe;
* report-only classes publish nothing and never reach Render, Assemble or Write;
* a class without eligible units never opens a socket, whatever provider is configured.

The class x stage cells this one test executes are registered with ``@pytest.mark.cells`` (see conftest): the literal
marker list and the per-class table below are asserted equal, so neither can drift. Engine gaps found here are
``xfail(strict=True, raises=KnownEngineGap, reason="M2-H: ...")`` - every other assertion of that case still runs.
"""

from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

STAGES = "sniff triage classify select convert render lookup plan approve transcribe assemble write".split()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
APPROVER = "plugin:class-sweep"
TRANSCRIPT = "mock transcription"  # MockHttp.default_text: deterministic provider answer


class KnownEngineGap(Exception):
    """A deviation from the SPEC found by the sweep; never an AssertionError so real failures stay red."""


# stages a file must show / must not show (an empty stage still emits an event, so effects carry the rest)
MUST = {
    "report_only": {"sniff", "triage", "classify"},
    "convert_only": {"sniff", "triage", "classify", "select", "convert", "assemble", "write"},
    "convert_and_ocr": set(STAGES),
    "recurse": set(STAGES[:5]) | {"lookup", "plan", "approve", "transcribe"},
}
NEVER = {"report_only": {"render", "assemble", "write"}, "convert_only": set(), "convert_and_ocr": set(),
         "recurse": {"render", "assemble"}}


def F(route, need, label, action, *, total=0, eligible=0, outputs=(), codes=(), media=0):
    return dict(route=route, need=need, label=label, action=action, total=total, eligible=eligible,
                outputs=list(outputs), codes=set(codes), media=media)


def native(need, label, action, **kw):
    return F("NATIVE", need, label, action, **kw)


def report_only(path, route, label, code, need="UNKNOWN"):
    return {path: F(route, need, label, "report_only", codes=(code,))}


CASES = {
    "K01": dict(fx=("FX-01",), files=lambda g, c: {"a.pdf": g.pdf_text(2)}, exit=0,
                expect={"a.pdf": native("NONE", "T", "convert_only", outputs=["a.pdf.md"])}),
    "K02": dict(fx=("FX-02",), files=lambda g, c: {"a.pdf": g.pdf_scan(3)}, exit=0,
                expect={"a.pdf": native("FULL", "S", "convert_and_ocr", total=3, eligible=3, outputs=["a.pdf.md"])}),
    "K03": dict(fx=("FX-03",), files=lambda g, c: {"a.pdf": g.pdf_mixed()}, exit=0,
                expect={"a.pdf": native("PARTIAL", "M", "convert_and_ocr", total=2, eligible=2, outputs=["a.pdf.md"])}),
    "K04": dict(fx=("FX-07",), files=lambda g, c: {"a.pdf": c.generate("FX-07", c.scratch).read_bytes()}, exit=0,
                args=("--max-units", "1000"),  # default 200 is E_PLAN_OVERSIZE: all pending, no egress (REQ-PLN)
                expect={"a.pdf": native("UNKNOWN", "U", "convert_and_ocr", total=1000, eligible=1000,
                                        outputs=["a.pdf.md"], codes=("W_TRIAGE_PARTIAL",))}),
    "K05": dict(fx=("FX-09",), files=lambda g, c: {"a.png": g.png_noise(seed=5)}, exit=0,
                expect={"a.png": native("FULL", "S", "convert_and_ocr", total=1, eligible=1, outputs=["a.png.md"])}),
    "K06": dict(fx=("FX-12",), files=lambda g, c: {"a.gif": c.generate("FX-12", c.scratch).read_bytes()}, exit=0,
                gap="Core converts only png/jpeg: a clean multi-frame GIF/TIFF is OCR'd and published but the file "
                    "is reported E_CONVERT_FAIL and the run exits 2 (REQ-CNV-03 converts non-PDF once, REQ-RPT-03)",
                expect={"a.gif": native("FULL", "S", "convert_and_ocr", total=2, eligible=2, outputs=["a.gif.md"])}),
    "K07": dict(fx=("FX-16",), files=lambda g, c: {"a.docx": c.generate("FX-16", c.scratch).read_bytes()}, exit=0,
                expect={"a.docx": native("PARTIAL", "M", "convert_and_ocr", total=2, eligible=2,
                                         outputs=["a.docx.md"], codes=("W_REVIEW_PRIORITY",), media=2)}),
    "K08": dict(fx=("FX-23",), files=lambda g, c: {"a.hwpx": c.generate("FX-23", c.scratch).read_bytes()}, exit=0,
                expect={"a.hwpx": native("PARTIAL", "M", "convert_and_ocr", total=1, eligible=1,
                                         outputs=["a.hwpx.md"], media=1)}),
    "K09": dict(fx=("FX-24",), files=lambda g, c: {"a.hwp": (FIXTURES / "FX-24.hwp").read_bytes()}, exit=0,
                expect={"a.hwp": native("PARTIAL", "M", "convert_and_ocr", total=2, eligible=1, outputs=["a.hwp.md"],
                                        codes=("W_REVIEW_PRIORITY", "W_MEDIA_FORMAT", "W_MEDIA_UNMAPPED"), media=1)}),
    "K10": dict(fx=("FX-28",), files=lambda g, c: {"a.txt": g.txt_utf8()}, exit=0,
                expect={"a.txt": native("NONE", "T", "convert_only", outputs=["a.txt.md"])}),
    "K11": dict(fx=("FX-30",), files=lambda g, c: {"a.csv": b"name,value\na,1\n"}, exit=0,
                expect={"a.csv": native("UNKNOWN", "U", "convert_only", outputs=["a.csv.md"],
                                        codes=("W_MEDIA_NOT_INSPECTED",))}),
    "K12": dict(fx=("FX-35",), files=lambda g, c: {"a.doc": g.cfb_legacy("doc")}, exit=2,
                expect=report_only("a.doc", "LEGACY", "L", "E_LEGACY")),
    "K13": dict(fx=("FX-38",), files=lambda g, c: {"a.mp3": b"ID3" + g.rng_bytes(200, 38)}, exit=2,
                expect=report_only("a.mp3", "UNSUPPORTED", "X", "E_MEDIA_OUT_OF_SCOPE")),
    "K14": dict(fx=("FX-43",), files=lambda g, c: {"a.zip": c.generate("FX-43", c.scratch).read_bytes()}, exit=0,
                expect={"a.zip": F("CONTAINER", "NONE", "C", "recurse", outputs=["a.zip.md"]),
                        "a.zip/text.pdf": native("NONE", "T", "convert_only", outputs=["a.zip/text.pdf.md"]),
                        "a.zip/text.txt": native("NONE", "T", "convert_only", outputs=["a.zip/text.txt.md"]),
                        "a.zip/mixed.docx": native("PARTIAL", "M", "convert_and_ocr", total=2, eligible=2,
                                                   outputs=["a.zip/mixed.docx.md"], codes=("W_REVIEW_PRIORITY",),
                                                   media=2)}),
    "K15": dict(fx=("FX-05",), files=lambda g, c: {"a.pdf": g.pdf_encrypted()}, exit=2,
                expect=report_only("a.pdf", "PROTECTED", "P", "E_ENCRYPTED")),
    "K16": dict(fx=("FX-06",), files=lambda g, c: {"a.pdf": g.pdf_corrupt()}, exit=2,
                expect=report_only("a.pdf", "NATIVE", "U", "E_CORRUPT")),
    "K17": dict(fx=("FX-42",), files=lambda g, c: {"a.txt": g.zero_padded_text(2 * 1024 * 1024)}, exit=2,
                args=("--max-bytes", "1048576"),
                expect=report_only("a.txt", "NATIVE", "U", "E_TOO_LARGE")),
    "K18": dict(fx=("FX-41",), files=lambda g, c: {"a.docx": g.pdf_text(2)}, exit=0,
                expect={"a.docx": native("NONE", "T", "convert_only", outputs=["a.docx.md"], codes=("W_EXT_MISMATCH",))}),
    "K19": dict(fx=("FX-39",), files=lambda g, c: {"a.xyz": g.rng_bytes(100, 39)}, exit=2,
                expect=report_only("a.xyz", "UNSUPPORTED", "X", "E_UNSUPPORTED")),
    "K20": dict(fx=("FX-51",), files=lambda g, c: {"d/n/a.png": g.png_noise(seed=51), "d/.hidden": b"x"}, exit=0,
                skipped=[{"path": "d/.hidden", "code": "W_SKIPPED_HIDDEN"}],
                expect={"d/n/a.png": native("FULL", "S", "convert_and_ocr", total=1, eligible=1,
                                            outputs=["d/n/a.png.md"])}),
}


def reached(klass):
    """class x stage cells this case executes, derived from its expectations (S12 output, S7/S9/S10 units)."""
    files = CASES[klass]["expect"].values()
    cells = set()
    if any(f["outputs"] for f in files):
        cells.add((klass, "S12"))
    if any(f["eligible"] for f in files):
        cells |= {(klass, "S7"), (klass, "S9"), (klass, "S10")}
    return cells


@pytest.fixture(scope="session")
def core_gen():
    """The manifest generators that need the Core-side test deps (python-docx, ...)."""
    spec = importlib.util.spec_from_file_location("mdflow_sweep_gen_core", FIXTURES / "gen_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sweep(tmp_path, cli_command, mock_http, core_gen):
    """Isolated launcher: own HOME/TEMP, loopback-only socket guard that logs every attempt in the child."""
    home, temp = tmp_path / "home", tmp_path / "temp"
    home.mkdir()
    temp.mkdir()
    attempts = tmp_path / "socket-attempts.jsonl"
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("MDFLOW_") and k.upper() != "PYTHONPATH"}
    env.update(HOME=str(home), USERPROFILE=str(home), TMP=str(temp), TEMP=str(temp), PYTHONIOENCODING="utf-8",
               MDFLOW_API_KEY="sweep-secret-key", MDFLOW_BASE_URL=mock_http.base_url)
    guard = f'''
import socket, json
_log = {str(attempts)!r}
def _check(address):
    with open(_log, 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(str(address)) + '\\n')
    if (address[0] if isinstance(address, tuple) else address) != '127.0.0.1':
        raise AssertionError('child attempted forbidden network access')
def _wrap(original):
    def guarded(sock, address, *args, **kwargs):
        _check(address)
        return original(sock, address, *args, **kwargs)
    return guarded
socket.socket.connect = _wrap(socket.socket.connect)
socket.socket.connect_ex = _wrap(socket.socket.connect_ex)
_sendto = socket.socket.sendto
socket.socket.sendto = lambda sock, data, *a: (_check(a[-1]), _sendto(sock, data, *a))[1]
def _dns(original):
    def guarded(host, *args, **kwargs):
        _check((host,))
        return original(host, *args, **kwargs)
    return guarded
for _name in ('getaddrinfo', 'gethostbyname', 'gethostbyname_ex'):
    setattr(socket, _name, _dns(getattr(socket, _name)))
'''

    def run(*args):
        return subprocess.run(cli_command(*args, prelude=guard), env=env, cwd=tmp_path, capture_output=True,
                              text=True, encoding="utf-8", timeout=600)

    def socket_attempts():
        return attempts.read_text(encoding="utf-8").splitlines() if attempts.exists() else []

    return type("Sweep", (), dict(run=staticmethod(run), attempts=staticmethod(socket_attempts), temp=temp))


def _objects(text):
    decoder, values = json.JSONDecoder(), []
    while text.strip():
        value, end = decoder.raw_decode(text.lstrip())
        values.append(value)
        text = text.lstrip()[end:]
    return values


def _files_under(directory):
    directory = Path(directory)
    return sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()) \
        if directory.exists() else []


def _snapshot(directory):
    return {name: ((Path(directory) / name).read_bytes(), (Path(directory) / name).stat().st_mtime_ns)
            for name in _files_under(directory)}


def _events(proc):
    return [json.loads(line) for line in proc.stderr.splitlines() if line.startswith("{")]


def _stages_by_file(events):
    result = {}
    for event in events:
        if event["ev"] == "stage" and event["state"] == "end":
            result.setdefault(event["file"], []).append(event["stage"])
    return result


@pytest.mark.req("REQ-GEN-07", "REQ-GEN-08", "REQ-LKP-01", "REQ-APR-02", "REQ-WRT-01")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-01", "FX-02", "FX-03", "FX-05", "FX-06", "FX-07", "FX-09", "FX-12", "FX-16", "FX-23", "FX-24",
                "FX-28", "FX-30", "FX-35", "FX-38", "FX-39", "FX-41", "FX-42", "FX-43", "FX-51")
@pytest.mark.cells(
    # S12 Write: every output-producing class publishes its .md
    "K01:S12", "K02:S12", "K03:S12", "K04:S12", "K05:S12", "K06:S12", "K07:S12", "K08:S12", "K09:S12",
    "K10:S12", "K11:S12", "K14:S12", "K18:S12", "K20:S12",
    # S7 Lookup / S9 Approve / S10 Transcribe: every unit-bearing class (K14, K20 through their members)
    "K02:S7", "K03:S7", "K04:S7", "K05:S7", "K06:S7", "K07:S7", "K08:S7", "K09:S7", "K14:S7", "K20:S7",
    "K02:S9", "K03:S9", "K04:S9", "K05:S9", "K06:S9", "K07:S9", "K08:S9", "K09:S9", "K14:S9", "K20:S9",
    "K02:S10", "K03:S10", "K04:S10", "K05:S10", "K06:S10", "K07:S10", "K08:S10", "K09:S10", "K14:S10", "K20:S10")
@pytest.mark.parametrize("klass", [
    pytest.param(k, marks=pytest.mark.xfail(strict=True, raises=KnownEngineGap, reason="M2-H: " + CASES[k]["gap"]))
    if "gap" in CASES[k] else k for k in CASES])
def test_T_GEN_85_class_sweep_reaches_exactly_the_stages_the_spec_prescribes(
        request, tmp_path, gen, core_gen, sweep, mock_http, klass):
    case = CASES[klass]
    declared = {tuple(cell.split(":")) for marker in request.node.iter_markers("cells") for cell in marker.args}
    assert declared == set().union(*(reached(k) for k in CASES)), "cells marker and per-class table must agree"
    assert reached(klass) <= declared

    core_gen.scratch = tmp_path / "scratch"
    root, out, cache = tmp_path / "in", tmp_path / "out", tmp_path / "cache"
    for name, data in case["files"](gen, core_gen).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    expect, deferred = case["expect"], []
    egress = {p for p, f in expect.items() if f["eligible"]}
    provider = ("--provider", "openai-compatible", "--model", "sweep-model")
    common = (root, "--cache", cache, *provider, *case.get("args", ()))
    run_args = ("run", *common, "-o", out, "--progress", "jsonl")
    sent_total = lambda: len(mock_http.requests)  # noqa: E731

    def check_run(report, label):
        """Report-level facts; the single known-gap deviation is deferred so every other assertion still runs."""
        actual = {f["path"]: set(i["code"] for i in f["issues"]) for f in report["files"]}
        wanted = {p: f["codes"] for p, f in expect.items()}
        if "gap" in case and (actual != wanted or report["exit"] != case["exit"]):
            deferred.append(f"{label}: codes {actual} exit {report['exit']} != {wanted} / {case['exit']}")
        else:
            assert actual == wanted, label
            assert report["exit"] == case["exit"], label
        assert {f["path"] for f in report["files"]} == set(expect), "every logical source appears exactly once"
        assert report.get("skipped") == case.get("skipped", []), label

    # ---- S9 plan: offline, publishes nothing, one Plan per source with the SPEC's unit counts
    plan = sweep.run("plan", *common)
    plans = {p["approved"]["file"]["path"]: p for p in _objects(plan.stdout)}
    assert set(plans) == set(expect), (plan.stdout[:500], plan.stderr[-500:])
    for path, f in expect.items():
        approved = plans[path]["approved"]
        assert len(approved["units"]) == f["total"], path
        assert (plans[path]["status"]["requests_to_send"] > 0) is (path in egress), path
        assert approved["keys_unique"] == plans[path]["status"]["requests_to_send"]
    assert not out.exists() and mock_http.requests == [] and sweep.attempts() == [], "plan: no output, no egress"
    yes_file = tmp_path / "approved.txt"
    yes_file.write_text("# class sweep\n" + "\n".join(p["plan_hash"] for p in plans.values()) + "\n", encoding="utf-8")

    # ---- S9 without consent: nothing sent, no socket, output still published with approval_required markers
    if egress:
        unconsented = sweep.run(*run_args)
        report, = _objects(unconsented.stdout)
        events = _events(unconsented)
        pending_exit = 3
        if "gap" in case and report["exit"] == 2:  # the known gap's E_CONVERT_FAIL outranks the missing consent (2 > 3)
            deferred.append("unconsented run exits 2 (E_CONVERT_FAIL) instead of 3")
            pending_exit = 2
        assert report["exit"] == pending_exit == unconsented.returncode, (unconsented.stdout[-400:], unconsented.stderr[-400:])
        assert mock_http.requests == [] and sweep.attempts() == [], "no egress without consent"
        by_path = {f["path"]: f for f in report["files"]}
        required = {e["file"]: e for e in events if e["ev"] == "approve_required"}
        assert set(required) == egress
        for path in egress:
            f = by_path[path]
            assert f["consent"] is None and f["requests"]["sent"] == 0 and f["plan_hash"] == plans[path]["plan_hash"]
            assert "E_APPROVAL_REQUIRED" in {i["code"] for i in f["issues"]}
            assert required[path]["plan_hash"] == f["plan_hash"]
            assert f["units"]["transcribed"] == 0 and f["units"]["pending"] == f["units"]["total"]
            text = (out / f["outputs"][0]).read_text(encoding="utf-8")
            assert text.count('reason="approval_required"') == expect[path]["eligible"], path
            assert TRANSCRIPT not in text

    # ---- S6-S12 with consent: first run transcribes and publishes
    first = sweep.run(*run_args, "--yes-file", yes_file, "--approved-by", APPROVER)
    report, = _objects(first.stdout)
    events, calls = _events(first), sent_total()
    assert first.returncode == report["exit"], (first.stdout[-400:], first.stderr[-400:])
    check_run(report, "first run")
    stages = _stages_by_file(events)
    by_path = {f["path"]: f for f in report["files"]}
    expected_sent = 0
    for path, f in expect.items():
        entry, seen = by_path[path], stages[path]
        order = [STAGES.index(s) for s in seen]
        assert order == sorted(order), f"{path}: stages run in pipeline order: {seen}"
        assert MUST[f["action"]] <= set(seen), f"{path}: missing {MUST[f['action']] - set(seen)}"
        assert not NEVER[f["action"]] & set(seen), f"{path}: reached {NEVER[f['action']] & set(seen)}"
        assert (entry["route"], entry["need"], entry["label"], entry["action"]) == (
            f["route"], f["need"], f["label"], f["action"]), path
        assert entry["plan_hash"] == plans[path]["plan_hash"], "the Plan is stable across plan and run"
        units, requests = entry["units"], entry["requests"]
        keys = plans[path]["approved"]["keys_unique"]
        assert (units["total"], units["eligible"], units["cached"], units["transcribed"], units["failed"]) == (
            f["total"], f["eligible"], 0, f["eligible"], 0), f"{path}: S7 miss then S10 transcription"
        assert units["pending"] == f["total"] - f["eligible"]
        assert requests == dict(to_send=keys, sent=keys, ok=keys, failed=0), path
        expected_sent += keys
        if path in egress:
            assert entry["consent"]["plan_hash"] == entry["plan_hash"] and entry["consent"]["by"] == APPROVER
        else:
            assert entry["consent"] is None and keys == 0, "S9 is a no-op without requests to send"
        states = Counter(e["state"] for e in events if e["ev"] == "unit" and e["file"] == path)
        assert states == Counter({k: v for k, v in (("ok", f["eligible"]), ("pending", f["total"] - f["eligible"])) if v})
        assert entry["outputs"] == f["outputs"], f"{path}: S12 outputs"
        for name in f["outputs"]:
            text = (out / name).read_text(encoding="utf-8")
            assert (TRANSCRIPT in text) is (path in egress), f"{path}: provider text assembled into the output"
            assert 'reason="approval_required"' not in text
    assert calls == expected_sent, "provider calls == unique Keys approved"
    attempts = sweep.attempts()
    assert (len(attempts) > 0) is bool(egress) and all("127.0.0.1" in a for a in attempts), \
        "a socket is opened only for approved egress, only to the loopback mock"
    published = _files_under(out)
    outputs = {name for f in expect.values() for name in f["outputs"]}
    media = [n for n in published if n not in outputs]
    assert outputs <= set(published) and all("/media/" in "/" + n for n in media)
    assert len(media) == sum(f["media"] for f in expect.values()), "media published beside the Markdown"
    if all(f["action"] == "report_only" for f in expect.values()):
        assert published == [] and not out.exists(), "report-only sources publish nothing"
    assert list(sweep.temp.iterdir()) == [], "run temp is removed"

    # ---- rerun: every unit cached, 0 provider calls, output byte- and mtime-stable
    snapshot = _snapshot(out)
    rerun = sweep.run(*run_args, "--yes-file", yes_file, "--approved-by", APPROVER)
    again, = _objects(rerun.stdout)
    events = _events(rerun)
    check_run(again, "rerun")
    assert sent_total() == calls and len(sweep.attempts()) == len(attempts), "rerun: 0 provider calls"
    assert _snapshot(out) == snapshot, "rerun publishes nothing new"
    for f in again["files"]:
        f_exp = expect[f["path"]]
        assert f["units"]["cached"] == f_exp["eligible"] and f["units"]["transcribed"] == 0, f["path"]
        assert f["requests"] == dict(to_send=0, sent=0, ok=0, failed=0) and f["consent"] is None
        cached = Counter(e["state"] for e in events if e["ev"] == "unit" and e["file"] == f["path"])
        assert cached["cached"] == f_exp["eligible"] and cached["ok"] == 0
    assert list(sweep.temp.iterdir()) == []
    if deferred:
        raise KnownEngineGap("; ".join(deferred))
