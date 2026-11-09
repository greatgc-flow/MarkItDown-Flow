"""Step 7 RED: the public CLI is exercised through a real isolated interpreter."""

import importlib.metadata
import json
from pathlib import Path
import re
import sys

import pytest


@pytest.mark.req("REQ-PLN-07", "REQ-RPT-01")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-02")
def test_T_CLI_01_plan_is_offline_pretty_per_file_and_publishes_nothing(tmp_path, gen, cli_probe):
    root = tmp_path / "입력 files"
    root.mkdir()
    (root / "a.pdf").write_bytes(gen.pdf_scan(1))
    (root / "b.pdf").write_bytes(gen.pdf_scan(2))
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "sentinel").write_bytes(b"unchanged")
    before = cli_probe.snapshot(tmp_path)
    proc = cli_probe.run("plan", root, "--cache", cache, expected=0)
    plans = cli_probe.objects(proc.stdout)
    assert len(plans) == 2 and "\n  " in proc.stdout, "one pretty Plan per source"
    assert [p["approved"]["file"]["path"] for p in plans] == ["a.pdf", "b.pdf"]
    for plan, total in zip(plans, (1, 2)):
        assert set(plan) == {"v", "approved", "status", "plan_hash"}
        approved = plan["approved"]
        assert len(approved["units"]) == approved["units_total"] == total
        assert approved["provider"]["name"] == "none"
        assert approved["provider"]["egress"] is False and approved["provider"]["destination"] is None
        assert approved["provider"]["model"] == "" and approved["provider"]["retries"] == 0
        assert approved["file"]["sha256"] == gen.sha256((root / approved["file"]["path"]).read_bytes())
        assert approved["keys_unique"] == approved["max_requests"] == total
        assert approved["est_max_cost"] == "0.000000" and approved["cost_known"] is True
        assert all(re.fullmatch("[0-9a-f]{64}", u["raster_sha256"]) for u in approved["units"])
        assert plan["status"]["requests_to_send"] == total
        assert plan["plan_hash"] == gen.sha256(gen.canonical(approved))
    assert proc.stderr == "" and not cli_probe.attempts.exists()
    assert cli_probe.snapshot(tmp_path) == before, "plan publishes no output/cache/ledger/report artifacts"
    assert list(cli_probe.temp.iterdir()) == [], "Convert/Render temp data is removed"
    again = cli_probe.run("plan", root, "--cache", cache, expected=0)
    assert cli_probe.objects(again.stdout) == plans
    assert cli_probe.snapshot(tmp_path) == before


@pytest.mark.req("REQ-GEN-02")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.parametrize("bad_version", ["0.3.4", "0.4.0", "1.0.0"])
def test_T_CLI_02_version_contract_and_rejected_core_before_input_read(tmp_path, gen, cli_probe, bad_version):
    proc = cli_probe.run("version", expected=0)
    value = json.loads(proc.stdout)
    assert set(value) == {"mdflow", "markitdown-gc", "pypdfium2", "pillow", "python", "platform",
                          "protocol", "triage_schema", "exiftool", "exiftool_status", "exiftool_source"}  # R31
    assert value["protocol"] == value["triage_schema"] == 1
    for field in ("mdflow", "markitdown-gc", "pypdfium2", "pillow", "python", "platform"):
        assert isinstance(value[field], str) and value[field]
    for package in ("markitdown-gc", "pypdfium2", "pillow"):
        assert value[package] == importlib.metadata.version(package)
    assert value["python"] == ".".join(map(str, sys.version_info[:3]))
    assert proc.stderr == ""

    source = tmp_path / "unread.txt"
    source.write_bytes(gen.txt_utf8())
    touched = tmp_path / "input-was-read"
    prelude = f'''
import importlib.metadata as metadata, builtins, io, os
_real_version = metadata.version
metadata.version = lambda name: {bad_version!r} if name == 'markitdown-gc' else _real_version(name)
def _track_open(original):
    def tracked(path, *args, **kwargs):
        if isinstance(path, (str, bytes, os.PathLike)) and os.path.realpath(path) == {str(source.resolve())!r}:
            with _original_open({str(touched)!r}, 'w') as marker:
                marker.write('read')
            raise AssertionError('input read before Core version gate')
        return original(path, *args, **kwargs)
    return tracked
_original_open = builtins.open
builtins.open = _track_open(builtins.open)
io.open = _track_open(io.open)
os.open = _track_open(os.open)
'''
    rejected = cli_probe.run("run", source, "-o", tmp_path / "out", prelude=prelude, expected=1)
    assert "E_CORE_VERSION" in rejected.stdout + rejected.stderr
    assert "Traceback" not in rejected.stderr and not touched.exists()
    assert not (tmp_path / "out").exists() and list(cli_probe.temp.iterdir()) == []


@pytest.mark.req("REQ-CLS-05")
@pytest.mark.cov("S0", "FM0")
def test_T_CLI_03_selftest_classifies_bundled_pdf_and_png_and_checks_goldens(tmp_path, cli_probe):
    seen = tmp_path / "classified-formats.jsonl"
    prelude = f'''
from mdflow import classify
import json
_classify = classify.classify
def observed(sniff, triage):
    with open({str(seen)!r}, 'a', encoding='utf-8') as log:
        log.write(json.dumps(sniff['format']) + '\\n')
    return _classify(sniff, triage)
classify.classify = observed
'''
    cli_probe.run("selftest", prelude=prelude, expected=0)
    formats = [json.loads(line) for line in seen.read_text(encoding="utf-8").splitlines()]
    assert "pdf" in formats and "png" in formats
    assert not cli_probe.attempts.exists()
    changed = '''
from mdflow import classify
_classify = classify.classify
def wrong(sniff, triage):
    value = dict(_classify(sniff, triage))
    value['label'] = 'X' if value['label'] != 'X' else 'T'
    return value
classify.classify = wrong
'''
    failed = cli_probe.run("selftest", prelude=changed)
    assert failed.returncode != 0 and "Traceback" not in failed.stderr, "selftest compares actual classifications"


@pytest.mark.req("REQ-RPT-03")
@pytest.mark.cov("S0", "FM1")
@pytest.mark.parametrize("extra", [
    ["--unknown"], ["--api-key", "forbidden"], ["--max-bytes", "268435457"],
    ["--max-bytes", "many"], ["--dpi", "201"], ["--provider", "made-up"],
    ["--min-priority", "high"], ["--progress", "xml"], ["--prompt-version", "missing"],
    ["--command-egress", "maybe"], ["--cost-hint", "NaN"], ["--cost-hint", "-0.01"],
    ["--max-units", "-1"], ["--zip-depth", "-1"], ["--zip-entries", "-1"],
    ["--zip-total-bytes", "-1"], ["--max-pixels", "-1"], ["--approve-threshold", "-1"],
])
def test_T_CLI_04_invalid_options_exit_one_with_usage_before_processing(tmp_path, gen, cli_probe, extra):
    source = tmp_path / "source.txt"
    source.write_bytes(gen.txt_utf8())
    out, cache = tmp_path / "out", tmp_path / "cache"
    proc = cli_probe.run("run", source, "-o", out, "--cache", cache, *extra, expected=1)
    assert "E_USAGE" in proc.stdout + proc.stderr
    assert "Traceback" not in proc.stderr
    assert not list(out.rglob("*.md")) and not list(cache.rglob("*"))
    assert not cli_probe.attempts.exists()
    if extra == ["--unknown"]:
        for command in (("run", source), ("run", "-o", out), ("plan",), ("classify",), ("unknown-command",)):
            invalid = cli_probe.run(*command, expected=1)
            assert "E_USAGE" in invalid.stdout + invalid.stderr and "Traceback" not in invalid.stderr


@pytest.mark.req("REQ-RPT-01", "REQ-GEN-09")
@pytest.mark.cov("S13", "FM0")
@pytest.mark.fx("FX-03")
def test_T_CLI_05_real_module_run_progress_order_report_file_and_quiet_mode(tmp_path, gen, cli_probe, mock_http):
    source = tmp_path / "한글 mixed.pdf"
    source.write_bytes(gen.pdf_mixed())
    out, cache, report = tmp_path / "out", tmp_path / "cache", tmp_path / "report.json"
    args = ("run", source, "-o", out, "--cache", cache, "--report", report)
    proc = cli_probe.run(*args, "--progress", "jsonl")
    value = cli_probe.report(proc, 0)
    assert json.loads(report.read_text(encoding="utf-8")) == value
    events = cli_probe.events(proc)
    from mdflow.contracts import CODES
    assert all(event.get("code") is None or event["code"] in CODES for event in events)
    assert events[0]["ev"] == "run_start" and events[-1]["ev"] == "run_end"
    assert events[0]["files"] == 1 and events[0]["provider"] == "none"
    assert events[-1]["exit"] == 0 and events[-1]["provider_calls"] == 0
    assert events[-1]["files_ok"] == 1 and events[-1]["files_failed"] == 0
    names = [event["ev"] for event in events]
    assert names.count("file_start") == names.count("classified") == names.count("file_end") == 1
    assert names.index("file_start") < names.index("classified") < names.index("file_end")
    file_events = [e for e in events if "file" in e]
    assert all(e["file"] == source.name for e in file_events)
    classified = next(e for e in events if e["ev"] == "classified")
    f = value["files"][0]
    assert {k: classified[k] for k in ("route", "need", "label", "action")} == {
        k: f[k] for k in ("route", "need", "label", "action")}
    stages = [e for e in events if e["ev"] == "stage"]
    stage_order = "sniff triage classify select convert render lookup plan approve transcribe assemble write".split()
    assert stages and all(e["stage"] in stage_order and e["state"] in {"start", "end"} for e in stages)
    assert all(isinstance(e["ms"], (int, float)) and e["ms"] >= 0 for e in stages if e["state"] == "end")
    ended = [stage_order.index(e["stage"]) for e in stages if e["state"] == "end"]
    assert ended == sorted(ended)
    units = [e for e in events if e["ev"] == "unit"]
    assert len(units) == f["units"]["total"]
    assert all(e["state"] == "pending" and e["code"] is None for e in units)
    end = next(e for e in events if e["ev"] == "file_end")
    assert end["outputs"] == f["outputs"]
    assert end["units"] == dict(total=f["units"]["total"], done=0,
                                pending=f["units"]["pending"], failed=0)
    before = cli_probe.snapshot(out), cli_probe.snapshot(cache)
    quiet = cli_probe.run(*args, "--progress", "none")
    cli_probe.report(quiet, 0)
    assert quiet.stderr == ""
    assert (cli_probe.snapshot(out), cli_probe.snapshot(cache)) == before
    assert list(cli_probe.temp.iterdir()) == [] and not cli_probe.attempts.exists()
    _other_commands(source, cache, cli_probe)
    _exit_precedence(tmp_path, gen, cli_probe, mock_http)


def _other_commands(source, cache, cli_probe):
    providers = json.loads(cli_probe.run("providers", expected=0).stdout)
    assert isinstance(providers, list) and {p["name"] for p in providers} == {"none", "openai-compatible", "command"}
    fields = {"name", "model", "egress", "cost_hint", "max_batch", "retries", "destination",
              "command_env_names", "accepts"}
    assert all(fields <= set(p) for p in providers)
    first = cli_probe.run("classify", source, expected=0)
    second = cli_probe.run("classify", source, expected=0)
    value = json.loads(first.stdout)
    assert set(value) == {"sniff", "triage", "classification"}
    assert value == json.loads(second.stdout) and value["sniff"]["format"] == "pdf"
    assert value["classification"]["route"] == "NATIVE" and value["triage"]["schema_version"] == 1
    before = cli_probe.snapshot(cache)
    assert isinstance(json.loads(cli_probe.run("cache", "stats", "--cache", cache, expected=0).stdout), dict)
    assert cli_probe.snapshot(cache) == before
    cli_probe.run("cache", "clear", "--cache", cache, expected=0)
    assert cache.is_dir() and list(cache.iterdir()) == []
    assert not cli_probe.attempts.exists()


def _exit_precedence(tmp_path, gen, cli_probe, mock_http):
    root = tmp_path / "precedence-inputs"
    root.mkdir()
    (root / "a.png").write_bytes(gen.png_noise(seed=401))
    (root / "b.png").write_bytes(gen.png_noise(seed=402))
    args = ("run", root, "-o", tmp_path / "precedence-out", "--cache", tmp_path / "precedence-cache",
            "--provider", "openai-compatible", "--model", "test-model", "--progress", "jsonl")
    env = {"MDFLOW_API_KEY": "precedence-secret", "MDFLOW_BASE_URL": mock_http.base_url}
    initial = cli_probe.run(*args, env=env, allowed_hosts=("127.0.0.1",))
    pending = cli_probe.report(initial, 3)
    chosen = pending["files"][0]["plan_hash"]
    assert mock_http.requests == []
    mock_http.reply(("json", 400, {"error": {"message": "fixture provider failure"}}))
    failed = cli_probe.run(*args, "--yes", chosen, env=env, allowed_hosts=("127.0.0.1",))
    value = cli_probe.report(failed, 4)  # provider failure outranks the other file's missing consent
    codes = {issue["code"] for f in value["files"] for issue in f["issues"]}
    assert {"E_PROVIDER_HTTP", "E_APPROVAL_REQUIRED"} <= codes
    (root / "0-empty.pdf").write_bytes(b"")
    mock_http.reply(("json", 400, {"error": {"message": "fixture provider failure"}}))
    corrupt = cli_probe.run(*args, "--yes", chosen, env=env, allowed_hosts=("127.0.0.1",))
    value = cli_probe.report(corrupt, 2)
    codes = {issue["code"] for f in value["files"] for issue in f["issues"]}
    assert {"E_CORRUPT", "E_PROVIDER_HTTP", "E_APPROVAL_REQUIRED"} <= codes
    calls = len(mock_http.requests)
    usage = cli_probe.run(*args, "--yes", chosen, "--dpi", "999", env=env,
                          allowed_hosts=("127.0.0.1",), expected=1)
    assert "E_USAGE" in usage.stdout + usage.stderr and len(mock_http.requests) == calls


@pytest.mark.req("REQ-SEC-10")
@pytest.mark.cov("S0", "FM9")
def test_T_SEC_10_trust_command_help_discloses_user_privileges_per_unit(cli_probe):
    proc = cli_probe.run("run", "--help", expected=0)
    text = " ".join(proc.stdout.split())
    assert "--trust-command" in text
    assert re.search(r"(?i)(user.s|your|current user.s) privileges", text)
    assert re.search(r"(?i)(every|each) (OCR )?unit", text)
