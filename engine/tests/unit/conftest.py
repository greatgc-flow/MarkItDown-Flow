"""Core RED fixtures; load the worktree package without changing sys.path."""
import importlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="session")
def tmp_path_factory(core_data, repo_root):
    return core_data.WorkspaceTemps(repo_root / "build/trace/redgreen/unit-tmp")


@pytest.fixture
def tmp_path(tmp_path_factory, request):
    return tmp_path_factory.mktemp(request.node.originalname or request.node.name)


@pytest.fixture(scope="session")
def core_data():
    path = Path(__file__).resolve().parents[1] / "fixtures/gen_core.py"
    spec = importlib.util.spec_from_file_location("mdflow_core_test_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def core_fx(core_data, tmp_path_factory):
    return core_data.Cases(tmp_path_factory.mktemp("core-fixtures"))


@pytest.fixture(scope="session")
def core_api():
    src = Path(__file__).resolve().parents[2] / "src/mdflow"
    spec = importlib.util.spec_from_file_location("mdflow", src / "__init__.py",
                                                submodule_search_locations=[str(src)])
    package = importlib.util.module_from_spec(spec)
    sys.modules["mdflow"] = package
    spec.loader.exec_module(package)
    names = "hashing sniff_pure classify select plan ledger approve assemble redact contracts".split()
    return SimpleNamespace(**{name: importlib.import_module("mdflow." + name) for name in names})


@pytest.fixture
def core_build_plan(core_api, core_data):
    def build(units=None, *, hits=(), p=None, opts=None, oversize=False, **render):
        units = units if units is not None else [core_data.unit(), core_data.unit("p4")]
        return core_api.plan.plan(dict(units=units, oversize=oversize),
            dict(dict(frames_total=None, uninspected_pages=0), **render),
            {u["source_id"]: "hit" if u["source_id"] in hits else "miss" for u in units},
            p or core_data.provider(), opts or core_data.options())
    return build
