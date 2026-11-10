"""PT-23 (mode A): the owner's manual-evidence path: evidence workflow, fill-in templates and review guide.

``release.yml`` downloads artifact ``named-release-evidence`` from a separate run; this module proves that
something produces it (``evidence.yml``), that the four templates carry every field ``tools/trace.py attest``
and ``tools/release_evidence.py validate_rehearsal`` need (so an unfilled template can never pass), and that
the owner guide exists. Nothing here certifies a human sign-off; a filled record is validated, never believed.
"""
from copy import deepcopy
import json
import re
import subprocess
import sys

import pytest

from _support import REPO, SUBJECTS, audit_uses, jobs, load_workflows, load_yaml, step_text, triggers

WORKFLOW = ".github/workflows/evidence.yml"
TEMPLATES = REPO / "docs/renewal/manual-templates"
GUIDE = REPO / "docs/renewal/MANUAL_REVIEW_GUIDE.md"
ARTIFACT = "named-release-evidence"
MANUAL_FILES = {"MAN-01": "R15_cleanroom.yml", "MAN-02": "R16_readme_review.yml",
                "MAN-03": "shell_i18n_review.yml", "MAN-04": "release_rehearsal.yml"}
# Same pattern the workflow greps with: an unfilled `<UPPER CASE>` placeholder or a TODO value.
PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9 /_.-]*>|\bTODO\b")
COMMIT = "c" * 40
HEX64 = "ab" * 32


def evidence_job():
    flow = load_workflows().get(WORKFLOW)
    assert flow is not None, f"{WORKFLOW} does not exist"
    assert len(jobs(flow)) == 1, "one job validates and uploads"
    return flow, next(iter(jobs(flow).values()))


def run_attest(identity, folder, commit=COMMIT):
    done = subprocess.run([sys.executable, "tools/trace.py", "attest", identity, "--attest-dir", str(folder),
                           "--commit", commit], cwd=REPO, capture_output=True, text=True, encoding="utf-8", timeout=120)
    return done.returncode, done.stdout + done.stderr


def fill(node, key=""):
    """Replace every placeholder/TODO the way a reviewer would, by field meaning."""
    if isinstance(node, dict):
        return {k: fill(v, k) for k, v in node.items()}
    if isinstance(node, list):
        return [fill(v, key) for v in node]
    if not isinstance(node, str) or not PLACEHOLDER.search(node):
        return node
    if node.strip() == "TODO":
        return "PASS"  # a result, a rehearsal check or the verdict
    return {"reviewer": "cx/cx.effort/gpt-6.1-sol", "implementer": "cc.fable", "date": "2026-11-09",
            "commit": COMMIT, "sha256": HEX64,
            "obsidian_version": json.loads((REPO / 'manifest.json').read_text())['minAppVersion']}.get(key, "filled value")


def load_template(identity):
    path = TEMPLATES / MANUAL_FILES[identity]
    assert path.is_file(), f"missing template {path.relative_to(REPO).as_posix()}"
    return path, load_yaml(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ workflow

@pytest.mark.req("REQ-PKG-22")
@pytest.mark.cov("S0", "FM9")
def test_PT_23_evidence_workflow_is_least_privilege_and_documented_with_an_owner_guide():
    check_workflow()
    check_documents()
    check_guide()


@pytest.mark.req("REQ-PKG-22")
@pytest.mark.cov("S0", "FM10")
def test_PT_37_placeholder_step_scans_peer_authored_source_evidence_only():
    _, job = evidence_job()
    step = next(s for s in job["steps"] if s.get("name") == "Reject unfilled template placeholders")
    assert step.get("env", {}).get("EVIDENCE_FOLDER") == "${{ steps.bind.outputs.folder }}"
    script = step["run"]
    assert "build/evidence" not in script, "machine-enriched pip metadata is validated by validate_extra"
    for extension in ("json", "yml"):
        assert f'"$EVIDENCE_FOLDER"/*.{extension}' in script
    assert f"grep -nE '{PLACEHOLDER.pattern}'" in script


def check_workflow():
    flow, job = evidence_job()
    assert triggers(flow) == {"workflow_dispatch"}, "evidence.yml must be dispatch-only"
    on = flow.get("on", flow.get(True))
    inputs = on["workflow_dispatch"]["inputs"]
    assert inputs["path"]["default"] == "release-evidence/2.0.0"
    assert flow.get("permissions") == {"contents": "read", "actions": "read"}
    assert 'permissions' not in job, 'no job-level elevation'
    WORKFLOW_TEXT = (REPO / WORKFLOW).read_text(encoding="utf-8")
    # pinned release tool (engine/requirements-build.txt); no PyYAML wheel exists yet for the
    # experimental Python 3.15 cells, where this release-tooling check cannot run.
    yaml = pytest.importorskip("yaml", reason="PyYAML (release tool) unavailable on this interpreter")
    yaml.safe_load(WORKFLOW_TEXT)  # the small structural test reader is deliberately permissive
    assert "secrets." not in WORKFLOW_TEXT.replace("secrets.GITHUB_TOKEN", ""), "only GITHUB_TOKEN may be referenced"
    assert audit_uses(WORKFLOW_TEXT) == [], "every external action must be a SHA with a version comment"
    packaging = (REPO / "docs/renewal/25_PACKAGING.md").read_text(encoding="utf-8")
    used = {s["uses"] for s in job["steps"] if "uses" in s}
    assert used, "no actions used"
    for ref in used:
        name, _, sha = ref.partition("@")
        assert name in {"actions/checkout", "actions/setup-python", "actions/upload-artifact"}, \
            f"{name} is not in the reviewed action table"
        assert sha in packaging, f"{ref}: SHA is not recorded in 25_PACKAGING section 4"
    # Identical pins to ci.yml / release.yml: no second version of an action in the repository.
    release = (REPO / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for ref in used:
        assert ref in release or ref in (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8"), \
            f"{ref} is not the exact pin used elsewhere"
    checkout = next(s for s in job["steps"] if s["uses"].startswith("actions/checkout@"))
    assert checkout["with"]["persist-credentials"] is False
    text = step_text(job)
    for identity in ('MAN-01', 'MAN-02', 'MAN-03'):
        assert identity in text, f"{identity} is not attested"
    assert 'for identity in MAN-01 MAN-02 MAN-03 MAN-04' not in text
    assert 'tools/release_evidence.py produce' in text
    assert 'acceptance-evidence' in text and 'gh run download' in text
    assert "tools/trace.py attest" in text and "--commit" in text and "--attest-dir" in text
    assert "requirements-build.txt" in text, "PyYAML (release tool pin) must be installed for the MAN-04 YAML"
    assert "MANUAL_FILES" in text, "staged file names must come from tools/trace.py::MANUAL_FILES"
    # Placeholder guard, path-escape guard, candidate resolved from the tag/SHA input.
    assert "TODO" in text and "<[A-Z]" in text, "unfilled placeholders must be rejected"
    assert ".." in text, "an evidence path escaping the checkout must be rejected"
    assert "inputs.candidate" in text or "INPUT_CANDIDATE" in text
    # A failed attest fails the run, and the upload happens only after every check.
    steps = job["steps"]
    upload = next(i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("actions/upload-artifact@"))
    attest = next(i for i, s in enumerate(steps) if "tools/trace.py attest" in str(s.get("run", "")))
    assert attest < upload and "if" not in steps[upload], "upload must be skipped when anything failed"
    assert "exit 1" in str(steps[attest]["run"]) or "failed" in str(steps[attest]["run"])
    assert steps[upload]["with"]["name"] == ARTIFACT
    assert steps[upload]["with"]["if-no-files-found"] == "error"
    assert f"name: {ARTIFACT}" in release, "release.yml consumes a different artifact name"
    assert set(re.findall(r"build/manual/", release)), "release.yml no longer reads build/manual/"


def check_documents():
    packaging = (REPO / "docs/renewal/25_PACKAGING.md").read_text(encoding="utf-8")
    assert re.search(r"^REQ-PKG-22 MUST:", packaging, re.M), "REQ-PKG-22 is not defined in 25_PACKAGING"
    plan = (REPO / "docs/renewal/30_TESTPLAN.md").read_text(encoding="utf-8")
    for tid in ("PT-23", "PT-24"):
        assert re.search(rf"^\| {tid} \| REQ-PKG-22 ", plan, re.M), f"{tid} is not in the 30_TESTPLAN catalog"
    assert "evidence.yml" in packaging and "MANUAL_REVIEW_GUIDE" in packaging


# ----------------------------------------------------------------- templates

@pytest.mark.req("REQ-PKG-22")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.parametrize("identity", sorted(MANUAL_FILES))
def test_PT_24_template_fails_until_filled_and_passes_once_every_placeholder_is_replaced(identity, tmp_path):
    path, template = load_template(identity)
    assert template["id"] == identity
    assert PLACEHOLDER.search(json.dumps(template)), "a template must contain placeholders"
    # 1. As shipped, with a matching candidate commit supplied, validation fails (and names the verdict/checks).
    shipped = tmp_path / "shipped"
    shipped.mkdir()
    (shipped / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    code, output = run_attest(identity, shipped)
    assert code != 0, f"unfilled {path.name} passed validation:\n{output}"
    # 2. Replacing every placeholder makes the same structure pass: no required field is missing.
    filled = fill(deepcopy(template))
    assert not PLACEHOLDER.search(json.dumps(filled))
    ok = tmp_path / "filled"
    ok.mkdir()
    (ok / path.name).write_text(json.dumps(filled), encoding="utf-8")  # JSON is YAML; no PyYAML needed to test
    code, output = run_attest(identity, ok)
    assert code == 0, f"filled {identity} still invalid:\n{output}"
    # 3. The template itself carries every top-level field the validators require.
    required = {"id", "reviewer", "date", "commit", "inputs", "checks", "evidence", "verdict"}
    if identity == "MAN-01":
        required.add("implementer")
    if identity == "MAN-04":
        required |= {"candidate_tag", "manifest_version", "versions_json_entry", "runs"}
    assert required <= set(template), f"{identity} template lacks {sorted(required - set(template))}"
    # 4a. Every angle-bracket placeholder is one the workflow's guard recognises (none can slip through).
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("#"):
            for token in re.findall(r"<[^<>\n]*>", line):
                assert PLACEHOLDER.fullmatch(token), f"placeholder the guard would miss: {token}"
    # 4. Comments never trip the workflow's placeholder guard if the owner keeps them.
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            assert not PLACEHOLDER.search(line), f"comment would trip the placeholder guard: {line}"
    if identity == "MAN-01":  # the filled record is rejected when one person is both implementer and reviewer
        same = deepcopy(filled)
        same["implementer"] = same["reviewer"]
        (ok / path.name).write_text(json.dumps(same), encoding="utf-8")
        code, output = run_attest(identity, ok)
        assert code != 0 and "independent named implementer/reviewer" in output
    if identity == "MAN-04":
        check_rehearsal_template(template)


def check_rehearsal_template(template):
    from _support import load_py
    tool = load_py(REPO / "tools/release_evidence.py", "mdflow_pt_manual_release_evidence")
    runs = template["runs"]
    assert {(r["os"], r["obsidian_channel"]) for r in runs} == {(o, c) for o in ("windows", "macos", "linux")
                                                               for c in ("minimum", "current")} and len(runs) == 6
    for run in runs:
        assert [d["asset"] for d in run["downloads"]] == list(SUBJECTS)
        assert set(run["checks"]) == set(tool.REHEARSAL), "template must list exactly the required rehearsal checks"
        assert set(run["checks"].values()) == {"TODO"}
        assert run["engine"] == "2.0.0" and run["core"] == "0.3.7"
    assert {template[k] for k in ("candidate_tag", "manifest_version", "versions_json_entry")} == {"2.0.0"}
    assert tool.validate_rehearsal(template), "the unfilled rehearsal must fail the schema validator"
    assert tool.validate_rehearsal(fill(deepcopy(template))) == []


# --------------------------------------------------------------------- guide

def check_guide():
    assert GUIDE.is_file(), "docs/renewal/MANUAL_REVIEW_GUIDE.md is missing"
    text = GUIDE.read_text(encoding="utf-8")
    assert re.search(r"[가-힣]", text[:1500]), "a Korean summary must open the guide"
    for needle in ("MAN-01", "MAN-02", "MAN-03", "MAN-04", "implementer", "frozen-candidate", "evidence.yml",
                   "release-evidence/2.0.0", "named-release-evidence", "gh workflow run release.yml",
                   "evidence-run", "minimum", "current", "manual-templates", *MANUAL_FILES.values()):
        assert needle in text, f"guide does not mention {needle!r}"
    for name in MANUAL_FILES.values():
        assert (TEMPLATES / name).is_file()
