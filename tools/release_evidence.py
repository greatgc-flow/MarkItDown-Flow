"""Release schemas validate supplied evidence, never certify the recorded claims."""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.request import urlopen

from build_engine import SUBJECTS
OSES = {'windows', 'macos', 'linux'}
REHEARSAL = {'fresh_install', 'upgrade_from_1_0_8', 'rollback', 'consent_dismiss', 'consent_approve',
             'mixed_document_mock_ocr', 'warm_rerun', 'cancel_restart', 'terminal_env_launch', 'commands', 'en_ko'}
POSTDEPLOY = {'install_via_listing', 'version_check', 'sanitized_migration', 'local_conversion',
              'offline_mock_ocr', 'restart', 'pending_failure_display', 'warm_rerun'}
EXTRA_FILES = ('oracles.json', 'actions-review.json', 'pkg04_core_artifacts.json', 'listing-review.json')
TARGETS = tuple(f'{runner}:{arch}:py{py}' for runner, arch in (
    ('windows-2022', 'x64'), ('ubuntu-24.04', 'x64'), ('macos-26', 'arm64')) for py in ('3.10', '3.14'))
ACTION_CHECKS = {'ownership', 'workflow_permissions'}
LISTING_CHECKS = {'identity', 'manifest_versions', 'description', 'commands', 'desktop_only', 'readme_disclosures'}


def action_pins(root: Path) -> dict[str, str]:
    """The reviewed table owns the pins; all workflow uses must agree with it."""
    text = (root / 'docs/renewal/25_PACKAGING.md').read_text(encoding='utf-8')
    pins = dict(re.findall(r'^\| `(actions/[\w-]+)`[^\n]*?\[`([0-9a-f]{40})`\]', text, re.M))
    if len(pins) != 6:
        raise ValueError('expected six pinned-SHA table entries')
    for path in (root / '.github').rglob('*.yml'):
        for ref in re.findall(r'^\s*-?\s*uses:\s*([^\s#]+)', path.read_text(encoding='utf-8'), re.M):
            if ref.startswith('./'):
                continue
            action, _, sha = ref.partition('@')
            if pins.get(action) != sha:
                raise ValueError(f'unreviewed action SHA: {ref}')
    return pins


def review_record(data, expected_commit, problems, *, verdict=True):
    from trace import peer_identity
    data = required(data, ('reviewer', 'date', 'commit', 'evidence') + (('verdict',) if verdict else ()), problems)
    named(data, problems)
    if not peer_identity(data.get('reviewer')):
        problems.append('reviewer must name peer/profile/model')
    if not re.fullmatch('[0-9a-f]{40}', expected_commit or '') or data.get('commit') != expected_commit:
        problems.append('review must bind the candidate commit')
    if verdict and data.get('verdict') != 'PASS':
        problems.append('peer PASS verdict required')
    if (not isinstance(data.get('evidence'), list) or not data['evidence'] or
            any(not isinstance(v, str) or not v.strip() for v in data['evidence'])):
        problems.append('nonempty evidence references required')
    return data


def validate_extra(filename: str, data, expected_commit: str, *, root: Path, executions: Path | None = None) -> list[str]:
    """Validate exact evidence contracts; machine identity is distinct from peer review."""
    problems = []
    if filename not in EXTRA_FILES:
        return ['unknown evidence filename']
    if re.search(r'<[A-Z][A-Z0-9 /_.-]*>|\bTODO\b', json.dumps(data)):
        problems.append('unfilled evidence placeholders')
    if not isinstance(data, dict):
        return problems + ['expected an object']
    if filename == 'oracles.json':
        identities = {f'G-{i:02d}' for i in range(1, 18)}
        review_record(data, expected_commit, problems, verdict=False)
        if set(data) != identities | {'reviewer', 'date', 'commit', 'evidence', 'spot_checks', 'generator_commit'}:
            problems.append('all 17 command-oracle receipts required exactly once')
        spots = data.get('spot_checks')
        if (not isinstance(spots, list) or any(not isinstance(s, str) or s not in identities for s in spots)
                or len(set(spots)) < 3):
            problems.append('at least 3 distinct valid oracle spot_checks required')
        if data.get('generator_commit') != expected_commit:
            problems.append('generator commit must bind the candidate commit')
        for identity in sorted(identities):
            row = required(data.get(identity), ('command', 'stdout', 'exit', 'expected', 'commit', 'sources'), problems)
            if (type(row.get('exit')) is not int or row['exit'] != 0 or
                    not isinstance(row.get('command'), str) or not row['command'].strip() or
                    not isinstance(row.get('stdout'), str) or not row['stdout'].strip() or
                    not isinstance(row.get('expected'), str) or not row['expected'].strip() or
                    row.get('commit') != expected_commit):
                problems.append(f'{identity}: candidate-bound successful receipt summary required')
            sources = row.get('sources')
            if not isinstance(sources, list) or not sources:
                problems.append(f'{identity}: source receipts required')
                continue
            paths = []
            for source in sources:
                if not isinstance(source, dict):
                    problems.append(f'{identity}: invalid source receipt')
                    continue
                name = source.get('path')
                if (not isinstance(name, str) or not re.fullmatch(r'(?:junit-[\w.-]+\.xml|junit-contract-max\.json|(?:registry|collection)-[\w.-]+\.json)', name)):
                    problems.append(f'{identity}: invalid source receipt path')
                    continue
                paths.append(name)
                try:
                    if executions is None:
                        raise ValueError('raw receipt directory required')
                    path = executions / name
                    if not path.resolve().is_relative_to(executions.resolve()):
                        raise ValueError('source receipt outside evidence')
                    if source.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
                        raise ValueError('source receipt hash mismatch')
                except (OSError, ValueError) as error:
                    problems.append(f'{identity}: {error}')
            junits = [p for p in paths if p.startswith('junit-') and p.endswith('.xml')]
            companions = {p.replace('junit-', prefix, 1).removesuffix('.xml') + '.json'
                          for p in junits for prefix in ('registry-', 'collection-')}
            extras = {'junit-contract-max.json'} & set(paths)
            if not junits or set(paths) != set(junits) | companions | extras or len(paths) != len(set(paths)):
                problems.append(f'{identity}: complete unique JUnit/registry/collection sources required')
        return problems
    review_record(data, expected_commit, problems)
    if filename == 'actions-review.json':
        pins = action_pins(root)
        rows = data.get('actions', [])
        if not isinstance(rows, list):
            return problems + ['actions must be a list']
        if len(rows) != len(pins) or {r.get('action') for r in rows if isinstance(r, dict)} != set(pins):
            problems.append('review every pinned action exactly once')
        for row in rows:
            if not isinstance(row, dict):
                problems.append('invalid action review')
                continue
            sha = pins.get(row.get('action'))
            verification = row.get('verification', {})
            if (not sha or row.get('sha') != sha or not isinstance(verification, dict) or
                    verification.get('command') != f"gh api repos/{row.get('action')}/commits/{sha}" or
                    type(verification.get('exit')) is not int or verification['exit'] != 0 or
                    not isinstance(verification.get('stdout'), dict) or verification['stdout'].get('sha') != sha):
                problems.append('action SHA verification missing or different from the table')
            checks(row, ACTION_CHECKS, problems)
            if not isinstance(row.get('evidence'), list) or not row['evidence']:
                problems.append('per-action ownership/workflow permissions review references required')
    elif filename == 'listing-review.json':
        if data.get('listing') != {'id': 'markitdown-flow', 'version': '2.0.0'}:
            problems.append('wrong candidate listing identity/version')
        checks(data, LISTING_CHECKS, problems)
    else:
        if data.get('package') != 'markitdown-gc' or data.get('version') != '0.3.7':
            problems.append('exact reference Core 0.3.7 required')
        if data.get('source') != 'https://pypi.org/pypi/markitdown-gc/0.3.7/json':
            problems.append('official PyPI JSON source required')
        artifacts = data.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            problems.append('PyPI artifact inventory required')
        else:
            names = []
            for item in artifacts:
                if not isinstance(item, dict):
                    problems.append('invalid Core artifact')
                    continue
                names.append(item.get('filename'))
                if (not isinstance(item.get('filename'), str) or
                        not str(item.get('url', '')).startswith('https://files.pythonhosted.org/') or
                        not re.fullmatch('[0-9a-f]{64}', str(item.get('sha256', ''))) or
                        type(item.get('size')) is not int or item['size'] <= 0 or
                        item.get('packagetype') not in {'bdist_wheel', 'sdist'} or item.get('yanked') is not False):
                    problems.append('invalid public artifact metadata/hash')
            if len(names) != len(set(names)):
                problems.append('duplicate Core artifact')
            if not any(isinstance(i, dict) and i.get('packagetype') == 'bdist_wheel' for i in artifacts):
                problems.append('public Core wheel required')
        checks(data, {'artifact_licenses'}, problems)
        reports = data.get('install_reports', [])
        if not isinstance(reports, list):
            return problems + ['install_reports must be a list']
        if len(reports) != 6 or {r.get('target') for r in reports if isinstance(r, dict)} != set(TARGETS):
            problems.append('six required target pip reports required')
        for run in reports:
            if not isinstance(run, dict):
                problems.append('invalid install report')
                continue
            if run.get('commit') != expected_commit or type(run.get('exit')) is not int or run['exit'] != 0:
                problems.append('candidate-bound successful install required')
            items = run.get('report', {}).get('install', [])
            core = [i.get('metadata', {}) for i in items if i.get('metadata', {}).get('name') == 'markitdown-gc']
            if len(core) != 1 or not re.fullmatch(r'0\.3\.(?:[7-9]|[1-9][0-9]+)', core[0].get('version', '')):
                problems.append('resolved compatible markitdown-gc required')
            for item in items:
                metadata, download = item.get('metadata', {}), item.get('download_info', {})
                if (not metadata.get('name') or not metadata.get('version') or
                        not str(download.get('url', '')).startswith(('https://', 'file://')) or
                        not re.fullmatch('[0-9a-f]{64}', str(download.get('archive_info', {}).get('hashes', {}).get('sha256', '')))):
                    problems.append('resolved distribution metadata/URL/hash required')
    return problems


def gh_json(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint], text=True))


def pypi_json(version):
    with urlopen(f'https://pypi.org/pypi/markitdown-gc/{version}/json', timeout=30) as response:
        return json.load(response)


def generate_oracles(root: Path, executions: Path, expected_commit: str, peer: dict) -> dict:
    """Summarize validated CI receipts; peer spot checks are supplied independently."""
    from trace import oracle_receipts, execution_registry_path, collection_path
    result = {k: peer[k] for k in ('reviewer', 'date', 'commit', 'evidence', 'spot_checks') if k in peer}
    result['generator_commit'] = expected_commit
    gates = oracle_receipts(root, executions, expected_commit, defer_release=True)
    if len(gates) != 17 or any(g['result'] == 'FAIL' for g in gates):
        raise ValueError('incomplete or failed candidate CI oracle receipts')
    for gate in gates:
        sources = []
        for name in gate['sources']:
            paths = [executions / name]
            if name.endswith('.xml'):
                paths += [execution_registry_path(executions, name), collection_path(executions, name)]
            for path in paths:
                sources.append(dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        result[gate['id']] = dict(commit=expected_commit, exit=0, result=gate['result'],
            command='tools/release_evidence.py produce: evaluate CI receipts for ' + gate['id'],
            stdout=f"{gate['result']}: {len(gate['tests'])} test ids evaluated across {len(gate['sources'])} candidate CI receipts",
            expected=gate['expected'], sources=sources)
    return result


def produce_extras(root: Path, source: Path, output: Path, expected_commit: str, *, executions: Path):
    """Enrich supplied peer reviews with API facts and existing CI receipts, never write verdicts."""
    records = {n: json.loads((source / n).read_text(encoding='utf-8')) for n in EXTRA_FILES}
    records['oracles.json'] = generate_oracles(root, executions, expected_commit, records['oracles.json'])
    actions = records['actions-review.json']
    pins = action_pins(root)
    for row in actions['actions']:
        action = row['action']
        sha = pins[action]
        if row.get('sha') != sha:
            raise ValueError(f'peer reviewed a different action SHA: {action}')
        endpoint = f'repos/{action}/commits/{sha}'
        actual = gh_json(endpoint)
        if actual.get('sha') != sha:
            raise ValueError(f'GitHub action SHA differs: {action}')
        row['verification'] = dict(command=f'gh api {endpoint}', stdout={'sha': actual['sha']}, exit=0)
    pkg = records['pkg04_core_artifacts.json']
    catalog = pypi_json('0.3.7')
    if catalog['info']['name'] != 'markitdown-gc' or catalog['info']['version'] != '0.3.7':
        raise ValueError('PyPI returned another Core')
    pkg.update(package='markitdown-gc', version='0.3.7', source='https://pypi.org/pypi/markitdown-gc/0.3.7/json',
               artifacts=[dict(filename=i['filename'], url=i['url'], sha256=i['digests']['sha256'],
                               size=i['size'], packagetype=i['packagetype'], yanked=i['yanked']) for i in catalog['urls']])
    pkg['install_reports'] = []
    for runner, platform, arch in (('windows-2022', 'win32', 'x64'), ('ubuntu-24.04', 'linux', 'x64'),
                                   ('macos-26', 'darwin', 'arm64')):
        for py in ('3.10', '3.14'):
            runtime = json.loads((executions / f'runtime-{runner}-py{py}.json').read_text(encoding='utf-8'))
            if runtime.get('commit') != expected_commit or runtime.get('installed') is not True:
                raise ValueError('install report runtime is not candidate-bound')
            report = json.loads((executions / f'install-{platform}-py{py}-compat-env.json').read_text(encoding='utf-8'))
            target = f'{runner}:{arch}:py{py}'
            pkg['install_reports'].append(dict(target=target, commit=expected_commit, exit=0, report=report))
    for name, data in records.items():
        problems = validate_extra(name, data, expected_commit, root=root, executions=executions)
        if problems:
            raise ValueError(name + ': ' + '\n'.join(problems))
    output.mkdir(parents=True, exist_ok=True)
    retained = output / 'receipts'
    retained.mkdir(exist_ok=True)
    for name in {s['path'] for key, row in records['oracles.json'].items() if key.startswith('G-') for s in row['sources']}:
        shutil.copyfile(executions / name, retained / name)
    for name, data in records.items():
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

class CleanupRefused(Exception):
    """Verification, rollback-window, ownership or containment check failed."""

def required(data, keys, problems):
    if not isinstance(data, dict):
        problems.append('expected an object')
        return {}
    for key in keys:
        if key not in data or data[key] is None or data[key] == '':
            problems.append(f'missing {key}')
    return data

def named(data, problems):
    if not isinstance(data.get('reviewer'), str) or not data['reviewer'].strip():
        problems.append('named reviewer required')
    try:
        date.fromisoformat(data.get('date', ''))
    except (ValueError, TypeError):
        problems.append('invalid review date')

def commit(data, problems):
    if not re.fullmatch('[0-9a-f]{40}', str(data.get('commit', ''))):
        problems.append('commit must be a full SHA')

def assets(items, expected, problems, *, version=None, matching=False):
    if not isinstance(items, list):
        problems.append('missing asset inventory')
        return
    names = []
    for item in items:
        if not isinstance(item, dict):
            problems.append('invalid asset record')
            continue
        if not isinstance(item.get('asset'), str):
            problems.append('asset name must be a string')
            continue
        names.append(item['asset'])
        if not re.fullmatch('[0-9a-f]{64}', str(item.get('sha256', ''))):
            problems.append('invalid asset digest')
        if version and item.get('version') != version:
            problems.append('wrong restored asset version')
        if matching and item.get('matches_release') is not True:
            problems.append('installed asset differs from release')
    if len(names) != len(expected) or set(names) != set(expected):
        problems.append('asset inventory missing, duplicated or unexpected')

def checks(data, expected, problems, *, allow_failure=False):
    values = data.get('checks')
    if not isinstance(values, dict) or not expected <= values.keys():
        problems.append('required checks missing')
        return
    allowed = {'PASS', 'FAIL'} if allow_failure else {'PASS'}
    if any(values[k] not in allowed for k in expected):
        problems.append('check did not pass')

def validate_rehearsal(data: dict, *, minimum_version=None) -> list[str]:
    problems = []
    data = required(data, ('id', 'reviewer', 'date', 'commit', 'candidate_tag', 'manifest_version',
                           'versions_json_entry', 'runs', 'verdict'), problems)
    named(data, problems)
    commit(data, problems)
    if data.get('id') != 'MAN-04' or data.get('verdict') != 'PASS':
        problems.append('MAN-04 PASS verdict required')
    if any(data.get(k) != '2.0.0' for k in ('candidate_tag', 'manifest_version', 'versions_json_entry')):
        problems.append('all release versions must equal 2.0.0')
    cells = []
    for run in data.get('runs', []) if isinstance(data.get('runs'), list) else []:
        run = required(run, ('os', 'obsidian_channel', 'obsidian_version', 'python', 'engine', 'core', 'downloads', 'checks'), problems)
        if not all(isinstance(run.get(k), str) and run[k].strip() for k in
                   ('os', 'obsidian_channel', 'obsidian_version', 'python', 'engine', 'core')):
            problems.append('run identifiers and runtime versions must be nonempty strings')
            continue
        cells.append((run.get('os'), run.get('obsidian_channel')))
        if minimum_version and run.get('obsidian_channel') == 'minimum' and run.get('obsidian_version') != minimum_version:
            problems.append('MAN-04 minimum Obsidian version differs from candidate manifest')
        if run.get('engine') != '2.0.0' or run.get('core') != '0.3.7':
            problems.append('rehearsal must use the exact engine/Core')
        assets(run.get('downloads'), SUBJECTS, problems)
        checks(run, REHEARSAL, problems)
    if len(cells) != 6 or set(cells) != {(o, c) for o in OSES for c in ('minimum', 'current')}:
        problems.append('six distinct OS/application-channel runs required')
    return problems

def validate_postdeploy(data: dict) -> list[str]:
    problems = []
    data = required(data, ('listing', 'commit', 'installed_assets', 'environments', 'critical_failed', 'rollback_triggered'), problems)
    commit(data, problems)
    if data.get('listing') != {'id': 'markitdown-flow', 'version': '2.0.0'}:
        problems.append('wrong listing identity/version')
    assets(data.get('installed_assets'), SUBJECTS[:-1], problems, matching=True)
    cells, failed = [], False
    for env in data.get('environments', []) if isinstance(data.get('environments'), list) else []:
        env = required(env, ('os', 'vault', 'app_version', 'python', 'unexpected_egress', 'checks'), problems)
        if not all(isinstance(env.get(k), str) and env[k].strip() for k in ('os', 'vault', 'app_version', 'python')):
            problems.append('environment identifiers and versions must be nonempty strings')
            continue
        cells.append((env.get('os'), env.get('vault')))
        if type(env.get('unexpected_egress')) is not int or env['unexpected_egress'] != 0:
            problems.append('unexpected egress')
        checks(env, POSTDEPLOY, problems, allow_failure=True)
        failed |= isinstance(env.get('checks'), dict) and any(v == 'FAIL' for v in env['checks'].values())
    if len(cells) != 6 or set(cells) != {(o, v) for o in OSES for v in ('clean', 'upgrade')}:
        problems.append('six distinct OS/vault environments required')
    if type(data.get('critical_failed')) is not bool or type(data.get('rollback_triggered')) is not bool:
        problems.append('failure flags must be boolean')
    if failed and data.get('critical_failed') is not True:
        problems.append('failed check must be declared critical')
    if (failed or data.get('critical_failed')) and data.get('rollback_triggered') is not True:
        problems.append('critical failure requires rollback/hotfix procedure')
    return problems

def validate_rollback(data: dict) -> list[str]:
    problems = []
    data = required(data, ('reviewer', 'date', 'vault', 'restored_assets', 'data_v1_json', 'v1_preferences_recovered',
                           'v1_commands_recovered', 'secrets_exposed', 'schema2_data_fed_to_v1',
                           'manual_credential_reconfiguration', 'runtime_rollback'), problems)
    named(data, problems)
    vault = required(data.get('vault'), ('isolated', 'label'), problems)
    if vault.get('isolated') is not True:
        problems.append('rollback vault must be isolated')
    assets(data.get('restored_assets'), SUBJECTS[:3], problems, version='1.0.8')
    settings = required(data.get('data_v1_json'), ('sanitized', 'secrets_present'), problems)
    if settings.get('sanitized') is not True or settings.get('secrets_present') is not False:
        problems.append('restored snapshot must be sanitized')
    for key, expected in (('v1_preferences_recovered', True), ('v1_commands_recovered', True),
                           ('secrets_exposed', False), ('schema2_data_fed_to_v1', False)):
        if data.get(key) is not expected:
            problems.append(f'invalid {key}')
    runtime = required(data.get('runtime_rollback'), ('previous_venv_selected', 'incompatible_interpreter_rejected'), problems)
    if any(runtime.get(k) is not True for k in ('previous_venv_selected', 'incompatible_interpreter_rejected')):
        problems.append('retained interpreter must pass rollback checks')
    if (not isinstance(data.get('manual_credential_reconfiguration'), list) or
            any(not isinstance(v, str) or not v.strip() for v in data.get('manual_credential_reconfiguration', []))):
        problems.append('credential reconfiguration must be recorded explicitly')
    return problems

def _owned_path(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not re.fullmatch(r'transport-[A-Za-z0-9_.-]+\.tmp|wrapper\.[A-Za-z0-9_.-]+', name):
        raise CleanupRefused(f'not an owned retired artifact: {name!r}')
    path = root / name
    if path.is_symlink() or path.resolve().parent != root or (path.exists() and not path.is_file()):
        raise CleanupRefused(f'unsafe cleanup path: {path}')
    return path

def plan_cleanup(plugin_dir: Path, owned: list[str], *, verified_at: datetime | None, now: datetime,
                 live: frozenset[str] = frozenset()) -> list[Path]:
    if verified_at is None or verified_at.tzinfo is None or now.tzinfo is None or now < verified_at + timedelta(days=7):
        raise CleanupRefused('successful post-deploy verification and seven-day rollback window required')
    root = Path(plugin_dir).resolve(strict=True)
    paths = [_owned_path(root, name) for name in owned]
    return sorted({p for p in paths if p.name not in live and p.exists()})

def execute_cleanup(plugin_dir: Path, plan: list[Path], *, log: Path) -> dict:
    root = Path(plugin_dir).resolve(strict=True)
    paths = []
    for raw in plan:
        path = Path(raw)
        if path.parent != root:
            raise CleanupRefused(f'plan outside plugin directory: {path}')
        paths.append(_owned_path(root, path.name))
    log = Path(log).absolute()
    if log.is_relative_to(root) or log.is_symlink():
        raise CleanupRefused('cleanup log must be outside the protected plugin directory')
    log.parent.mkdir(parents=True, exist_ok=True)
    # Establish a durable plan record before any removal; log failures leave all targets intact.
    log.write_text(json.dumps({'planned': [str(p) for p in paths], 'removed': [],
                               'retained': sorted(str(p) for p in root.rglob('*') if p.is_file())},
                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    removed = []
    for path in sorted(set(paths)):
        _owned_path(root, path.name).unlink(missing_ok=True)
        removed.append(str(path))
    retained = sorted(str(p) for p in root.rglob('*') if p.is_file())
    result = {'removed': removed, 'retained': retained}
    log.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='kind', required=True)
    for kind in ('rehearsal', 'postdeploy', 'rollback'):
        commands.add_parser(kind).add_argument('record', type=Path)
    produce = commands.add_parser('produce', help='enrich peer templates with GitHub/PyPI facts and CI pip reports')
    produce.add_argument('--source', type=Path, required=True)
    produce.add_argument('--output', type=Path, required=True)
    produce.add_argument('--executions', type=Path, required=True)
    produce.add_argument('--commit', required=True)
    args = parser.parse_args(argv)
    if args.kind == 'produce':
        produce_extras(Path(__file__).resolve().parents[1], args.source, args.output, args.commit, executions=args.executions)
        print('Four extra evidence files validated; peer verdicts preserved.')
        return 0
    source = args.record.read_text(encoding='utf-8')
    try:
        record = json.loads(source)
    except ValueError:
        import yaml  # requirements-build.txt; never an engine runtime dependency
        record = yaml.safe_load(source)
    problems = globals()[f'validate_{args.kind}'](record)
    print('\n'.join(problems) if problems else 'Schema valid; claims require independent verification.')
    return int(bool(problems))

if __name__ == '__main__':
    raise SystemExit(main())
