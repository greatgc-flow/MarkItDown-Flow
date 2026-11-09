"""R30: legacy-encoded plain text (CP949 / Windows-1252 / Shift-JIS ...) is born-digital text, not an unsupported file.

Core's Triage validates only UTF-8/UTF-16 text (G2a); any other encoding comes back ``unsupported_format``. Sniff
therefore records the reason ``legacy_text`` for ``txt|log`` files that are control-free text in a legacy codec, and
Classify accepts exactly that combination as row 9d (NATIVE / NONE / T / convert_only). Binary files renamed ``.txt``
stay row 9a (X / E_UNSUPPORTED).
"""

import pytest

KO = "한국어 텍스트입니다. 두 번째 문장도 있습니다.\n세 번째 줄입니다.\n"
SAMPLES_ACCEPTED = {
    "cp949": KO.encode("cp949"),
    "cp1252": "Café déjà vu — “quoted” naïve résumé\n".encode("cp1252"),
    "shift_jis": "日本語のテキストです。これは二番目の文です。\n".encode("shift_jis"),
    "gbk": "中文文本。这是第二句话。\n".encode("gbk"),
}
SAMPLES_REJECTED = {
    "utf8": KO.encode("utf-8"),
    "ascii": b"plain ascii\n",
    "utf16": KO.encode("utf-16"),
    "nul": b"abc\x00def\n" * 8,
    "controls": bytes(range(0, 32)) * 4,
    "random": bytes((i * 37 + 11) % 256 for i in range(2048)),
    "id3": b"ID3" + bytes((i * 91 + 5) % 256 for i in range(256)),
    "empty": b"",
}


@pytest.mark.req("REQ-CLS-07")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-28", "FX-38")
@pytest.mark.parametrize("name", sorted(SAMPLES_ACCEPTED))
def test_T_SNF_81_pure_detector_accepts_legacy_text(core_api, name):
    assert core_api.sniff_pure.is_legacy_text(SAMPLES_ACCEPTED[name]) is True


@pytest.mark.req("REQ-CLS-07")
@pytest.mark.cov("S1", "FM9")
@pytest.mark.fx("FX-28", "FX-38")
@pytest.mark.parametrize("name", sorted(SAMPLES_REJECTED))
def test_T_SNF_82_pure_detector_rejects_utf_text_and_binary(core_api, name):
    assert core_api.sniff_pure.is_legacy_text(SAMPLES_REJECTED[name]) is False


@pytest.mark.req("REQ-CLS-07")
@pytest.mark.cov("S3", "FM4")
@pytest.mark.fx("FX-38")
def test_T_CLS_92_row_9d_needs_both_core_unsupported_and_the_sniff_reason(core_api, core_fx):
    report = core_fx.report("FX-38")
    assert report["coverage"]["state"] == "none" and report["issues"][0]["code"] == "unsupported_format"
    plain = core_fx.sniff("FX-38", format="txt", route="NATIVE")
    legacy = dict(plain, reasons=["legacy_text"])
    row_9a = core_api.classify.classify(plain, report)
    assert (row_9a["route"], row_9a["label"], row_9a["action"]) == ("UNSUPPORTED", "X", "report_only")
    assert [i["code"] for i in row_9a["issues"]] == ["E_UNSUPPORTED"]
    row_9d = core_api.classify.classify(legacy, report)
    assert (row_9d["route"], row_9d["need"], row_9d["label"], row_9d["action"]) == ("NATIVE", "NONE", "T", "convert_only")
    assert [i["code"] for i in row_9d["issues"]] == []
    assert "legacy_text" in row_9d["reasons"]
    # the reason never rescues other groups or Core verdicts other than "unsupported_format"
    csv = core_api.classify.classify(dict(core_fx.sniff("FX-30", format="csv"), reasons=["legacy_text"]), core_fx.report("FX-30"))
    assert csv["label"] == "T" and csv["need"] == "NONE" and csv["issues"] == []  # R33
    corrupt = dict(report, issues=[{"code": "corrupt", "detail": "x"}])
    assert core_api.classify.classify(legacy, corrupt)["label"] == "X"
    assert core_api.classify.classify(dict(legacy, format="pdf"), report)["label"] != "T"
