"""Step 7 RED: real cooperative signals and forced process death, no sleep-to-guess race."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time

import pytest


@contextmanager
def _process(cli_probe, *args, prelude=""):
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {}
    proc = subprocess.Popen(cli_probe.argv(*args, prelude=prelude), env=cli_probe.env,
                            cwd=cli_probe.home.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", **flags)
    try:
        yield proc
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.communicate(timeout=10)


def _wait_ready(proc, marker):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if marker.exists():
            try:
                return json.loads(marker.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass  # file creation and close can straddle one polling interval
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=5)
            raise AssertionError(f"engine exited before readiness: {proc.returncode}\n{stdout}\n{stderr}")
        time.sleep(0.01)
    raise AssertionError("engine never reached the instrumented request/publication boundary")


@pytest.mark.req("REQ-GEN-09")
@pytest.mark.cov("S0", "FM7")
@pytest.mark.fx("FX-03", "FX-61", "FX-63", "FX-65")
@pytest.mark.parametrize("kind", ["break"] if os.name == "nt" else ["interrupt", "terminate"])
def test_T_GEN_09_cooperative_cancel_reports_130_removes_temp_and_command_child(tmp_path, gen, cli_probe, kind):
    root = tmp_path / "input"
    root.mkdir()
    (root / "a-bad.pdf").write_bytes(gen.pdf_corrupt())  # cancellation overrides an earlier exit-2 issue
    (root / "b-scan.png").write_bytes(gen.png_noise(seed=63))
    marker, script = tmp_path / "request-ready.json", tmp_path / "one_second_request.py"
    script.write_text(
        "import json, os, sys, time\n"
        "with open(sys.argv[1], 'w', encoding='utf-8') as f:\n"
        "    json.dump({'pid': os.getpid(), 'raster': sys.argv[2]}, f)\n"
        "time.sleep(1)\nprint('completed mock request')\n", encoding="utf-8")
    template = gen.command_template(script, shlex.quote(marker.as_posix()), "{input}")
    report, out, cache = tmp_path / "cancelled.json", tmp_path / "out", tmp_path / "cache"
    args = ("run", root, "-o", out, "--cache", cache, "--report", report, "--progress", "jsonl",
            "--provider", "command", "--model", "one-second", "--command", template,
            "--command-egress", "false", "--trust-command")
    cli_probe.env["MDFLOW_TIMEOUT_S"] = "2"
    child = None
    try:
        with _process(cli_probe, *args) as proc:
            ready = _wait_ready(proc, marker)
            child = ready["pid"]
            assert gen.pid_alive(child) and Path(ready["raster"]).exists()
            proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else
                             signal.SIGINT if kind == "interrupt" else signal.SIGTERM)
            stdout, stderr = proc.communicate(timeout=10)
            result = subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
            value = cli_probe.report(result, 130)
            assert json.loads(report.read_text(encoding="utf-8")) == value
            events = cli_probe.events(result)
            assert events[-1]["ev"] == "run_end" and events[-1]["exit"] == 130
            assert any(i["code"] == "E_CORRUPT" for f in value["files"] for i in f["issues"])
            assert not gen.pid_alive(child), "cooperative cancellation reaps its own command child"
            assert not Path(ready["raster"]).exists() and list(cli_probe.temp.iterdir()) == []
            for f in value["files"]:
                for output in f["outputs"]:
                    data = (out / output).read_bytes()
                    assert data.startswith(b"---\n") and b"content_sha256:" in data
            assert not list(out.rglob("*.tmp-*")), "handled cancellation removes publication temps"
    finally:
        # Harness cleanup is unconditional, including RED and broken cancellation implementations.
        if child is not None and gen.pid_alive(child):
            os.kill(child, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)


@pytest.mark.req("REQ-GEN-09", "REQ-GEN-05")
@pytest.mark.cov("S0", "FM7")
@pytest.mark.fx("FX-03", "FX-65")
def test_T_GEN_12_forced_kill_has_os_status_no_report_and_recovers_without_cleanup(tmp_path, gen, cli_probe):
    source = tmp_path / "scan.png"
    source.write_bytes(gen.png_noise(seed=65))
    out, cache, report = tmp_path / "out", tmp_path / "cache", tmp_path / "run-report.json"
    target, marker = out / "scan.png.md", tmp_path / "publication-ready.json"
    prelude = f'''
import os, json, time
_replace = os.replace
def blocked_replace(source, destination, *args, **kwargs):
    if os.path.realpath(destination) == {str(target.resolve())!r}:
        with open({str(marker)!r}, 'w', encoding='utf-8') as ready:
            json.dump({{'temp': str(source)}}, ready)
        time.sleep(60)
    return _replace(source, destination, *args, **kwargs)
os.replace = blocked_replace
'''
    args = ("run", source, "-o", out, "--cache", cache, "--report", report)
    with _process(cli_probe, *args, prelude=prelude) as proc:
        ready = _wait_ready(proc, marker)
        temporary = Path(ready["temp"])
        assert temporary.parent == target.parent and temporary.name.startswith(target.name + ".tmp-")
        assert temporary.read_bytes().startswith(b"---\n") and not target.exists()
        proc.kill()
        stdout, stderr = proc.communicate(timeout=10)
        assert proc.returncode != 0 and proc.returncode != 130
        if os.name == "posix":
            assert proc.returncode == -signal.SIGKILL
        assert stdout == "" and not report.exists(), "forced death never publishes a run report"
    assert not target.exists() and temporary.exists(), "unpublished temp survived the forced kill"
    # A rerun must ignore stale bytes rather than treating them as output or a ledger entry.
    temporary.write_bytes(b"poisoned stale publication")
    stale_cache = cache / "units" / "aa" / (("a" * 64) + ".json.tmp-999-1")
    stale_cache.parent.mkdir(parents=True, exist_ok=True)
    stale_cache.write_bytes(b"invalid stale ledger, never parse me")
    rerun = cli_probe.run(*args)
    recovered = cli_probe.report(rerun, 0)
    assert recovered["files"][0]["outputs"] == [target.name]
    assert target.read_bytes().startswith(b"---\n") and b"poisoned stale" not in target.read_bytes()
    assert all(i["code"] != "W_CACHE_CORRUPT" for f in recovered["files"] for i in f["issues"])
    assert not cli_probe.attempts.exists()
    cli_probe.run("cache", "clear", "--cache", cache, expected=0)
    assert cache.is_dir() and list(cache.iterdir()) == []
