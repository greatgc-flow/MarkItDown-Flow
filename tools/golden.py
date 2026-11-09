"""Orchestrator-only Core golden generation and integrity verification.

Usage: python tools/golden.py gen [--fx FX-01 ...]
       python tools/golden.py verify

Generation writes ONLY Core triage reports and a lock. Reviewed classification,
plan and Markdown oracles must be supplied independently, then sealed by gen.
No mdflow implementation is imported and no classification oracle is inferred.
"""
import argparse
from hashlib import sha256
import importlib.metadata
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_CORE = '0.3.6'


def recipes(root):
    spec = importlib.util.spec_from_file_location("golden_recipes", root / "engine/tests/fixtures/gen_core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def generate(root=ROOT, fixture_ids=None):
    from markitdown.ocr_triage import triage
    data = recipes(root)
    default_ids = data.GENERATED + (("FX-24",) if (root / "engine/tests/fixtures/FX-24.hwp").is_file() else ())
    fixture_ids = list(fixture_ids or default_ids)
    destination = root / "engine/tests/golden"
    destination.mkdir(parents=True, exist_ok=True)
    old_lock = destination / "GOLDEN.lock"
    sources = json.loads(old_lock.read_text(encoding="utf-8")).get("sources", {}) if old_lock.exists() else {}
    # Keep deterministic input artifacts for the orchestrator's review. A normal
    # mkdir avoids Python 3.15's Windows mode=0700 sandbox DACL problem.
    temporary = data.WorkspaceTemps(root / "build/golden-inputs").mktemp("sources")
    for fx in fixture_ids:
        source = data.generate(fx, temporary)
        # A second generation detects nondeterministic recipe regressions.
        original = source.read_bytes()
        assert data.generate(fx, temporary).read_bytes() == original, f"Nondeterministic generator: {fx}"
        report = triage(source)
        assert report["schema_version"] == 1 and report["rules_version"] == "1", "Core schema/rules drift"
        if fx == "FX-04":
            assert any("suspect_text_layer" in c["reasons"] for c in report["candidates"])
        if fx == "FX-19":
            assert report["candidates"] and all(c["priority"] == "low" for c in report["candidates"])
            assert any("decor_media" in c["reasons"] for c in report["candidates"])
        folder = destination / fx
        folder.mkdir(exist_ok=True)
        (folder / "triage.json").write_bytes(canonical(report) + b"\n")
        sources[fx] = dict(sha256=sha256(original).hexdigest(), bytes=len(original), filename=source.name)
        if fx == "FX-17":
            source_b = data.generate(fx, temporary, variant="b")
            (folder / "triage-b.json").write_bytes(canonical(triage(source_b)) + b"\n")
            sources[fx + "b"] = dict(sha256=sha256(source_b.read_bytes()).hexdigest(), bytes=source_b.stat().st_size, filename=source_b.name)
        if fx == "FX-02":
            source_12p = data.generate(fx, temporary, pages=12)
            (folder / "triage-12p.json").write_bytes(canonical(triage(source_12p)) + b"\n")
            sources[fx + "-12p"] = dict(sha256=sha256(source_12p.read_bytes()).hexdigest(), bytes=source_12p.stat().st_size, filename=source_12p.name)
    files = {p.relative_to(destination).as_posix(): sha256(p.read_bytes()).hexdigest()
             for p in sorted(destination.rglob("*")) if p.is_file() and p.name != "GOLDEN.lock"}
    lock = dict(v=1, core_version=importlib.metadata.version("markitdown-gc"),
                sources=sources, files=files)
    old_lock.write_bytes(canonical(lock) + b"\n")
    return lock


def verify(root=ROOT):
    destination = root / "engine/tests/golden"
    lock_path = destination / "GOLDEN.lock"
    assert lock_path.is_file(), "Orchestrator must run tools/golden.py gen"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["v"] == 1
    # The seal records the reference producer, not whichever compatible Core
    # endpoint is now regenerating and comparing the reports in CT-03.
    assert lock["core_version"] == REFERENCE_CORE, "Core version differs from reference GOLDEN.lock"
    actual = {p.relative_to(destination).as_posix(): sha256(p.read_bytes()).hexdigest()
              for p in destination.rglob("*") if p.is_file() and p.name != "GOLDEN.lock"}
    assert actual == lock["files"], "Missing, extra or modified golden file"
    assert lock["sources"], "Empty golden corpus"
    for fx in lock["sources"]:
        name = {"FX-17b": "FX-17/triage-b.json", "FX-02-12p": "FX-02/triage-12p.json"}.get(fx, f"{fx}/triage.json")
        assert name in actual, f"Unsealed Core report: {fx}"
    return lock


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("gen", "verify"))
    parser.add_argument("--fx", action="append", dest="fixture_ids")
    args = parser.parse_args(argv)
    try:
        lock = generate(fixture_ids=args.fixture_ids) if args.command == "gen" else verify()
    except (AssertionError, ImportError, OSError, ValueError, NotImplementedError) as error:
        print(f"golden {args.command} failed: {error}")
        return 1
    print(f"golden {args.command}: Core {lock['core_version']}, {len(lock['files'])} sealed files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
