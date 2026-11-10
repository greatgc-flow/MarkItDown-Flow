"""R29: markitdown-gc's own LLM features are permanently OFF.

Whatever ``mdflow`` passes to ``MarkItDown()`` / ``convert_stream()`` is checked against explicit allow-lists, using
the fake Core and the real class wrapped by a recording subclass (monkeypatched ``MarkItDown``), and the engine source
is pinned to contain no LLM / Document Intelligence / Content Understanding plumbing. Our own OCR providers are
unaffected (they live in ``mdflow.providers``).
"""

import ast
from pathlib import Path

import pytest

from mdflow import convert

# R31/R34 allow only local tool settings besides plugins; Core LLM features stay off.
INIT_ALLOWED = {"enable_plugins", "exiftool_path", "libreoffice_path", "libreoffice_timeout"}
CONVERT_ALLOWED = {"file_extension", "extract_media", "media_base_dir"}
FORBIDDEN_PREFIXES = ("llm_", "docintel", "cu_", "azure")
SRC = Path(__file__).resolve().parents[2] / "src" / "mdflow"


def llm_violations(init_calls, convert_calls):
    """Every kwarg/positional that is not on the allow-lists (the helper itself is mutation-checked below)."""
    problems = []
    for args, kwargs in init_calls:
        if args:
            problems.append(("MarkItDown positional", args))
        problems += [("MarkItDown", k) for k in kwargs if k not in INIT_ALLOWED or k.startswith(FORBIDDEN_PREFIXES)]
        if kwargs.get("enable_plugins"):
            problems.append(("MarkItDown", "enable_plugins"))
    for args, kwargs in convert_calls:
        problems += [("convert_stream", k) for k in kwargs if k not in CONVERT_ALLOWED]
    return problems


@pytest.mark.req("REQ-CNV-05")
@pytest.mark.cov("S5", "FM9")
@pytest.mark.fx("FX-38")
def test_T_CNV_81_no_llm_argument_ever_reaches_core(tmp_path, gen, fake_core, run_temp):
    docs = {"pdf": gen.pdf_text(2), "docx": gen.docx_like({"i.png": gen.png_noise(seed=29)}), "png": gen.png_noise(),
            "jpeg": gen.jpeg_noise(), "txt": gen.txt_utf8(), "hwpx": gen.hwpx_like(), "pptx": gen.pptx_like()}
    for fmt, data in docs.items():
        convert.convert_source(data, sniff=gen.fake_sniff(f"f.{fmt}", data, fmt=fmt), action="convert_and_ocr",
                               run_temp=run_temp)
    assert fake_core.init_calls and fake_core.convert_calls
    assert llm_violations(fake_core.init_calls, fake_core.convert_calls) == []
    for _args, kwargs in fake_core.init_calls:
        assert not {"llm_client", "llm_model", "llm_prompt", "docintel_endpoint", "cu_endpoint"} & set(kwargs)
    # the guard really bites: an LLM kwarg anywhere is reported
    assert llm_violations([((), {"enable_plugins": False, "llm_client": object()})], []) != []
    assert llm_violations([((), {"enable_plugins": False, "docintel_endpoint": "https://x"})], []) != []
    assert llm_violations([((), {"enable_plugins": False})], [((), {"llm_prompt": "caption"})]) != []
    assert llm_violations([((), {"enable_plugins": False, "llm_model": None})], []) != [], "None-valued is still passed"


@pytest.mark.req("REQ-CNV-05")
@pytest.mark.cov("S5", "FM9")
@pytest.mark.fx("FX-38")
def test_T_CNV_82_real_markitdown_receives_only_allow_listed_arguments(tmp_path, gen, run_temp, monkeypatch):
    import markitdown

    init_calls, convert_calls = [], []

    class Recording(markitdown.MarkItDown):
        def __init__(self, *args, **kwargs):
            init_calls.append((args, kwargs))
            super().__init__(*args, **kwargs)

        def convert_stream(self, stream, *args, **kwargs):
            convert_calls.append((args, kwargs))
            return super().convert_stream(stream, *args, **kwargs)

    monkeypatch.setattr(markitdown, "MarkItDown", Recording)
    for fmt, data in {"pdf": gen.pdf_text(1), "png": gen.png_noise(), "txt": gen.txt_utf8(),
                      "docx": gen.docx_like()}.items():
        convert.convert_source(data, sniff=gen.fake_sniff(f"f.{fmt}", data, fmt=fmt), action="convert_only",
                               run_temp=run_temp)
    assert len(init_calls) >= 4 and len(convert_calls) >= 4
    assert llm_violations(init_calls, convert_calls) == []


@pytest.mark.req("REQ-CNV-05")
@pytest.mark.cov("S5", "FM9")
@pytest.mark.fx("FX-38")
def test_T_CNV_83_engine_source_has_no_core_llm_plumbing():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                      if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))
                      and node.body and isinstance(node.body[0], ast.Expr)
                      and isinstance(node.body[0].value, ast.Constant)}
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.keyword) and node.arg:
                names.append(node.arg)
            elif isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, ast.arg):
                names.append(node.arg)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                names.append(node.value)
            offenders += [f"{path.name}:{getattr(node, 'lineno', 0)}:{n}" for n in names
                          if n.lower().startswith(FORBIDDEN_PREFIXES)]
    assert offenders == []
    cli = (SRC / "cli.py").read_text(encoding="utf-8")
    for flag in ("--llm", "--llm-model", "--llm-client", "--docintel", "--caption"):
        assert flag not in cli
