"""Fixtures for the step 5/6 IO red suite.

FX-61 mock provider, FX-62 mock HTTP server (127.0.0.1 only, behind the socket guard), FX-63 child
scripts (gen_io.CHILD_SOURCES) and a fake Core. The real Core is never imported by these tests: stages
must resolve ``markitdown`` / ``markitdown.ocr_triage`` at call time so ``sys.modules`` substitution works.
"""

import importlib.util
import json
import socketserver
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

GEN_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "gen_io.py"


@pytest.fixture(scope="session")
def gen():
    spec = importlib.util.spec_from_file_location("mdflow_gen_io", GEN_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def run_temp(tmp_path):
    path = tmp_path / "run-temp"
    path.mkdir()
    return path


@pytest.fixture
def out_dir(tmp_path):
    path = tmp_path / "out"
    path.mkdir()
    return path


@pytest.fixture
def sleeps(monkeypatch):
    """Record time.sleep calls instead of sleeping (provider back-off)."""
    calls = []
    monkeypatch.setattr(time, "sleep", lambda seconds: calls.append(seconds))
    return calls


@pytest.fixture
def mock_provider(gen):
    """FX-61 factory: mock_provider(**ProviderMeta overrides) -> ScriptedProvider."""
    return gen.ScriptedProvider


class FakeCore:
    """Records every call made to the fake ``markitdown`` package."""

    def __init__(self):
        self.triage_calls = []
        self.triage_impl = self.default_report
        self.init_calls = []
        self.convert_calls = []
        self.forbidden_calls = []
        self.convert_text = "converted by fake core"

    @staticmethod
    def default_report(*args, **kwargs):
        return {
            "schema_version": 1, "rules_version": "1", "decision": "no_candidates",
            "coverage": {"state": "complete"}, "candidates": [], "issues": [],
        }


@pytest.fixture
def fake_core(monkeypatch):
    core = FakeCore()
    package = types.ModuleType("markitdown")
    package.__path__ = []
    triage_module = types.ModuleType("markitdown.ocr_triage")

    def triage(*args, **kwargs):
        core.triage_calls.append((args, kwargs))
        return core.triage_impl(*args, **kwargs)

    class StreamInfo:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __repr__(self):
            return "StreamInfo(%r)" % (self.kwargs,)

    class MarkItDown:
        def __init__(self, *args, **kwargs):
            core.init_calls.append((args, kwargs))

        def _result(self):
            return types.SimpleNamespace(markdown=core.convert_text, text_content=core.convert_text)

        def convert_stream(self, stream, *args, **kwargs):
            core.convert_calls.append(((stream,) + args, kwargs))
            return self._result()

        def convert(self, source, *args, **kwargs):
            core.forbidden_calls.append(("convert", source))
            return self._result()

        def convert_local(self, source, *args, **kwargs):
            core.forbidden_calls.append(("convert_local", source))
            return self._result()

        def convert_uri(self, source, *args, **kwargs):
            core.forbidden_calls.append(("convert_uri", source))
            return self._result()

        def convert_url(self, source, *args, **kwargs):
            core.forbidden_calls.append(("convert_url", source))
            return self._result()

    triage_module.triage = triage
    package.ocr_triage = triage_module
    package.MarkItDown = MarkItDown
    package.StreamInfo = StreamInfo
    monkeypatch.setitem(sys.modules, "markitdown", package)
    monkeypatch.setitem(sys.modules, "markitdown.ocr_triage", triage_module)
    return core


class CoreSpy:
    """Replacement for ``mdflow.convert.core_convert``; ``behavior(spy, index, data, ext, extract_media, media_base_dir)``."""

    def __init__(self):
        self.calls = []
        self.behavior = None

    def __call__(self, data, ext, *, extract_media=None, media_base_dir=None):
        self.calls.append({"data": data, "ext": ext, "extract_media": extract_media, "media_base_dir": media_base_dir})
        index = len(self.calls) - 1
        if self.behavior is not None:
            return self.behavior(self, index, data, ext, extract_media, media_base_dir)
        return f"converted-{index + 1}"


@pytest.fixture
def core_spy(monkeypatch):
    from mdflow import convert

    spy = CoreSpy()
    monkeypatch.setattr(convert, "core_convert", spy)
    return spy


def chat_ok(text):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name = "127.0.0.1"
        self.server_port = self.server_address[1]

    def handle_error(self, request, client_address):
        pass


class MockHttp:
    """FX-62. Steps: ('json', status, obj) | ('raw', status, bytes, headers) | ('redirect', status, location)
    | ('hang',) | ('echo_auth', status). With no script left, answers 200 with the ``default_text``."""

    def __init__(self):
        self.requests = []
        self.script = []
        self.default_text = "mock transcription"
        self.release = threading.Event()
        self._lock = threading.Lock()
        self.server = None
        self.thread = None

    def reply(self, *steps):
        self.script.extend(steps)

    @property
    def port(self):
        return self.server.server_address[1]

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}/v1"

    @property
    def endpoint_path(self):
        return "/v1/chat/completions"

    def _next(self):
        with self._lock:
            return self.script.pop(0) if self.script else ("json", 200, chat_ok(self.default_text))

    def start(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length)
                outer.requests.append({
                    "method": "POST", "path": self.path, "body": body,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                })
                step = outer._next()
                if step[0] == "hang":
                    outer.release.wait(30)
                    return
                if step[0] == "redirect":
                    self.send_response(step[1])
                    self.send_header("Location", step[2])
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                headers = {}
                if step[0] == "json":
                    status, payload = step[1], json.dumps(step[2]).encode()
                elif step[0] == "raw":
                    status, payload, headers = step[1], step[2], dict(step[3]) if len(step) > 3 else {}
                else:  # echo_auth: hostile server reflecting the credential
                    auth = self.headers.get("Authorization", "")
                    status = step[1]
                    payload = json.dumps({"error": {"message": "rejected credential " + auth}}).encode()
                    headers = {"X-Echo-Auth": auth}
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                outer.requests.append({"method": "GET", "path": self.path, "body": b"", "headers": {}})
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

        self.server = _Server(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    def stop(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)


@pytest.fixture
def mock_http(socket_guard):
    server = MockHttp()
    server.start()
    socket_guard.allowed_hosts.add("127.0.0.1")
    yield server
    server.stop()
