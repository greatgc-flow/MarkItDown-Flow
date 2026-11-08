"""Fixtures for the PT-* packaging tests (30_TESTPLAN section 4.4).

Modes: A runs on every CI run. R needs the FX-72 release bundle (built in CI from the candidate
commit). H needs a human evidence file. R/H tests *collect* and ``skip`` with an explicit reason when their
input is absent; they never pass without it (90_ACCEPTANCE: skipped = FAIL for a release candidate).

FX-72 layout (``$MDFLOW_RELEASE_BUNDLE``), the exact bytes that would be attached to the draft release:
    main.js manifest.json styles.css engine.zip engine.lock SHA256SUMS
    <asset>.sigstore.json         attestation bundle per attested subject (6)
    release-candidate.json        PKG-17 candidate manifest (see test_pt_release.py)
Human evidence lives in ``attest/`` of the repository (or ``$MDFLOW_ATTEST_DIR``).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _support  # noqa: E402  (helper module next to this file)

REPO = _support.REPO
BUNDLE_ENV = "MDFLOW_RELEASE_BUNDLE"
ATTEST_ENV = "MDFLOW_ATTEST_DIR"
SUBJECTS = ("main.js", "manifest.json", "styles.css", "engine.zip", "engine.lock", "SHA256SUMS")


def pytest_configure(config):
    config.addinivalue_line("markers", "release: needs the FX-72 release bundle or release evidence (mode R/H)")
    config.addinivalue_line("markers", "human: validates a human evidence file; validation is not proof")


@pytest.fixture(scope="session")
def support():
    return _support


@pytest.fixture(scope="session")
def pt_temps():
    # Same workaround as the other suites: Python 3.15 on Windows cannot use mode=0700 pytest temp dirs.
    module = _support.load_py(REPO / "engine/tests/fixtures/gen_core.py", "mdflow_pt_gen_core")
    return module.WorkspaceTemps(REPO / "build/trace/redgreen/pt-tmp")


@pytest.fixture
def tmp_path(pt_temps, request):
    return pt_temps.mktemp(request.node.name)


@pytest.fixture(scope="session")
def gen_core():
    return _support.load_py(REPO / "engine/tests/fixtures/gen_core.py", "mdflow_pt_gen_core_fx")


@pytest.fixture(scope="session")
def gen_io():
    return _support.load_py(REPO / "engine/tests/fixtures/gen_io.py", "mdflow_pt_gen_io")


@pytest.fixture(scope="session")
def release_bundle() -> Path:
    raw = os.environ.get(BUNDLE_ENV)
    if not raw:
        pytest.skip(f"FX-72 release bundle absent: set {BUNDLE_ENV} to the directory of release assets "
                    "built in CI from the candidate commit (mode R; skipped is FAIL for a release candidate)")
    path = Path(raw)
    assert path.is_dir(), f"{BUNDLE_ENV}={raw} is not a directory"
    return path


@pytest.fixture(scope="session")
def candidate(release_bundle) -> dict:
    path = release_bundle / "release-candidate.json"
    assert path.is_file(), "release-candidate.json missing from the FX-72 bundle"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def attest_dir() -> Path:
    return Path(os.environ.get(ATTEST_ENV) or REPO / "attest")


def require_evidence(path: Path, what: str) -> Path:
    if not path.is_file():
        pytest.skip(f"human evidence absent: {what} ({path.as_posix()}); validation of a file is not proof of "
                    "the property and the file must be supplied by the named reviewer (mode H)")
    return path


@pytest.fixture(scope="session")
def bootstrap_root(release_bundle, pt_temps) -> Path:
    """engine.zip extracted under a path with a space and Korean text."""
    root = pt_temps.mktemp("엔진 번들 extract")
    with zipfile.ZipFile(release_bundle / "engine.zip") as archive:
        archive.extractall(root)
    entries = [p for p in root.iterdir()]
    return entries[0] if len(entries) == 1 and entries[0].is_dir() else root


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


@pytest.fixture(scope="session")
def packaged_venv(bootstrap_root, pt_temps) -> SimpleNamespace:
    """Fresh venv installed exactly as BOOTSTRAP.md says: hash-checked, wheel-only, from engine.lock."""
    venv = pt_temps.mktemp("venv 한글") / "2.0.0"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, timeout=600)
    python = venv_python(venv)
    install = [str(python), "-m", "pip", "install", "--require-hashes", "--only-binary=:all:",
               "--find-links", "./wheels", "-r", "./engine.lock"]
    done = subprocess.run(install, cwd=bootstrap_root, capture_output=True, text=True, timeout=1800)
    assert done.returncode == 0, f"locked install failed:\n{done.stdout[-2000:]}\n{done.stderr[-2000:]}"
    check = subprocess.run([str(python), "-m", "pip", "check"], capture_output=True, text=True, timeout=300)
    assert check.returncode == 0, check.stdout + check.stderr
    return SimpleNamespace(python=python, venv=venv, root=bootstrap_root)


@pytest.fixture
def source_engine(tmp_path, cli_command):
    """The source-tree engine through the root conftest launcher (python -I, repo engine/src first)."""
    return _support.Engine(lambda args: cli_command(*args), tmp_path, tmp_path / "scratch")


@pytest.fixture
def packaged_engine(packaged_venv, tmp_path):
    python = str(packaged_venv.python)
    return _support.Engine(lambda args: [python, "-I", "-m", "mdflow", *args], tmp_path, tmp_path / "scratch")


@pytest.fixture
def mock_http():
    """FX-62 loopback server, reusing the scripted server of the stage tests."""
    module = _support.load_py(REPO / "engine/tests/stage_io/conftest.py", "mdflow_pt_stage_io_conftest")
    server = module.MockHttp()
    server.start()
    yield server
    server.stop()
