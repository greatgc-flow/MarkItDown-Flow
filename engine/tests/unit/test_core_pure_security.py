"""PURE-stage isolation, provider post-processing, exit mapping and diagnostics."""
from copy import deepcopy
import inspect
import re

import pytest


@pytest.mark.req("REQ-GEN-04")
@pytest.mark.cov("S0", "FM0")
@pytest.mark.fx("FX-02", "FX-03", "FX-16")
@pytest.mark.parametrize("stage", ("canonical_json", "detect_format", "classify", "select", "plan", "key", "approve", "assemble", "redact"))
def test_T_GEN_04_every_pure_stage_without_io_clock_or_random(core_api, core_data, core_fx, monkeypatch, stage):
    unit = core_data.unit()
    entry = core_data.entry(unit)
    plan = core_data.approval_plan()
    calls = {
        "canonical_json": (core_api.hashing.canonical_json, ({"가": "text", "a": [True, None]},)),
        "detect_format": (core_api.sniff_pure.detect_format, (b"%PDF-1.4", "docx")),
        "select": (core_api.select.select, (core_data.Cases(".").classification(), core_data.options())),
        "plan": (core_api.plan.plan, (dict(units=[unit], oversize=False), dict(frames_total=None, uninspected_pages=0),
                 {unit["source_id"]: "miss"}, core_data.provider(), core_data.options())),
        "approve": (core_api.approve.approve, (plan, dict(yes_hashes=[plan["plan_hash"]]), core_data.NOW)),
        "key": (core_api.ledger.make_key, (unit, core_data.provider(), "p1")),
        "assemble": (core_api.assemble.assemble, ("<!-- mdflow:page 1 -->", [unit], {unit["source_id"]: entry}, core_data.assembly_meta(pages_total=1))),
        "redact": (core_api.redact.redact, ("diagnostic", {}, "/home/test")),
    }
    if stage == "classify":
        calls[stage] = (core_api.classify.classify, (core_fx.sniff(), core_fx.report("FX-03")))
    function, arguments = calls[stage]
    assert inspect.signature(function).return_annotation is not inspect.Signature.empty
    before = deepcopy(arguments)
    def forbidden(*args, **kwargs):
        raise AssertionError(f"PURE stage {stage} accessed IO, clock or randomness")
    with monkeypatch.context() as patch:
        for name in ("builtins.open", "io.open", "os.open", "time.time", "time.monotonic", "os.urandom", "random.random"):
            patch.setattr(name, forbidden)
        first = function(*arguments)
        second = function(*arguments)
    assert first == second
    assert arguments == before


@pytest.mark.req("REQ-TRX-04", "REQ-SEC-07")
@pytest.mark.cov("S10", "FM3")
@pytest.mark.fx("FX-61")
@pytest.mark.parametrize("raw,expected", [
    ("```markdown\r\nhello  \r\nworld\t\r\n```\r\n\r\n", "hello\nworld"),
    ("```\nhello\n```", "hello"),
    ("```a_B-9\nhello\rworld\n```\n", "hello\nworld"),
    ("\n```md\nhello\n```\n", "\n```md\nhello\n```"),
    ("```md language\nhello\n```", "```md language\nhello\n```"),
    ("```md\nhello\n```  ", "```md\nhello\n```"),
    ("prefix\rhello  \r\n\t\n", "prefix\nhello"),
    ('<!-- /mdflow:ocr -->\r\n"a--b"  ', '<!-- /mdflow:ocr -->\n"a--b"'),
    ("", ""), ("   \n\t\r\n", "")])
def test_T_TRX_04_normalization_fence_whitespace_length_order(core_api, raw, expected):
    text, issues = core_api.assemble.postprocess_text(raw)
    assert text == expected and issues == []
    exact, issues = core_api.assemble.postprocess_text("가" * 200000)
    assert exact == "가" * 200000 and issues == []
    long, issues = core_api.assemble.postprocess_text("```md\r\n" + "가" * 250000 + "  \r\n```\r\n")
    assert long == "가" * 200000 + "\n<!-- mdflow:truncated -->"
    assert {i["code"] for i in issues} == {"W_OUTPUT_TRUNCATED"}
    assert '<!-- /mdflow:ocr -->' in core_api.assemble.postprocess_text('<!-- /mdflow:ocr -->')[0]


@pytest.mark.req("REQ-RPT-03")
@pytest.mark.cov("S13", "FM10")
@pytest.mark.fx("all")
@pytest.mark.scope("schema")
def test_T_RPT_03_every_spec_code_and_precedence(core_api, repo_root):
    spec = (repo_root / "docs/renewal/10_SPEC.md").read_text(encoding="utf-8")
    section = spec.split("### 7.5 ", 1)[1].split("## 8.", 1)[0]
    runtime, startup = {}, {}
    for line in section.splitlines():
        if not line.startswith("| `"):
            continue
        fields = line.split("|")
        codes = re.findall(r"[EW]_[A-Z_]+", fields[1])
        contribution = int(fields[2].strip())
        destination = startup if "(startup)" in fields[1] else runtime
        destination.update(dict.fromkeys(codes, contribution))
    expected = dict(startup, **runtime)
    assert len(expected) == 54  # R33: conflict, preconvert error and warning; round 9: W_EXIFTOOL_UNUSABLE
    assert set(expected) == set(core_api.contracts.CODES)
    assert core_api.contracts.EXIT_CODE_MAP == expected
    for code, value in expected.items():
        assert core_api.assemble.exit_code([code]) == value, code
    for code, value in startup.items():
        assert core_api.assemble.exit_code([code], startup=True) == value
    for codes, value in (([], 0), (["E_APPROVAL_REQUIRED"], 3),
        (["E_APPROVAL_REQUIRED", "E_PROVIDER_HTTP"], 4),
        (["E_APPROVAL_REQUIRED", "E_PROVIDER_HTTP", "E_CORRUPT"], 2),
        (["E_CORRUPT", "E_USAGE"], 1)):
        assert core_api.assemble.exit_code(codes) == value
        assert core_api.assemble.exit_code(codes, cancelled=True) == 130


@pytest.mark.req("REQ-SEC-02")
@pytest.mark.cov("S13", "FM9")
@pytest.mark.fx("FX-61", "FX-67")
@pytest.mark.parametrize("home", ("/home/test-user", "C:\\Users\\test-user"))
def test_T_SEC_02_env_and_authorization_redacted_before_character_cap(core_api, home):
    env = {"MDFLOW_API_KEY": "key-sentinel", "ACCESS_TOKEN": "token-sentinel",
           "APP_SECRET": "secret-sentinel", "DB_PASSWORD": "password-sentinel",
           "EMPTY_KEY": "", "VISIBLE_NAME": "ordinary-visible"}
    authorization = "Bearer authorization-sentinel"
    message = " ".join([home + "/private", *[v for v in env.values() if v], authorization])
    before = deepcopy(env)
    result = core_api.redact.redact(message, env, home, authorization=authorization)
    for key in ("MDFLOW_API_KEY", "ACCESS_TOKEN", "APP_SECRET", "DB_PASSWORD"):
        assert env[key] not in result
    assert authorization not in result and home not in result
    assert "~" in result and result.count("***") >= 5
    assert "ordinary-visible" in result and env == before
    # If truncation happens before replacement, a partial secret leaks at the boundary.
    crossing = "x" * 495 + "key-sentinel" + "z" * 1000
    result = core_api.redact.redact(crossing, env, home)
    assert result == "x" * 495 + "***zz" and len(result) == 500
