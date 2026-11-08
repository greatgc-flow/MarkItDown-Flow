"""Shared helpers for the PT-* packaging tests (not a test module; stdlib only).

* ``load_yaml``: the small YAML subset GitHub workflows and attest files use
  (block maps/sequences, flow lists, quoted scalars, ``|``/``>`` blocks, comments).
  No PyYAML dependency: requirements-test.txt carries none.
* workflow helpers: matrix expansion, ``uses:`` audit, permissions access.
* ``Engine``: run ``python -m mdflow`` (source tree or packaged venv) in an isolated
  HOME/TEMP with explicit environment, reading UTF-8 text.
"""
from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
SHA40 = re.compile(r"[0-9a-f]{40}")
SENTINEL = "sk-pt-dummy-sentinel-7f3a"  # never a credential; must not appear in any produced byte
SUBJECTS = ("main.js", "manifest.json", "styles.css", "engine.zip", "engine.lock", "SHA256SUMS")


def load_py(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_digest(root: Path) -> dict[str, str]:
    """Relative path -> sha256 for every file under ``root`` (symlinks not followed)."""
    root = Path(root)
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


# ------------------------------------------------------------------------ YAML

_KEY = re.compile(r"""^(?P<key>"[^"]*"|'[^']*'|[^\s:#\-\[{"'][^:]*?)\s*:(?:\s+(?P<val>.*)|\s*)$""")


def _strip_comment(text: str) -> str:
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
    return text.rstrip()


def _split_flow(text: str) -> list[str]:
    parts, depth, quote, start = [], 0, None, 0
    for i, ch in enumerate(text):
        if quote:
            quote = None if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    tail = text[start:]
    if tail.strip():
        parts.append(tail)
    return [p.strip() for p in parts]


def _scalar(text: str):
    text = _strip_comment(text.strip())
    if text[:1] in "\"'" and len(text) >= 2 and text[-1] == text[0]:
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        return [_scalar(p) for p in _split_flow(text[1:-1])]
    if text.startswith("{") and text.endswith("}"):
        out = {}
        for part in _split_flow(text[1:-1]):
            key, _, value = part.partition(":")
            out[_scalar(key)] = _scalar(value)
        return out
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if text in {"null", "~", ""}:
        return None
    return text  # numbers stay strings: 3.10 must not become 3.1


class _Parser:
    def __init__(self, text: str):
        self.lines = text.replace("\r\n", "\n").split("\n")
        self.i = 0

    def peek(self):
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self.i += 1
                continue
            return len(raw) - len(raw.lstrip(" ")), stripped
        return None

    def block(self, indent: int):
        item = self.peek()
        if item is None or item[0] < indent:
            return None
        if item[1] == "-" or item[1].startswith("- "):
            return self.sequence(item[0])
        return self.mapping(item[0])

    def sequence(self, indent: int) -> list:
        out = []
        while True:
            item = self.peek()
            if item is None or item[0] != indent or not (item[1] == "-" or item[1].startswith("- ")):
                return out
            rest = item[1][1:].strip()
            if not rest:
                self.i += 1
                out.append(self.block(indent + 1))
            elif _KEY.match(_strip_comment(rest)):
                column = indent + (len(item[1]) - len(rest))
                self.lines[self.i] = " " * column + rest  # re-read the item as a map at its key column
                out.append(self.mapping(column))
            else:
                self.i += 1
                out.append(_scalar(rest))

    def mapping(self, indent: int) -> dict:
        out = {}
        while True:
            item = self.peek()
            if item is None or item[0] != indent:
                return out
            match = _KEY.match(item[1])
            if not match:
                raise ValueError(f"unsupported YAML at line {self.i + 1}: {item[1]!r}")
            key = _scalar(match["key"])
            value = (match["val"] or "").strip()
            self.i += 1
            if value[:1] in {"|", ">"} and re.fullmatch(r"[|>][+-]?", _strip_comment(value)):
                out[key] = self.block_scalar(indent, folded=value[0] == ">")
            elif _strip_comment(value) == "":
                nxt = self.peek()
                same_indent_seq = nxt and nxt[0] == indent and (nxt[1] == "-" or nxt[1].startswith("- "))
                out[key] = self.block(indent if same_indent_seq else indent + 1) if nxt and (
                    nxt[0] > indent or same_indent_seq) else None
            else:
                out[key] = _scalar(value)

    def block_scalar(self, indent: int, *, folded: bool) -> str:
        body, base = [], None
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if raw.strip() and len(raw) - len(raw.lstrip(" ")) <= indent:
                break
            if raw.strip() and base is None:
                base = len(raw) - len(raw.lstrip(" "))
            body.append(raw[base:] if base is not None and raw.strip() else "")
            self.i += 1
        while body and not body[-1]:
            body.pop()
        return (" " if folded else "\n").join(body) + "\n"


def load_yaml(text: str):
    parser = _Parser(text)
    value = parser.block(0)
    if parser.peek() is not None:
        raise ValueError(f"unparsed YAML near line {parser.i + 1}")
    return value


# ------------------------------------------------------------------- workflows

def workflow_files(repo: Path = REPO) -> list[Path]:
    base = repo / ".github"
    found = [*sorted((base / "workflows").glob("*.y*ml")), *sorted((base / "actions").rglob("action.y*ml"))]
    return [p for p in found if p.is_file()]


def load_workflows(repo: Path = REPO) -> dict[str, dict]:
    return {p.relative_to(repo).as_posix(): load_yaml(p.read_text(encoding="utf-8"))
            for p in workflow_files(repo) if "workflows" in p.parts}


def triggers(workflow: dict) -> set[str]:
    on = workflow.get("on", workflow.get(True))  # a naive loader may read `on` as boolean True
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    return set(on or {})


def jobs(workflow: dict) -> dict[str, dict]:
    return workflow.get("jobs") or {}


def needs(job: dict) -> list[str]:
    value = job.get("needs") or []
    return [value] if isinstance(value, str) else list(value)


def transitive_needs(all_jobs: dict, name: str) -> set[str]:
    seen, todo = set(), list(needs(all_jobs[name]))
    while todo:
        current = todo.pop()
        if current not in seen:
            seen.add(current)
            todo.extend(needs(all_jobs.get(current, {})))
    return seen


def expand_matrix(job: dict) -> list[dict]:
    matrix = ((job.get("strategy") or {}).get("matrix")) or {}
    axes = {k: v for k, v in matrix.items() if k not in {"include", "exclude"} and isinstance(v, list)}
    cells = [dict(zip(axes, combo)) for combo in itertools.product(*axes.values())] if axes else [{}]
    exclude = matrix.get("exclude") or []
    cells = [c for c in cells if not any(all(c.get(k) == v for k, v in e.items()) for e in exclude)]
    return cells + [dict(i) for i in (matrix.get("include") or [])]


_EXPR_EQ = re.compile(r"^\$\{\{\s*matrix\.(\w+)\s*==\s*'([^']*)'\s*\}\}$")


def allowed_failure(job: dict, cell: dict) -> bool:
    value = job.get("continue-on-error", False)
    if isinstance(value, bool):
        return value
    match = _EXPR_EQ.match(str(value).strip())
    if not match:
        raise AssertionError(f"unsupported continue-on-error expression: {value!r}")
    return cell.get(match[1]) == match[2]


def step_text(job: dict) -> str:
    """Everything a job runs or configures, as one string for substring oracles."""
    parts = []
    for step in job.get("steps") or []:
        parts.append(json.dumps(step, ensure_ascii=False, sort_keys=True))
        parts.append(str(step.get("run", "")))
    return "\n".join(parts)


_USES = re.compile(r"^(?P<indent>\s*)(?:-\s+)?uses:\s*(?P<ref>\S+)(?P<tail>.*)$")
_VERSION_COMMENT = re.compile(r"#\s*v?\d+(?:\.\d+)*\S*")


def audit_uses(text: str) -> list[str]:
    """Problems for each external ``uses:`` that is not a 40-hex SHA with a readable version comment."""
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        match = _USES.match(line)
        if not match:
            continue
        ref = match["ref"].strip("'\"")
        if ref.startswith("./"):
            continue  # local action/workflow: reviewed with this repository
        if ref.startswith("docker://"):
            if "@sha256:" not in ref:
                problems.append(f"line {number}: docker image not pinned by digest: {ref}")
            continue
        _, _, version = ref.partition("@")
        if not SHA40.fullmatch(version):
            problems.append(f"line {number}: not a full 40-hex commit SHA: {ref}")
        elif not _VERSION_COMMENT.search(match["tail"]):
            problems.append(f"line {number}: pinned SHA lacks a readable version comment: {ref}")
    return problems


# ------------------------------------------------------------ repository copies

def copy_repo_subset(destination: Path) -> Path:
    """Copy exactly what ``tools/trace.py check`` reads, for the mutation self-test (PT-10)."""
    import shutil
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "node_modules")
    for relative in ("docs/renewal", "engine/tests", "tools", "shell/test"):
        if (REPO / relative).exists():
            shutil.copytree(REPO / relative, destination / relative, ignore=ignore)
    return destination


# ---------------------------------------------------------------------- engine

class Engine:
    """Run ``python -m mdflow`` with an isolated HOME/TEMP and an explicit environment."""

    def __init__(self, argv_for, cwd: Path, scratch: Path, env: dict | None = None):
        self._argv_for, self.cwd = argv_for, Path(cwd)
        home, temp = scratch / "home", scratch / "temp"
        for folder in (home, temp):
            folder.mkdir(parents=True, exist_ok=True)
        base = {k: v for k, v in os.environ.items()
                if not k.upper().startswith("MDFLOW_") and k.upper() not in {"PYTHONPATH", "PYTHONHOME"}}
        base.update(HOME=str(home), USERPROFILE=str(home), TMP=str(temp), TEMP=str(temp), PYTHONIOENCODING="utf-8")
        self.env = dict(base, **(env or {}))

    def popen_args(self, args, env=None):
        return dict(args=self._argv_for(args), cwd=self.cwd, env=dict(self.env, **(env or {})))

    def run(self, *args, env=None, timeout=300) -> subprocess.CompletedProcess:
        return subprocess.run(**self.popen_args([str(a) for a in args], env), capture_output=True, text=True,
                              encoding="utf-8", timeout=timeout)


def json_objects(text: str) -> list:
    """Consecutive JSON values: pretty Plans on stdout, or one report."""
    decoder, values, text = json.JSONDecoder(), [], text.lstrip()
    while text:
        value, end = decoder.raw_decode(text)
        values.append(value)
        text = text[end:].lstrip()
    return values


def progress_events(stderr: str) -> list[dict]:
    lines = [line for line in stderr.splitlines() if line.strip()]
    assert all(len(line.encode("utf-8")) <= 64 * 1024 for line in lines), "progress line over 64 KiB"
    return [json.loads(line) for line in lines]


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.match(r"\d+(?:\.\d+)*", text)[0].split("."))
