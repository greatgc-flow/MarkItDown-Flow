"""Security review of 2.0.0 (engine): C1 program lookup, C2 template credentials, P6 redaction names."""

import json
import os
from pathlib import Path

import pytest

from mdflow import cli, convert, exiftool, ledger, providers, redact
from mdflow.providers import command as command_module
from mdflow.providers.command import CommandProvider


def _program(folder: Path, name: str, marker: Path | None = None) -> Path:
    """A tiny program printing an exiftool-like version; it touches ``marker`` when it runs."""
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        path = folder / (name + ".cmd")
        touch = f'type nul > "{marker}"\n' if marker else ""
        path.write_text("@echo off\n" + touch + "echo 13.59\n", encoding="ascii")
    else:
        path = folder / name
        touch = f": > '{marker}'\n" if marker else ""
        path.write_text("#!/bin/sh\n" + touch + "echo 13.59\n", encoding="ascii")
        path.chmod(0o755)
    return path


@pytest.mark.req("REQ-SEC-03", "REQ-CNV-06")
@pytest.mark.cov("S0", "FM9")
def test_T_SEC_60_resolve_executable_skips_empty_current_and_relative_path_entries(tmp_path, monkeypatch):
    from mdflow.executable import resolve_executable

    work = tmp_path / "work"
    _program(work, "ocrtool")
    _program(work / "sub", "ocrtool")
    genuine = _program(tmp_path / "bin", "ocrtool")
    monkeypatch.chdir(work)
    unsafe = ["", ".", "sub", os.path.join(".", "sub")]
    assert resolve_executable("ocrtool", os.pathsep.join(unsafe)) is None, "only absolute PATH entries are searched"
    found = resolve_executable("ocrtool", os.pathsep.join([*unsafe, str(genuine.parent)]))
    assert found is not None and os.path.isabs(found) and Path(found).samefile(genuine)
    if os.name == "nt":
        monkeypatch.setenv("PATHEXT", ".COM;.EXE")
        assert resolve_executable("ocrtool", str(genuine.parent)) is None, "PATHEXT decides which extensions run"
        monkeypatch.setenv("PATHEXT", ".CMD")
        assert Path(resolve_executable("ocrtool.cmd", str(genuine.parent))).samefile(genuine), \
            "a name already carrying a PATHEXT extension is tried as is"


@pytest.mark.req("REQ-CNV-06", "REQ-CNV-07")
@pytest.mark.cov("S5", "FM9")
def test_T_SEC_61_exiftool_and_soffice_lookups_never_run_a_program_planted_in_the_current_folder(tmp_path, monkeypatch):
    marker = tmp_path / "planted-ran"
    work = tmp_path / "work"
    _program(work, "exiftool", marker)
    _program(work, "soffice", marker)
    empty = tmp_path / "empty"
    empty.mkdir()
    for name in ("EXIFTOOL_PATH", "SOFFICE_PATH", "NoDefaultCurrentDirectoryInExePath"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.chdir(work)
    cli.reset_optional_tool_probes()
    called = []
    monkeypatch.setattr(convert, "core_convert", lambda *args, **kwargs: called.append(kwargs))
    try:
        assert exiftool.detect()["status"] == "not_found"
        assert cli._libreoffice_versions()["libreoffice_status"] == "not_found"
        legacy = convert.convert_legacy(b"{\\rtf1 x}", dict(format="rtf"), run_temp=tmp_path / "run")
        assert [i["code"] for i in legacy["issues"]] == ["E_PRECONVERT"] and not called, "Core never looks soffice up"
        monkeypatch.setenv("EXIFTOOL_PATH", "exiftool")
        exiftool.reset()
        assert exiftool.detect()["status"] == "unusable", "a bare EXIFTOOL_PATH name is looked up on PATH only"
        # A bare SOFFICE_PATH name is looked up like EXIFTOOL_PATH, never handed to Core's own lookup (round 10).
        monkeypatch.setenv("SOFFICE_PATH", "soffice")
        cli.reset_optional_tool_probes()
        probe = cli._libreoffice_versions()
        assert probe["libreoffice_status"] == "unusable" and probe["libreoffice_source"] == "SOFFICE_PATH"
        legacy = convert.convert_legacy(b"{\\rtf1 x}", dict(format="rtf"), run_temp=tmp_path / "run")
        assert [i["code"] for i in legacy["issues"]] == ["E_PRECONVERT"] and not called, "bare SOFFICE_PATH not on PATH"
        genuine = _program(tmp_path / "bin", "soffice")
        monkeypatch.setenv("PATH", str(genuine.parent))
        convert.convert_legacy(b"{\\rtf1 x}", dict(format="rtf"), run_temp=tmp_path / "run2")
        assert len(called) == 1 and Path(called[0]["libreoffice_path"]).samefile(genuine), \
            "a bare SOFFICE_PATH name reaches Core as the absolute PATH program"
    finally:
        cli.reset_optional_tool_probes()
    assert not marker.exists(), "the planted program ran"


@pytest.mark.req("REQ-SEC-03")
@pytest.mark.cov("S10", "FM9")
@pytest.mark.fx("FX-63")
def test_T_SEC_62_command_program_is_pinned_to_an_absolute_path_in_the_destination(tmp_path, monkeypatch):
    _program(tmp_path / "work", "ocrtool")
    one = _program(tmp_path / "bin1", "ocrtool")
    _program(tmp_path / "bin2", "ocrtool")
    monkeypatch.chdir(tmp_path / "work")
    seen = []

    def popen(argv, **kwargs):
        seen.append(list(argv))
        raise FileNotFoundError("not started in this test")

    monkeypatch.setattr(command_module.subprocess, "Popen", popen)
    monkeypatch.setenv("PATH", str(one.parent))
    first = CommandProvider(command="ocrtool --x {input}", egress=False, model="m")
    assert first.transcribe(dict(mime="image/png"), b"png", None)["status"] == "failed"
    assert os.path.isabs(seen[0][0]) and Path(seen[0][0]).samefile(one)
    assert json.loads(first.meta["destination"][len("command:"):])[0] == seen[0][0]
    monkeypatch.setenv("PATH", str(tmp_path / "bin2"))
    second = CommandProvider(command="ocrtool --x {input}", egress=False, model="m")
    assert first.meta["destination"] != second.meta["destination"]
    assert ledger.provider_fingerprint(first.meta, "p1") != ledger.provider_fingerprint(second.meta, "p1"), \
        "a different same-named program invalidates approvals and cached results"
    monkeypatch.setenv("PATH", str(tmp_path / "nowhere"))
    seen.clear()
    missing = CommandProvider(command="ocrtool {input}", egress=False, model="m")
    result = missing.transcribe(dict(mime="image/png"), b"png", None)
    assert result["error"]["code"] == "E_PROVIDER_CONFIG" and not seen, "an unresolved bare name is never started"


@pytest.mark.req("REQ-SEC-01")
@pytest.mark.cov("S0", "FM9")
def test_T_SEC_63_command_template_containing_a_credential_value_is_refused_without_echo():
    env = {"OCR_TOKEN": "s3cr3t-v", "PGPASSWORD": "hunter2pw", "KEYBOARD": "layout-us", "MDFLOW_TIMEOUT_S": "5"}
    config = dict(model="m", env=env, command_egress=True, trust_command=True)
    for template in ("tool --t s3cr3t-v {input}", "tool --t=prefix-s3cr3t-v {input}", "ocr --pw hunter2pw {input}"):
        with pytest.raises(providers.ProviderConfigError) as caught:
            providers.build_provider("command", command=template, **config)
        assert caught.value.code == "E_PROVIDER_CONFIG"
        assert "s3cr3t" not in str(caught.value) and "hunter2pw" not in str(caught.value)
        assert "--command-env" in str(caught.value)
    accepted = providers.build_provider("command", command="tool --t {input}", command_env=["OCR_TOKEN"], **config)
    assert "s3cr3t" not in accepted.meta["destination"]
    providers.build_provider("command", command="tool --layout layout-us {input}", **config)


@pytest.mark.req("REQ-SEC-02")
@pytest.mark.cov("S13", "FM9")
def test_T_SEC_64_redaction_matches_secret_name_parts_and_one_word_credential_names():
    secret = {"GITHUB_PAT": "v-pat", "DB_PASS": "v-pass", "NPM_AUTH": "v-auth", "GCP_CREDENTIAL": "v-cred",
              "SMTP_PASSWORD": "v-pw", "MDFLOW_API_KEY": "v-key", "AWS_SESSION_TOKEN": "v-tok", "APP_SECRET": "v-sec",
              # One-word names: a part ending in a strong secret word is a secret (round 10, Defect 1).
              "PGPASSWORD": "v-pg", "GHTOKEN": "v-gh", "OPENAIKEY": "v-oai", "MYAPIKEY": "v-api",
              "DBPASSWD": "v-passwd", "APPSECRET": "v-appsec", "GCPCREDENTIAL": "v-gcpcred"}
    plain = {"KEYBOARD": "us", "MONKEY_MODE": "on", "TOKENIZERS_PARALLELISM": "false", "PATH": "plain-path"}
    assert all(redact.is_secret_name(name) for name in secret)
    assert not any(redact.is_secret_name(name) for name in plain)
    message = " ".join([*secret.values(), *plain.values(), "house"])
    result = redact.redact(message, {**secret, **plain}, "")
    assert not any(value in result for value in secret.values())
    assert result.split()[len(secret):] == ["us", "on", "false", "plain-path", "house"]
