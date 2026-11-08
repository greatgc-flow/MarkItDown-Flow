"""PT-04, PT-18, PT-19, PT-20, PT-21: release evidence schemas and the cleanup tool.

The validators and cleanup live in ``tools/release_evidence.py`` (red stubs). The schemas below ARE the
specification the green step implements. A schema-valid file proves a named person supplied a well-formed
record, never that the recorded property is true; real evidence files are supplied outside this repository's CI.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

import pytest

from _support import REPO, SHA40, load_py, load_yaml, sha256_file, tree_digest

OSES = ("windows", "macos", "linux")
CHANNELS = ("minimum", "current")
ASSETS = ("main.js", "manifest.json", "styles.css", "engine.zip", "engine.lock", "SHA256SUMS")
REHEARSAL_CHECKS = ("fresh_install", "upgrade_from_1_0_8", "rollback", "consent_dismiss", "consent_approve",
                    "mixed_document_mock_ocr", "warm_rerun", "cancel_restart", "terminal_env_launch", "commands", "en_ko")
POSTDEPLOY_CHECKS = ("install_via_listing", "version_check", "sanitized_migration", "local_conversion",
                     "offline_mock_ocr", "restart", "pending_failure_display", "warm_rerun")
HEX = "ab" * 32


@pytest.fixture(scope="module")
def evidence():
    return load_py(REPO / "tools/release_evidence.py", "mdflow_pt_release_evidence")


def without(sample, *path):
    data = deepcopy(sample)
    node = data
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return data


def changed(sample, value, *path):
    data = deepcopy(sample)
    node = data
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return data


def assert_validator(validate, sample, mutations):
    assert validate(sample) == [], validate(sample)
    escaped = [name for name, bad in mutations.items() if not validate(bad)]
    assert not escaped, f"invalid records accepted: {escaped}"


# ------------------------------------------------------------------- PT-04 (H)

REQUIRED_TARGETS = tuple(f"{o}:x64:py{p}" for o in ("windows-2022", "ubuntu-24.04", "macos-15-intel") for p in ("3.10", "3.14"))


def check_artifacts(data: dict) -> list[str]:
    problems = [f"missing {k}" for k in ("checked_by", "date", "commit", "lock_entries", "install_logs") if not data.get(k)]
    if problems:
        return problems
    if not SHA40.fullmatch(str(data["commit"])):
        problems.append("commit is not a 40-hex SHA")
    entries = {e.get("name"): e for e in data["lock_entries"]}
    core = entries.get("markitdown-gc")
    if not core or core.get("version") != "0.3.5":
        problems.append("markitdown-gc 0.3.5 is not recorded (do not substitute upstream markitdown)")
    for entry in data["lock_entries"]:
        label = f"{entry.get('name')}=={entry.get('version')}"
        if not str(entry.get("url", "")).startswith("https://"):
            problems.append(f"{label}: no https artifact URL")
        if not (isinstance(entry.get("sha256"), str) and len(entry["sha256"]) == 64):
            problems.append(f"{label}: no sha256")
        if not entry.get("license"):
            problems.append(f"{label}: no license")
        missing = set(REQUIRED_TARGETS) - set(entry.get("targets") or [])
        if missing:
            problems.append(f"{label}: no wheel for {sorted(missing)}")
    logged = {log.get("target") for log in data["install_logs"] if log.get("exit") == 0}
    if set(REQUIRED_TARGETS) - logged:
        problems.append(f"no passing isolated install log for {sorted(set(REQUIRED_TARGETS) - logged)}")
    return problems


@pytest.mark.release
@pytest.mark.human
@pytest.mark.req("REQ-PKG-04")
@pytest.mark.cov("S0", "FM10")
def test_PT_04_public_artifact_license_and_target_wheel_evidence(attest_dir):
    good = {"checked_by": "Reviewer", "date": "2026-11-09", "commit": "a" * 40,
            "lock_entries": [{"name": "markitdown-gc", "version": "0.3.5", "url": "https://files.example/x.whl",
                              "sha256": HEX, "license": "MIT", "targets": list(REQUIRED_TARGETS)}],
            "install_logs": [{"target": t, "exit": 0, "log": "isolated install log"} for t in REQUIRED_TARGETS]}
    assert check_artifacts(good) == []
    for broken in (without(good, "lock_entries"), changed(good, "0.3.4", "lock_entries", 0, "version"),
                   changed(good, "", "lock_entries", 0, "license"), changed(good, [], "install_logs")):
        assert check_artifacts(broken), "the validator accepted incomplete artifact evidence"
    path = attest_dir / "pkg04_core_artifacts.json"
    if not path.is_file():
        pytest.skip(f"human evidence absent: {path.as_posix()} (TODO-VERIFY public markitdown-gc 0.3.5 artifacts; mode H)")
    problems = check_artifacts(json.loads(path.read_text(encoding="utf-8")))
    assert not problems, "\n".join(problems)


# ------------------------------------------------------------------- PT-18

def rehearsal_sample():
    runs = [{"os": o, "obsidian_channel": c, "obsidian_version": "1.8.9" if c == "current" else "1.6.0",
             "python": "3.14.0", "engine": "2.0.0", "core": "0.3.5",
             "downloads": [{"asset": a, "sha256": HEX} for a in ASSETS],
             "checks": {name: "PASS" for name in REHEARSAL_CHECKS}} for o in OSES for c in CHANNELS]
    return {"id": "MAN-04", "reviewer": "Named Reviewer", "date": "2026-11-09", "commit": "a" * 40,
            "candidate_tag": "2.0.0", "manifest_version": "2.0.0", "versions_json_entry": "2.0.0",
            "runs": runs, "verdict": "PASS"}


@pytest.mark.release
@pytest.mark.req("REQ-PKG-18")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-72")
def test_PT_18_rehearsal_checklist_schema_and_draft_release_is_the_tested_bytes(evidence, attest_dir):
    sample = rehearsal_sample()
    mutations = {f"missing {k}": without(sample, k) for k in sample}
    mutations.update({
        "missing run (windows/minimum)": changed(sample, sample["runs"][1:], "runs"),
        "failed check": changed(sample, "FAIL", "runs", 0, "checks", "warm_rerun"),
        "absent check": without(sample, "runs", 3, "checks", "cancel_restart"),
        "bad digest": changed(sample, "xyz", "runs", 0, "downloads", 0, "sha256"),
        "tag and manifest disagree": changed(sample, "2.0.1", "manifest_version"),
        "bad commit": changed(sample, "abc", "commit"),
        "verdict": changed(sample, "FAIL", "verdict"),
    })
    assert_validator(evidence.validate_rehearsal, sample, mutations)
    bundle = os.environ.get("MDFLOW_RELEASE_BUNDLE")
    if not bundle:
        pytest.skip("FX-72 release bundle absent: draft release == tested bytes cannot be checked (mode R)")
    folder = Path(bundle)
    candidate = json.loads((folder / "release-candidate.json").read_text(encoding="utf-8"))
    draft = {a["name"]: a["sha256"] for a in candidate["draft_release"]["assets"]}
    assert draft == {name: sha256_file(folder / name) for name in ASSETS}, "draft release bytes differ from the tested bytes"
    path = attest_dir / "release_rehearsal.yml"
    if not path.is_file():
        pytest.skip(f"human evidence absent: {path.as_posix()} (MAN-04 rehearsal; mode H)")
    problems = evidence.validate_rehearsal(load_yaml(path.read_text(encoding="utf-8")))
    assert not problems, "\n".join(problems)


# ------------------------------------------------------------------- PT-19

def postdeploy_sample():
    environments = [{"os": o, "vault": v, "app_version": "1.8.9", "python": "3.14.0", "unexpected_egress": 0,
                     "checks": {name: "PASS" for name in POSTDEPLOY_CHECKS}} for o in OSES for v in ("clean", "upgrade")]
    return {"listing": {"id": "markitdown-flow", "version": "2.0.0"}, "commit": "a" * 40,
            "installed_assets": [{"asset": a, "sha256": HEX, "matches_release": True} for a in ASSETS[:5]],
            "environments": environments, "critical_failed": False, "rollback_triggered": False}


@pytest.mark.req("REQ-PKG-19")
@pytest.mark.cov("S0", "FM0")
def test_PT_19_postdeploy_report_schema_validator(evidence):
    sample = postdeploy_sample()
    failing = changed(changed(sample, "FAIL", "environments", 0, "checks", "restart"), True, "critical_failed")
    mutations = {f"missing {k}": without(sample, k) for k in sample}
    mutations.update({
        "missing environment (linux/upgrade)": changed(sample, sample["environments"][:-1], "environments"),
        "unexpected egress": changed(sample, 1, "environments", 0, "unexpected_egress"),
        "asset differs from release": changed(sample, False, "installed_assets", 0, "matches_release"),
        "failed check without rollback": changed(sample, "FAIL", "environments", 0, "checks", "restart"),
        "critical failure without rollback procedure": failing,
        "absent check": without(sample, "environments", 2, "checks", "warm_rerun"),
        "wrong listing version": changed(sample, "1.0.8", "listing", "version"),
    })
    assert_validator(evidence.validate_postdeploy, sample, mutations)
    # A failed critical check is valid only when the rollback/hotfix procedure was triggered.
    assert evidence.validate_postdeploy(changed(failing, True, "rollback_triggered")) == []


# ------------------------------------------------------------------- PT-20

def rollback_sample():
    return {"reviewer": "Named Reviewer", "date": "2026-11-09", "vault": {"isolated": True, "label": "rehearsal-vault"},
            "restored_assets": [{"asset": a, "sha256": HEX, "version": "1.0.8"} for a in ("main.js", "manifest.json", "styles.css")],
            "data_v1_json": {"sanitized": True, "secrets_present": False}, "v1_preferences_recovered": True,
            "v1_commands_recovered": True, "secrets_exposed": False, "schema2_data_fed_to_v1": False,
            "manual_credential_reconfiguration": ["re-enter provider key in the terminal environment"],
            "runtime_rollback": {"previous_venv_selected": True, "incompatible_interpreter_rejected": True}}


@pytest.mark.release
@pytest.mark.human
@pytest.mark.req("REQ-PKG-20")
@pytest.mark.cov("S0", "FM0")
def test_PT_20_rollback_rehearsal_schema_validator(evidence, attest_dir):
    sample = rollback_sample()
    mutations = {f"missing {k}": without(sample, k) for k in sample}
    mutations.update({
        "not isolated": changed(sample, False, "vault", "isolated"),
        "secrets exposed": changed(sample, True, "secrets_exposed"),
        "secret in restored data": changed(sample, True, "data_v1_json", "secrets_present"),
        "schema 2 data fed to v1": changed(sample, True, "schema2_data_fed_to_v1"),
        "v1 preferences lost": changed(sample, False, "v1_preferences_recovered"),
        "incompatible interpreter accepted": changed(sample, False, "runtime_rollback", "incompatible_interpreter_rejected"),
        "non-1.0.8 asset restored": changed(sample, "2.0.0", "restored_assets", 0, "version"),
    })
    assert_validator(evidence.validate_rollback, sample, mutations)
    path = attest_dir / "rollback_rehearsal.json"
    if not path.is_file():
        pytest.skip(f"human evidence absent: {path.as_posix()} (isolated-vault rollback rehearsal; mode H)")
    problems = evidence.validate_rollback(json.loads(path.read_text(encoding="utf-8")))
    assert not problems, "\n".join(problems)


# ------------------------------------------------------------------- PT-21

def build_vault(root: Path):
    plugin = root / ".obsidian/plugins/markitdown-flow"
    content = {
        "notes/user.md": "user note", "out/report.pdf.md": "converted output", "external-backups/data.json.bak": "backup",
        ".obsidian/plugins/markitdown-flow/data.json": "settings", ".obsidian/plugins/markitdown-flow/cache/units/ab/e.json": "{}",
        ".obsidian/plugins/markitdown-flow/logs/run.log": "historic log",
        ".obsidian/plugins/markitdown-flow/data.v1.json.bak": "sanitized snapshot",
        ".obsidian/plugins/markitdown-flow/engine.lock.released": "released lock",
        ".obsidian/plugins/markitdown-flow/transport-123.tmp": "stale transport",
        ".obsidian/plugins/markitdown-flow/wrapper.v1.cmd": "retired generated wrapper",
        ".obsidian/plugins/markitdown-flow/transport-live.tmp": "owned but its process is alive",
    }
    for relative, text in content.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return plugin


@pytest.mark.req("REQ-PKG-21")
@pytest.mark.cov("S0", "FM12")
def test_PT_21_cleanup_dry_run_lists_only_owned_paths_and_leaves_sentinels_unchanged(evidence, tmp_path):
    plugin = build_vault(tmp_path / "vault")
    owned = ["transport-123.tmp", "wrapper.v1.cmd", "transport-live.tmp"]
    verified = datetime(2026, 11, 9, tzinfo=timezone.utc)
    after = verified + timedelta(days=7, seconds=1)
    live = frozenset({"transport-live.tmp"})
    before = tree_digest(tmp_path / "vault")

    with pytest.raises(evidence.CleanupRefused):  # no successful post-deploy verification
        evidence.plan_cleanup(plugin, owned, verified_at=None, now=after, live=live)
    with pytest.raises(evidence.CleanupRefused):  # still inside the seven-day rollback window
        evidence.plan_cleanup(plugin, owned, verified_at=verified, now=verified + timedelta(days=6, hours=23), live=live)
    for escaping in (["../../notes/user.md"], [str(tmp_path / "vault/notes/user.md")], ["cache/../../data.json", "x/../.."]):
        with pytest.raises(evidence.CleanupRefused):
            evidence.plan_cleanup(plugin, escaping, verified_at=verified, now=after, live=live)
    protected = ["data.json", "data.v1.json.bak", "engine.lock.released", "logs/run.log", "cache/units/ab/e.json"]
    with pytest.raises(evidence.CleanupRefused):  # settings, snapshot, locks, logs and cache are never cleanup targets
        evidence.plan_cleanup(plugin, protected, verified_at=verified, now=after, live=live)

    plan = evidence.plan_cleanup(plugin, owned, verified_at=verified, now=after, live=live)
    assert sorted(Path(p).resolve() for p in plan) == sorted([(plugin / "transport-123.tmp").resolve(),
                                                             (plugin / "wrapper.v1.cmd").resolve()])
    assert tree_digest(tmp_path / "vault") == before, "the dry run changed files"

    log = tmp_path / "cleanup-log.txt"
    result = evidence.execute_cleanup(plugin, plan, log=log)
    removed = {Path(p).name for p in result["removed"]}
    assert removed == {"transport-123.tmp", "wrapper.v1.cmd"}
    assert "transport-live.tmp" in {Path(p).name for p in result["retained"]}
    after_digest = tree_digest(tmp_path / "vault")
    assert after_digest == {k: v for k, v in before.items() if Path(k).name not in removed}, \
        "cleanup changed or removed a protected file"
    text = log.read_text(encoding="utf-8")
    assert all(name in text for name in removed) and "transport-live.tmp" in text, "log must record removed and retained"
