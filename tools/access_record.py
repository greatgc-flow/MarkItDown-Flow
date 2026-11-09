"""MAN-01 evidence: scan peer Claude Code session transcripts for any access to retired v1 shell source.

Usage: python tools/access_record.py <projects-dir> <project-folder> [<project-folder> ...]
Reports sessions, tool calls and every tool call whose input references v1 source (tag 1.0.8 objects,
root src/ styles.css main.ts build config, upstream repo names). Each flagged call is printed with the
tool result head so a reviewer can tell reads of v1 content from writes, denylists and missing files.
"""
import collections
import json
import re
import sys
from pathlib import Path

V1 = re.compile(r"(git\s+(show|cat-file|archive|checkout|diff)[^\n]*(1\.0\.8|be75110|55cf148)|1\.0\.8:"
                r"|MarkItDown-Flow/(src|main\.ts|styles\.css|esbuild\.config|jest\.config)"
                r"|(?<!shell/)(?<![\w.-])src/(converter|modals|services|settings|types|utils|__tests__|__mocks__)/"
                r"|ethanolivertroy|obsidian-markitdown)", re.I)


def scan(root: Path, folders: list[str]) -> dict:
    sessions, flagged = collections.Counter(), []
    for folder in folders:
        for path in sorted((root / folder).glob("*.jsonl")):
            uses, results = {}, {}
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                content = (record.get("message") or {}).get("content")
                for item in content if isinstance(content, list) else []:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "tool_use":
                        sessions[f"{folder}/{path.stem[:8]}"] += 1
                        text = json.dumps(item.get("input", {}), ensure_ascii=False).replace("\\\\", "/")
                        if V1.search(text):
                            uses[item["id"]] = (item.get("name"), text[:200])
                    elif item.get("type") == "tool_result":
                        results[item.get("tool_use_id")] = json.dumps(item.get("content"), ensure_ascii=False)[:160]
            for key, (name, text) in uses.items():
                flagged.append({"session": f"{folder}/{path.stem[:8]}", "tool": name, "input": text,
                                "result_head": results.get(key, "")})
    return {"sessions": len(sessions), "tool_calls": sum(sessions.values()), "flagged": flagged}


if __name__ == "__main__":
    print(json.dumps(scan(Path(sys.argv[1]), sys.argv[2:]), indent=1, ensure_ascii=False))
