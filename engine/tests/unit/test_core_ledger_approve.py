"""Key/entry/store ownership remains in this worktree (R26/C3)."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import errno
import json
import os
from pathlib import Path
import threading
import time

import pytest


@pytest.mark.req("REQ-LKP-01")
@pytest.mark.cov("S7", "FM0")
@pytest.mark.fx("FX-02", "FX-66")
def test_T_LKP_01_key_is_three_fields_and_ok_entry_hits(core_api, core_data, tmp_path):
    u, p = core_data.unit(), core_data.provider()
    expected_entry = core_data.entry(u, p)
    key = core_api.ledger.make_key(u, p, "p1")
    assert key == expected_entry["key"]
    assert set(key) == {"raster_sha256", "provider_fingerprint", "dpi"}
    kid = core_data.digest(core_data.canonical(key))
    assert core_api.ledger.key_id(key) == core_api.hashing.key_id(key) == kid
    store = core_api.ledger.Ledger(tmp_path)
    assert store.write(expected_entry) == []
    path = tmp_path / "units" / kid[:2] / (kid + ".json")
    assert json.loads(path.read_text(encoding="utf-8")) == expected_entry
    found = store.lookup(key)
    assert found == dict(hit=True, entry=expected_entry, issues=[])
    for changed in (dict(name="command"), dict(model="other"), dict(destination="https://other.invalid/ocr"),
                    dict(egress=False), dict(command_env_names=["SECRET_NAME"])):
        assert core_api.ledger.make_key(u, dict(p, **changed), "p1") != key
    assert core_api.ledger.make_key(u, p, "p2") != key
    assert core_api.ledger.make_key(dict(u, dpi=300), p, "p1") != key
    assert core_api.ledger.make_key(dict(u, raster_sha256="b" * 64), p, "p1") != key


@pytest.mark.req("REQ-LKP-02")
@pytest.mark.cov("S7", "FM12")
@pytest.mark.fx("FX-66", "FX-55")
def test_T_LKP_02_failed_retry_and_atomic_concurrent_last_writer(core_api, core_data, tmp_path):
    store = core_api.ledger.Ledger(tmp_path)
    failed = core_data.entry(status="failed")
    assert store.write(failed) == [] and store.lookup(failed["key"])["hit"] is False
    ok = core_data.entry()
    assert store.write(ok) == [] and store.lookup(ok["key"])["hit"] is True
    barrier = threading.Barrier(2)
    def publish(text):
        local = core_api.ledger.Ledger(tmp_path)
        barrier.wait(timeout=5)
        return local.write(core_data.entry(text=text))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish, text) for text in ("writer A", "writer B")]
        assert [future.result(timeout=10) for future in futures] == [[], []]
    found = store.lookup(ok["key"])
    assert found["hit"] is True and found["entry"]["text"] in {"writer A", "writer B"}
    assert core_api.ledger.validate_entry(found["entry"], ok["key"], ok["key_id"]) is True
    assert len(list((tmp_path / "units").rglob("*.json"))) == 1


@pytest.mark.req("REQ-LKP-03")
@pytest.mark.cov("S7", "FM12")
@pytest.mark.fx("FX-66", "FX-65")
def test_T_LKP_03_force_preserves_old_until_atomic_replacement(core_api, core_data, tmp_path, monkeypatch):
    store = core_api.ledger.Ledger(tmp_path)
    old = core_data.entry(text="old")
    assert store.write(old) == []
    target = tmp_path / "units" / old["key_id"][:2] / (old["key_id"] + ".json")
    old_bytes = target.read_bytes()
    assert store.lookup(old["key"], force=True)["hit"] is False
    assert target.read_bytes() == old_bytes
    real_replace = os.replace
    observed = []
    def check_before_replace(source, destination):
        if Path(destination) == target:
            assert target.read_bytes() == old_bytes
            assert Path(source).parent == target.parent
            assert Path(source).name.startswith(target.name + ".tmp-")
            observed.append(True)
        return real_replace(source, destination)
    monkeypatch.setattr(os, "replace", check_before_replace)
    assert store.write(core_data.entry(text="new")) == []
    assert observed and store.lookup(old["key"])["entry"]["text"] == "new"


@pytest.mark.req("REQ-LKP-04")
@pytest.mark.cov("S7", "FM1")
@pytest.mark.fx("FX-66")
@pytest.mark.parametrize("mutation", ("non_object", "version", "id", "stem", "key", "ok_null", "ok_error", "inflight", "failed_text", "failed_error", "invalid_json", "informational_provider"))
def test_T_LKP_04_entry_validation_and_corrupt_store_miss(core_api, core_data, tmp_path, mutation):
    good = core_data.entry()
    candidate, stem = deepcopy(good), good["key_id"]
    if mutation == "non_object":
        candidate = []
    elif mutation == "version":
        candidate["v"] = 2
    elif mutation == "id":
        candidate["key_id"] = "b" * 64
    elif mutation == "stem":
        stem = "b" * 64
    elif mutation == "key":
        candidate["key"]["provider_fingerprint"] = "b" * 64
    elif mutation == "ok_null":
        candidate["text"] = None
    elif mutation == "ok_error":
        candidate["error"] = {"code": "E_PROVIDER_HTTP"}
    elif mutation == "inflight":
        candidate["status"] = "inflight"
    elif mutation == "failed_text":
        candidate.update(status="failed", text="not null", error={"code": "E_PROVIDER_HTTP"})
    elif mutation == "failed_error":
        candidate.update(status="failed", text=None, error=None)
    elif mutation == "informational_provider":
        candidate["provider"]["model"] = "informational only"
    expected_valid = mutation == "informational_provider"
    if mutation != "invalid_json":
        assert core_api.ledger.validate_entry(candidate, good["key"], stem) is expected_valid
    store = core_api.ledger.Ledger(tmp_path)
    assert store.write(good) == []
    target = tmp_path / "units" / good["key_id"][:2] / (good["key_id"] + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    if mutation == "stem":
        # Entry key_id must equal the name of the requested entry.
        candidate["key_id"] = stem
    target.write_text("{broken" if mutation == "invalid_json" else json.dumps(candidate), encoding="utf-8")
    found = store.lookup(good["key"])
    assert found["hit"] is expected_valid
    if not expected_valid:
        assert "W_CACHE_CORRUPT" in {i["code"] for i in found["issues"]}
        assert store.write(good) == []
        assert store.lookup(good["key"])["hit"] is True


@pytest.mark.req("REQ-LKP-05")
@pytest.mark.cov("S7", "FM5")
@pytest.mark.fx("FX-02")
def test_T_LKP_05_write_failure_returns_issue_and_keeps_run_result(core_api, core_data, tmp_path, monkeypatch):
    store = core_api.ledger.Ledger(tmp_path)
    result = core_data.entry(text="still available to output")
    before = deepcopy(result)
    def denied(*args, **kwargs):
        raise PermissionError("fixture cache publication denied")
    monkeypatch.setattr(os, "replace", denied)
    issues = store.write(result)
    assert {i["code"] for i in issues} == {"E_CACHE_IO"}
    assert result == before and result["text"] == "still available to output"
    assert core_api.assemble.exit_code([i["code"] for i in issues]) == 2


@pytest.mark.req("REQ-LKP-01")
@pytest.mark.cov("S7", "FM12")
@pytest.mark.fx("FX-63")
def test_T_LKP_06_command_script_body_hit_env_name_set_miss(core_api, core_data, tmp_path):
    script = tmp_path / "ocr.py"
    script.write_text("print('first')", encoding="utf-8")
    p = core_data.provider(name="command", destination='command:["python","ocr.py","{input}"]', command_env_names=["B", "A", "A"])
    u = core_data.unit()
    first = core_api.ledger.make_key(u, p, "p1")
    script.write_text("print('changed script body')", encoding="utf-8")
    assert core_api.ledger.make_key(u, p, "p1") == first
    assert core_api.ledger.make_key(u, dict(p, command_env_names=["A", "B"]), "p1") == first
    for changes in (dict(command_env_names=["A"]), dict(model="new-label"), dict(destination='command:["python","other.py","{input}"]')):
        assert core_api.ledger.make_key(u, dict(p, **changes), "p1") != first


@pytest.mark.req("REQ-LKP-02", "REQ-LKP-03")
@pytest.mark.cov("S7", "FM12")
@pytest.mark.fx("FX-66", "FX-55")
@pytest.mark.parametrize("winerror", (5, 32))
def test_T_LKP_07_transient_windows_replace_retries_preserve_last_writer(core_api, core_data, tmp_path,
                                                                      monkeypatch, winerror):
    store = core_api.ledger.Ledger(tmp_path)
    old, rival, new = [core_data.entry(text=text) for text in ("old", "competing writer", "last writer")]
    assert store.write(old) == []
    target = store._path(old["key"])
    rival_temp = target.with_suffix(".rival")
    rival_temp.write_bytes(core_data.canonical(rival) + b"\n")
    real_replace, real_fsync = os.replace, os.fsync
    sources, waits, syncs = [], [], []

    def transient(source, destination):
        assert Path(destination) == target
        assert json.loads(Path(source).read_bytes()) == new
        sources.append(source)
        if len(sources) <= 2:
            if len(sources) == 2:
                real_replace(rival_temp, target)
            assert store.lookup(old["key"])["entry"] in (old, rival)
            error = PermissionError(errno.EACCES, "injected Windows sharing violation")
            error.winerror = winerror
            raise error
        return real_replace(source, destination)

    monkeypatch.setattr(os, "replace", transient)
    monkeypatch.setattr(os, "fsync", lambda fd: (syncs.append(fd), real_fsync(fd))[1])
    monkeypatch.setattr(time, "sleep", waits.append)
    assert store.write(new) == []
    assert waits == [0.01, 0.02]
    assert len(sources) == 3 and len(set(sources)) == 1
    assert len(syncs) == 1, "retry only replace, retaining the fsynced temporary file"
    assert store.lookup(new["key"]) == dict(hit=True, entry=new, issues=[])
    assert not list(tmp_path.rglob("*.tmp-*"))


@pytest.mark.req("REQ-LKP-02", "REQ-LKP-03", "REQ-LKP-05")
@pytest.mark.cov("S7", "FM5")
@pytest.mark.fx("FX-66", "FX-65")
@pytest.mark.parametrize("error_type,winerror,retry", (
    (PermissionError, 5, True), (PermissionError, 32, True),
    (PermissionError, 13, False), (PermissionError, None, False), (OSError, 32, False),
))
def test_T_LKP_08_replace_retry_is_bounded_and_specific(core_api, core_data, tmp_path, monkeypatch,
                                                     error_type, winerror, retry):
    store = core_api.ledger.Ledger(tmp_path)
    old, new = core_data.entry(text="old"), core_data.entry(text="new")
    assert store.write(old) == []
    before = deepcopy(new)
    target = store._path(old["key"])
    old_bytes = target.read_bytes()
    attempts, waits = [], []

    def denied(source, destination):
        attempts.append(source)
        assert Path(destination) == target and target.read_bytes() == old_bytes
        error = error_type(errno.EACCES if error_type is PermissionError else errno.EIO, "injected failure")
        if winerror is not None:
            error.winerror = winerror
        raise error

    monkeypatch.setattr(os, "replace", denied)
    monkeypatch.setattr(time, "sleep", waits.append)
    assert store.write(new) == [dict(code="E_CACHE_IO", message="Ledger entry could not be published.")]
    assert waits == ([0.01, 0.02, 0.04, 0.08, 0.16] if retry else [])
    assert len(attempts) == (6 if retry else 1) and len(set(attempts)) == 1
    assert target.read_bytes() == old_bytes and new == before
    assert not list(tmp_path.rglob("*.tmp-*"))


@pytest.mark.req("REQ-APR-01")
@pytest.mark.cov("S9", "FM0")
@pytest.mark.fx("FX-01", "FX-02")
def test_T_APR_01_none_local_and_all_cached_need_no_consent(core_api, core_build_plan, core_data):
    local = core_build_plan(p=core_data.provider(egress=False))
    warm = core_build_plan(hits=("p2", "p4"))
    for plan in (local, warm):
        assert core_api.approve.approve(plan, {}, core_data.NOW) is None


@pytest.mark.req("REQ-APR-02")
@pytest.mark.cov("S9", "FM3")
@pytest.mark.fx("FX-02", "FX-03")
def test_T_APR_02_bare_yes_guards_and_per_file_hash_lists(core_api, core_build_plan, core_data):
    base = core_build_plan()
    flags = dict(yes=True, yes_hashes=[], approved_by=None)
    assert core_api.approve.approve(base, flags, core_data.NOW)["plan_hash"] == base["plan_hash"]
    for field, value in (("threshold_exceeded", True), ("sensitive_hits", ["*/HR/*"]), ("cost_known", False)):
        guarded = deepcopy(base)
        guarded["approved"][field] = value
        guarded["plan_hash"] = core_data.digest(core_data.canonical(guarded["approved"]))
        with pytest.raises(core_api.approve.ApprovalRequired):
            core_api.approve.approve(guarded, flags, core_data.NOW)
        # Explicit hash authorizes each of the same refusals.
        consent = core_api.approve.approve(guarded, dict(yes=False, yes_hashes=[guarded["plan_hash"]]), core_data.NOW)
        assert consent["plan_hash"] == guarded["plan_hash"]
    plans = []
    for logical in ("a.pdf", "b.pdf", "c.pdf"):
        opts = core_data.options()
        opts["file"]["path"] = logical
        plans.append(core_build_plan(opts=opts))
    text = f"# chosen files\n\n{plans[0]['plan_hash']}\n  {plans[1]['plan_hash']}  \n# end\n"
    hashes = core_api.approve.parse_yes_lines(text)
    assert hashes == [p["plan_hash"] for p in plans[:2]]
    for plan in plans[:2]:
        assert core_api.approve.approve(plan, dict(yes_hashes=hashes), core_data.NOW)["plan_hash"] == plan["plan_hash"]
    with pytest.raises(core_api.approve.ApprovalRequired):
        core_api.approve.approve(plans[2], dict(yes_hashes=hashes), core_data.NOW)


@pytest.mark.req("REQ-APR-05")
@pytest.mark.cov("S9", "FM0")
@pytest.mark.fx("FX-03", "FX-67")
def test_T_APR_05_exact_consent_uses_injected_now(core_api, core_build_plan, core_data, fake_clock):
    plan = core_build_plan()
    before = deepcopy(plan)
    now = fake_clock.now().isoformat(timespec="seconds")
    for by in (None, "plugin:modal"):
        consent = core_api.approve.approve(plan, dict(yes_hashes=[plan["plan_hash"]], approved_by=by), now)
        assert consent == dict(plan_hash=plan["plan_hash"], approved_at=now, by=by or "cli:--yes")
    assert plan == before


@pytest.mark.req("REQ-APR-07")
@pytest.mark.cov("S9", "FM8")
@pytest.mark.fx("FX-03")
def test_T_APR_07_pure_approval_and_changed_raster_denied(core_api, core_build_plan, core_data, monkeypatch):
    plan = core_build_plan()
    flags = dict(yes_hashes=[plan["plan_hash"]])
    def forbidden(*args, **kwargs):
        raise AssertionError("Approve performed IO, clock or random access")
    with monkeypatch.context() as patch:
        for name in ("builtins.open", "io.open", "time.time", "time.monotonic", "os.urandom"):
            patch.setattr(name, forbidden)
        assert core_api.approve.approve(plan, flags, core_data.NOW)["plan_hash"] == plan["plan_hash"]
    original = b"approved raster bytes"
    u = core_data.unit(raster=core_data.digest(original))
    assert core_api.approve.verify_raster(u, original) is None
    sent = []
    with pytest.raises(core_api.approve.ApprovalDenied):
        core_api.approve.verify_raster(u, b"overwritten raster bytes")
        sent.append(b"must never send")
    assert sent == []
    assert core_api.assemble.exit_code(["E_APPROVAL_DENIED"]) == 3


@pytest.mark.req("REQ-APR-04", "REQ-PLN-02")
@pytest.mark.cov("S9", "FM12")
@pytest.mark.fx("FX-02")
def test_T_APR_08_other_file_warming_cache_preserves_authorization(core_api, core_data, core_build_plan):
    cold = core_build_plan()
    # Another file fills one of the same Keys before this file is processed.
    warm = core_build_plan(hits=("p2",))
    assert warm["plan_hash"] == cold["plan_hash"] and warm["status"]["requests_to_send"] == 1
    consent = core_api.approve.approve(warm, dict(yes_hashes=[cold["plan_hash"]]), core_data.NOW)
    assert consent["plan_hash"] == cold["plan_hash"]
