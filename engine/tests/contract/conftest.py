"""Installed-Core fixture recipes, independent of mdflow runtime imports."""
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def tmp_path_factory(contract_data, repo_root):
    return contract_data.WorkspaceTemps(repo_root / "build/trace/redgreen/contract-tmp")


@pytest.fixture
def tmp_path(tmp_path_factory, request):
    return tmp_path_factory.mktemp(request.node.originalname or request.node.name)


@pytest.fixture(scope="session")
def contract_data():
    path = Path(__file__).resolve().parents[1] / "fixtures/gen_core.py"
    spec = importlib.util.spec_from_file_location("mdflow_contract_test_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def contract_fx(contract_data, tmp_path_factory):
    return contract_data.Cases(tmp_path_factory.mktemp("contract-fixtures"))


@pytest.fixture(scope="session")
def installed_core():
    try:
        from markitdown import MarkItDown, StreamInfo
        from markitdown.ocr_triage import triage
    except ImportError as error:
        raise AssertionError("Installed markitdown-gc is required for CT-01..15") from error
    return MarkItDown, StreamInfo, triage
