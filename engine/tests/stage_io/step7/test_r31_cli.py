"""R31: ``mdflow version`` and ``mdflow selftest`` report exiftool status; absence is a normal, exit-0 state."""

import json

import pytest


@pytest.fixture
def absent_env(tmp_path):
    """Environment overrides producing 'no exiftool' for a child process (no skip, no dependence on the host)."""
    empty = tmp_path / "no-tools"
    empty.mkdir()
    return {"PATH": str(empty), "EXIFTOOL_PATH": ""}


@pytest.mark.req("REQ-GEN-02", "REQ-CNV-06")
@pytest.mark.cov("S0", "FM10")
def test_T_CLI_81_version_reports_exiftool_status_for_present_old_and_absent(tmp_path, cli_probe, fake_exiftool, absent_env):
    present = json.loads(cli_probe.run("version", env={"EXIFTOOL_PATH": str(fake_exiftool(tmp_path / "ok", "13.59"))},
                                       expected=0).stdout)
    assert (present["exiftool"], present["exiftool_status"], present["exiftool_source"]) == ("13.59", "ok", "EXIFTOOL_PATH")
    required = {"mdflow", "markitdown-gc", "pypdfium2", "pillow", "python", "platform", "protocol", "triage_schema"}
    assert required <= set(present) and set(present) - required == {"exiftool", "exiftool_status", "exiftool_source"}
    old = json.loads(cli_probe.run("version", env={"EXIFTOOL_PATH": str(fake_exiftool(tmp_path / "old", "12.23"))},
                                   expected=0).stdout)
    assert (old["exiftool"], old["exiftool_status"], old["exiftool_source"]) == ("unavailable", "too_old", "EXIFTOOL_PATH")
    proc = cli_probe.run("version", env=absent_env, expected=0)
    absent = json.loads(proc.stdout)
    assert (absent["exiftool"], absent["exiftool_status"], absent["exiftool_source"]) == ("unavailable", "not_found", None)
    assert proc.stderr == "" and all(absent[k] for k in required - {"protocol", "triage_schema"})
    assert not cli_probe.attempts.exists()


@pytest.mark.req("REQ-CNV-06", "REQ-CLS-05")
@pytest.mark.cov("S0", "FM10")
def test_T_CLI_82_selftest_reports_exiftool_and_passes_without_it(tmp_path, cli_probe, fake_exiftool, absent_env):
    with_tool = cli_probe.run("selftest", env={"EXIFTOOL_PATH": str(fake_exiftool(tmp_path / "ok", "13.59"))}, expected=0)
    value = json.loads(with_tool.stdout)
    assert value["ok"] is True
    assert value["exiftool"] == {"status": "ok", "version": "13.59", "metadata": True}
    without = cli_probe.run("selftest", env=absent_env, expected=0)
    value = json.loads(without.stdout)
    assert value["ok"] is True
    assert value["exiftool"] == {"status": "not_found", "version": None, "metadata": False}
    assert without.stderr == "" and not cli_probe.attempts.exists()
    broken = cli_probe.run("selftest", env={"EXIFTOOL_PATH": str(fake_exiftool(tmp_path / "bad", "13.59", fail_json=True))},
                           expected=0)
    value = json.loads(broken.stdout)
    assert value["ok"] is True and value["exiftool"] == {"status": "ok", "version": "13.59", "metadata": False}, \
        "a tool that cannot read the bundled PNG is reported, not fatal"
