"""M7-V01: base-cache identity follows real conversion inputs."""
import json
from unittest.mock import patch

import pytest

from mdflow import convert, sniff_pure


DATA = b"Name,Amount\nAlice,42\nBob,17\n"
EXPECTED = {
    "txt": "Name,Amount\nAlice,42\nBob,17\n",
    "csv": "| Name | Amount |\n| --- | --- |\n| Alice | 42 |\n| Bob | 17 |",
}


def source(fmt):
    return sniff_pure.sniff_result(
        DATA, f"sample.{fmt}", "",
        sniff_pure.detect_format(DATA, fmt),
    )


@pytest.mark.req("REQ-CNV-04", "REQ-CNV-05")
@pytest.mark.cov("S5", "FM12")
@pytest.mark.fx("FX-28", "FX-29")
@pytest.mark.parametrize("order", [("txt", "csv"), ("csv", "txt")])
def test_T_CNV_96_same_bytes_different_formats_match_cold_real_core(tmp_path, order):
    assert source("txt")["sha256"] == source("csv")["sha256"] == (
        "08f6e005ea37fe226ea2c395e73112444684a1aee001a3fa720327bde74cabdb")
    cache = tmp_path / "cache"
    with patch.object(convert, "core_convert", wraps=convert.core_convert) as core:
        for fmt in order:
            sniff = source(fmt)
            assert sniff["format"] == fmt and sniff["issues"] == []
            cold = convert.convert_source(DATA, sniff=sniff, action="convert_only", run_temp=tmp_path / f"cold-{fmt}")
            assert cold == dict(body=EXPECTED[fmt], pages=None, media={}, issues=[])
        core.reset_mock()
        for fmt in order:
            first = convert.convert_source(DATA, sniff=source(fmt), action="convert_only",
                                           run_temp=tmp_path / f"first-{fmt}", cache_dir=cache)
            assert first == dict(body=EXPECTED[fmt], pages=None, media={}, issues=[])
        assert [call.args[1] for call in core.call_args_list] == ["." + fmt for fmt in order]
        core.reset_mock()
        for fmt in reversed(order):
            warm = convert.convert_source(DATA, sniff=source(fmt), action="convert_and_ocr",
                                          run_temp=tmp_path / f"warm-{fmt}", cache_dir=cache)
            assert warm == dict(body=EXPECTED[fmt], pages=None, media={}, issues=[])
        core.assert_not_called()


@pytest.mark.req("REQ-CNV-04")
@pytest.mark.cov("S5", "FM12")
@pytest.mark.fx("FX-28")
@pytest.mark.parametrize("entry", ["legacy", "missing-identity", "wrong-identity", "nonobject"])
def test_T_CNV_97_cache_without_matching_conversion_identity_is_rejected(tmp_path, entry):
    cache = tmp_path / "cache"
    sniff = source("txt")
    convert.convert_source(DATA, sniff=sniff, action="convert_only", run_temp=tmp_path / "first", cache_dir=cache)
    body_path, = (cache / "base").glob("*.md")
    meta_path = body_path.with_suffix(".json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if entry == "legacy":
        body_path.unlink()
        meta_path.unlink()
        body_path = cache / "base" / f"{sniff['sha256']}-{convert._core_version()}.md"
        meta_path = body_path.with_suffix(".json")
        meta.pop("conversion", None)
    elif entry == "missing-identity":
        meta.pop("conversion", None)
    elif entry == "wrong-identity":
        meta["conversion"] = {"extension": ".csv"}
    else:
        meta = []
    body_path.write_text("wrong cached body", encoding="utf-8")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    with patch.object(convert, "core_convert", wraps=convert.core_convert) as core:
        result = convert.convert_source(DATA, sniff=sniff, action="convert_only",
                                        run_temp=tmp_path / "second", cache_dir=cache)
        assert result == dict(body=EXPECTED["txt"], pages=None, media={}, issues=[])
        core.assert_called_once()
