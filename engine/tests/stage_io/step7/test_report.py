"""Step 7 RED: stdout/report publication and bounded JSONL diagnostics."""

from copy import deepcopy
import io
import json
import os
from pathlib import Path
import re
import stat

import pytest

from mdflow import report


@pytest.mark.req("REQ-RPT-01", "REQ-SEC-02", "REQ-GEN-05")
@pytest.mark.cov("S13", "FM0")
@pytest.mark.fx("all")
def test_T_RPT_01_one_full_report_and_bounded_redacted_progress(tmp_path, monkeypatch):
    ts = "2026-11-09T00:00:00+00:00"
    home, secret = str(tmp_path / "private-home"), "secret-at-character-boundary"
    events = [
        dict(v=1, ev="run_start", ts=ts, files=1, provider="none"),
        dict(v=1, ev="error", ts=ts, file="한글.png", code="E_RENDER_FAIL",
             message="x" * 495 + secret + home + "가" * 2000),
        dict(v=1, ev="approve_required", ts=ts, file="한글.png", plan_hash="a" * 64,
             destination="https://example.test/v1/chat/completions", model="model", keys_unique=200,
             requests_to_send=200, max_requests=600, est_max_cost=None, cost_known=False,
             threshold_exceeded=True, sensitive_hits=[f"{n}:" + "가" * 1000 for n in range(30)]),
        dict(v=1, ev="run_end", ts=ts, exit=2, files_ok=0, files_failed=1, provider_calls=0),
    ]
    before, stderr = deepcopy(events), io.StringIO()
    for event in events:
        report.emit_progress(event, stderr, env={"MDFLOW_API_KEY": secret}, home=home)
    lines = stderr.getvalue().splitlines()
    assert len(lines) == len(events)
    assert all(len(line.encode("utf-8")) <= 65536 for line in lines)
    parsed = [json.loads(line) for line in lines]
    assert [e["ev"] for e in parsed] == [e["ev"] for e in events]
    diagnostic = parsed[1]["message"]
    assert len(diagnostic) <= 500 and secret not in diagnostic and home not in diagnostic
    assert diagnostic.startswith("x" * 495 + "***"), "redact before applying the 500-character cap"
    approval = parsed[2]
    assert len(approval["sensitive_hits"]) == 20
    assert set(approval) == set(events[2]) and "units" not in approval
    assert events == before

    value = dict(v=1, mdflow="2.0.0", started=ts, finished=ts, options={},
                 files=[{"triage": {"document_text": "가" * 40000}}], skipped=[], exit=0)
    untouched = deepcopy(value)
    stdout, path = io.StringIO(), tmp_path / "run-report.json"
    observed, real_replace = [], os.replace

    def replace(source, destination):
        if Path(destination) == path:
            source = Path(source)
            assert source.parent == path.parent
            assert re.fullmatch(re.escape(path.name) + r"\.tmp-\d+-\d+", source.name)
            if os.name == "posix":
                assert stat.S_IMODE(source.stat().st_mode) == 0o600
            assert json.loads(source.read_text(encoding="utf-8")) == value
            observed.append(True)
        return real_replace(source, destination)
    monkeypatch.setattr(os, "replace", replace)
    report.publish(value, stdout=stdout, report_path=path)
    assert json.loads(stdout.getvalue()) == value
    assert len(stdout.getvalue().encode("utf-8")) > 65536, "report has no progress-line limit"
    assert json.loads(path.read_text(encoding="utf-8")) == value
    assert observed == [True] and value == untouched
    assert list(tmp_path.glob("run-report.json.tmp-*")) == []
