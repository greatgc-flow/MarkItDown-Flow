# Core reference snapshots

Release/reference baseline: **markitdown-gc 0.3.6**, released 2026-11-09. Runtime compatibility remains `>=0.3.5,<0.4`; CI retains 0.3.5 as the minimum compatible endpoint.

The `markitdown-gc_GUIDE_0.3.5.md` and `ocr_triage_0.3.5.py.txt` copies are archived evidence retained for stable SPEC line references. They are not a release pin. The orchestrator regenerated the golden corpus under 0.3.6 and reported byte-identical triage. M3 preserves all 50 sealed triage report bytes; contract tests regenerate observations using each installed Core endpoint and compare them with those reports. Assembly examples now name Core 0.3.6; no classification decision was inferred or rewritten by the repair.

Fresh reference resolution, complete dependency hashes/licenses and required target CI/manual evidence remain separate release gates. Local Windows Python 3.14 execution does not substitute for the Linux reference install.
