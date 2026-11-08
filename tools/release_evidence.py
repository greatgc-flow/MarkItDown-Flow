"""Release schemas validate supplied evidence, never certify the recorded claims."""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re

SUBJECTS = ('main.js', 'manifest.json', 'styles.css', 'engine.zip', 'engine.lock', 'SHA256SUMS')
OSES = {'windows', 'macos', 'linux'}
REHEARSAL = {'fresh_install', 'upgrade_from_1_0_8', 'rollback', 'consent_dismiss', 'consent_approve',
             'mixed_document_mock_ocr', 'warm_rerun', 'cancel_restart', 'terminal_env_launch', 'commands', 'en_ko'}
POSTDEPLOY = {'install_via_listing', 'version_check', 'sanitized_migration', 'local_conversion',
              'offline_mock_ocr', 'restart', 'pending_failure_display', 'warm_rerun'}

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

def validate_rehearsal(data: dict) -> list[str]:
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
        if run.get('engine') != '2.0.0' or run.get('core') != '0.3.5':
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
    assets(data.get('installed_assets'), SUBJECTS[:5], problems, matching=True)
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
    parser.add_argument('kind', choices=('rehearsal', 'postdeploy', 'rollback'))
    parser.add_argument('record', type=Path)
    args = parser.parse_args(argv)
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
