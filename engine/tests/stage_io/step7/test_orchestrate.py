"""Step 7 RED: real discovery-to-publication behavior, with a deterministic provider."""

from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path
import zipfile

import pytest

from mdflow import contracts, render, triage


@pytest.mark.req("REQ-GEN-06")
@pytest.mark.cov("S0", "FM12")
@pytest.mark.fx("FX-02", "FX-03", "FX-16", "FX-61")
@pytest.mark.parametrize("source", ["scan", "mixed", "office", "retry"])
def test_T_GEN_06_successful_warm_rerun_changes_no_output_or_cache(flow, gen, step7_data, mock_provider, monkeypatch, source):
    if source == "retry":
        _retry_failed_and_pending(flow, gen, mock_provider, monkeypatch)
        return
    data = {"scan": gen.pdf_scan, "mixed": gen.pdf_mixed,
            "office": step7_data.docx_bytes}[source]()
    path = flow.put("doc.docx" if source == "office" else "doc.pdf", data)

    # Office media publication and in-situ placement participate in the byte snapshot.
    if source == "office":
        def office_body(spy, index, raw, ext, extract_media, media_base_dir):
            links = []
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for name in archive.namelist():
                    if name.startswith("word/media/"):
                        media = archive.read(name)
                        target = Path(extract_media) / (gen.h12(media) + Path(name).suffix)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(media)
                        links.append(f"![image](media/{target.name})")
            return "\n".join(links)
        flow.core.behavior = office_body

    first_provider = mock_provider(egress=False)
    first = flow.run([path], provider=first_provider)
    flow.assert_report(first, 0)
    assert first_provider.calls, "cold run must actually transcribe before the warm oracle matters"
    before_out, before_cache = flow.snapshot(flow.out), flow.snapshot(flow.cache)
    assert before_out and before_cache
    warm_provider = mock_provider(egress=False)
    second = flow.run([path], provider=warm_provider)
    flow.assert_report(second, 0)
    assert warm_provider.calls == []
    assert flow.snapshot(flow.out) == before_out
    assert flow.snapshot(flow.cache) == before_cache
    assert second["files"][0]["units"]["cached"] == first["files"][0]["units"]["transcribed"]
    assert second["files"][0]["plan_hash"] == first["files"][0]["plan_hash"]


@pytest.mark.req("REQ-GEN-07")
@pytest.mark.cov("S13", "FM0")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_GEN_07_every_discovered_source_and_skip_is_reported_once(flow, gen):
    files = gen.sample_files(flow.inputs)
    flow.put("mismatch.txt", gen.png_noise())
    flow.put("song.mp3", b"ID3" + b"x" * 30)
    flow.put("unknown.blob", b"unknown bytes")
    flow.put(".hidden.txt", b"hidden")
    flow.put("nested/.secret.txt", b"hidden")
    result = flow.run()
    flow.assert_report(result, 2)
    expected = set(files) | {"mismatch.txt", "song.mp3", "unknown.blob",
                            "pack.zip/docs/report.pdf", "pack.zip/notes.txt", "pack.zip/files/memo.docx"}
    assert Counter(f["path"] for f in result["files"]) == Counter(dict.fromkeys(expected, 1))
    assert Counter((s["path"], s["code"]) for s in result["skipped"]) == Counter({
        (".hidden.txt", "W_SKIPPED_HIDDEN"): 1, ("nested/.secret.txt", "W_SKIPPED_HIDDEN"): 1})
    by_path = {f["path"]: f for f in result["files"]}
    for name, route, label in (("old.doc", "LEGACY", "L"), ("locked.pdf", "PROTECTED", "P"),
                                ("pack.zip", "CONTAINER", "C")):
        assert (by_path[name]["route"], by_path[name]["label"]) == (route, label)
    assert all(by_path[p]["triage"] is None for p in ("old.doc", "locked.pdf", "empty.pdf", "pack.zip"))
    assert by_path["empty.pdf"]["action"] == "report_only"
    assert "E_CORRUPT" in {i["code"] for i in by_path["empty.pdf"]["issues"]}


@pytest.mark.req("REQ-GEN-08")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-01", "FX-02", "FX-03", "FX-64")
def test_T_GEN_08_default_none_has_pending_markers_and_zero_egress(flow, gen, socket_guard, monkeypatch):
    from mdflow.providers.none import NoneProvider

    def forbidden(*args, **kwargs):
        raise AssertionError("provider none must never be invoked")
    monkeypatch.setattr(NoneProvider, "transcribe", forbidden)
    for name, data in (("text.pdf", gen.pdf_text(1)), ("scan.pdf", gen.pdf_scan(1)),
                       ("mixed.pdf", gen.pdf_mixed())):
        flow.put(name, data)
    result = flow.run()
    flow.assert_report(result, 0)
    assert result["options"]["provider"] == "none"
    assert socket_guard.attempts == []
    assert sum(f["units"]["pending"] for f in result["files"]) > 0
    for f in result["files"]:
        assert f["requests"] == dict(to_send=f["requests"]["to_send"], sent=0, ok=0, failed=0)
        assert f["consent"] is None
        if f["units"]["pending"]:
            text = (flow.out / f["outputs"][0]).read_text(encoding="utf-8")
            assert text.count('reason="no_provider"') == f["units"]["pending"]


@pytest.mark.req("REQ-GEN-10")
@pytest.mark.cov("S13", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_GEN_10_closed_mdflow_codes_exclude_verbatim_triage(flow, gen, monkeypatch, repo_root):
    # A novel candidate reason belongs to Core; the engine reports its own closed warning code.
    source = flow.put("image.png", gen.png_noise())
    real_triage = triage.run_triage
    raw_reports = []

    def novel_reason(path, sniff):
        outcome = deepcopy(real_triage(path, sniff))
        outcome["report"]["candidates"][0]["reasons"].append("future_core_reason")
        outcome["report"]["issues"].append({"code": "image_probe_failed", "detail": "Core-owned diagnostic"})
        raw_reports.append(deepcopy(outcome["report"]))
        return outcome
    monkeypatch.setattr(triage, "run_triage", novel_reason)
    result = flow.run([source])
    flow.assert_report(result, 0)

    spec = (repo_root / "docs/renewal/10_SPEC.md").read_text(encoding="utf-8")
    import re
    section = spec.split("### 7.5 ", 1)[1].split("## 8.", 1)[0]
    allowed = set()
    for line in section.splitlines():
        if line.startswith("| `"):
            allowed.update(re.findall(r"[EW]_[A-Z_]+", line.split("|")[1]))
    assert allowed == set(contracts.CODES)

    def codes(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "triage":
                    continue
                if key == "code" and child is not None:
                    yield child
                else:
                    yield from codes(child)
        elif isinstance(value, list):
            for child in value:
                yield from codes(child)

    seen = list(codes(result))
    assert {"W_TRIAGE_UNKNOWN_VALUE", "W_IMAGE_PROBE"} <= set(seen) <= allowed
    assert "image_probe_failed" not in seen
    assert result["files"][0]["triage"] == raw_reports[0]
    assert "future_core_reason" in json.dumps(result["files"][0]["triage"])
    assert result["files"][0]["triage"]["issues"][-1]["code"] == "image_probe_failed"


@pytest.mark.req("REQ-RPT-02")
@pytest.mark.cov("S13", "FM0")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
@pytest.mark.parametrize("scenario", ["ok", "cached", "none", "approval", "failed", "oversize",
                                      "low_priority", "render_failed", "unsupported_media", "shared_key"])
def test_T_RPT_02_unit_equations_and_request_budget(flow, gen, step7_data, mock_provider, monkeypatch, scenario):
    source = flow.put("image.png", gen.png_noise(seed=71))
    provider, flags = mock_provider(egress=False), {}
    total, cached, transcribed, pending, failed, sent = 1, 0, 1, 0, 0, 1
    if scenario == "cached":
        cold = flow.run([source], provider=provider)
        flow.assert_report(cold, 0)
        provider.calls.clear()
        cached, transcribed, sent = 1, 0, 0
    elif scenario == "none":
        provider = None
        transcribed, pending, sent = 0, 1, 0
    elif scenario == "approval":
        provider.meta["egress"] = True
        transcribed, pending, sent = 0, 1, 0
    elif scenario == "failed":
        provider.script = [("fail", "E_PROVIDER_HTTP")]
        transcribed, failed = 0, 1
    elif scenario == "oversize":
        flags["max_units"] = 0
        transcribed, pending, sent = 0, 1, 0
    elif scenario == "low_priority":
        real = triage.run_triage
        def low(path, sniff):
            result = deepcopy(real(path, sniff))
            result["report"]["candidates"][0]["priority"] = "low"
            result["report"]["decision"] = "review"
            result["report"]["summary"].update(candidates_high=0, candidates_low=1)
            return result
        monkeypatch.setattr(triage, "run_triage", low)
        flags["min_priority"] = "normal"
        transcribed, pending, sent = 0, 1, 0
    elif scenario == "unsupported_media":
        source = flow.put("office.docx", step7_data.docx_bytes("emf"))
        total, pending = 2, 1
    elif scenario == "render_failed":
        real_render = render.render_units
        def unavailable(*args, **kwargs):
            result = real_render(*args, **kwargs)
            for unit in result["units"]:
                unit.update(status="render_failed", raster_sha256=None, mime=None, bytes=None)
            result["rasters"] = {}
            result["issues"] = [{"code": "E_RENDER_FAIL", "message": "injected unavailable raster"}]
            return result
        monkeypatch.setattr(render, "render_units", unavailable)
        transcribed, pending, sent = 0, 1, 0
    elif scenario == "shared_key":
        source = flow.put("twins.pdf", gen.make_pdf([{"image_seed": 9}, {"image_seed": 9}]))
        total, transcribed = 2, 2

    result = flow.run([source], provider=provider, **flags)
    expected_exit = {"approval": 3, "failed": 4, "oversize": 2, "render_failed": 2}.get(scenario, 0)
    flow.assert_report(result, expected_exit)
    f = result["files"][0]
    assert f["units"] == dict(total=total, eligible=cached + transcribed + failed,
                              cached=cached, transcribed=transcribed, pending=pending, failed=failed)
    assert f["requests"]["sent"] == sent
    assert f["requests"]["ok"] == (sent if transcribed else 0)
    assert f["requests"]["failed"] == failed
    keys_unique = 0 if scenario in {"oversize", "low_priority", "render_failed"} else 1
    retries = provider.meta["retries"] if provider is not None else 0
    assert f["requests"]["sent"] <= keys_unique * (1 + retries), "approved.max_requests bound"
    assert f["requests"]["to_send"] == (0 if scenario == "cached" else keys_unique)
    assert f["placements"] == total
    if provider is not None:
        assert len(provider.calls) == sent
        keys = {gen.sha256(call["raster"]) for call in provider.calls}
        assert sent <= len(keys) * (1 + provider.meta["retries"])
    assert f["outputs"] == [source.name + ".md"]


def _retry_failed_and_pending(flow, gen, mock_provider, monkeypatch):
    source = flow.put("scan.pdf", gen.pdf_scan(3))
    real_render = render.render_units
    def one_pending(*args, **kwargs):
        result = real_render(*args, **kwargs)
        unit = result["units"][-1]
        unit.update(status="render_failed", raster_sha256=None, mime=None, bytes=None)
        result["rasters"].pop(unit["source_id"], None)
        result["issues"].append({"code": "E_RENDER_FAIL", "message": "temporary render failure"})
        return result
    provider = mock_provider(egress=False)
    provider.script = [("ok", "first successful"), ("fail", "E_PROVIDER_HTTP")]
    with monkeypatch.context() as patch:
        patch.setattr(render, "render_units", one_pending)
        first = flow.run([source], provider=provider)
    flow.assert_report(first, 2)
    assert first["files"][0]["units"] == dict(total=3, eligible=2, cached=0, transcribed=1, pending=1, failed=1)
    succeeded = provider.calls[0]["raster"]
    rerun = mock_provider(egress=False)
    second = flow.run([source], provider=rerun)
    flow.assert_report(second, 0)
    assert len(rerun.calls) == 2 and all(c["raster"] != succeeded for c in rerun.calls)
    assert second["files"][0]["units"] == dict(total=3, eligible=3, cached=1, transcribed=2, pending=0, failed=0)


@pytest.mark.req("REQ-RPT-02")
@pytest.mark.cov("S13", "FM3")
@pytest.mark.fx("FX-09")
def test_T_RPT_53_m1_report_oversize(flow, gen, step7_data, mock_provider, monkeypatch):
    test_T_RPT_02_unit_equations_and_request_budget(flow, gen, step7_data, mock_provider, monkeypatch, 'oversize')


@pytest.mark.req("REQ-RPT-02")
@pytest.mark.cov("S13", "FM6")
@pytest.mark.fx("FX-09")
def test_T_RPT_54_m1_report_failed(flow, gen, step7_data, mock_provider, monkeypatch):
    test_T_RPT_02_unit_equations_and_request_budget(flow, gen, step7_data, mock_provider, monkeypatch, 'failed')


@pytest.mark.req("REQ-RPT-02")
@pytest.mark.cov("S13", "FM8")
@pytest.mark.fx("FX-09")
def test_T_RPT_55_m1_report_approval(flow, gen, step7_data, mock_provider, monkeypatch):
    test_T_RPT_02_unit_equations_and_request_budget(flow, gen, step7_data, mock_provider, monkeypatch, 'approval')


@pytest.mark.req("REQ-RPT-02")
@pytest.mark.cov("S13", "FM11")
@pytest.mark.fx("FX-09")
def test_T_RPT_56_m1_report_low_priority(flow, gen, step7_data, mock_provider, monkeypatch):
    test_T_RPT_02_unit_equations_and_request_budget(flow, gen, step7_data, mock_provider, monkeypatch, 'low_priority')
