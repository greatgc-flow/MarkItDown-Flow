"""PT-03, PT-07, PT-09, PT-11, PT-12: CI matrix, action pinning and permissions (mode A, every CI run).

These read the repository's workflows as data. They are RED while ``.github/workflows`` still carries the
v1 release workflow and no shell/contract/smoke jobs; they never run CI.
"""
import json
import re

import pytest

from _support import (REPO, SHA40, allowed_failure, audit_uses, expand_matrix, jobs, load_workflows, step_text,
                      transitive_needs, triggers, workflow_files)

REQUIRED_OS = ("windows-2022", "ubuntu-24.04", "macos-15-intel")
REQUIRED_PY = ("3.10", "3.14")
EXPERIMENTAL_PY = "3.15"


def all_jobs():
    return [(name, jid, job) for name, wf in load_workflows().items() for jid, job in jobs(wf).items()]


def job_named(jid):
    found = [job for _, name, job in all_jobs() if name == jid]
    assert found, f"no workflow job named {jid!r}"
    return found[0]


def runs_on_cells(job):
    return [(c.get("os"), c.get("python"), allowed_failure(job, c)) for c in expand_matrix(job)]


@pytest.mark.req("REQ-PKG-03")
@pytest.mark.cov("S0", "FM10")
def test_PT_03_core_range_endpoints_are_visible_jobs_and_resolver_failure_fails():
    low, high = job_named("contract-min"), job_named("contract-max")
    text_low, text_high = step_text(low), step_text(high)
    assert "markitdown-gc==0.3.5" in text_low, "contract-min must install exactly Core 0.3.5"
    assert re.search(r"markitdown-gc\s*(>=\s*0\.3\.5\s*,\s*)?<\s*0\.4", text_high), \
        "contract-max must resolve the newest publicly available Core below 0.4"
    for label, job, text in (("contract-min", low, text_low), ("contract-max", high, text_high)):
        assert "engine/tests/contract" in text and "pytest" in text, f"{label} does not run the contract suite"
        assert re.search(r"importlib\.metadata|pip show|pip freeze", text), f"{label} does not log the resolved Core"
        assert job.get("continue-on-error") in (None, False), f"{label} is allowed to fail"
        assert not any(step.get("continue-on-error") for step in job.get("steps") or []), label
        assert not re.search(r"\|\|\s*(true|:)|exit\s+0\b", text), f"{label} swallows a resolver/network failure"
    pyproject = (REPO / "engine/pyproject.toml").read_text(encoding="utf-8")
    assert '"markitdown-gc>=0.3.5,<0.4"' in pyproject, "engine dependency range must equal SPEC 3.0"


@pytest.mark.req("REQ-PKG-07", "REQ-GEN-03")
@pytest.mark.cov("S0", "FM0")
def test_PT_07_engine_matrix_has_six_required_three_experimental_cells_and_gates_release():
    engine = [(name, jid, job) for name, jid, job in all_jobs()
              if "pytest" in step_text(job) and EXPERIMENTAL_PY in {c.get("python") for c in expand_matrix(job)}]
    assert engine, "no engine pytest matrix job with the 3.10/3.14/3.15 cells"
    cells = set()
    for _, jid, job in engine:
        assert (job.get("strategy") or {}).get("fail-fast") is False, f"{jid}: fail-fast must be false"
        cells |= set(runs_on_cells(job))
    expected = {(o, p, p == EXPERIMENTAL_PY) for o in REQUIRED_OS for p in (*REQUIRED_PY, EXPERIMENTAL_PY)}
    assert cells == expected, f"matrix cells differ from 25_PACKAGING 3: {sorted(cells ^ expected)}"
    assert sum(1 for c in cells if not c[2]) == 6 and sum(1 for c in cells if c[2]) == 3
    for _, jid, job in engine:
        text = step_text(job)
        setups = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/setup-python@")]
        assert setups, f"{jid}: Python must be set explicitly with setup-python"
        with_ = setups[0].get("with") or {}
        assert with_.get("python-version") == "${{ matrix.python }}" and with_.get("architecture") == "x64"
        for needle in ("sys.version", "platform.machine", "ImageVersion"):
            assert needle in text, f"{jid}: log must record {needle} (resolved patch, architecture, runner image)"
        run_text = "\n".join(str(s.get("run", "")) for s in job["steps"])
        for sha in set(re.findall(r"@([0-9a-f]{40})", json.dumps(job["steps"]))):
            assert sha in run_text, f"{jid}: action SHA {sha} is not recorded in the log"
    for name, wf in load_workflows().items():
        for jid, job in jobs(wf).items():
            on = str(job.get("runs-on"))
            assert "macos-14" not in on and "latest" not in on, f"{name}:{jid} uses a retired or floating label"
    # Release is gated on the six required results; experimental failures cannot turn it green or block it.
    flows = load_workflows()
    publishers = [(name, wf, jid) for name, wf in flows.items() for jid, job in jobs(wf).items()
                  if isinstance(job.get("permissions"), dict) and "write" in job["permissions"].values()]
    assert publishers, "no release workflow job with elevated permissions to gate"
    for name, wf, jid in publishers:
        gating = [jobs(wf)[n] for n in transitive_needs(jobs(wf), jid)]
        reusable = [j for j in gating if str(j.get("uses", "")).startswith("./.github/workflows/")]
        covered = any({(c[0], c[1]) for c in runs_on_cells(j) if not c[2]} >= {(o, p) for o in REQUIRED_OS for p in REQUIRED_PY}
                      for j in gating if expand_matrix(j) != [{}])
        assert covered or reusable, f"{name}:{jid} does not depend on the six required engine cells"


@pytest.mark.req("REQ-PKG-09")
@pytest.mark.cov("S0", "FM0")
def test_PT_09_shell_jobs_on_three_os_pinned_node_and_python_smokes():
    shell = [(name, jid, job) for name, jid, job in all_jobs() if "npm ci" in step_text(job)]
    assert shell, "no shell job runs `npm ci`"
    oses = set()
    for name, jid, job in shell:
        assert job.get("if") not in (False, "false", "${{ false }}"), f"{name}:{jid} is disabled"
        text = step_text(job)
        for command in ("npm ci", "npm run typecheck", "npm run build"):
            assert command in text, f"{jid}: missing `{command}`"
        assert re.search(r"npm test|npx jest|npm run test", text), f"{jid}: Jest is not run"
        assert re.search(r"working-directory\W+shell|cd shell", text), f"{jid}: not run in shell/"
        node = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/setup-node@")]
        assert node, f"{jid}: Node must be set up explicitly"
        version = str((node[0].get("with") or {}).get("node-version", ""))
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"{jid}: exact Node patch required, got {version!r}"
        oses |= {c.get("os") for c in expand_matrix(job)}
    assert oses == set(REQUIRED_OS), f"shell jobs must run on the three labels, got {sorted(map(str, oses))}"
    assert any("JT-SHL-19-01" in step_text(job) for _, _, job in all_jobs()), "JT-SHL-19-01 is not run by name"
    package = json.loads((REPO / "shell/package.json").read_text(encoding="utf-8"))
    assert {"test", "typecheck", "build"} <= set(package["scripts"])
    smoke = {(c.get("os"), c.get("python")) for _, _, job in all_jobs()
             if "mdflow version" in step_text(job) and "classify" in step_text(job) for c in expand_matrix(job)}
    expected = {(o, p) for o in REQUIRED_OS for p in ("3.11", "3.12", "3.13")}
    assert expected <= smoke, f"install/version/classify smokes missing for {sorted(expected - smoke)}"


@pytest.mark.req("REQ-PKG-11")
@pytest.mark.cov("S0", "FM9")
def test_PT_11_every_external_uses_is_a_reviewed_full_sha():
    floating = "steps:\n  - uses: actions/checkout@v4\n  - uses: actions/setup-node@main\n" \
               f"  - uses: a/b/.github/workflows/w.yml@{'a' * 39}\n  - uses: docker://alpine:3\n"
    assert len(audit_uses(floating)) == 4, "the scanner must reject tags, branches, short SHAs and tag-only images"
    assert len(audit_uses(f"  - uses: actions/checkout@{'a' * 40}\n")) == 1, "a version comment is required"
    assert audit_uses(f"  - uses: actions/checkout@{'a' * 40} # v4.2.2\n  - uses: ./.github/actions/x\n") == []
    files = workflow_files()
    assert files, "no workflows or composite actions found"
    evidence = (REPO / "docs/renewal/25_PACKAGING.md").read_text(encoding="utf-8")
    problems = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        problems += [f"{path.name}: {p}" for p in audit_uses(text)]
        for sha in re.findall(r"uses:\s*[^@\s]+@([0-9a-f]{40})", text):
            assert SHA40.fullmatch(sha)
            if sha not in evidence:
                problems.append(f"{path.name}: SHA {sha} has no review record in 25_PACKAGING section 4")
    assert not problems, "\n".join(problems)


@pytest.mark.req("REQ-PKG-12")
@pytest.mark.cov("S0", "FM9")
def test_PT_12_least_privilege_jobs_and_no_privileged_pr_context():
    flows = load_workflows()
    assert flows, "no workflows"
    problems, attest_jobs, publish_jobs = [], [], []
    for name, wf in flows.items():
        trig = triggers(wf)
        if "pull_request_target" in trig:
            problems.append(f"{name}: pull_request_target is forbidden")
        if wf.get("permissions") != {"contents": "read"}:
            problems.append(f"{name}: top-level permissions must be exactly `contents: read`")
        raw = (REPO / name).read_text(encoding="utf-8")
        if "pull_request" in trig and re.search(r"secrets\.(?!GITHUB_TOKEN\b)\w+", raw):
            problems.append(f"{name}: PR-triggered workflow references a secret")
        for jid, job in jobs(wf).items():
            perms = job.get("permissions") or {}
            if not isinstance(perms, dict):
                problems.append(f"{name}:{jid}: permissions must be an explicit map")
                continue
            elevated = {k for k, v in perms.items() if v == "write"}
            if elevated & {"id-token", "attestations"}:
                attest_jobs.append((name, jid))
                if elevated - {"id-token", "attestations"}:
                    problems.append(f"{name}:{jid}: the attestation job may hold nothing but id-token/attestations")
            elif elevated == {"contents"}:
                publish_jobs.append((name, jid))
            elif elevated:
                problems.append(f"{name}:{jid}: unexpected write permissions {sorted(elevated)}")
            if elevated and trig & {"pull_request", "pull_request_target"}:
                problems.append(f"{name}:{jid}: write token reachable from a pull request")
    assert not problems, "\n".join(problems)
    assert len(attest_jobs) == 1 and len(publish_jobs) == 1, \
        f"exactly one attest job and one publish job expected, got {attest_jobs} / {publish_jobs}"
    (aname, attest), (pname, publish) = attest_jobs[0], publish_jobs[0]
    assert aname == pname, "attest and publish must live in one release workflow"
    all_ = jobs(flows[pname])
    assert attest in transitive_needs(all_, publish), "publication must follow attestation"
    assert transitive_needs(all_, attest), "attestation must follow build and test jobs"
