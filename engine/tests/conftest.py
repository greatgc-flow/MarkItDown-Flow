"""Requirement registration, offline isolation and deterministic test time."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys

import pytest

# Installed-wheel CI has no source injection, including child launchers.
INSTALLED_MODE = os.environ.get('MDFLOW_TEST_INSTALLED') == '1'
if not INSTALLED_MODE:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def assert_installed_import():
    import mdflow
    location = Path(mdflow.__file__).resolve()
    source = Path(__file__).resolve().parents[1] / 'src'
    assert location.is_relative_to(Path(sys.prefix).resolve()) and 'site-packages' in location.parts
    assert not location.is_relative_to(source), location



def _sandbox_temp_prelude():
    """Explicit test-only bridge for Python 3.15's restricted-token Windows DACL.

    Production chmod/mkdir calls and real desktop security evidence stay separate.
    The bridge is opt-in, Windows-only and limited to test paths inside the repo.
    """
    return '''
import os, pathlib
if os.name == 'nt' and os.environ.get('M1_WINDOWS_TEST_TEMP') == '1':
    _test_root = pathlib.Path(%r).resolve()
    _mkdir = os.mkdir
    def _test_mkdir(path, mode=0o777, *, dir_fd=None):
        target = pathlib.Path(path).absolute()
        if mode == 0o700 and target.is_relative_to(_test_root):
            mode = 0o777
        return _mkdir(path, mode, dir_fd=dir_fd)
    os.mkdir = _test_mkdir
''' % str(Path(__file__).resolve().parents[2])


def pytest_sessionstart(session):
    if INSTALLED_MODE:
        assert_installed_import()
        target = os.environ.get('MDFLOW_CI_TARGET')
        if target:
            destination = REPO_ROOT / 'build/trace' / f'runtime-{target}-py{sys.version_info.major}.{sys.version_info.minor}.json'
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(dict(installed=True, commit=os.environ.get('GITHUB_SHA'),
                                                  python=sys.version, prefix=sys.prefix)), encoding='utf-8')
    if os.environ.get('M1_WINDOWS_TEST_TEMP') == '1':
        exec(_sandbox_temp_prelude(), {})

REPO_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("mdflow_trace", REPO_ROOT / "tools/trace.py")
trace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trace)


def pytest_configure(config):
    for name, description in {
        "req": "normative requirement IDs",
        "cov": "one primary stage and failure-mode cell",
        "fx": "fixture IDs or all",
        "plat": "posix or windows; absent on other platforms",
        "scope": "schema for common contracts; execution for actual fixture consumption",
        "cells": "extra class x stage cells (\"K02:S7\") a class sweep executes besides its one primary cov cell (M2-H)",
    }.items():
        config.addinivalue_line("markers", f"{name}(*args): {description}")


def pytest_addoption(parser):
    parser.addoption('--mdflow-collection-output', help='internal full-suite collection destination')


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_collection_modifyitems(config, items):
    # Snapshot before pytest's -k/-m filters: a passing subset cannot stand in
    # for the complete collected parameter family in release evidence.
    collected = list(items)
    yield
    admitted = set(items)
    selected, deselected, records = [], [], []
    for item in collected:
        markers = {
            name: [list(marker.args) for marker in item.iter_markers(name)]
            for name in ("req", "cov", "fx", "plat", "scope", "cells")
        }
        tid = trace.test_id(item.originalname or item.name)
        nodeid = item.path.relative_to(REPO_ROOT).as_posix() + '::' + item.nodeid.split('::', 1)[1]
        if item.get_closest_marker('release'):
            markers['release'] = [[]]
        # Direct properties also work with JUnit xunit2 (no record_property warning).
        item.user_properties.extend([
            ("tid", tid),
            ('nodeid', nodeid),
            *[(name, json.dumps(groups, separators=(",", ":"))) for name, groups in markers.items()
              if name != "cells" or groups],
        ])
        record = {"nodeid": nodeid, "tid": tid, "markers": markers, 'selected': False}
        records.append(record)
        platforms = [value for group in markers["plat"] for value in group]
        if platforms and (len(platforms) != 1 or platforms[0] not in {"posix", "windows"}):
            raise pytest.UsageError(f"Invalid plat marker: {item.nodeid}")
        current = "windows" if os.name == "nt" else "posix"
        if item in admitted:
            if platforms and current not in platforms:
                deselected.append(item)
            else:
                selected.append(item)
                record['selected'] = True
    config._mdflow_registry = records
    items[:] = selected
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    canonical = config.getoption('--mdflow-collection-output')
    if canonical:
        if not config.getoption('collectonly') or config.args != ['engine/tests']:
            raise pytest.UsageError('canonical collection requires the full engine/tests root and --collect-only')
        trace.write_collection(Path(canonical), records, os.environ.get('GITHUB_SHA', ''))
        return
    trace.write_registry(REPO_ROOT, trace.requirement_registry(REPO_ROOT), records)
    junit = config.getoption('xmlpath')
    if junit:
        destination = Path(junit)
        trace.collect_complete(trace.collection_path(destination.parent, destination.name), os.environ.get('GITHUB_SHA', ''))
        trace.write_execution_registry(destination.parent, destination.name, records, os.environ.get('GITHUB_SHA', ''))


@pytest.fixture(scope="session")
def trace_module():
    return trace


@pytest.fixture(scope="session")
def repo_root():
    return REPO_ROOT


@pytest.fixture(scope="session")
def test_registry():
    # Source discovery makes the meta oracle independent of -k/-m selection.
    return trace.discover_tests(REPO_ROOT)


class SocketGuard:
    def __init__(self):
        self.allowed_hosts = set()
        self.attempts = []

    def check(self, address):
        self.attempts.append(address)
        host = address[0] if isinstance(address, tuple) else address
        if host not in self.allowed_hosts:
            raise AssertionError("Network access blocked by the test socket guard")


@pytest.fixture(autouse=True)
def socket_guard(monkeypatch):
    """Block outbound sockets and DNS; mocks may explicitly allow loopback hosts."""
    guard = SocketGuard()

    def wrap_address(original):
        def guarded(sock, address, *args):
            guard.check(address)
            return original(sock, address, *args)
        return guarded

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, wrap_address(getattr(socket.socket, name)))
    original_sendto = socket.socket.sendto

    def sendto(sock, data, *args):
        guard.check(args[-1])
        return original_sendto(sock, data, *args)

    monkeypatch.setattr(socket.socket, "sendto", sendto)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex"):
        original = getattr(socket, name)

        def lookup(host, *args, _original=original, **kwargs):
            guard.check((host,))
            return _original(host, *args, **kwargs)

        monkeypatch.setattr(socket, name, lookup)
    return guard


class FakeClock:
    def __init__(self):
        self._now = datetime(2026, 11, 9, tzinfo=timezone.utc)
        self._elapsed = 0.0

    def now(self):
        return self._now

    def monotonic(self):
        return self._elapsed

    def advance(self, seconds):
        if seconds < 0:
            raise ValueError("Fake time cannot move backwards")
        self._now += timedelta(seconds=seconds)
        self._elapsed += seconds

    def sleep(self, seconds):
        self.advance(seconds)


@pytest.fixture
def fake_clock():
    """Inject this clock explicitly; pure stages receive fake_clock.now()."""
    return FakeClock()


@pytest.fixture
def cli_command():
    """One isolated launcher for CLI and crash probes; -I ignores PYTHONPATH.

    ``code`` replaces the module entry point only for a deliberately instrumented
    child (e.g. death inside atomic_write). ``prelude`` runs before the real CLI.
    """
    src = str(REPO_ROOT / "engine" / "src")

    def command(*args, code=None, prelude=""):
        bootstrap = _sandbox_temp_prelude()
        if not INSTALLED_MODE:
            bootstrap = f"import sys; sys.path.insert(0, {src!r});\n" + bootstrap
        entry = code if code is not None else (
            "import runpy; runpy.run_module('mdflow', run_name='__main__')"
        )
        return [sys.executable, "-I", "-c", bootstrap + prelude + "\n" + entry,
                *map(str, args)]

    return command
