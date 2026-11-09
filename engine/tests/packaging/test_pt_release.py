"""PT-01, PT-02, PT-05, PT-06, PT-08, PT-13, PT-14, PT-15, PT-17 (mode R: the FX-72 release bundle).

Every test here asks for ``release_bundle`` (or a fixture built on it) and therefore *collects and skips with an
explicit reason* until CI supplies ``$MDFLOW_RELEASE_BUNDLE``. They never pass without the real bytes.

release-candidate.json (inside the bundle; REQ-PKG-17 candidate manifest):
    {"repo": "owner/name", "commit": "<40 hex>", "tag": "2.0.0", "signer_workflow": "owner/name/.github/workflows/release.yml",
     "reference_sha256": "<64 hex>", "required_jobs": [{"name", "os", "python", "result": "success"}] x6,
     "shell_jobs": [{"name", "os", "result": "success"}] x3,
     "acceptance": {"score": "SCORE 100/100 (automated 93/93, manual 7/7)", "gates": [{"id": "G-01", "result": "PASS"}, ...]},
     "blockers": [], "rollback": {"tag": "1.0.8", "artifacts_retained": true},
     "draft_release": {"assets": [{"name": "main.js", "sha256": "<64 hex>"}, ...]}, "verifier": {"gh": "<version>"}}
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
import zipfile

import pytest

from _support import (REPO, SHA40, SUBJECTS, json_objects, load_py, load_yaml, progress_events, version_tuple, ASSETS, WHEEL, REFERENCE)

PLATFORMS = ("windows-2022", "ubuntu-24.04", "macos-15-intel")
LOCKED_ASSETS = ASSETS
FROZEN_COMMANDS = ("convert-file", "convert-folder", "convert-url", "view-conversion-history", "open-log-folder",
                   "run-image-pipeline-selftest")
PRIOR_VERSIONS = {"0.1.0": "0.15.0", "1.0.0": "0.15.0", "1.0.1": "0.15.0", "1.0.2": "1.6.0", "1.0.3": "1.6.0",
                  "1.0.4": "1.6.0", "1.0.5": "1.6.0", "1.0.6": "1.6.0", "1.0.7": "1.6.0", "1.0.8": "1.6.0"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_lock(text: str):
    """Logical requirement lines -> (requirement without hashes, [sha256 hashes])."""
    logical, buffer = [], ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            buffer += stripped[:-1].strip() + " "
            continue
        logical.append((buffer + stripped).strip())
        buffer = ""
    return [(re.sub(r"\s+--hash=\S+", "", line).strip(), re.findall(r"--hash=sha256:([0-9a-f]{64})", line))
            for line in logical]


def lock_pins(text: str) -> dict:
    pins = {}
    for requirement, _ in parse_lock(text):
        match = re.match(r"^([A-Za-z0-9_.\-]+)==([^\s;]+)", requirement)
        if match:
            pins[match[1].lower().replace("_", "-")] = match[2]
    return pins


def engine_wheel(bundle: Path) -> tuple[str, bytes]:
    return WHEEL, (bundle / WHEEL).read_bytes()


def assert_full_lock_rejects_dependency_mutations(release_bundle, work, *, pip_prefix=None, offline=False):
    """Exercise the real complete lock, including transitives, in a local wheelhouse.

    The release control downloads only hash-authorized target wheels. The small
    mode-A control supplies its own three wheels and never accesses an index.
    """
    from email.parser import Parser
    work.mkdir(parents=True)
    for path in release_bundle.iterdir():
        if path.is_file():
            shutil.copyfile(path, work / path.name)
    if (release_bundle / 'wheels').is_dir():
        shutil.copytree(release_bundle / 'wheels', work / 'wheels')
    prefix = pip_prefix or [sys.executable, '-m', 'pip']
    def run(arguments):
        return subprocess.run([*prefix, *arguments], cwd=work, capture_output=True,
                              text=True, encoding='utf-8', timeout=600)
    download = run(['download', '--no-cache-dir', '--require-hashes', '--only-binary=:all:',
                    '--find-links', './wheels', '-r', 'reference-requirements.txt', '--dest', 'wheelhouse',
                    *(['--no-index'] if offline else ['--index-url', 'https://pypi.org/simple'])])
    assert download.returncode == 0, download.stdout + download.stderr
    dependencies = []
    for path in sorted((work / 'wheelhouse').glob('*.whl')):
        with zipfile.ZipFile(path) as archive:
            metadata_name, = [n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
            metadata = Parser().parsestr(archive.read(metadata_name).decode())
        name = metadata['Name'].lower().replace('_', '-')
        if name not in {'mdflow', 'markitdown-gc'}:
            dependencies.append((name, path))
    assert dependencies, 'the full-lock oracle needs a real transitive dependency'
    name, wheel = dependencies[0]
    lock = (work / 'reference-requirements.txt').read_text(encoding='utf-8')
    logical = []
    buffer = ''
    for line in lock.splitlines():
        part = line.strip()
        if not part or part.startswith('#'): continue
        buffer += part.rstrip('\\').rstrip() + ' '
        if not part.endswith('\\'):
            logical.append(buffer.strip())
            buffer = ''
    chosen = next(line for line in logical if re.match(re.escape(name) + r'==', line.replace('_', '-'), re.I))
    missing = [line for line in logical if line != chosen]
    unhashed = [re.sub(r'\s+--hash=\S+', '', line) if line == chosen else line for line in logical]
    def install(lines, label):
        req = work / (label + '.txt')
        req.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return run(['install', '--no-cache-dir', '--ignore-installed', '--require-hashes', '--only-binary=:all:',
                    '--no-index', '--find-links', './wheelhouse', '--target', label + '-site', '-r', req.name])
    good = install(logical, 'good')
    assert good.returncode == 0, good.stdout + good.stderr
    for lines, label in ((missing, 'missing-pin'), (unhashed, 'missing-hash')):
        rejected = install(lines, label)
        text = (rejected.stdout + rejected.stderr).lower()
        assert rejected.returncode != 0 and ('hash' in text or 'pinned' in text), text
    original = wheel.read_bytes()
    try:
        wheel.write_bytes(original + b'\0')
        rejected = install(logical, 'changed-dependency')
        assert rejected.returncode != 0 and 'do not match the hashes' in (rejected.stdout + rejected.stderr).lower()
    finally:
        wheel.write_bytes(original)


@pytest.mark.release
@pytest.mark.req("REQ-PKG-01")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-72")
def test_PT_01_direct_wheel_inventory_wheel_metadata_and_run_outside_the_source_tree(release_bundle, packaged_venv,
                                                                                    tmp_path):
    for name in ('BOOTSTRAP.md', 'NOTICE.txt', 'LICENSE'):
        assert (release_bundle / name).stat().st_size, name
    wheel_name, wheel = engine_wheel(release_bundle)
    with zipfile.ZipFile(io.BytesIO(wheel)) as inner:
        names = inner.namelist()
        assert not [n for n in names if n.lower().endswith((".so", ".pyd", ".dll", ".dylib"))], "native code in mdflow wheel"
        metadata = inner.read(next(n for n in names if n.endswith(".dist-info/METADATA"))).decode("utf-8")
        wheel_meta = inner.read(next(n for n in names if n.endswith(".dist-info/WHEEL"))).decode("utf-8")
    requires = {re.match(r"Requires-Dist:\s*([A-Za-z0-9_.\-]+)", line)[1].lower()
                for line in metadata.splitlines() if line.startswith("Requires-Dist:")}
    assert requires == {"markitdown-gc", "pypdfium2", "pillow"}, f"runtime dependency policy differs: {requires}"
    assert re.search(r"^Version: 2\.0\.0$", metadata, re.M) and re.search(r"^Name: mdflow$", metadata, re.M | re.I)
    assert "Root-Is-Purelib: true" in wheel_meta and "Tag: py3-none-any" in wheel_meta
    # Import and run from the fresh compatibility environment, cwd outside the source tree.
    probe = subprocess.run([str(packaged_venv.python), "-I", "-c",
                            "import mdflow, sys; print(mdflow.__file__)"], cwd=tmp_path, capture_output=True,
                           text=True, encoding="utf-8", timeout=120)
    assert probe.returncode == 0, probe.stderr
    location = Path(probe.stdout.strip()).resolve()
    from _support import installed_import
    assert installed_import(location, packaged_venv.venv, REPO), location


@pytest.mark.release
@pytest.mark.req("REQ-PKG-02")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("FX-72")
def test_PT_02_reference_is_exact_hash_checked_wheel_only_and_a_changed_wheel_fails(release_bundle, tmp_path, cli_command):
    lock = (release_bundle / "reference-requirements.txt").read_text(encoding="utf-8")
    assert 'Linux x64' in lock and 'CPython 3.14' in lock and 'Core 0.3.6' in lock
    assert sys.platform == 'linux' and sys.version_info[:2] == (3, 14), 'PT-02 runs on the reference target only'
    wheel_name, wheel = engine_wheel(release_bundle)
    entries = parse_lock(lock)
    assert entries
    engine = [e for e in entries if "mdflow-2.0.0-py3-none-any.whl" in e[0]]
    assert len(engine) == 1 and re.match(r"^(mdflow\s*@\s*)?\./mdflow-2\.0\.0-py3-none-any\.whl$", engine[0][0]), \
        "the engine must be the local wheel path ./mdflow-2.0.0-py3-none-any.whl"
    assert engine[0][1] == [sha(wheel)], "locked engine hash differs from the attached release wheel"
    problems = []
    for requirement, hashes in entries:
        if re.search(r"git\+|https?://|\.tar\.gz|\.zip\b|\[all\]|^-e\b|^--editable", requirement):
            problems.append(f"forbidden requirement form: {requirement}")
        if requirement.startswith("-") or (requirement, hashes) == engine[0]:
            continue
        if not re.match(r"^[A-Za-z0-9_.\-]+==[^\s;]+(\s*;.*)?$", requirement):
            problems.append(f"not an exact pin without extras: {requirement}")
        if not hashes:
            problems.append(f"no --hash: {requirement}")
    assert not problems, "\n".join(problems)
    pins = lock_pins(lock)
    assert pins.get("markitdown-gc") == "0.3.6"
    assert "pillow" in pins and "pypdfium2" in pins, "renderer and Pillow must be exact lock entries"
    # A changed wheel fails hash-mode installation; the real one installs.
    good, bad = tmp_path / "good" / "wheels", tmp_path / "bad" / "wheels"
    for folder, payload in ((good, wheel), (bad, wheel + b"\0")):
        folder.mkdir(parents=True)
        (folder / "mdflow-2.0.0-py3-none-any.whl").write_bytes(payload)
        (folder.parent / "req.txt").write_text(
            f"./wheels/mdflow-2.0.0-py3-none-any.whl --hash=sha256:{sha(wheel)}\n", encoding="utf-8")
    def install(folder):
        return subprocess.run([sys.executable, "-m", "pip", "install", "--require-hashes", "--no-deps", "--no-index",
                               "--target", str(folder.parent / "site"), "-r", "req.txt"], cwd=folder.parent,
                              capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert install(good).returncode == 0
    tampered = install(bad)
    assert tampered.returncode != 0 and "do not match the hashes" in (tampered.stdout + tampered.stderr).lower()
    assert_full_lock_rejects_dependency_mutations(release_bundle, tmp_path / 'full-lock',
        pip_prefix=cli_command(code='from pip._internal.cli.main import main; raise SystemExit(main())'))


@pytest.mark.req('REQ-PKG-02')
@pytest.mark.cov('S0', 'FM9')
@pytest.mark.fx('FX-72')
def test_T_GEN_52_m1_v32_offline_dependency_hash_mutation_control(tmp_path, cli_command):
    """Three real tiny wheels prove the stronger oracle runs without release assets."""
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    members, requirements = {}, []
    packages = [('mdflow', '2.0.0', 'markitdown-gc>=0.3.5,<0.4'),
                ('markitdown_gc', '0.3.6', 'm1-dependency>=1'), ('m1_dependency', '1.0', None)]
    for name, version, dependency in packages:
        stream = io.BytesIO()
        info = f'{name}-{version}.dist-info'
        with zipfile.ZipFile(stream, 'w') as archive:
            metadata = f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n'
            if dependency: metadata += f'Requires-Dist: {dependency}\n'
            archive.writestr(info + '/METADATA', metadata)
            archive.writestr(info + '/WHEEL', 'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
            archive.writestr(name + '/__init__.py', '')
            archive.writestr(info + '/RECORD', '')
        wheel = f'{name}-{version}-py3-none-any.whl'
        members['wheels/' + wheel] = stream.getvalue()
        requirement = './wheels/' + wheel if name == 'mdflow' else name.replace('_', '-') + '==' + version
        requirements.append(requirement + ' --hash=sha256:' + sha(stream.getvalue()))
    members['reference-requirements.txt'] = ('\n'.join(requirements) + '\n').encode()
    for name, data in members.items():
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    assert_full_lock_rejects_dependency_mutations(bundle, tmp_path / 'closure', offline=True,
        pip_prefix=cli_command(code='from pip._internal.cli.main import main; raise SystemExit(main())'))


@pytest.mark.release
@pytest.mark.req("REQ-PKG-05")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-72")
def test_PT_05_bootstrap_commands_run_unchanged_after_placeholder_substitution(release_bundle, bootstrap_root, tmp_path):
    text = (bootstrap_root / "BOOTSTRAP.md").read_text(encoding="utf-8")
    windows = os.name == "nt"
    languages = {"powershell", "pwsh", "ps1"} if windows else {"sh", "bash", "shell", "zsh"}
    fences = [(lang.lower(), body) for lang, body in re.findall(r"```(\w*)\n(.*?)```", text, re.S)]
    blocks = [body for lang, body in fences if lang in languages and "pip install" in body]
    assert blocks, "BOOTSTRAP.md has no install block for this OS"
    block = blocks[0]
    for needle in ("--only-binary=:all:", "./mdflow-2.0.0-py3-none-any.whl", "markitdown-gc>=0.3.5,<0.4", "https://pypi.org/simple", "-m mdflow selftest",
                   "pip check", "-m mdflow version", "-m venv"):
        assert needle in block, f"install block lacks {needle!r}"
    before = text[:text.index(block)]
    assert re.search(r"package index|PyPI", before, re.I) and re.search(r"network|download", before, re.I), \
        "index/network use must be shown before the setup commands"
    assert re.search(r"(plugin|Obsidian)[^.\n]*(never|does not|doesn't)[^.\n]*install|your own terminal", text, re.I)
    assert "MDFLOW_API_KEY" in text and re.search(r"quit", text, re.I), "terminal-launch guidance missing"
    root_placeholder = re.search(r"(?:Set-Location -LiteralPath|\bcd)\s+'([^']+)'", block)[1]
    venv_placeholder = re.search(r"-m venv\s+'([^']+)'", block)[1]
    venv = tmp_path / "venv 한글" / "2.0.0"
    script = block.replace(root_placeholder, str(bootstrap_root)).replace(venv_placeholder, str(venv))
    interpreter = sys.executable
    script = re.sub(r"(?m)^(\s*)(py -3\.\d+|python3\.\d+)\b",
                    (lambda m: f"{m[1]}& '{interpreter}'") if windows else (lambda m: f"{m[1]}'{interpreter}'"), script)
    command = ["powershell", "-NoProfile", "-NonInteractive", "-Command", script] if windows else ["sh", "-e", "-c", script]
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=2400)
    assert done.returncode == 0, f"{done.stdout[-1500:]}\n{done.stderr[-1500:]}"
    assert json.loads(done.stdout.strip().splitlines()[-1])["protocol"] == 1, "the last command is `mdflow version`"
    # The plugin only diagnoses: no shell source spawns an installer.
    for source in (REPO / "shell/src").rglob("*.ts"):
        assert not re.search(r"pip install|['\"]pip['\"]|-m['\"],\s*['\"]venv", source.read_text(encoding="utf-8")), source


def gate(response: dict) -> list[str]:
    """SPEC 10.1 / REQ-PKG-06 acceptance rule, evaluated on the *package* side (the shell gate is JT-17)."""
    required = {"mdflow": str, "markitdown-gc": str, "pypdfium2": str, "pillow": str, "python": str, "platform": str,
                "protocol": int, "triage_schema": int}
    problems = [f"missing {k}" for k in required if k not in response]
    problems += [f"bad type {k}" for k, t in required.items() if k in response and type(response[k]) is not t]
    if problems:
        return problems
    if not response['platform'].strip():
        problems.append('platform')
    if response["protocol"] != 1:
        problems.append("protocol")
    if response["triage_schema"] != 1:
        problems.append("triage_schema")
    from packaging.version import InvalidVersion, Version
    def valid(text):
        if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)', text):
            return False
        try:
            Version(text)
            return True
        except InvalidVersion:
            return False
    if not valid(response['mdflow']) or not (2, 0, 0) <= version_tuple(response["mdflow"]) < (2, 1, 0):
        problems.append("engine range")
    if not valid(response['markitdown-gc']) or not (0, 3, 5) <= version_tuple(response["markitdown-gc"]) < (0, 4):
        problems.append("Core range")
    if not valid(response['python']) or not (3, 10) <= version_tuple(response["python"])[:2] < (3, 15):
        problems.append("Python range")
    for key in ("pillow", "pypdfium2"):
        if not valid(response[key]):
            problems.append(f"{key} version is malformed")
        else:
            low, high = ((11, 0), (14, 0)) if key == 'pillow' else ((5, 0), (6, 0))
            if not low <= version_tuple(response[key]) < high:
                problems.append(f'{key} range')
    return problems


@pytest.mark.release
@pytest.mark.req("REQ-PKG-06")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("FX-71", "FX-72")
def test_PT_06_packaged_version_and_selftest_follow_declared_compatibility_policy(release_bundle,
                                                                                            packaged_engine):
    done = packaged_engine.run("version")
    assert done.returncode == 0, done.stderr
    real = json.loads(done.stdout)
    assert set(real) == {"mdflow", "markitdown-gc", "pypdfium2", "pillow", "python", "platform", "protocol", "triage_schema",
                         "exiftool", "exiftool_status", "exiftool_source",
                         "libreoffice", "libreoffice_status", "libreoffice_source"}  # Optional tool diagnostics
    assert gate(real) == [], "the packaged engine fails its own gate"
    assert packaged_engine.run("selftest").returncode == 0
    record = load_py(REPO / "tools/record_protocol.py", "mdflow_pt_record_protocol")
    real_bytes = done.stdout.encode("utf-8")
    for name in record.VERSION_VARIANTS:
        variant = json.loads(record.version_variant(name, real_bytes))
        problems = gate(variant)
        assert bool(problems) == (name not in {"unknown-optional-field"}), f"{name}: gate verdict {problems}"
    fx71 = REPO / "shell/test/fixtures/fx71"
    assert (fx71 / "manifest.json").is_file(), "FX-71 not recorded: run python tools/record_protocol.py"
    assert record.verify(fx71) == 0, "FX-71 fixtures were edited or no longer match their parents"
    parent = json.loads((fx71 / "version.json").read_text(encoding="utf-8"))
    for path in sorted(fx71.glob("version.*.json")):
        name = path.name[len("version."):-len(".json")]
        verdict = gate(json.loads(path.read_text(encoding="utf-8")))
        assert bool(verdict) == (name not in {"unknown-optional-field"}), f"{path.name}: {verdict}"


@pytest.mark.release
@pytest.mark.req("REQ-PKG-08")
@pytest.mark.cov("S0", "FM12")
@pytest.mark.fx("FX-02", "FX-03", "FX-72")
def test_PT_08_packaged_engine_batch_consent_hash_stability_and_os_cancellation(release_bundle, packaged_engine,
                                                                                tmp_path, gen_core, gen_io):
    base = tmp_path / "작업 공간 with space"
    first, second = base / "입력 하나", base / "input two"
    sources = {first / "sub/a.pdf": ("FX-03", {}), first / "보고서/3분기 결산.pdf": ("FX-02", {"pages": 3}),
               second / "b c.docx": ("FX-16", {}), second / "memo.txt": ("FX-28", {})}
    for target, (fx, kwargs) in sources.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(gen_core.generate(fx, base / "_gen", **kwargs), target)
    calls, script = base / "calls.txt", base / "ocr 모의.py"
    script.write_text("import sys\nopen(sys.argv[2], 'a').write('x')\nsys.stdout.reconfigure(encoding='utf-8')\n"
                      "print('모의 OCR 텍스트')\n", encoding="utf-8")
    template = gen_io.command_template(script, "{input}", shlex.quote(calls.as_posix()))
    flags = ["--provider", "command", "--command", template, "--command-egress", "true", "--trust-command",
             "--model", "pt-echo", "--cache", str(base / "cache")]
    roots = [str(first), str(second)]

    planned = packaged_engine.run("plan", *roots, *flags)
    assert planned.returncode in (0, 3), planned.stderr  # plan may announce missing consent (SPEC 8.4)
    plans = {(p["approved"]["file"]["path"]): p for p in json_objects(planned.stdout)}
    assert {"sub/a.pdf", "보고서/3분기 결산.pdf", "b c.docx", "memo.txt"} <= set(plans), "nested logical paths changed"
    assert not (base / "out").exists() and not (base / "cache").exists() and not calls.exists(), "plan wrote or called"
    needing = {path: p for path, p in plans.items() if p["status"]["requests_to_send"] > 0}
    assert len(needing) >= 3

    pending = packaged_engine.run("run", *roots, "-o", str(base / "out"), *flags, "--progress", "jsonl")
    assert pending.returncode == 3 and not calls.exists(), (pending.stdout, pending.stderr)
    required = {e["file"]: e for e in progress_events(pending.stderr) if e["ev"] == "approve_required"}
    assert set(required) == set(needing)
    for path, event in required.items():
        plan = needing[path]
        shown = {k: event[k] for k in ("plan_hash", "destination", "model", "keys_unique", "requests_to_send",
                                       "max_requests", "est_max_cost", "cost_known", "threshold_exceeded", "sensitive_hits")}
        expected = {"plan_hash": plan["plan_hash"], "destination": plan["approved"]["provider"]["destination"],
                    "model": plan["approved"]["provider"]["model"], "keys_unique": plan["approved"]["keys_unique"],
                    "requests_to_send": plan["status"]["requests_to_send"], "max_requests": plan["approved"]["max_requests"],
                    "est_max_cost": plan["approved"]["est_max_cost"], "cost_known": plan["approved"]["cost_known"],
                    "threshold_exceeded": plan["approved"]["threshold_exceeded"],
                    "sensitive_hits": plan["approved"]["sensitive_hits"]}
        assert shown == expected and "units" not in event, path

    yes = [item for p in needing.values() for item in ("--yes", p["plan_hash"])]
    done = packaged_engine.run("run", *roots, "-o", str(base / "out"), *flags, *yes, "--approved-by", "plugin:modal",
                               "--progress", "jsonl")
    assert done.returncode == 0, (done.stdout, done.stderr)
    report = json_objects(done.stdout)[0]
    assert all(f["consent"]["by"] == "plugin:modal" for f in report["files"] if f["path"] in needing)
    assert calls.exists() and len(calls.read_text()) >= 1

    warm = {p["approved"]["file"]["path"]: p for p in json_objects(packaged_engine.run("plan", *roots, *flags).stdout)}
    assert {k: v["plan_hash"] for k, v in warm.items()} == {k: v["plan_hash"] for k, v in plans.items()}, \
        "plan_hash changed after cache warming"
    assert all(p["status"]["requests_to_send"] == 0 for p in warm.values())

    # Changed approved bytes require fresh consent: nothing is sent for the stale hash.
    image = first / "new image.png"
    image.write_bytes(gen_core.image_bytes("PNG", seed=41))
    stale = {p["approved"]["file"]["path"]: p for p in json_objects(packaged_engine.run("plan", *roots, *flags).stdout)}["new image.png"]
    image.write_bytes(gen_core.image_bytes("PNG", seed=42))
    sent = len(calls.read_text())
    again = packaged_engine.run("run", *roots, "-o", str(base / "out"), *flags, "--yes", stale["plan_hash"],
                                "--progress", "jsonl")
    assert again.returncode == 3 and len(calls.read_text()) == sent, "stale approval sent data"
    assert "W_APPROVAL_UNUSED" in {e.get("code") for e in progress_events(again.stderr)}

    # Cooperative OS cancellation leaves no owned process.
    pidfile = base / "child.pid"
    sleeper = gen_io.write_child(base, "sleeper")
    slow = ["--provider", "command", "--command", gen_io.command_template(sleeper, shlex.quote(pidfile.as_posix())),
            "--command-egress", "true", "--trust-command", "--model", "pt-sleep", "--cache", str(base / "cache2")]
    slow_plan = json_objects(packaged_engine.run("plan", str(first / "sub"), *slow).stdout)[0]
    spec = packaged_engine.popen_args(["run", str(first / "sub"), "-o", str(base / "out2"), *slow, "--yes",
                                       slow_plan["plan_hash"]], env={"MDFLOW_TIMEOUT_S": "60"})
    extra = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {}
    proc = subprocess.Popen(**spec, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", **extra)
    deadline = time.monotonic() + 90
    while not pidfile.exists() and time.monotonic() < deadline and proc.poll() is None:
        time.sleep(0.2)
    assert pidfile.exists(), "the command child never started"
    child = int(pidfile.read_text())
    proc.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM)
    out, err = proc.communicate(timeout=120)
    assert proc.returncode == 130, (proc.returncode, err[-800:])
    assert json_objects(out)[0]["exit"] == 130
    assert not gen_io.pid_alive(child), "an owned command child survived cancellation"


@pytest.mark.release
@pytest.mark.req("REQ-PKG-13")
@pytest.mark.cov("S0", "FM9")
@pytest.mark.fx("FX-72")
def test_PT_13_every_release_subject_verifies_and_tampering_or_wrong_repo_fails(release_bundle, candidate, tmp_path):
    gh = shutil.which("gh")
    if gh is None:
        pytest.skip("gh CLI absent: `gh attestation verify` cannot be exercised (TODO-VERIFY plan eligibility/flags)")
    assert SHA40.fullmatch(candidate["commit"]) and candidate["repo"] and candidate["signer_workflow"]

    def verify(asset: Path, bundle: Path, repo: str):
        return subprocess.run([gh, "attestation", "verify", str(asset), "--repo", repo, "--bundle", str(bundle),
                               "--signer-workflow", candidate["signer_workflow"], "--source-digest", candidate["commit"]],
                              capture_output=True, text=True, encoding="utf-8", timeout=300)

    for subject in SUBJECTS:
        bundle = release_bundle / f"{subject}.sigstore.json"
        assert bundle.is_file(), f"attestation bundle missing for {subject}"
        done = verify(release_bundle / subject, bundle, candidate["repo"])
        assert done.returncode == 0, f"{subject}: {done.stdout}{done.stderr}"
    changed = tmp_path / "main.js"
    changed.write_bytes((release_bundle / "main.js").read_bytes() + b"\n")
    assert verify(changed, release_bundle / "main.js.sigstore.json", candidate["repo"]).returncode != 0
    assert verify(release_bundle / "main.js", release_bundle / "main.js.sigstore.json", "someone-else/other").returncode != 0


@pytest.mark.release
@pytest.mark.req("REQ-PKG-14")
@pytest.mark.cov("S0", "FM12")
@pytest.mark.fx("FX-72")
def test_PT_14_asset_inventory_digests_lock_identity_and_package_scan(release_bundle):
    present = {p.name for p in release_bundle.iterdir() if p.is_file()}
    assert set(SUBJECTS) <= present, f"missing assets: {sorted(set(SUBJECTS) - present)}"
    extra = present - set(SUBJECTS) - {"release-candidate.json"}
    assert all(name.endswith((".sigstore.json", ".intoto.jsonl")) for name in extra), f"unexpected assets: {sorted(extra)}"
    sums = {}
    for line in (release_bundle / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.partition("  ")
            sums[name.strip().lstrip("*")] = digest
    assert set(sums) == set(LOCKED_ASSETS), "SHA256SUMS must cover exactly the shared release ASSETS"
    for name, digest in sums.items():
        assert sha((release_bundle / name).read_bytes()) == digest, f"{name}: digest mismatch"
    wheel_name, wheel = engine_wheel(release_bundle)
    lock = (release_bundle / REFERENCE).read_text(encoding='utf-8')
    assert f'./{WHEEL} --hash=sha256:{sha(wheel)}' in lock.splitlines()
    with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
        bad = [n for n in archive.namelist() if re.search(
            r"(^|/)(data\.json|\.env|\.venv|venv|__pycache__|cache|\.mdflow)(/|$)|\.pyc$", n)]
        assert not bad, f"settings/cache/keys/venv in wheel: {bad}"



def check_attest(name: str, data: dict) -> list[str]:
    problems = [f"{name}: missing {k}" for k in ("id", "reviewer", "date", "commit", "inputs", "checks", "evidence", "verdict")
                if not (data or {}).get(k)]
    if data:
        if data.get("verdict") != "PASS":
            problems.append(f"{name}: verdict is not PASS")
        for check in data.get("checks") or []:
            result = check.get("result", check.get("status")) if isinstance(check, dict) else check
            if result != "PASS":
                problems.append(f"{name}: check not PASS: {check}")
        if name == "MAN-01" and (not data.get("implementer") or data.get("implementer") == data.get("reviewer")):
            problems.append("MAN-01: implementer and reviewer must be named and different")
    return problems


@pytest.mark.release
@pytest.mark.human
@pytest.mark.req("REQ-PKG-15")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("FX-72")
def test_PT_15_checklist_machine_rows_and_human_evidence_rows(release_bundle, candidate, attest_dir):
    manifest = json.loads((release_bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["id"] == "markitdown-flow" and manifest["isDesktopOnly"] is True
    package = json.loads((REPO / "shell/package.json").read_text(encoding="utf-8"))
    engine_wheel(release_bundle)  # exactly one mdflow-2.0.0 attached release wheel
    assert manifest["version"] == package["version"] == candidate["tag"] == "2.0.0", "version fields disagree"
    assert not candidate["tag"].startswith("v")
    versions = json.loads((REPO / "versions.json").read_text(encoding="utf-8"))
    assert versions.get("2.0.0") == manifest["minAppVersion"], "versions.json lacks the 2.0.0 entry"
    assert all(versions.get(k) == v for k, v in PRIOR_VERSIONS.items()), "prior versions.json entries not preserved"
    description = manifest["description"]
    assert len(description) <= 250 and description.endswith(".")
    assert not re.search("[\U0001F000-\U0001FFFF☀-➿⬀-⯿←-⇿—]", description)
    assert not re.search(r"azure|content understanding|youtube|audio|fall-?back", description, re.I), \
        "description promises removed features"
    bundle = (release_bundle / "main.js").read_text(encoding="utf-8", errors="replace")
    for command in FROZEN_COMMANDS:
        assert re.search(rf"['\"]{re.escape(command)}['\"]", bundle), f"command {command} not registered"
        assert f"markitdown-flow:{command}" not in bundle, f"{command} carries an embedded plugin prefix"
    assert not re.search(r"sample-modal-simple|open-sample-modal|SampleSettingTab|SampleModal|Sample Plugin", bundle)
    # Human-evidence rows: schema only; a valid file is not proof of authorship, meaning or rehearsal.
    wanted = {"MAN-01": "R15_cleanroom.yml", "MAN-03": "shell_i18n_review.yml", "MAN-04": "release_rehearsal.yml"}
    missing = [f for f in wanted.values() if not (attest_dir / f).is_file()]
    if missing:
        pytest.skip(f"human evidence absent: {', '.join(missing)} in {attest_dir.as_posix()} (mode H); machine rows passed")
    problems = []
    for man, filename in wanted.items():
        data = load_yaml((attest_dir / filename).read_text(encoding="utf-8"))
        problems += check_attest(man, data)
        if man == "MAN-04":
            minimum = [r["obsidian_version"] for r in data.get("runs") or [] if r.get("obsidian_channel") == "minimum"]
            if not minimum or {manifest["minAppVersion"]} != set(minimum):
                problems.append("minAppVersion is not the tested minimum recorded in MAN-04")
    assert not problems, "\n".join(problems)


@pytest.mark.release
@pytest.mark.req("REQ-PKG-17")
@pytest.mark.cov("S0", "FM10")
@pytest.mark.fx("FX-72")
def test_PT_17_candidate_manifest_binds_commit_lock_required_runs_and_binary_acceptance(release_bundle, candidate, trace_module):
    assert SHA40.fullmatch(candidate["commit"]) and candidate["tag"] == "2.0.0"
    assert candidate["reference_sha256"] == sha((release_bundle / "reference-requirements.txt").read_bytes())
    # A test contributing to acceptance must not demand its own final score.
    evidence = Path(os.environ.get('MDFLOW_EXECUTION_EVIDENCE', REPO / 'build/trace'))
    assert trace_module.required_executions(evidence, candidate['commit']) == []
    if os.environ.get('GITHUB_SHA'):
        assert candidate['commit'] == os.environ['GITHUB_SHA']
    assert candidate['rollback']['tag'] == '1.0.8'
    draft = {a["name"]: a["sha256"] for a in candidate["draft_release"]["assets"]}
    for name in LOCKED_ASSETS:
        assert draft.get(name) == sha((release_bundle / name).read_bytes()), f"draft release differs for {name}"
