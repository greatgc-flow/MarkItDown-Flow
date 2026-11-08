"""Step 7 RED: per-invocation consent through the public batch CLI."""

import json

import pytest


def _remote(mock_http):
    return {"MDFLOW_API_KEY": "step7-secret-key", "MDFLOW_BASE_URL": mock_http.base_url}


def _args(root, tmp_path):
    return ("run", root, "-o", tmp_path / "out", "--cache", tmp_path / "cache",
            "--provider", "openai-compatible", "--model", "test-model", "--cost-hint", "0.001",
            "--progress", "jsonl")


def _codes(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "triage":
                continue
            if key == "code" and child is not None:
                yield child
            else:
                yield from _codes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _codes(child)


@pytest.mark.req("REQ-APR-03", "REQ-RPT-01")
@pytest.mark.cov("S9", "FM8")
@pytest.mark.fx("FX-02", "FX-64")
def test_T_APR_03_missing_consent_emits_bounded_summary_and_full_plan(tmp_path, gen, cli_probe, mock_http):
    source = tmp_path / "scan.pdf"
    # Many placements sharing one raster: full Plan exceeds the progress line cap.
    source.write_bytes(gen.make_pdf([{"image_seed": 3, "box": (30, 30)}] * 200))
    sensitive = [arg for _ in range(30) for arg in ("--sensitive", "*SCAN.PDF")]
    args = (*_args(source, tmp_path), "--approve-threshold", "0", *sensitive)
    proc = cli_probe.run(*args, env=_remote(mock_http), allowed_hosts=("127.0.0.1",))
    value = cli_probe.report(proc, 3)
    f, = value["files"]
    assert f["units"]["pending"] == f["units"]["total"] == 200
    assert f["requests"]["sent"] == 0 and f["consent"] is None
    assert "E_APPROVAL_REQUIRED" in set(_codes(f))
    text = (tmp_path / "out" / f["outputs"][0]).read_text(encoding="utf-8")
    assert text.count('reason="approval_required"') == 200
    events = cli_probe.events(proc)
    summary, = [e for e in events if e["ev"] == "approve_required"]
    assert set(summary) == {"v", "ev", "ts", "file", "plan_hash", "destination", "model",
                            "keys_unique", "requests_to_send", "max_requests", "est_max_cost",
                            "cost_known", "threshold_exceeded", "sensitive_hits"}
    assert "units" not in summary and len(summary["sensitive_hits"]) == 20
    assert summary["plan_hash"] == f["plan_hash"] and summary["file"] == source.name
    assert mock_http.requests == [] and not cli_probe.attempts.exists()

    before = cli_probe.snapshot(tmp_path / "out"), cli_probe.snapshot(tmp_path / "cache")
    plan_proc = cli_probe.run("plan", args[1], *args[4:], env=_remote(mock_http),
                              allowed_hosts=("127.0.0.1",))
    # Section 8.4 permits plan to announce missing consent; it must still print the full Plan.
    assert plan_proc.returncode in {0, 3}, (plan_proc.stdout, plan_proc.stderr)
    plan, = cli_probe.objects(plan_proc.stdout)
    assert len(plan_proc.stdout.encode("utf-8")) > 65536
    assert len(plan["approved"]["units"]) == 200
    assert plan["plan_hash"] == f["plan_hash"]
    for field in ("keys_unique", "max_requests", "est_max_cost", "cost_known", "threshold_exceeded"):
        assert summary[field] == plan["approved"][field]
    assert summary["requests_to_send"] == plan["status"]["requests_to_send"]
    assert summary["destination"] == plan["approved"]["provider"]["destination"]
    assert plan["approved"]["sensitive_hits"] == ["*SCAN.PDF"] * 30
    assert (cli_probe.snapshot(tmp_path / "out"), cli_probe.snapshot(tmp_path / "cache")) == before
    assert mock_http.requests == [] and list(cli_probe.temp.iterdir()) == []


@pytest.mark.req("REQ-APR-04", "REQ-APR-02", "REQ-PLN-02")
@pytest.mark.cov("S9", "FM8")
@pytest.mark.fx("FX-02")
def test_T_APR_04_batch_hash_flags_yes_file_cache_warming_and_stale_source(tmp_path, gen, cli_probe, mock_http):
    root = tmp_path / "inputs"
    root.mkdir()
    for i, name in enumerate(("a.png", "b.png", "c.png")):
        (root / name).write_bytes(gen.png_noise(seed=90 + i))
    args, env = _args(root, tmp_path), _remote(mock_http)
    pending = cli_probe.run(*args, env=env, allowed_hosts=("127.0.0.1",))
    original = cli_probe.report(pending, 3)
    hashes = {f["path"]: f["plan_hash"] for f in original["files"]}
    unused = "f" * 64
    yes_file = tmp_path / "accepted.txt"
    yes_file.write_text(f"# selected hashes\n\n  {hashes['b.png']}  \n{unused}\n# end\n", encoding="utf-8")
    selected = cli_probe.run(*args, "--yes", hashes["a.png"], "--yes-file", yes_file,
                             "--approved-by", "plugin:modal", env=env, allowed_hosts=("127.0.0.1",))
    value = cli_probe.report(selected, 3)
    by_path = {f["path"]: f for f in value["files"]}
    assert len(mock_http.requests) == 2
    for name in ("a.png", "b.png"):
        assert by_path[name]["units"]["transcribed"] == 1
        assert by_path[name]["consent"]["plan_hash"] == hashes[name]
        assert by_path[name]["consent"]["by"] == "plugin:modal"
    assert by_path["c.png"]["units"]["pending"] == 1 and by_path["c.png"]["consent"] is None
    assert "W_APPROVAL_UNUSED" in set(_codes(cli_probe.events(selected)))

    approved_args = [arg for name in hashes for arg in ("--yes", hashes[name])]
    replay = cli_probe.run(*args, *approved_args, env=env, allowed_hosts=("127.0.0.1",))
    warm = cli_probe.report(replay, 0)
    assert len(mock_http.requests) == 3
    assert {f["path"]: f["plan_hash"] for f in warm["files"]} == hashes
    assert "W_APPROVAL_UNUSED" not in set(_codes(cli_probe.events(replay)))
    assert all(f["units"]["cached"] == 1 for f in warm["files"] if f["path"] != "c.png")

    (root / "a.png").write_bytes(gen.png_noise(seed=999))
    changed = cli_probe.run(*args, *approved_args, env=env, allowed_hosts=("127.0.0.1",))
    updated = cli_probe.report(changed, 3)
    a = next(f for f in updated["files"] if f["path"] == "a.png")
    assert a["plan_hash"] != hashes["a.png"] and a["units"]["pending"] == 1
    assert a["consent"] is None and len(mock_http.requests) == 3
    assert {"W_APPROVAL_UNUSED", "E_APPROVAL_REQUIRED"} <= set(_codes(cli_probe.events(changed)))


@pytest.mark.req("REQ-APR-06")
@pytest.mark.cov("S9", "FM8")
@pytest.mark.fx("FX-03")
@pytest.mark.parametrize("previous_result", ["ok", "failed"])
def test_T_APR_06_recorded_consent_never_authorizes_a_new_invocation(tmp_path, gen, cli_probe, mock_http, previous_result):
    source = tmp_path / "scan.png"
    source.write_bytes(gen.png_noise(seed=33))
    args, env = _args(source, tmp_path), _remote(mock_http)
    if previous_result == "failed":
        mock_http.reply(("json", 400, {"error": {"message": "fixture failure"}}))
    first = cli_probe.run(*args, "--yes", env=env, allowed_hosts=("127.0.0.1",))
    value = cli_probe.report(first, 0 if previous_result == "ok" else 4)
    assert value["files"][0]["consent"] is not None and len(mock_http.requests) == 1
    ledger = list((tmp_path / "cache" / "units").rglob("*.json"))
    assert len(ledger) == 1
    evidence = json.loads(ledger[0].read_text(encoding="utf-8"))
    assert evidence["consent"] == value["files"][0]["consent"]
    before = ledger[0].read_bytes()

    config = cli_probe.home / ".mdflow" / "config.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"yes": True, "yes_hashes": [evidence["consent"]["plan_hash"]]}), encoding="utf-8")
    force = ("--force",) if previous_result == "ok" else ()
    second = cli_probe.run(*args, *force, env=env, allowed_hosts=("127.0.0.1",))
    denied = cli_probe.report(second, 3)
    f, = denied["files"]
    assert f["consent"] is None and f["units"]["pending"] == 1
    assert f["requests"]["sent"] == 0 and len(mock_http.requests) == 1
    assert "E_APPROVAL_REQUIRED" in set(_codes(f))
    assert ledger[0].read_bytes() == before, "audit entry survives; it grants no new authority"
