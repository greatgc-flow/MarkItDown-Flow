"""T-GEN-01, T-GEN-02, T-GEN-03, T-SEC-04: planned tests that no earlier step had written (TESTPLAN 4.1).

They run against the real engine; nothing here changes engine/src.
"""

import ast
import builtins
from importlib import metadata
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import pytest

ENGINE_SRC = Path(__file__).resolve().parents[2] / "src" / "mdflow"
NATIVE_SUFFIXES = {".so", ".pyd", ".dll", ".dylib", ".c", ".cpp", ".pyx", ".rs"}
# Core's own transitive dependencies (Pillow, pypdfium2 are exact lock entries of the Core install).
THIRD_PARTY_OK = {"mdflow", "markitdown", "PIL", "pypdfium2"}


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from ((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module, node.lineno


@pytest.mark.req("REQ-GEN-01")
@pytest.mark.cov("S0", "FM0")
def test_T_GEN_01_pure_python_with_declared_runtime_dependencies():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    requires = tomllib.loads((ENGINE_SRC.parents[1] / 'pyproject.toml').read_text(encoding='utf-8'))['project']['dependencies']
    names = {re.match(r"[A-Za-z0-9_.\-]+", r)[0].lower().replace("_", "-") for r in requires if "extra ==" not in r}
    assert names == {"markitdown-gc", "pypdfium2", "pillow"}, f"runtime policy differs: {requires}"
    native = sorted(p.relative_to(ENGINE_SRC).as_posix() for p in ENGINE_SRC.rglob("*")
                    if p.is_file() and p.suffix.lower() in NATIVE_SUFFIXES)
    assert not native, f"native or compiled sources in the mdflow package: {native}"
    foreign = {}
    for path in sorted(ENGINE_SRC.rglob("*.py")):
        for module, line in _imports(ast.parse(path.read_text(encoding="utf-8"))):
            top = module.split(".")[0]
            if top not in sys.stdlib_module_names and top not in THIRD_PARTY_OK:
                foreign.setdefault(top, f"{path.name}:{line}")
    assert not foreign, f"runtime imports beyond stdlib + markitdown-gc: {foreign}"


_PRELUDE = '''
import atexit, builtins, importlib.metadata as md, io, json, os
_real_version = md.version
md.version = lambda name, *a, **k: {version!r} if name == "markitdown-gc" else _real_version(name, *a, **k)
from mdflow import core_guard
with core_guard.quiet_output():
    from markitdown import tools
tools.installation_conflict = lambda: None  # the faked metadata is out of range, not a broken install
_opened = []
def _wrap(real):
    def wrapper(file, *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)):
            _opened.append(os.path.normcase(os.path.abspath(os.fsdecode(file))))
        return real(file, *a, **k)
    return wrapper
_open, _io_open, _os_open = builtins.open, io.open, os.open
builtins.open, io.open, os.open = _wrap(_open), _wrap(_io_open), _wrap(_os_open)
atexit.register(lambda: _open({log!r}, "w", encoding="utf-8").write(json.dumps(_opened)))
'''


@pytest.mark.req("REQ-GEN-02")
@pytest.mark.cov("S0", "FM10")
def test_T_GEN_02_core_outside_range_exits_one_before_any_file_is_read(tmp_path, cli_command):
    source = tmp_path / "input" / "note.txt"
    source.parent.mkdir()
    source.write_text("own text", encoding="utf-8")
    home, temp = tmp_path / "home", tmp_path / "temp"
    home.mkdir()
    temp.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("MDFLOW_") and k.upper() != "PYTHONPATH"}
    env.update(HOME=str(home), USERPROFILE=str(home), TMP=str(temp), TEMP=str(temp), PYTHONIOENCODING="utf-8")
    wanted = os.path.normcase(os.path.abspath(source))

    def run(version, label):
        log = tmp_path / f"opened-{label}.json"
        argv = cli_command("run", source.parent, "-o", tmp_path / f"out-{label}", "--cache", tmp_path / f"cache-{label}",
                           prelude=_PRELUDE.format(version=version, log=str(log)))
        done = subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120)
        opened = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
        return done, opened

    for version in ("0.4.0", "0.3.4", "0.3.7", "1.0.0"):
        done, opened = run(version, version)
        assert done.returncode == 1 and "E_CORE_VERSION" in done.stdout + done.stderr, (version, done.stderr)
        assert wanted not in opened, f"{version}: input was opened before the version gate"
        assert not (tmp_path / f"out-{version}").exists() and not (tmp_path / f"cache-{version}").exists()
    done, opened = run("0.3.8", "control")  # the spy does see the input when the gate passes
    assert done.returncode == 0, done.stderr
    assert wanted in opened, "control: the open spy did not observe the input file"


@pytest.mark.req("REQ-GEN-03")
@pytest.mark.cov("S0", "FM0")
def test_T_GEN_03_source_is_python_3_10_compatible_with_no_upper_cap():
    pyproject = (ENGINE_SRC.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    spec = re.search(r'^requires-python\s*=\s*"([^"]+)"', pyproject, re.M)[1]
    assert spec.replace(" ", "") == ">=3.10", f"3.10 floor and no cap (3.15 is allowed-failure, not excluded): {spec}"
    newer = {"tomllib": "3.11", "typing.Self": "3.11", "typing.LiteralString": "3.11", "typing.Never": "3.11",
             "typing.assert_never": "3.11", "enum.StrEnum": "3.11", "datetime.UTC": "3.11",
             "asyncio.TaskGroup": "3.11", "asyncio.timeout": "3.11"}
    problems = []
    for path in sorted(ENGINE_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path), feature_version=(3, 10))
        except SyntaxError as error:
            problems.append(f"{path.name}: syntax newer than 3.10 ({error.msg})")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = node.module if isinstance(node, ast.ImportFrom) else None
                for alias in node.names:
                    for dotted in {alias.name, f"{module}.{alias.name}" if module else alias.name}:
                        if dotted in newer:
                            problems.append(f"{path.name}:{node.lineno}: {dotted} needs Python {newer[dotted]}")
            elif isinstance(node, ast.Attribute) and ast.unparse(node) in newer:
                problems.append(f"{path.name}:{node.lineno}: {ast.unparse(node)} needs Python {newer[ast.unparse(node)]}")
    assert not problems, "\n".join(problems)


def _spy_opens(monkeypatch):
    opened = []

    def wrap(real):
        def wrapper(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                opened.append(os.path.normcase(os.path.abspath(os.fsdecode(file))))
            return real(file, *args, **kwargs)
        return wrapper

    for owner in (builtins, io, os):
        monkeypatch.setattr(owner, "open", wrap(owner.open))
    return opened


@pytest.mark.req("REQ-SEC-04")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-44")
def test_T_SEC_04_members_never_become_paths_and_the_temp_dir_is_removed_on_every_handled_path(tmp_path, gen, monkeypatch):
    from mdflow import convert, orchestrate

    root, scratch = tmp_path / "input", tmp_path / "tmp"
    root.mkdir()
    scratch.mkdir()
    (root / "slip.zip").write_bytes(gen.zip_slip())
    (root / "plain.txt").write_text("own text", encoding="utf-8")
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    opened = _spy_opens(monkeypatch)
    unsafe = ["../x", "C:\\x", "a\\b", "/abs.txt", "A.txt", "a.txt", "ok.txt"]
    real_convert, calls = convert.core_convert, []

    def injected(*args, **kwargs):
        calls.append(args)
        raise RuntimeError("injected failure inside a stage")

    for label in ("clean", "injected"):
        if label == "injected":
            monkeypatch.setattr(convert, "core_convert", injected)
        else:
            monkeypatch.setattr(convert, "core_convert", real_convert)
        report = orchestrate.run([root], dict(out=tmp_path / f"out-{label}", cache=tmp_path / f"cache-{label}"))
        assert report["files"], f"{label}: nothing was processed"
        assert list(scratch.iterdir()) == [], f"{label}: run temp directory was not removed"
    assert calls, "the error injection never fired"

    roots = [root, tmp_path / "out-clean", tmp_path / "cache-clean", scratch, Path.cwd(), tmp_path, tmp_path.parent]
    candidates = {os.path.normcase(os.path.abspath(os.path.join(str(r), name))) for r in roots for name in unsafe}
    forbidden = sorted(set(opened) & candidates)
    assert not forbidden, f"member names were used as filesystem paths: {forbidden}"
    assert not (tmp_path / "x").exists() and not (root / "x").exists() and not (tmp_path.parent / "x").exists()
    assert {p.name for p in tmp_path.iterdir()} <= {"input", "tmp", "out-clean", "cache-clean", "out-injected", "cache-injected"}
