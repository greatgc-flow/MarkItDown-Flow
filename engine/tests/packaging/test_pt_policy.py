"""PT-10, PT-16, PT-22 (mode A): traceability mutation self-test, README/network policy, terminal-launch env smoke."""
from pathlib import Path
import re
import subprocess
import sys

import pytest

from _support import REPO, SENTINEL, copy_repo_subset, json_objects

COUNTER = re.compile(r"(\w+)=(\d+)")


def run_check(root: Path):
    done = subprocess.run([sys.executable, "tools/trace.py", "check"], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", timeout=600)
    first = done.stdout.splitlines()[0] if done.stdout.strip() else ""
    return done.returncode, {k: int(v) for k, v in COUNTER.findall(first)}, done.stdout + done.stderr


def rewrite_first(root: Path, pattern: str, replacement: str, *, files):
    regex = re.compile(pattern, re.M)
    for relative in files:
        path = root / relative
        text = path.read_text(encoding="utf-8")
        if regex.search(text):
            path.write_text(regex.sub(replacement, text, count=1), encoding="utf-8", newline="\n")
            return relative
    raise AssertionError(f"mutation target not found for {pattern!r}")


@pytest.mark.req("REQ-PKG-10")
@pytest.mark.cov("S0", "FM10")
def test_PT_10_mutations_fail_trace_check_and_manual_results_are_reported_separately(tmp_path):
    base_exit, base, _ = run_check(copy_repo_subset(tmp_path / "base"))
    assert {"unknown_req", "untagged_tests", "registration_errors"} <= set(base), base
    tests = ["engine/tests/unit/test_core_classify.py", "engine/tests/unit/test_core_select_plan.py"]
    mutations = {
        # (a) a marker deleted -> a test without `req`
        "untagged_tests": lambda root: rewrite_first(root, r"^@pytest\.mark\.req\([^\n]*\)\n", "", files=tests),
        # (b) an invented REQ id
        "unknown_req": lambda root: rewrite_first(root, r'(@pytest\.mark\.req\()"REQ-[A-Z]+-\w+"',
                                                  r'\1"REQ-INVENTED-99"', files=tests),
        # (c) a fixture removed from the manifest while a test still names it
        "registration_errors": lambda root: rewrite_first(root, r"^\| FX-02 [^\n]*\n", "",
                                                           files=["docs/renewal/30_TESTPLAN.md"]),
    }
    failures = []
    for counter, mutate in mutations.items():
        root = copy_repo_subset(tmp_path / f"mutated-{counter}")
        mutate(root)
        code, counts, output = run_check(root)
        if code == 0 or counts.get(counter, 0) <= base[counter]:
            failures.append(f"{counter}: exit {code}, {counts.get(counter)} vs baseline {base[counter]}")
        if base_exit == 0 and code == 0:
            failures.append(f"{counter}: a clean baseline stayed green after the mutation")
    assert not failures, "\n".join(failures)
    # Automated results and manual sign-offs are produced by different, separately reported commands.
    for command in ("report", "score", "attest"):
        done = subprocess.run([sys.executable, "tools/trace.py", command, "--help"], cwd=REPO, capture_output=True,
                              text=True, timeout=120)
        assert done.returncode == 0, f"tools/trace.py {command} is not implemented"
    score = subprocess.run([sys.executable, "tools/trace.py", "score", "--help"], cwd=REPO, capture_output=True,
                           text=True, timeout=120).stdout.lower()
    assert "automated" in score and "manual" in score, "score must report automated and manual separately"


DISCLOSURES = {
    "network services and purpose": (r"network", [r"provider\s+`?none`?", r"openai-compatible", r"release host|package index"]),
    "outside-vault access": (r"outside[- ](the[- ])?vault", [r"~/\.mdflow/cache", r"cache"]),
    "telemetry": (r"telemetry", [r"\bno (client )?telemetry"]),
    "account, key and cost": (r"(account|api key).*(cost|key)|cost", [r"MDFLOW_API_KEY", r"charge|cost"]),
    "migration and operation": (r"migration|operation", [r"venv|virtual environment", r"snapshot"]),
}
TELEMETRY_HOSTS = re.compile(r"sentry\.io|google-analytics|googletagmanager|segment\.(io|com)|mixpanel|amplitude\.com|"
                             r"posthog|datadoghq|newrelic|bugsnag|rollbar|hotjar|plausible\.io|app-measurement", re.I)
NET_IMPORTS = re.compile(r"^\s*(import|from)\s+(socket|ssl|http\.client|http\.server|urllib\.request|requests|httpx|aiohttp|"
                         r"websockets?)\b", re.M)
SHELL_NET = re.compile(r"\bfetch\(|XMLHttpRequest|WebSocket|requestUrl|require\(['\"](http|https|net|dgram|tls)['\"]\)|"
                       r"from ['\"](node:)?(http|https|net|dgram|tls)['\"]")
ALLOWED_HOSTS = {"api.openai.com", "localhost", "127.0.0.1"}


def readme_sections(text):
    sections, current = {}, None
    for line in text.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            current = (len(heading[1]), heading[2])
            sections[current] = []
        elif current:
            sections[current].append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


@pytest.mark.req("REQ-PKG-16")
@pytest.mark.cov("S0", "FM9")
def test_PT_16_readme_has_the_five_disclosures_and_code_has_no_telemetry_or_unplanned_sockets():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    sections = readme_sections(readme)
    missing = []
    for label, (heading_pattern, body_patterns) in DISCLOSURES.items():
        bodies = [body for (_, title), body in sections.items() if re.search(heading_pattern, title, re.I)]
        if not bodies or not any(len(b.strip()) >= 150 for b in bodies):
            missing.append(f"{label}: no README heading with substantive content")
            continue
        for pattern in body_patterns:
            if not any(re.search(pattern, b, re.I) for b in bodies):
                missing.append(f"{label}: content lacks /{pattern}/")
    assert not missing, "\n".join(missing)

    problems, sources = [], [*sorted((REPO / "engine/src").rglob("*.py")), *sorted((REPO / "shell/src").rglob("*.ts"))]
    assert sources
    for path in [REPO / "README.md", *sources]:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(REPO).as_posix()
        for match in TELEMETRY_HOSTS.finditer(text):
            problems.append(f"{relative}: telemetry endpoint {match[0]!r}")
        if path.suffix == ".py":
            if NET_IMPORTS.search(text) and relative != "engine/src/mdflow/providers/openai_compat.py":
                problems.append(f"{relative}: network-capable import outside the OpenAI-compatible provider")
        elif path.suffix == ".ts" and SHELL_NET.search(text):
            problems.append(f"{relative}: the shell must not open sockets (JT-20)")
        if path != REPO / "README.md":
            # The LibreOffice profile's XML namespace is a schema identifier,
            # not a destination; retain the network-host checks for other URLs.
            text = text.replace('xmlns:oor="http://openoffice.org/2001/registry"', '')
            for host in re.findall(r"https?://([^/\s\"'`)<>\]:]+)", text):
                if host.lower() not in ALLOWED_HOSTS:
                    problems.append(f"{relative}: unplanned host {host}")
    assert not problems, "\n".join(problems)


LAUNCHER = "import subprocess, sys; sys.exit(subprocess.call(sys.argv[1:]))"


@pytest.mark.req("REQ-PKG-05")
@pytest.mark.cov("S0", "FM9")
@pytest.mark.fx("FX-02", "FX-62")
def test_PT_22_terminal_launched_key_reaches_the_engine_child_but_no_diagnostic_or_file(tmp_path, gen_core,
                                                                                       source_engine, mock_http):
    source = gen_core.generate("FX-02", tmp_path / "input", pages=2)
    flags = ["--provider", "openai-compatible", "--model", "pt-model", "--cache", "cache"]
    launch_env = {"MDFLOW_API_KEY": SENTINEL, "MDFLOW_BASE_URL": mock_http.base_url}

    def through_terminal(*args):
        """terminal (key in env) -> launched app -> engine: two inheriting hops, no argv, no file."""
        engine_argv = source_engine.popen_args([str(a) for a in args])["args"]
        argv = [sys.executable, "-c", LAUNCHER, sys.executable, "-c", LAUNCHER, *engine_argv]
        env = dict(source_engine.env, **launch_env)
        return subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8",
                              timeout=300)

    outputs = []
    plan = through_terminal("plan", source.parent.name, *flags)
    outputs.append(plan)
    assert plan.returncode in (0, 3), plan.stderr  # SPEC 8.4: plan may announce missing consent (exit 3)
    plan_hash = json_objects(plan.stdout)[0]["plan_hash"]
    run = through_terminal("run", source.parent.name, "-o", "out", *flags, "--yes", plan_hash, "--progress", "jsonl")
    outputs.append(run)
    assert run.returncode == 0, (run.stdout, run.stderr)
    posts = [r for r in mock_http.requests if r["method"] == "POST"]
    assert posts, "the provider received no request: the key did not reach the engine child"
    assert all(r["headers"].get("authorization") == f"Bearer {SENTINEL}" for r in posts)
    for command in (("version",), ("providers",), ("selftest",)):
        outputs.append(through_terminal(*command))
    for done in outputs:
        assert SENTINEL not in done.stdout and SENTINEL not in done.stderr
    leaked = [p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")
              if p.is_file() and SENTINEL.encode() in p.read_bytes()]
    assert not leaked, f"credential persisted in {leaked}"
    # Without the key the remote provider is refused at startup while the default provider stays usable.
    missing = source_engine.run("run", source.parent.name, "-o", "out2", *flags, env={"MDFLOW_BASE_URL": mock_http.base_url})
    assert missing.returncode == 1 and "E_PROVIDER_CONFIG" in missing.stderr
    local = source_engine.run("run", source.parent.name, "-o", "out3", "--cache", "cache3")
    assert local.returncode == 0, local.stderr
