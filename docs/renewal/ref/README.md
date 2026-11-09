# Core reference snapshots

R34 release/reference baseline: **markitdown-gc 0.3.7** (published on PyPI 2026-11-09). Runtime compatibility is `>=0.3.7,<0.4`; CI uses 0.3.7 as the minimum endpoint. The orchestrator regenerated GOLDEN.lock with producer 0.3.7; triage files are unchanged. Verification checks that reference producer independently of the installed compatible Core endpoint. `engine/requirements-reference.txt` pins the [published PyPI wheel/sdist hashes](https://pypi.org/pypi/markitdown-gc/0.3.7/json) for CI reference compilation.

The `markitdown-gc_GUIDE_0.3.5.md` and `ocr_triage_0.3.5.py.txt` copies are archived evidence retained for stable SPEC line references. They are not a release pin. The orchestrator regenerated the golden corpus under 0.3.7 and reported byte-identical triage (as in the earlier 0.3.6 migration). M3 preserves all 50 sealed triage report bytes; contract tests regenerate observations using each installed Core endpoint and compare them with those reports. Historical assembly fixtures retain Core 0.3.6 provenance; no classification decision was inferred or rewritten by the repair.

Fresh reference resolution, complete dependency hashes/licenses and required target CI/manual evidence remain separate release gates. Local Windows Python 3.14 execution does not substitute for the Linux reference install.
