"""Step 7 integration fixtures. Production stages stay real unless explicitly injected."""

from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="session")
def step7_data(repo_root):
    path = repo_root / "engine/tests/fixtures/gen_core.py"
    spec = importlib.util.spec_from_file_location("mdflow_step7_temps", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def step7_temps(repo_root, step7_data):
    # Reuse the established fixture workaround for Python 3.15 Windows DACLs.
    return step7_data.WorkspaceTemps(repo_root / "build/trace/redgreen/step7-tmp")


@pytest.fixture
def tmp_path(step7_temps, request):
    return step7_temps.mktemp(request.node.name)


def snapshot(directory):
    directory = Path(directory)
    return {p.relative_to(directory).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest(),
                                                p.stat().st_mtime_ns)
            for p in directory.rglob("*") if p.is_file()}


def decode_objects(text):
    """Decode consecutive pretty JSON objects without imposing a JSONL limit on Plans."""
    decoder, values = json.JSONDecoder(), []
    while text.strip():
        value, end = decoder.raw_decode(text.lstrip())
        values.append(value)
        text = text.lstrip()[end:]
    return values


def assert_report(value, expected_exit=None):
    assert set(value) == {"v", "mdflow", "started", "finished", "options", "files", "skipped", "exit"}
    assert value["v"] == 1
    for field in ("started", "finished"):
        stamp = datetime.fromisoformat(value[field])
        assert stamp.tzinfo is not None and stamp.microsecond == 0
    assert datetime.fromisoformat(value["finished"]) >= datetime.fromisoformat(value["started"])
    if expected_exit is not None:
        assert value["exit"] == expected_exit
    required = {"path", "root", "sha256", "bytes", "format", "route", "need", "label", "action",
                "decision", "coverage_state", "units", "requests", "placements", "issues",
                "outputs", "plan_hash", "consent", "triage"}
    assert all(set(f) == required for f in value["files"])
    assert all(count == 1 for count in Counter((f["root"], f["path"]) for f in value["files"]).values())
    for f in value["files"]:
        u, r = f["units"], f["requests"]
        assert set(u) == {"total", "eligible", "cached", "transcribed", "pending", "failed"}
        assert set(r) == {"to_send", "sent", "ok", "failed"}
        assert all(type(n) is int and n >= 0 for n in [*u.values(), *r.values(), f["placements"]])
        assert u["total"] == u["eligible"] + u["pending"]
        assert u["eligible"] == u["cached"] + u["transcribed"] + u["failed"]
        assert all(not Path(p).is_absolute() and "\\" not in p for p in f["outputs"])
        assert f["route"] in {"NATIVE", "CONTAINER", "LEGACY", "PROTECTED", "UNSUPPORTED"}
        assert f["need"] in {"NONE", "PARTIAL", "FULL", "UNKNOWN"}


@pytest.fixture
def flow(tmp_path, gen, core_spy):
    from mdflow import orchestrate

    inputs = tmp_path / "input"
    inputs.mkdir()
    options = dict(out=tmp_path / "out", cache=tmp_path / "cache", provider="none", model=None,
                   dpi=200, min_priority="low", max_units=200, approve_threshold=20, force=False,
                   prompt_version="p1", max_bytes=209715200, max_pixels=50000000,
                   zip_depth=3, zip_entries=1000, zip_total_bytes=1073741824,
                   sensitive=[], yes=False, yes_hashes=[], approved_by=None, progress="none")

    def put(name, data):
        path = inputs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run(roots=None, *, provider=None, **changes):
        opts = dict(options, **changes)
        if provider is not None:
            opts.update(provider=provider.meta["name"], model=provider.meta["model"])
        return orchestrate.run(roots or [inputs], opts, provider=provider, now=gen.NOW)

    return SimpleNamespace(put=put, run=run, options=options, inputs=inputs,
                           out=options["out"], cache=options["cache"], snapshot=snapshot,
                           assert_report=assert_report, core=core_spy)


@pytest.fixture
def cli_probe(tmp_path, cli_command):
    """Isolate HOME/temp/config; block all network except explicitly allowed loopback mocks.

    The guard executes inside the subprocess: pytest's parent socket monkeypatch
    cannot protect ``python -I``. Each attempt is recorded before any connection.
    """
    home, temp = tmp_path / "home", tmp_path / "temp"
    home.mkdir()
    temp.mkdir()
    attempts = tmp_path / "socket-attempts.jsonl"
    environment = {k: v for k, v in os.environ.items()
                   if not k.upper().startswith("MDFLOW_") and k.upper() != "PYTHONPATH"}
    environment.update(HOME=str(home), USERPROFILE=str(home), TMP=str(temp), TEMP=str(temp),
                       PYTHONIOENCODING="utf-8")

    def argv(*args, prelude="", allowed_hosts=()):
        guard = f'''
import socket
_attempt_path = {str(attempts)!r}
_allowed_hosts = {tuple(allowed_hosts)!r}
def _check(address):
    import json
    with open(_attempt_path, 'a', encoding='utf-8') as log:
        log.write(json.dumps(str(address)) + '\\n')
    host = address[0] if isinstance(address, tuple) else address
    if host not in _allowed_hosts:
        raise AssertionError('child attempted forbidden network access')
def _wrap(original):
    def guarded(sock, address, *args, **kwargs):
        _check(address)
        return original(sock, address, *args, **kwargs)
    return guarded
socket.socket.connect = _wrap(socket.socket.connect)
socket.socket.connect_ex = _wrap(socket.socket.connect_ex)
_sendto = socket.socket.sendto
def _guard_sendto(sock, data, *args):
    _check(args[-1])
    return _sendto(sock, data, *args)
socket.socket.sendto = _guard_sendto
def _wrap_dns(original):
    def guarded(host, *args, **kwargs):
        _check((host,))
        return original(host, *args, **kwargs)
    return guarded
for _name in ('getaddrinfo', 'gethostbyname', 'gethostbyname_ex'):
    setattr(socket, _name, _wrap_dns(getattr(socket, _name)))
'''
        return cli_command(*args, prelude=guard + "\n" + prelude)

    def run(*args, env=None, prelude="", allowed_hosts=(), expected=None):
        proc = subprocess.run(argv(*args, prelude=prelude, allowed_hosts=allowed_hosts),
                              env=dict(environment, **(env or {})), cwd=tmp_path,
                              capture_output=True, text=True, encoding="utf-8", timeout=30)
        if expected is not None:
            assert proc.returncode == expected, (proc.stdout, proc.stderr)
        return proc

    def report(proc, expected):
        assert proc.returncode == expected, (proc.stdout, proc.stderr)
        values = decode_objects(proc.stdout)
        assert len(values) == 1, "run stdout is exactly one JSON object"
        assert_report(values[0], expected)
        return values[0]

    def events(proc):
        lines = proc.stderr.splitlines()
        assert all(len(line.encode("utf-8")) <= 65536 for line in lines)
        values = [json.loads(line) for line in lines]
        assert all(v["v"] == 1 and datetime.fromisoformat(v["ts"]).tzinfo for v in values)
        return values

    return SimpleNamespace(run=run, argv=argv, env=environment, home=home, temp=temp,
                           attempts=attempts, report=report, events=events,
                           objects=decode_objects, snapshot=snapshot)
