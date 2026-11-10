"""Rebind named release evidence from one candidate commit to the next when the attested bytes did not change.

    python tools/rebind_evidence.py --folder release-evidence/2.0.0 --from OLD --to NEW [--repo .]

A named review attests specific repository paths. When a new candidate commit leaves every one of those
paths byte-identical (``git diff --quiet OLD NEW -- <paths>``), the review still applies; this tool then
rewrites the record's ``commit`` fields from OLD to NEW and appends one standard evidence line

    Rebound <date> from OLD to NEW: <paths> byte-identical

as a YAML list item / JSON ``evidence`` array entry, preserving the file's line endings. If ANY attested
path changed (content or mode), an attested pathspec matches nothing in either commit, a record is not
bound to OLD, or git fails, it refuses (exit 1, naming the records and files) and writes nothing.
``oracles.json`` is never rebound: it summarizes CI receipts of one commit and must be regenerated
(``tools/release_evidence.py produce``). Other files (MAN-04, receipts/) are left alone.

Commit fields: JSON records get every ``commit`` key equal to OLD replaced (top level and nested, e.g.
``install_reports``) and are re-serialized as ``json.dumps(indent=2)`` (the format the release tools
write; the trailing newline is kept as found). YAML records are edited line by line: only the top-level
``commit:`` scalar is rewritten, so a YAML record with a NESTED commit bound to OLD is refused.

``--ignore-eol`` additionally accepts a path whose OLD blob contains CRLF and whose NEW blob is exactly
that blob with CRLF -> LF (the repository-wide LF renormalization); such paths are named in the evidence
line. The reverse direction (LF -> CRLF) and mode-only changes are still refused.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import fnmatch
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
# record file -> the repository paths (git pathspecs) its named review attests
ATTESTS = {
    'R15_cleanroom.yml': ('shell/src', 'shell/styles.css'),                       # MAN-01
    'R16_readme_review.yml': ('README.md',),                                       # MAN-02
    'shell_i18n_review.yml': ('shell/src/pure/i18n.ts', 'docs/renewal/10_SPEC.md'),  # MAN-03 (7.5 table)
    'actions-review.json': ('.github/workflows',),
    'listing-review.json': ('manifest.json', 'versions.json', 'README.md'),
    'pkg04_core_artifacts.json': ('engine/requirements*.txt', 'engine/pyproject.toml'),
}
NEVER = {'oracles.json': 'not rebound: regenerate it at the new commit (tools/release_evidence.py produce)'}
SHA = re.compile(r'[0-9a-f]{40}')
COMMIT_LINE = re.compile(r'^commit:[ \t]*(["\']?)([^"\'\s#]*)\1[ \t]*(#.*)?$')
EVIDENCE_KEY = re.compile(r'^evidence:[ \t]*(#.*)?$')
ITEM = re.compile(r'^([ \t]*)- ')
NESTED_COMMIT = re.compile(r'^[ \t]*(- +)?["\']?commit["\']?[ \t]*:')


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=check)


def blob(repo: Path, commit: str, path: str) -> bytes | None:
    result = git(repo, 'cat-file', 'blob', f'{commit}:{path}', check=False)
    return result.stdout if result.returncode == 0 else None


def changed(repo: Path, old: str, new: str, paths, *, ignore_eol: bool) -> tuple[list[str], list[str]]:
    """(changed files, EOL-only files) between OLD and NEW below the attested pathspecs."""
    out = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames', '--name-only', '-z',
              old, new, '--', *paths).stdout.decode('utf-8')
    names = [n for n in out.split('\0') if n]
    if not ignore_eol:
        return names, []
    real, eol_only = [], []
    for name in names:
        before, after = blob(repo, old, name), blob(repo, new, name)
        # Only CRLF -> LF counts; identical bytes here mean a mode change, which is a real change.
        same = before is not None and after is not None and before != after and before.replace(b'\r\n', b'\n') == after
        (eol_only if same else real).append(name)
    return real, eol_only


def missing(repo: Path, old: str, new: str, paths) -> list[str]:
    """Attested pathspecs that match no file in OLD nor in NEW (a typo or a removed path attests nothing)."""
    files = set()
    for commit in (old, new):
        files.update(n for n in git(repo, 'ls-tree', '-r', '-z', '--name-only', commit).stdout.decode('utf-8').split('\0') if n)
    return [p for p in paths if not any(f == p or f.startswith(p + '/') or fnmatch.fnmatchcase(f, p) for f in files)]


def evidence_line(day: str, old: str, new: str, paths, eol_only) -> str:
    line = f'Rebound {day} from {old} to {new}: {", ".join(paths)} byte-identical'
    if eol_only:
        line += f' after CRLF->LF normalization (EOL-only: {", ".join(eol_only)})'
    return line


def _replace_commits(value, old: str, new: str):
    if isinstance(value, dict):
        return {k: (new if k == 'commit' and v == old else _replace_commits(v, old, new)) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_commits(v, old, new) for v in value]
    return value


def rebind_json(text: str, old: str, new: str, line: str) -> str:
    data = json.loads(text)
    if not isinstance(data, dict) or data.get('commit') != old:
        raise ValueError(f'not bound to {old}')
    if not isinstance(data.get('evidence'), list):
        raise ValueError('evidence must be a JSON array')
    data = _replace_commits(data, old, new)
    data['evidence'].append(line)
    return json.dumps(data, ensure_ascii=False, indent=2) + ('\n' if text.endswith('\n') else '')


def rebind_yaml(text: str, old: str, new: str, line: str) -> str:
    """Line-level edit of the attest subset (top-level ``commit:`` scalar, ``evidence:`` block list)."""
    lines = text.split('\n')
    commits = [i for i, l in enumerate(lines) if COMMIT_LINE.match(l)]
    if len(commits) != 1 or COMMIT_LINE.match(lines[commits[0]])[2] != old:
        raise ValueError(f'not bound to {old}')
    nested = [i + 1 for i, l in enumerate(lines) if i != commits[0] and NESTED_COMMIT.match(l) and old in l]
    if nested:
        raise ValueError(f'nested commit field bound to {old} on line {nested[0]} (YAML: only the top-level '
                         'commit is rebound; re-review or edit by hand)')
    match = COMMIT_LINE.match(lines[commits[0]])
    lines[commits[0]] = f'commit: {match[1]}{new}{match[1]}' + (f' {match[3]}' if match[3] else '')
    keys = [i for i, l in enumerate(lines) if EVIDENCE_KEY.match(l)]
    if len(keys) != 1:
        raise ValueError('evidence must be one top-level block list')
    last, indent, index = None, None, keys[0] + 1
    while index < len(lines) and (not lines[index].strip() or lines[index][0] in ' \t' or lines[index].startswith('- ')):
        if lines[index].strip() and not lines[index].lstrip().startswith('#'):
            last = index
            item = ITEM.match(lines[index])
            if item and indent is None:
                indent = item[1]
        index += 1
    if last is None or indent is None:
        raise ValueError('evidence must be a non-empty block list')
    lines.insert(last + 1, f'{indent}- {json.dumps(line, ensure_ascii=False)}')
    return '\n'.join(lines)


def plan(folder: Path, repo: Path, old: str, new: str, day: str, *, ignore_eol: bool):
    """(writes, problems, notes); nothing is written unless problems is empty."""
    writes, problems, notes = {}, [], []
    for name in sorted(p.name for p in folder.iterdir() if p.is_file()):
        if name in NEVER:
            notes.append(f'{name}: {NEVER[name]}')
            continue
        if name not in ATTESTS:
            continue
        paths = ATTESTS[name]
        absent = missing(repo, old, new, paths)
        if absent:
            problems.append(f'{name}: attested paths absent in both {old} and {new}: {", ".join(absent)}')
            continue
        real, eol_only = changed(repo, old, new, paths, ignore_eol=ignore_eol)
        if real:
            problems.append(f'{name}: attested paths changed between {old} and {new}: {", ".join(real)}')
            continue
        raw = (folder / name).read_bytes()
        crlf = b'\r\n' in raw
        line = evidence_line(day, old, new, paths, eol_only)
        try:
            text = raw.decode('utf-8').replace('\r\n', '\n')
            result = (rebind_json if name.endswith('.json') else rebind_yaml)(text, old, new, line)
        except ValueError as error:
            problems.append(f'{name}: {error}')
            continue
        writes[folder / name] = (result.replace('\n', '\r\n') if crlf else result).encode('utf-8')
        notes.append(f'{name}: rebound ({line})')
    if not writes and not problems:
        problems.append(f'no rebindable record in {folder} (expected one of: {", ".join(ATTESTS)})')
    return writes, problems, notes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--folder', type=Path, required=True, help='e.g. release-evidence/2.0.0')
    parser.add_argument('--from', dest='old', required=True, help='commit the records are bound to (40 hex)')
    parser.add_argument('--to', dest='new', required=True, help='new candidate commit (40 hex)')
    parser.add_argument('--repo', type=Path, default=ROOT, help='git repository containing both commits')
    parser.add_argument('--date', default=datetime.now(timezone.utc).date().isoformat(), help='YYYY-MM-DD (default: today, UTC)')
    parser.add_argument('--ignore-eol', action='store_true', help='accept paths whose blobs differ only by CRLF -> LF')
    args = parser.parse_args(argv)
    problems = [f'{label} must be a full 40-hex commit SHA: {value}' for label, value in (('--from', args.old), ('--to', args.new))
                if not SHA.fullmatch(value)]
    if args.old == args.new:
        problems.append('--from and --to name the same commit')
    try:
        valid_date = date.fromisoformat(args.date).isoformat() == args.date
    except ValueError:
        valid_date = False
    if not valid_date:
        problems.append(f'--date must be a valid YYYY-MM-DD date: {args.date}')
    if not args.folder.is_dir():
        problems.append(f'evidence folder not found: {args.folder}')
    writes, notes = {}, []
    try:
        if not problems:
            problems = [f'commit not found in {args.repo}: {value}' for value in (args.old, args.new)
                        if git(args.repo, 'rev-parse', '--verify', '--quiet', value + '^{commit}', check=False).returncode]
        if not problems:
            writes, problems, notes = plan(args.folder, args.repo, args.old, args.new, args.date, ignore_eol=args.ignore_eol)
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, 'stderr', None)
        detail = detail.decode('utf-8', 'replace').strip() if isinstance(detail, bytes) else ''
        writes, problems = {}, [f'git/IO failure: {error}' + (f': {detail}' if detail else '')]
    if problems:
        print('REFUSED (nothing written):', *problems, sep='\n', file=sys.stderr)
        return 1
    for path, data in writes.items():
        path.write_bytes(data)
    print(*notes, sep='\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
