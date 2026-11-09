# MAN-01 implementation access record (R15 clean-room evidence)

Generated 2026-11-10 by the orchestrator with `python -I tools/access_record.py D:/Engram2/.engram/claude/projects D--Engram2-workspace-mdf-wt-shell D--Engram2-workspace-MarkItDown-Flow`.
These two folders hold every headless Claude Code session that peerhub ran for the shell implementers (cc/cc.fable, cc/cc.effort) and for the cc reviewers, in the shell worktree and the repository.

| Fact | Value |
|---|---|
| Sessions with tool calls | 31 |
| Tool calls scanned (Read/Grep/Glob/Bash/Edit/Write/...) | 5937 |
| Calls whose input references v1 source (tag 1.0.8 objects, root `src/`, `styles.css`, `main.ts`, root build config, upstream repo names) | 7 |
| Calls that returned v1 source content | **0** |

The 7 flagged calls:

| Session | Tool | What it was | Returned v1 content? |
|---|---|---|---|
| 09438bc6 | Bash | `gh api` read of the Obsidian community plugin list (listing identity); denied before running | No |
| 2702062f | Write, Edit x2 | wrote the JT-01 clean-room test, whose denylist contains the strings `obsidian-markitdown`, `ethanolivertroy`, `../src/` | No (writes) |
| 6810efda | Write | wrote review/R7_fable_ratify.md mentioning the upstream name | No (write) |
| 723cfd72 | Write | wrote review/M2_fable_cross.md mentioning the upstream name | No (write) |
| d853af5a | Read | `MarkItDown-Flow/esbuild.config.mjs` at the repository root | No: "File does not exist" (root v1 build config was deleted in aac5dac) |

Chronology: v1 `src/`, `styles.css`, tests and root build config were deleted in commit aac5dac (2026-11-09 02:32 +0900) before the shell worktree was created from 20c7853; neither tree contains v1 shell source. Limits: transcripts record what the implementers' tools touched in these sessions; they cannot prove what a model "knows" from training data. Similarity review (cx, MAN-01 first pass) found no copied substantive code.
