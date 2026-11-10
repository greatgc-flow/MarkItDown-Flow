"""PT-39..41: structural fixes for recurring bottlenecks (one EOL policy, venv-free FX-71 engine import,
commit rebinding of unchanged named evidence)."""
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from _support import REPO, load_py, tree_digest

SEALED = ('engine/tests/golden/', 'engine/tests/fixtures/', 'shell/test/fixtures/fx71/')
OLD_POLICY_ERROR = 'the repository stores and checks out every text file with LF'


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), '-c', 'core.autocrlf=false', '-c', 'commit.gpgsign=false',
                           '-c', 'user.name=pt', '-c', 'user.email=pt@example.invalid', *args],
                          capture_output=True, check=True)


def needs_git(repo=REPO):
    if shutil.which('git') is None or subprocess.run(['git', '-C', str(repo), 'rev-parse', '--git-dir'],
                                                     capture_output=True).returncode:
        pytest.skip('git checkout required')


@pytest.mark.req('REQ-PKG-17', 'REQ-PKG-10')
@pytest.mark.cov('S0', 'FM10')
def test_PT_39_one_lf_policy_for_every_tracked_text_file_and_sealed_bytes_are_never_converted():
    rules = [line for line in (REPO / '.gitattributes').read_text(encoding='utf-8').splitlines()
             if line.strip() and not line.startswith('#')]
    assert rules[0] == '* text=auto eol=lf'
    assert sorted(rules[1:]) == sorted(f'/{prefix}** -text' for prefix in SEALED)
    needs_git()
    listing = git(REPO, 'ls-files', '--eol', '-z').stdout.decode('utf-8')
    offenders, sealed = [], {}
    for entry in filter(None, listing.split('\0')):
        info, path = entry.split('\t', 1)
        index, worktree, attr = info.split(None, 2)
        if path.startswith(SEALED):
            sealed[path] = attr
        elif index not in {'i/lf', 'i/none', 'i/-text', 'i/'} or worktree not in {'w/lf', 'w/none', 'w/-text', 'w/'}:
            offenders.append(f'{path} ({index} {worktree})')
    assert not offenders, OLD_POLICY_ERROR + ': ' + ', '.join(offenders)
    assert sealed and all('-text' in attr for attr in sealed.values()), sealed
    # Recorded CRLF protocol streams keep their exact bytes (FX-71 manifest sha256 covers them).
    assert b'\r\n' in (REPO / 'shell/test/fixtures/fx71/approve-required.crlf.jsonl').read_bytes()


@pytest.mark.req('REQ-PKG-09', 'REQ-PKG-01')
@pytest.mark.cov('S0', 'FM9')
def test_PT_40_recorder_imports_engine_src_through_an_isolated_bootstrap_without_touching_a_venv(
        tmp_path, monkeypatch, capsys):
    record = load_py(REPO / 'tools/record_protocol.py', 'pt40_recorder')
    src = tmp_path / 'engine-src'
    (src / 'mdflow').mkdir(parents=True)
    (src / 'mdflow/__init__.py').write_text('', encoding='utf-8')
    (src / 'mdflow/__main__.py').write_text(
        'import json, os, sys\n'
        'print(json.dumps(dict(argv=sys.argv[1:], isolated=sys.flags.isolated, no_user_site=sys.flags.no_user_site,\n'
        '                      ignore_environment=sys.flags.ignore_environment,\n'
        '                      cwd_on_path="" in sys.path or os.getcwd() in sys.path)))\n'
        'raise SystemExit(7)\n', encoding='utf-8')
    work = tmp_path / 'work'
    (work / 'mdflow').mkdir(parents=True)
    (work / 'mdflow/__init__.py').write_text('raise SystemExit("work-directory module imported")\n', encoding='utf-8')
    argv = record.child_argv(src, ['version', 'a b'])
    assert argv[:3] == [sys.executable, '-I', '-c'] and argv[4:] == ['version', 'a b']
    # A hostile PYTHONPATH and work-directory package are ignored; only --engine-src is imported.
    env = dict(os.environ, PYTHONPATH=str(work))
    result = subprocess.run(argv, cwd=work, env=env, capture_output=True, timeout=60)
    assert result.returncode == 7, result.stderr
    assert json.loads(result.stdout) == dict(argv=['version', 'a b'], isolated=1, no_user_site=1,
                                             ignore_environment=1, cwd_on_path=False)
    # A folder without the package can never fall back to an installed or venv-provided mdflow silently.
    empty = tmp_path / 'empty'
    empty.mkdir()
    refused = subprocess.run(record.child_argv(empty, ['version']), cwd=work, capture_output=True, timeout=60)
    assert refused.returncode != 0
    assert b'not imported from --engine-src' in refused.stderr or b'No module named' in refused.stderr
    # Recorder wiring through the real save/leak check: real argv uses the bootstrap, the manifest label
    # and environment do not, and output naming the source folder is rejected before it is written.
    out = tmp_path / 'out'
    out.mkdir()
    recorder = record.Recorder(out, tmp_path / 'rec', engine_src=src)
    launches = []
    replies = iter([b'{"mdflow": "2.0.0"}\n', json.dumps({'file': str(src / 'mdflow/cli.py')}).encode()])
    with monkeypatch.context() as patch:
        patch.setattr(record.subprocess, 'run', lambda argv, **kw: launches.append((argv, kw)) or
                      SimpleNamespace(returncode=0, stdout=next(replies), stderr=b''))
        recorder.record('version', ['version'], expect=0, stdout='version.json')
        with pytest.raises(SystemExit, match='leaks an absolute path'):
            recorder.record('leak', ['providers'], expect=0, stdout='leak.json')
    assert launches[0][0] == record.child_argv(src, ['version'])
    assert 'PYTHONPATH' not in launches[0][1]['env'] and 'PYTHONHOME' not in launches[0][1]['env']
    assert recorder.entries['version.json']['argv'] == ['python', '-I', '-m', 'mdflow', 'version']
    assert 'leak.json' not in recorder.entries and not (out / 'leak.json').exists()
    # Provenance: the manifest binds a path-free digest of the imported source; --verify checks it.
    recorder.manifest()
    text = (out / 'manifest.json').read_text(encoding='utf-8')
    manifest = json.loads(text)
    assert manifest['engine_source']['sha256'] == record.source_digest(src / 'mdflow')['sha256']
    assert manifest['engine_source']['files'] == 2
    assert not any(spelling in text for spelling in (str(tmp_path), tmp_path.as_posix(), json.dumps(str(tmp_path))[1:-1]))
    capsys.readouterr()
    assert record.verify(out, src) == 0 and 'engine source bound' in capsys.readouterr().out
    elsewhere = tmp_path / 'elsewhere/src'
    shutil.copytree(src, elsewhere)  # same bytes at another location (and a CRLF checkout) = same source
    main_py = record.lf((src / 'mdflow/__main__.py').read_bytes())
    (elsewhere / 'mdflow/__main__.py').write_bytes(main_py.replace(b'\n', b'\r\n'))
    (elsewhere / 'mdflow/__pycache__').mkdir(exist_ok=True)
    (elsewhere / 'mdflow/__pycache__/stale.py').write_text('x = 1\n', encoding='utf-8')
    assert record.verify(out, elsewhere) == 0
    (elsewhere / 'mdflow/__init__.py').write_text('changed = True\n', encoding='utf-8')
    assert record.verify(out, elsewhere) == 1 and 'engine source mismatch' in capsys.readouterr().out
    assert record.verify(out) == 0  # library default: integrity only
    # A manifest recorded before engine_source is reported UNBOUND, never silently "bound".
    del manifest['engine_source']
    (out / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    capsys.readouterr()
    assert record.verify(out, src) == 0 and 'engine source UNBOUND' in capsys.readouterr().out
    assert record.Recorder(tmp_path / 'o2', tmp_path / 'r2').engine_src is None  # library default: installed
    # CLI default is this checkout's engine/src; --installed selects the interpreter's package; --verify
    # checks against the same choice.
    calls, verified = [], []
    monkeypatch.setattr(record, 'record', lambda out, work, engine_src: calls.append(engine_src))
    monkeypatch.setattr(record, 'verify', lambda out, engine_src: verified.append(engine_src) or 0)
    for args in ([], ['--installed'], ['--engine-src', str(src)], ['--verify'], ['--verify', '--installed']):
        assert record.main(args) == 0
    assert calls == [REPO / 'engine/src', None, src]
    assert verified == [REPO / 'engine/src', None, src, REPO / 'engine/src', None]


OLD_FILES = {
    'shell/src/main.ts': 'export {};\n', 'shell/src/pure/i18n.ts': 'export const en = {};\n',
    'shell/styles.css': '.a {}\n', 'README.md': '# README\r\n\r\ntext\r\n',
    'docs/renewal/10_SPEC.md': '### 7.5 Codes\n', 'docs/renewal/HANDOFF.md': 'handoff\n',
    '.github/workflows/ci.yml': 'name: ci\n', 'manifest.json': '{"version": "2.0.0"}\n',
    'versions.json': '{"2.0.0": "1.8.0"}\n', 'engine/requirements-build.txt': 'hatchling==1.33.0\n',
    'engine/pyproject.toml': '[project]\n', 'engine/src/mdflow/cli.py': 'x = 1\n',
}


def candidate_repo(root, changes, executable=()):
    root.mkdir()
    git(root, 'init', '-q')
    for name, text in OLD_FILES.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(text.encode('utf-8'))
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', 'old')
    old = git(root, 'rev-parse', 'HEAD').stdout.decode().strip()
    for name, text in changes.items():
        (root / name).write_bytes(text.encode('utf-8'))
    git(root, 'add', '-A')
    for name in executable:  # mode-only change (100644 -> 100755), bytes untouched
        git(root, 'update-index', '--chmod=+x', name)
    git(root, 'commit', '-q', '--allow-empty', '-m', 'new')
    return old, git(root, 'rev-parse', 'HEAD').stdout.decode().strip()


def yaml_record(identity, commit):
    return (f'# {identity} named review\r\nid: {identity}\r\nreviewer: peer/profile/model\r\ndate: 2026-11-01\r\n'
            f'commit: {commit}\r\ninputs:\r\n  - spec\r\nevidence:\r\n  # how\r\n  - notes/{identity}.md\r\n'
            'verdict: PASS\r\n')


def evidence_folder(folder, old):
    folder.mkdir()
    for name, identity in (('R15_cleanroom.yml', 'MAN-01'), ('R16_readme_review.yml', 'MAN-02'),
                           ('shell_i18n_review.yml', 'MAN-03')):
        (folder / name).write_bytes(yaml_record(identity, old).encode('utf-8'))
    review = dict(reviewer='peer/profile/model', date='2026-11-01', commit=old, evidence=['link'], verdict='PASS')
    (folder / 'actions-review.json').write_text(json.dumps(dict(review, actions=[]), indent=2) + '\n', encoding='utf-8', newline='\n')
    (folder / 'listing-review.json').write_bytes((json.dumps(dict(review, listing={'id': 'markitdown-flow'}),
                                                             indent=2) + '\n').replace('\n', '\r\n').encode('utf-8'))
    pkg = dict(review, install_reports=[dict(target='t', commit=old, exit=0, report={'install': []})])
    (folder / 'pkg04_core_artifacts.json').write_text(json.dumps(pkg, indent=2) + '\n', encoding='utf-8', newline='\n')
    (folder / 'oracles.json').write_text(json.dumps(dict(commit=old, generator_commit=old)), encoding='utf-8')
    (folder / 'release_rehearsal.yml').write_text(f'id: MAN-04\ncommit: {old}\n', encoding='utf-8')


@pytest.mark.req('REQ-PKG-22', 'REQ-PKG-17')
@pytest.mark.cov('S0', 'FM10')
def test_PT_41_rebind_moves_unchanged_named_evidence_to_the_new_commit_and_refuses_changed_attested_paths(
        tmp_path, capsys, monkeypatch):
    if shutil.which('git') is None:
        pytest.skip('git required')
    tool = load_py(REPO / 'tools/rebind_evidence.py', 'pt41_rebind')
    run = lambda folder, repo, old, new, *extra: tool.main(['--folder', str(folder), '--repo', str(repo), '--from', old,
                                                          '--to', new, '--date', '2026-11-10', *extra])
    # Positive: only unattested files changed -> every rebindable record is rebound, oracles/MAN-04 untouched.
    repo = tmp_path / 'repo'
    old, new = candidate_repo(repo, {'engine/src/mdflow/cli.py': 'x = 2\n', 'docs/renewal/HANDOFF.md': 'next\n'})
    folder = tmp_path / 'evidence'
    evidence_folder(folder, old)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert run(folder, repo, old, new) == 0
    notes = capsys.readouterr().out
    assert 'oracles.json: not rebound: regenerate' in notes
    for name in ('oracles.json', 'release_rehearsal.yml'):
        assert (folder / name).read_bytes() == before[name], name
    for name, paths in tool.ATTESTS.items():
        line = f'Rebound 2026-11-10 from {old} to {new}: {", ".join(paths)} byte-identical'
        raw = (folder / name).read_bytes()
        original = before[name]
        # The file keeps its own line-ending convention (CRLF records stay CRLF, LF records stay LF).
        if b'\r\n' in original:
            assert b'\n' not in raw.replace(b'\r\n', b''), f'{name}: bare LF written into a CRLF record'
        else:
            assert b'\r' not in raw, f'{name}: CR written into an LF record'
        text = raw.decode('utf-8').replace('\r\n', '\n')
        if name.endswith('.yml'):
            # Exactly two edits: the commit value and one appended evidence item; comments/order untouched.
            lines = original.decode('utf-8').replace('\r\n', '\n').replace(f'commit: {old}', f'commit: {new}').split('\n')
            lines.insert(lines.index('verdict: PASS'), '  - ' + json.dumps(line))
            assert text == '\n'.join(lines), name
        else:
            data = json.loads(text)
            assert data['commit'] == new and data['evidence'] == ['link', line], name
            # Only the appended rebind note may name OLD (as "from OLD to NEW").
            assert old not in text.replace(json.dumps(line), ''), f'{name}: a commit field still names OLD'
            expected = json.loads(original)
            expected['commit'] = new
            expected['evidence'].append(line)
            for report in expected.get('install_reports', []):
                report['commit'] = new
            assert data == expected, name
    # Refusal: attested files changed -> exit 1, every affected record and file named, nothing written.
    repo2 = tmp_path / 'repo2'
    old2, new2 = candidate_repo(repo2, {'shell/styles.css': '.b {}\n', 'README.md': '# README v2\r\n'})
    folder2 = tmp_path / 'evidence2'
    evidence_folder(folder2, old2)
    digest = tree_digest(folder2)
    assert run(folder2, repo2, old2, new2) == 1
    refused = capsys.readouterr().err
    assert 'REFUSED (nothing written)' in refused
    for record, path in (('R15_cleanroom.yml', 'shell/styles.css'), ('R16_readme_review.yml', 'README.md'),
                         ('listing-review.json', 'README.md')):
        assert any(record in line and path in line for line in refused.splitlines()), (record, path, refused)
    assert 'shell_i18n_review.yml' not in refused and tree_digest(folder2) == digest

    def refused_only(folder, repo, old, new, *extra):
        """Exit 1, nothing written; the REFUSED problem lines."""
        digest = tree_digest(folder)
        assert run(folder, repo, old, new, *extra) == 1
        err = capsys.readouterr().err.splitlines()
        assert err[0] == 'REFUSED (nothing written):' and tree_digest(folder) == digest, err
        return err[1:]

    def fresh(label, commit):
        evidence_folder(tmp_path / label, commit)
        return tmp_path / label

    # A record bound to another commit is refused even when every attested path is unchanged (repo 1).
    folder = fresh('mismatch', old)
    (folder / 'shell_i18n_review.yml').write_bytes(yaml_record('MAN-03', 'b' * 40).encode('utf-8'))
    assert refused_only(folder, repo, old, new) == [f'shell_i18n_review.yml: not bound to {old}']
    # YAML rebinds only the top-level commit, so a nested commit still naming OLD is refused, not left stale.
    folder = fresh('nested', old)
    (folder / 'R15_cleanroom.yml').write_bytes(yaml_record('MAN-01', old).replace(
        'verdict: PASS', f'reports:\r\n  - target: t\r\n    commit: {old}\r\nverdict: PASS').encode('utf-8'))
    assert [p.split(' on line')[0] for p in refused_only(folder, repo, old, new)] == [
        f'R15_cleanroom.yml: nested commit field bound to {old}']
    # An attested pathspec matching nothing in either commit (typo / removed file) attests nothing.
    monkeypatch.setitem(tool.ATTESTS, 'shell_i18n_review.yml', ('shell/src/pure/i18n.ts', 'docs/renewal/NO_SUCH.md'))
    assert refused_only(fresh('absent', old), repo, old, new) == [
        f'shell_i18n_review.yml: attested paths absent in both {old} and {new}: docs/renewal/NO_SUCH.md']
    monkeypatch.undo()
    # Argument errors: same commit, missing folder, bad date, a folder without rebindable records.
    assert refused_only(fresh('same', old), repo, old, old) == ['--from and --to name the same commit']
    assert run(tmp_path / 'no-such-folder', repo, old, new) == 1
    assert 'evidence folder not found' in capsys.readouterr().err
    assert refused_only(fresh('date', old), repo, old, new, '--date', '2026-02-30') == [
        '--date must be a valid YYYY-MM-DD date: 2026-02-30']
    folder = tmp_path / 'only-oracles'
    folder.mkdir()
    (folder / 'oracles.json').write_text('{}', encoding='utf-8')
    (folder / 'notes.md').write_text('x', encoding='utf-8')
    assert refused_only(folder, repo, old, new)[0].startswith(f'no rebindable record in {folder}')
    # Both unknown commits are reported, not only the first.
    assert refused_only(fresh('unknown', old), repo, 'c' * 40, 'd' * 40) == [
        f'commit not found in {repo}: {"c" * 40}', f'commit not found in {repo}: {"d" * 40}']
    # A git failure is a refusal (exit 1), not a traceback.
    real_git = tool.git

    def failing_git(repo_, *args, check=True):
        if args[0] == 'diff':
            raise subprocess.CalledProcessError(128, ['git', *args], b'', b'fatal: bad object')
        return real_git(repo_, *args, check=check)

    monkeypatch.setattr(tool, 'git', failing_git)
    problems = refused_only(fresh('git-fails', old), repo, old, new)
    assert len(problems) == 1 and problems[0].startswith('git/IO failure:') and 'fatal: bad object' in problems[0]
    monkeypatch.undo()
    # EOL-only renormalization: refused by default, accepted and named with --ignore-eol.
    repo3 = tmp_path / 'repo3'
    old3, new3 = candidate_repo(repo3, {'README.md': OLD_FILES['README.md'].replace('\r\n', '\n')})
    folder3 = tmp_path / 'evidence3'
    evidence_folder(folder3, old3)
    assert run(folder3, repo3, old3, new3) == 1 and 'README.md' in capsys.readouterr().err
    assert run(folder3, repo3, old3, new3, '--ignore-eol') == 0
    capsys.readouterr()
    listing = json.loads((folder3 / 'listing-review.json').read_text(encoding='utf-8'))
    assert listing['commit'] == new3
    assert listing['evidence'][-1].endswith('byte-identical after CRLF->LF normalization (EOL-only: README.md)')
    # --ignore-eol never accepts LF -> CRLF or a mode-only change (identical bytes, 100644 -> 100755).
    repo4 = tmp_path / 'repo4'
    old4, new4 = candidate_repo(repo4, {'shell/styles.css': '.a {}\r\n'}, executable=['README.md'])
    assert git(repo4, 'diff', '--summary', old4, new4).stdout.decode().count('mode change 100644 => 100755 README.md') == 1
    problems = refused_only(fresh('evidence4', old4), repo4, old4, new4, '--ignore-eol')
    assert sorted(p.split(':')[0] for p in problems) == ['R15_cleanroom.yml', 'R16_readme_review.yml', 'listing-review.json']
    assert all(p.endswith(('shell/styles.css', 'README.md')) for p in problems), problems
    # Short or unknown commits are refused before anything is read.
    assert run(folder3, repo3, new3[:12], new3) == 1 and 'full 40-hex' in capsys.readouterr().err
    assert run(folder3, repo3, 'c' * 40, new3) == 1 and 'commit not found' in capsys.readouterr().err
