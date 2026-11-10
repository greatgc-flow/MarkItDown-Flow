"""Security review of 2.0.0 (engine, whole pipeline): C4 sensitive source paths, (b) deferred cancel."""

import io
import json
import os
import signal
import zipfile

import pytest


@pytest.mark.req("REQ-PLN-06")
@pytest.mark.cov("S8", "FM9")
@pytest.mark.fx("FX-09", "FX-61")
def test_T_PLN_60_sensitive_globs_match_the_absolute_source_path_of_direct_files_and_members(flow, gen):
    direct = flow.put("HR/scan.png", gen.png_noise(seed=3))
    packed = io.BytesIO()
    with zipfile.ZipFile(packed, "w") as archive:
        archive.writestr("inner.png", gen.png_noise(seed=4))
    container = flow.put("HR/pack.zip", packed.getvalue())
    patterns = ["*/hr/*", "*/pack.zip/inner.png", "*unmatched*"]
    plans = []
    flow.run([direct, container], provider=gen.ScriptedProvider(), sensitive=patterns,
             _plan_only=True, _on_plan=plans.append)
    hits = {plan["approved"]["file"]["path"]: plan["approved"]["sensitive_hits"] for plan in plans}
    assert hits["scan.png"] == ["*/hr/*"], "a directly passed file is matched by its folder"
    assert hits["pack.zip/inner.png"] == ["*/hr/*", "*/pack.zip/inner.png"], "members match as container + member"
    assert str(flow.inputs) not in json.dumps(plans) and flow.inputs.as_posix() not in json.dumps(plans), \
        "only the matching patterns are stored, never the absolute path"
    provider = gen.ScriptedProvider()
    value = flow.run([direct], provider=provider, sensitive=patterns, yes=True)
    assert value["exit"] == 3 and not provider.calls, "bare --yes never approves a sensitive file"
    assert "E_APPROVAL_REQUIRED" in [issue["code"] for issue in value["files"][0]["issues"]]


@pytest.mark.req("REQ-TRX-02", "REQ-TRX-06")
@pytest.mark.cov("S10", "FM7")
@pytest.mark.fx("FX-09", "FX-61", "FX-65")
def test_T_TRX_60_cancel_after_the_reply_arrives_keeps_the_billed_result_in_the_ledger(flow, gen, monkeypatch):
    from mdflow import assemble

    flow.put("a.png", gen.png_noise(seed=5))
    flow.put("b.png", gen.png_noise(seed=6))
    number = signal.SIGBREAK if os.name == "nt" else signal.SIGTERM
    original, fired = assemble.postprocess_text, []

    def cancel_after_reply(text):
        handler = signal.getsignal(number)
        if not fired and callable(handler):
            fired.append(number)
            handler(number, None)  # the cooperative cancel arrives after the provider returned
        return original(text)

    monkeypatch.setattr(assemble, "postprocess_text", cancel_after_reply)
    provider = gen.ScriptedProvider()
    value = flow.run(provider=provider, yes=True)
    assert fired and value["exit"] == 130
    assert len(provider.calls) == 1, "the pending cancel still stops the run before the next request"
    entries = [json.loads(p.read_text(encoding="utf-8")) for p in (flow.cache / "units").rglob("*.json")]
    assert [entry["status"] for entry in entries] == ["ok"], "the reply that arrived is stored, not resent next run"
