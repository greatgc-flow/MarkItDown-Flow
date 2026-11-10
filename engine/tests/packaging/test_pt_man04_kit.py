"""PT-39: ``tools/man04_kit.py`` automates only the mechanical part of MAN-04 and never writes a human verdict.

Offline: a fake asset folder and a stub engine step stand in for ``gh release download`` and the venv install.
A kit-generated record is validated by the real gate (``trace.py attest MAN-04``), never believed; the human
fields (including the Obsidian version actually run) stay placeholders until the owner fills them.
"""
from argparse import Namespace
import hashlib
import json
import platform
import re
import subprocess

import pytest

from _support import ASSETS, REPO, SUBJECTS, load_py, load_yaml

kit = load_py(REPO / "tools/man04_kit.py", "mdflow_pt_man04_kit")
MANIFEST = json.loads((REPO / "manifest.json").read_text(encoding="utf-8"))
ENGINE = {"python": "3.14.0", "engine": "2.0.0", "core": "0.3.7", "enginePython": "venv/python", "logs": "logs"}
PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9 /_.-]*>|\bTODO\b")
CELLS = [(o, c) for o in ("windows", "macos", "linux") for c in ("minimum", "current")]
COMMIT = "c" * 40


def fake_assets(folder):
    folder.mkdir()
    for name in ASSETS:
        data = json.dumps(MANIFEST).encode() if name == "manifest.json" else f"bytes of {name}".encode()
        (folder / name).write_bytes(data)
    sums = "".join(f"{hashlib.sha256((folder / n).read_bytes()).hexdigest()}  {n}\n" for n in ASSETS)
    (folder / "SHA256SUMS").write_text(sums, encoding="utf-8")
    return folder


def template_record(tmp_path):
    """Template as JSON, read by the stdlib test reader so the test needs no PyYAML."""
    record = tmp_path / "release_rehearsal.yml"
    record.write_text(json.dumps(load_yaml(kit.TEMPLATE.read_text(encoding="utf-8"))),
                      encoding="utf-8")
    return record


def write_record(folder, data):
    folder.mkdir(exist_ok=True)
    (folder / "release_rehearsal.yml").write_text(json.dumps(data), encoding="utf-8")
    return folder / "release_rehearsal.yml"


def args(tmp_path, assets, channel="minimum"):
    return Namespace(channel=channel, repo=None, assets=assets, work=tmp_path / "work",
                     record=tmp_path / "release_rehearsal.yml", python="python")


def owner_fills(node, key=""):
    """What the owner does by hand: replace every placeholder and mark observed checks PASS."""
    if isinstance(node, dict):
        return {k: owner_fills(v, k) for k, v in node.items()}
    if isinstance(node, list):
        return [owner_fills(v, key) for v in node]
    if not isinstance(node, str) or not PLACEHOLDER.search(node):
        return node
    owner = {"date": "2026-11-12", "commit": COMMIT, "obsidian_version": MANIFEST["minAppVersion"]}
    return "PASS" if node == "TODO" else owner.get(key, "owner value")


@pytest.mark.req("REQ-PKG-22")
@pytest.mark.cov("S0", "FM0")
def test_PT_39_man04_kit_fills_only_mechanical_fields_detects_tampering_and_output_attests(tmp_path, monkeypatch):
    assets = fake_assets(tmp_path / "assets")
    template_record(tmp_path)
    # 1. A run installs the plugin, fills mechanical fields, and leaves every human field TODO (never PASS).
    assert kit.run(args(tmp_path, assets), provision=lambda *_: ENGINE) == 0
    vault = tmp_path / "work/vault/.obsidian"
    plugin = vault / "plugins" / MANIFEST["id"]
    assert [(plugin / n).read_bytes() for n in ("main.js", "manifest.json", "styles.css")] == \
        [(assets / n).read_bytes() for n in ("main.js", "manifest.json", "styles.css")]
    assert json.loads((vault / "community-plugins.json").read_text()) == [MANIFEST["id"]]
    record = json.loads((tmp_path / "release_rehearsal.yml").read_text(encoding="utf-8"))
    os_name = kit.OS_NAMES[platform.system()]
    mine = next(r for r in record["runs"] if (r["os"], r["obsidian_channel"]) == (os_name, "minimum"))
    assert mine["downloads"] == [{"asset": n, "sha256": hashlib.sha256((assets / n).read_bytes()).hexdigest()}
                                 for n in SUBJECTS]
    assert mine["python"] == "3.14.0"
    assert all(PLACEHOLDER.search(r["obsidian_version"]) for r in record["runs"]), "the app version run is the owner's"
    assert "PASS" not in json.dumps(record) and record["verdict"] == "TODO"
    assert all(set(r["checks"].values()) == {"TODO"} for r in record["runs"])
    assert all(c["result"] == "TODO" for c in record["checks"])
    assert kit.validate(tmp_path / "release_rehearsal.yml", COMMIT), "an unfilled kit record must not validate"
    # Re-running keeps owner edits (a PASS the owner typed is not reset) and does not duplicate the plugin listing.
    mine["checks"]["fresh_install"] = "PASS"
    (tmp_path / "release_rehearsal.yml").write_text(json.dumps(record), encoding="utf-8")
    assert kit.run(args(tmp_path, assets), provision=lambda *_: ENGINE) == 0
    again = json.loads((tmp_path / "release_rehearsal.yml").read_text(encoding="utf-8"))
    assert next(r for r in again["runs"] if (r["os"], r["obsidian_channel"]) == (os_name, "minimum"))["checks"]["fresh_install"] == "PASS"
    assert json.loads((vault / "community-plugins.json").read_text()) == [MANIFEST["id"]]

    # 2. A tampered or unlisted asset is detected before anything is installed or recorded.
    bad = fake_assets(tmp_path / "bad")
    (bad / "main.js").write_bytes(b"tampered")
    with pytest.raises(kit.KitError, match="mismatch.*main.js"):
        kit.verify_assets(bad)
    (bad / "main.js").write_bytes(b"bytes of main.js")
    (bad / "SHA256SUMS").write_text("".join(l for l in (bad / "SHA256SUMS").read_text().splitlines(True)
                                            if "LICENSE" not in l), encoding="utf-8")
    with pytest.raises(kit.KitError, match="LICENSE"):
        kit.verify_assets(bad)
    (bad / "BOOTSTRAP.md").unlink()
    with pytest.raises(kit.KitError, match="missing"):
        kit.verify_assets(bad)
    refused = tmp_path / "refused"
    refused.mkdir()
    flags = ["run", "--channel", "current", "--assets", str(bad), "--work", str(refused / "w"),
             "--record", str(refused / "r.yml")]
    assert kit.main(flags) == 2
    assert not (refused / "w/vault").exists() and not (refused / "r.yml").exists()

    # 3. Once the owner fills the human fields, the kit-generated record passes trace.py attest MAN-04.
    record = json.loads(template_record(tmp_path).read_text(encoding="utf-8"))
    for os_name, channel in CELLS:
        kit.update_record(record, os_name=os_name, channel=channel, hashes=kit.verify_assets(assets), engine=ENGINE)
    filled = owner_fills(record)
    done = write_record(tmp_path / "done", filled)
    assert kit.validate(done, COMMIT) == []
    assert kit.main(["validate", str(done), "--commit", COMMIT]) == 0
    assert kit.validate(done, "d" * 40), "the record must bind the candidate commit"
    unobserved = json.loads(json.dumps(filled))
    unobserved["runs"][2]["checks"]["cancel_restart"] = "TODO"
    assert kit.validate(write_record(tmp_path / "run_todo", unobserved), COMMIT), "one unobserved check must fail"
    top = json.loads(json.dumps(filled))
    top["checks"][1]["result"] = "TODO"
    assert kit.validate(write_record(tmp_path / "top_todo", top), COMMIT), "a top-level TODO check must fail"

    # 4. The venv steps run isolated in UTF-8 mode with the right per-OS interpreter path.
    calls = []
    monkeypatch.setattr(kit.subprocess, "run", lambda cmd, **_: calls.append(cmd) or
                        subprocess.CompletedProcess(cmd, 0, "3.14.0 2.0.0 0.3.7", ""))
    for system, exe in (("Windows", "Scripts/python.exe"), ("Linux", "bin/python")):
        monkeypatch.setattr(kit.platform, "system", lambda: system)
        calls.clear()
        engine = kit.provision_engine(assets, tmp_path / system, "base")
        assert engine["enginePython"] == str(tmp_path / system / "venv-2.0.0" / exe)
        assert calls[0][:2] == ["base", "-I"]
        assert all(c[1:4] == ["-I", "-X", "utf8"] for c in calls[1:]) and len(calls) == 6
