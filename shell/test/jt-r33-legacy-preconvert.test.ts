/**
 * R33 shell side (01_DECISIONS.md R33, unanimous with amendments) and M5 residuals:
 *  - JT-04: `enableLegacyPreconvert` (off by default) is a schema-2 boolean shown in the
 *    Conversion section with a one-line explanation and the detected LibreOffice status;
 *  - JT-11/12: the flag reaches the engine as `--preconvert-legacy` (SPEC REQ-CNV-07) only when on;
 *    the tool location variables `SOFFICE_PATH`/`EXIFTOOL_PATH` are forwarded (paths, never secrets);
 *  - JT-17: optional `libreoffice*`/`exiftool_*` fields are diagnostics only; the co-install guard
 *    (SPEC REQ-GEN-12: `version` exits 1 with `E_CORE_CONFLICT`) blocks jobs with `core_conflict`;
 *  - JT-10: the SetupModal shows LibreOffice and exiftool status and the co-install guard error
 *    with the exact fix command;
 *  - JT-09: a pre-converted file (`W_PRECONVERTED{tool,version}`) is marked derived in the results
 *    list with the tool and version; `E_PRECONVERT`/`W_PRECONVERTED`/`E_CORE_CONFLICT` have en/ko text.
 *
 * `version` does not report LibreOffice in SPEC 10.1 yet: the `libreoffice`/`libreoffice_status`/
 * `libreoffice_source` names follow the R33 text and the exiftool precedent, and an engine that omits
 * them reads as "not reported".
 */
import { req } from './req';
import { asFake, asMockPlugin, createApp, type FakeElement, mockState } from './__mocks__/obsidian';
import { loadNodeApis } from '../src/process/node-apis';
import { APPROVED_BY_MODAL, buildSpawnRequest, LEGACY_PRECONVERT_OPTION, snapshotJob } from '../src/process/launcher';
import { collectSetupDiagnostics, renderUpstreamUninstall } from '../src/process/setup';
import type { SpawnRequest } from '../src/process/types';
import { CORE_CONFLICT_CODE, evaluateVersionResponse, probeVersion, startupErrorCode, type VersionGate } from '../src/process/version-gate';
import { scrubEngineEnv, TOOL_PATH_ENV_VARS } from '../src/pure/env';
import { dictionary, formatMessage } from '../src/pure/i18n';
import { decodeReport } from '../src/pure/protocol';
import { defaultSettings, migrateSettings } from '../src/pure/settings';
import { buildResultsView, ResultsModal } from '../src/ui/results-modal';
import { SetupModal } from '../src/ui/setup-modal';
import { FakeClock } from './fixtures/fake-clock';
import { FakeSpawner, type ScriptedChild, subcommandOf } from './fixtures/fake-spawner';
import { fx71Json } from './fixtures/fx71';
import { fakeApis, loadPluginWith, tick } from './fixtures/plugin-harness';
import { invocationViolations, SPEC_OPTIONS } from './fixtures/protocol';
import { abs, ENGINE_PYTHON, HOME, HOST_ENV, KEY_VALUE, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R4 = req('REQ-SHL-04');
const R6 = req('REQ-SHL-06');
const R9 = req('REQ-SHL-09');
const R10 = req('REQ-SHL-10');
const R11 = req('REQ-SHL-11', 'REQ-SHL-12');
const R17 = req('REQ-SHL-17');
const R19 = req('REQ-SHL-19');

const EN = dictionary('en');
const KO = dictionary('ko');
const mocked = jest.mocked(loadNodeApis);

beforeEach(() => {
  mockState.reset();
  mocked.mockReset();
});

function versionResponse(extra: Record<string, unknown>, omit: string[] = []): string {
  const base = { ...fx71Json<Record<string, unknown>>('version.json'), ...extra };
  for (const key of omit) delete base[key];
  return JSON.stringify(base);
}

const LIBREOFFICE_FOUND = { libreoffice: '24.8.2.1', libreoffice_status: 'ok', libreoffice_source: 'PATH' };
const LIBREOFFICE_MISSING = { libreoffice: 'unavailable', libreoffice_status: 'not_found', libreoffice_source: null };
/** The engine's exit-1 startup object for the co-install guard (cli._error / core_guard.check). */
const CONFLICT_STDERR = `${JSON.stringify({ error: { code: CORE_CONFLICT_CODE, message: 'E_CORE_CONFLICT: upstream markitdown is installed alongside markitdown-gc; remove markitdown or create a dedicated mdflow virtual environment.' } })}\n`;

// ----------------------------------------------------------------------------- JT-04 setting

it(R4('JT-04 enableLegacyPreconvert is a schema-2 boolean, off by default; non-boolean values reset with a notice item and no other key is added'), () => {
  expect(defaultSettings().enableLegacyPreconvert).toBe(false);
  const fresh = migrateSettings(null);
  expect(fresh.settings?.enableLegacyPreconvert).toBe(false);
  const on = migrateSettings({ ...settingsV2(), enableLegacyPreconvert: true });
  expect(on.settings?.enableLegacyPreconvert).toBe(true);
  expect(on.items).toEqual([]);
  const bad = migrateSettings({ ...settingsV2(), enableLegacyPreconvert: 'yes' });
  expect(bad.settings?.enableLegacyPreconvert).toBe(false);
  expect(bad.items).toContainEqual({ key: 'enableLegacyPreconvert', action: 'reset', count: 1 });
  // A v1 file never carried the key: the migrated candidate still has it, off.
  const v1 = migrateSettings({ pythonPath: '/usr/bin/python3', outputPath: 'notes' });
  expect(v1.settings?.enableLegacyPreconvert).toBe(false);
  expect(Object.keys(on.settings ?? {})).toContain('enableLegacyPreconvert');
});

function settingItems(container: FakeElement): { name: string; desc: string; heading: boolean; item: FakeElement }[] {
  return container.findAll((e) => e.hasClass('setting-item')).map((item) => ({
    name: item.findAll((n) => n.hasClass('setting-item-name'))[0]?.textContent ?? '',
    desc: item.findAll((n) => n.hasClass('setting-item-description'))[0]?.textContent ?? '',
    heading: item.hasClass('setting-item-heading'),
    item,
  }));
}

async function displayedTab(version: string, data = settingsV2()): Promise<{ items: ReturnType<typeof settingItems>; unload: () => void }> {
  const apis = fakeApis((request: SpawnRequest): ScriptedChild => (subcommandOf(request) === 'version'
    ? { stdout: [Buffer.from(version, 'utf8')], exit: { code: 0, signal: null } }
    : { exit: { code: 0, signal: null } }));
  const { plugin } = await loadPluginWith(mocked, data, apis);
  await tick(6);
  const tab = asMockPlugin(plugin).settingTabs[0];
  tab.display();
  return { items: settingItems(asFake(tab.containerEl)), unload: () => plugin.unload() };
}

it(R4('JT-04 the Conversion section shows a "Legacy formats (LibreOffice)" toggle, off by default, with a one-line explanation and the detected LibreOffice status (R33)'), async () => {
  const label = EN['shell.settings.enableLegacyPreconvert'];
  expect(label.toLowerCase()).toContain('libreoffice');
  for (const key of ['shell.settings.enableLegacyPreconvert', 'shell.settings.enableLegacyPreconvertNote', 'shell.settings.libreofficeStatus', 'shell.settings.libreofficeFound', 'shell.settings.libreofficeMissing', 'shell.settings.libreofficeUnknown']) {
    expect(EN[key]?.length).toBeGreaterThan(0);
    expect(KO[key]?.length).toBeGreaterThan(0);
  }
  const found = await displayedTab(versionResponse(LIBREOFFICE_FOUND));
  let section = -1;
  let seen: ReturnType<typeof settingItems>[number] | undefined;
  for (const entry of found.items) {
    if (entry.heading) section += 1;
    else if (entry.name === label) {
      seen = entry;
      break;
    }
  }
  if (!seen) throw new Error('legacy toggle missing');
  expect(section).toBe(1); // Conversion
  expect(seen.desc).toContain(EN['shell.settings.enableLegacyPreconvertNote']);
  expect(seen.desc).toContain(formatMessage('en', 'shell.settings.libreofficeStatus', { status: formatMessage('en', 'shell.settings.libreofficeFound', { version: '24.8.2.1' }) }));
  // Off by default: the toggle reflects the persisted value, never a guessed one.
  const toggle = seen.item.findAll((e) => e.hasClass('setting-item-control'))[0];
  expect(toggle).toBeDefined();
  found.unload();

  const missing = await displayedTab(versionResponse(LIBREOFFICE_MISSING));
  const missingEntry = missing.items.find((e) => e.name === label);
  expect(missingEntry?.desc).toContain(EN['shell.settings.libreofficeMissing']);
  missing.unload();

  const unknown = await displayedTab(versionResponse({}));
  const unknownEntry = unknown.items.find((e) => e.name === label);
  expect(unknownEntry?.desc).toContain(EN['shell.settings.libreofficeUnknown']);
  unknown.unload();
});

// ----------------------------------------------------------------------------- JT-11/12 flag and env

it(R11('JT-12 the flag reaches the engine as --preconvert-legacy (SPEC REQ-CNV-07) on plan and run only when the setting is on; the timeout keeps the engine default'), () => {
  expect(LEGACY_PRECONVERT_OPTION).toBe('--preconvert-legacy');
  expect(SPEC_OPTIONS).toContain(LEGACY_PRECONVERT_OPTION);
  const inputs = [abs(VAULT_ROOT, 'inbox', 'old.doc')];
  const common = { inputs, cwd: abs(HOME, 'venv'), outDir: abs(VAULT_ROOT, 'out'), cacheDir: abs(PLUGIN_DIR, 'cache') };
  const off = snapshotJob({ settings: settingsV2(), ...common });
  const on = snapshotJob({ settings: settingsV2({ enableLegacyPreconvert: true }), ...common });
  expect(off.legacyPreconvert).toBe(false);
  expect(on.legacyPreconvert).toBe(true);
  for (const command of ['plan', 'run'] as const) {
    expect(buildSpawnRequest(off, command, HOST_ENV).args).not.toContain(LEGACY_PRECONVERT_OPTION);
    const args = buildSpawnRequest(on, command, HOST_ENV).args;
    expect(args.filter((t) => t === LEGACY_PRECONVERT_OPTION)).toHaveLength(1);
    expect(args).not.toContain('--preconvert-timeout-s');
    expect(invocationViolations(buildSpawnRequest(on, command, HOST_ENV))).toEqual([]);
  }
  const authorized = buildSpawnRequest(on, 'run', HOST_ENV, { yesFile: abs(PLUGIN_DIR, 'consent', 'yes.txt'), approvedBy: APPROVED_BY_MODAL });
  expect(authorized.args).toContain(LEGACY_PRECONVERT_OPTION);
  expect(invocationViolations(authorized)).toEqual([]);
});

it(R6('JT-06 SOFFICE_PATH and EXIFTOOL_PATH (tool locations, never secrets) are forwarded to the engine for every provider; unrelated variables still are not'), () => {
  expect(TOOL_PATH_ENV_VARS).toEqual(['EXIFTOOL_PATH', 'SOFFICE_PATH']);
  const host = { ...HOST_ENV, SOFFICE_PATH: 'C:\\Program Files\\LibreOffice\\program\\soffice.exe', EXIFTOOL_PATH: '/opt/exiftool/exiftool', SOFFICE_OTHER: 'x' };
  for (const provider of ['none', 'openai-compatible'] as const) {
    const env = scrubEngineEnv(host, provider);
    expect(env.SOFFICE_PATH).toBe(host.SOFFICE_PATH);
    expect(env.EXIFTOOL_PATH).toBe(host.EXIFTOOL_PATH);
    expect(env).not.toHaveProperty('SOFFICE_OTHER');
    expect(env).not.toHaveProperty('PYTHONPATH');
  }
  expect(scrubEngineEnv(HOST_ENV, 'none')).not.toHaveProperty('SOFFICE_PATH');
  expect(scrubEngineEnv({ ...HOST_ENV, SOFFICE_PATH: '' }, 'none').SOFFICE_PATH).toBe('');
});

// ----------------------------------------------------------------------------- JT-17 version fields

it(R17('JT-17 optional libreoffice/exiftool status fields are diagnostics only ("unavailable" reads as missing); other shapes are dropped; the gate is unchanged'), () => {
  const found = evaluateVersionResponse(versionResponse({ ...LIBREOFFICE_FOUND, exiftool: '13.10', exiftool_status: 'ok', exiftool_source: 'EXIFTOOL_PATH' }));
  expect(found.enabled).toBe(true);
  if (found.enabled) {
    expect(found.info.libreoffice).toBe('24.8.2.1');
    expect(found.info.libreoffice_status).toBe('ok');
    expect(found.info.libreoffice_source).toBe('PATH');
    expect(found.info.exiftool).toBe('13.10');
    expect(found.info.exiftool_status).toBe('ok');
    expect(found.info.exiftool_source).toBe('EXIFTOOL_PATH');
  }
  const missing = evaluateVersionResponse(versionResponse({ ...LIBREOFFICE_MISSING, exiftool: 'unavailable', exiftool_status: 'not_found', exiftool_source: null }));
  expect(missing.enabled).toBe(true);
  if (missing.enabled) {
    expect(missing.info.libreoffice).toBeNull();
    expect(missing.info.libreoffice_status).toBe('not_found');
    expect(missing.info.libreoffice_source).toBeNull();
    expect(missing.info.exiftool).toBeNull();
    expect(missing.info.exiftool_status).toBe('not_found');
  }
  const odd = evaluateVersionResponse(versionResponse({ libreoffice: 24, libreoffice_status: 'great', libreoffice_source: 7, exiftool_status: 1 }));
  expect(odd.enabled).toBe(true);
  if (odd.enabled) {
    for (const key of ['libreoffice', 'libreoffice_status', 'libreoffice_source', 'exiftool_status']) expect(odd.info).not.toHaveProperty(key);
  }
  const absent = evaluateVersionResponse(versionResponse({}));
  expect(absent.enabled).toBe(true);
  if (absent.enabled) expect(absent.info).not.toHaveProperty('libreoffice');
});

async function probeWith(child: ScriptedChild): Promise<VersionGate> {
  const spawner = new FakeSpawner(() => child);
  return probeVersion(ENGINE_PYTHON, { spawner, clock: new FakeClock(), hostEnv: HOST_ENV, cwd: PLUGIN_DIR });
}

it(R17('JT-17 the co-install guard (SPEC REQ-GEN-12): `version` exiting 1 with E_CORE_CONFLICT on stderr blocks jobs with reason core_conflict; any other exit 1 stays `exit`'), async () => {
  expect(startupErrorCode(CONFLICT_STDERR)).toBe('E_CORE_CONFLICT');
  expect(startupErrorCode('{"error": {"code": "E_CORE_VERSION", "message": "x"}}')).toBe('E_CORE_VERSION');
  for (const text of ['', 'Traceback (most recent call last)', '{"error": {"message": "no code"}}', '{"v":1,"ev":"warning","code":"W_X"}\n{"error":{"code":"E_CORE_CONFLICT"}}', '[]', '{"error": {"code": "e_lower"}}']) {
    expect(startupErrorCode(text)).toBeNull();
  }
  const conflict = await probeWith({ stderr: [Buffer.from(CONFLICT_STDERR, 'utf8')], exit: { code: 1, signal: null } });
  expect(conflict.enabled).toBe(false);
  if (!conflict.enabled) {
    expect(conflict.reason).toBe('core_conflict');
    expect(conflict.diagnostic).toBe('shell.RUNTIME');
    expect(conflict.field).toBeUndefined();
  }
  const other = await probeWith({ stderr: [Buffer.from('{"error": {"code": "E_USAGE", "message": "x"}}\n', 'utf8')], exit: { code: 1, signal: null } });
  expect(!other.enabled && other.reason).toBe('exit');
  const silent = await probeWith({ exit: { code: 1, signal: null } });
  expect(!silent.enabled && silent.reason).toBe('exit');
  // A clean venv: the recorded response is unchanged by the guard.
  const clean = await probeWith({ stdout: [Buffer.from(versionResponse({}), 'utf8')], exit: { code: 0, signal: null } });
  expect(clean.enabled).toBe(true);
});

// ----------------------------------------------------------------------------- JT-10 SetupModal

function setupModalWith(stdout: string, clipboard: string[], engineChild?: ScriptedChild): { modal: SetupModal; spawner: FakeSpawner } {
  const spawner = new FakeSpawner((request) => (request.command === ENGINE_PYTHON
    ? engineChild ?? { stdout: [Buffer.from(stdout, 'utf8')], exit: { code: 0, signal: null } }
    : { spawnError: new Error('ENOENT'), exit: { code: null, signal: null } }));
  const modal = new SetupModal(createApp(), {
    spawner,
    clock: new FakeClock(),
    hostEnv: { ...HOST_ENV, SOFFICE_PATH: '/opt/libreoffice/program/soffice' },
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    cwd: PLUGIN_DIR,
    enginePython: ENGINE_PYTHON,
    home: HOME,
    vault: VAULT_ROOT,
    writeClipboard: async (text) => {
      clipboard.push(text);
    },
    locale: 'en',
  });
  return { modal, spawner };
}

it(R10('JT-10 setup diagnostics show LibreOffice status (found with version and source, missing, too old/unusable, or not reported) next to exiftool; still version probes only (R33)'), async () => {
  const cases: [string, string][] = [
    [versionResponse(LIBREOFFICE_FOUND), '24.8.2.1'],
    [versionResponse(LIBREOFFICE_MISSING), EN['shell.setup.libreofficeMissing']],
    [versionResponse({ libreoffice: 'unavailable', libreoffice_status: 'too_old', libreoffice_source: 'SOFFICE_PATH' }), EN['shell.setup.tool.too_old']],
    [versionResponse({ libreoffice: 'unavailable', libreoffice_status: 'unusable', libreoffice_source: 'PATH' }), EN['shell.setup.tool.unusable']],
    [versionResponse({}), EN['shell.setup.libreofficeUnknown']],
  ];
  for (const [stdout, expected] of cases) {
    const clipboard: string[] = [];
    const { modal, spawner } = setupModalWith(stdout, clipboard);
    modal.open();
    await modal.refresh();
    const content = asFake(modal.contentEl);
    const row = content.findAll((e) => e.hasClass('mdflow-setup-libreoffice'));
    expect(row).toHaveLength(1);
    expect(row[0].textContent).toContain(EN['shell.setup.libreoffice']);
    expect(row[0].textContent).toContain(expected);
    expect(content.findAll((e) => e.hasClass('mdflow-setup-exiftool'))).toHaveLength(1);
    // The exiftool "unavailable" spelling of the real engine reads as missing, not as a version.
    expect(content.textContent).not.toContain('unavailable');
    expect(content.textContent).not.toContain(KEY_VALUE);
    // Tool location variables are reported by presence only.
    expect(content.textContent).toContain('SOFFICE_PATH');
    expect(content.textContent).not.toContain('/opt/libreoffice');
    for (const request of spawner.requests) expect(request.args).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow', 'version']);
    await modal.copyDiagnostics();
    expect(clipboard[0].includes('libreoffice')).toBe(expected !== EN['shell.setup.libreofficeUnknown']);
    expect(clipboard[0]).not.toContain('/opt/libreoffice');
    modal.close();
  }
  for (const key of ['shell.setup.libreoffice', 'shell.setup.libreofficeMissing', 'shell.setup.libreofficeUnknown', 'shell.setup.tool.too_old', 'shell.setup.tool.unusable']) {
    expect(KO[key]?.length).toBeGreaterThan(0);
  }
});

it(R10('JT-10 the co-install guard: an upstream markitdown in the venv is shown as a blocking error with the exact uninstall command for that interpreter (R33c)'), async () => {
  const clipboard: string[] = [];
  const conflictChild: ScriptedChild = { stderr: [Buffer.from(CONFLICT_STDERR, 'utf8')], exit: { code: 1, signal: null } };
  const { modal } = setupModalWith('', clipboard, conflictChild);
  modal.open();
  await modal.refresh();
  const content = asFake(modal.contentEl);
  const warning = content.findAll((e) => e.hasClass('mdflow-setup-conflict'));
  expect(warning).toHaveLength(1);
  expect(warning[0].textContent).toContain(EN['shell.setup.upstreamConflict']);
  const fix = renderUpstreamUninstall(ENGINE_PYTHON, process.platform === 'win32' ? 'win32' : 'posix');
  expect(fix).toContain(ENGINE_PYTHON);
  expect(fix).toContain('-m pip uninstall -y markitdown');
  expect(fix).not.toContain('markitdown-gc');
  expect(warning[0].textContent).toContain(fix);
  expect(modal.diagnostics?.jobsEnabled).toBe(false);
  expect(modal.diagnostics?.conflictFix).toBe(fix);
  expect(content.textContent).toContain(formatMessage('en', 'shell.setup.probeBlocked', { reason: 'core_conflict' }));
  // The raw engine message is never rendered; only the code-keyed text and the fix command are.
  expect(content.textContent).not.toContain('dedicated mdflow virtual environment');
  // No conflict: no warning, no fix text.
  const { modal: clean } = setupModalWith(versionResponse({}), clipboard);
  clean.open();
  await clean.refresh();
  expect(asFake(clean.contentEl).findAll((e) => e.hasClass('mdflow-setup-conflict'))).toEqual([]);
  expect(asFake(clean.contentEl).textContent).not.toContain('pip uninstall');
  expect(clean.diagnostics?.conflictFix).toBeNull();
  // A different exit-1 startup error (or a silent exit 1) is a plain blocked probe without the uninstall text.
  const { modal: usage } = setupModalWith('', clipboard, { stderr: [Buffer.from('{"error":{"code":"E_USAGE","message":"x"}}\n', 'utf8')], exit: { code: 1, signal: null } });
  usage.open();
  await usage.refresh();
  expect(asFake(usage.contentEl).findAll((e) => e.hasClass('mdflow-setup-conflict'))).toEqual([]);
  expect(usage.diagnostics?.conflictFix).toBeNull();
  const diagnostics = await collectSetupDiagnostics({
    spawner: new FakeSpawner(() => conflictChild),
    clock: new FakeClock(), hostEnv: HOST_ENV, platform: 'posix', cwd: PLUGIN_DIR, enginePython: '/venvs/mdflow/bin/python',
  });
  expect(diagnostics.conflictFix).toBe("'/venvs/mdflow/bin/python' -m pip uninstall -y markitdown");
  expect(diagnostics.summary).toContain('core_conflict');
  expect(KO['shell.setup.upstreamConflict']?.length).toBeGreaterThan(0);
  expect(KO['shell.setup.upstreamConflictFix']?.length).toBeGreaterThan(0);
});

// ----------------------------------------------------------------------------- JT-09 results

type RawReport = { files: Record<string, unknown>[] };
type RawIssue = { code: string; message: string; tool?: unknown; version?: unknown };

it(R9('JT-09 a pre-converted file (W_PRECONVERTED with tool/version, SPEC REQ-CNV-07) is marked derived with the tool and version in the result list; native files are not marked (R33)'), () => {
  const raw = fx71Json<RawReport>('run-mixed.stdout.json');
  // The engine's exact issue shape (preconvert.prepare): tool and version beside code/message.
  (raw.files[0].issues as RawIssue[]).unshift({ code: 'W_PRECONVERTED', message: 'Converted locally with LibreOffice; fidelity is DERIVED.', tool: 'LibreOffice', version: '24.8.2' });
  const decoded = decodeReport(JSON.stringify(raw));
  if (!decoded.ok) throw new Error(decoded.reason);
  expect(decoded.value.files[0].issues[0]).toEqual({ code: 'W_PRECONVERTED', message: 'Converted locally with LibreOffice; fidelity is DERIVED.', tool: 'LibreOffice', version: '24.8.2' });
  expect(decoded.value.files[1].issues.every((i) => i.tool === undefined && i.version === undefined)).toBe(true);
  const view = buildResultsView(decoded.value, 'partial_failure');
  expect(view.rows[0].derived).toBe(true);
  expect(view.rows[0].derivedBy).toEqual({ tool: 'LibreOffice', version: '24.8.2' });
  expect(view.rows[0].issueCodes[0]).toBe('W_PRECONVERTED');
  expect(view.rows.slice(1).every((r) => r.derived === false && r.derivedBy === null)).toBe(true);
  // A numeric version (REQ-CNV-07 "numeric version") is shown as written; a warning without tool/version still marks the row.
  const variants = fx71Json<RawReport>('run-mixed.stdout.json');
  (variants.files[2].issues as RawIssue[]).push({ code: 'W_PRECONVERTED', message: 'x', tool: 'LibreOffice', version: 24.8 });
  (variants.files[3].issues as RawIssue[]).push({ code: 'W_PRECONVERTED', message: 'x' });
  const decodedVariants = decodeReport(JSON.stringify(variants));
  if (!decodedVariants.ok) throw new Error(decodedVariants.reason);
  const variantRows = buildResultsView(decodedVariants.value, 'partial_failure').rows;
  expect(variantRows[2].derivedBy).toEqual({ tool: 'LibreOffice', version: '24.8' });
  expect(variantRows[3]).toMatchObject({ derived: true, derivedBy: null });
  // An optional per-file `fidelity` string (frontmatter vocabulary) is decoded when present; any other type is a protocol fault.
  const withFidelity = fx71Json<RawReport>('run-mixed.stdout.json');
  withFidelity.files[0].fidelity = 'DERIVED';
  withFidelity.files[1].fidelity = 'NATIVE';
  const decodedFidelity = decodeReport(JSON.stringify(withFidelity));
  if (!decodedFidelity.ok) throw new Error(decodedFidelity.reason);
  expect(decodedFidelity.value.files.map((f) => f.fidelity)).toEqual(['DERIVED', 'NATIVE', undefined, undefined, undefined, undefined, undefined]);
  expect(buildResultsView(decodedFidelity.value, 'partial_failure').rows.map((r) => r.derived)).toEqual([true, false, false, false, false, false, false]);
  const badRaw = fx71Json<RawReport>('run-mixed.stdout.json');
  badRaw.files[0].fidelity = 7;
  expect(decodeReport(JSON.stringify(badRaw)).ok).toBe(false);
  // E_PRECONVERT (exit 2) is a failed row like every other E_ code.
  const failed = fx71Json<RawReport>('run-mixed.stdout.json');
  (failed.files[1].issues as RawIssue[]).push({ code: 'E_PRECONVERT', message: 'x' });
  const decodedFailed = decodeReport(JSON.stringify(failed));
  if (!decodedFailed.ok) throw new Error(decodedFailed.reason);
  expect(buildResultsView(decodedFailed.value, 'partial_failure').rows[1].status).toBe('failed');

  const modal = new ResultsModal(createApp(), view, 'en');
  modal.open();
  const content = asFake(modal.contentEl);
  const badges = content.findAll((e) => e.hasClass('mdflow-badge-derived'));
  expect(badges).toHaveLength(1);
  expect(badges[0].textContent).toBe(formatMessage('en', 'shell.results.derivedBy', { tool: 'LibreOffice', version: '24.8.2' }));
  expect(badges[0].textContent).toContain('LibreOffice 24.8.2');
  expect(badges[0].getAttr('title')).toBe(EN['shell.results.derivedHint']);
  const rows = content.findAll((e) => e.tagName === 'tr' && e.children.some((c) => c.tagName === 'td'));
  expect(rows[0].textContent).toContain('LibreOffice 24.8.2');
  expect(rows[1].textContent).not.toContain(EN['shell.results.derived']);
  expect(rows[0].textContent).toContain('W_PRECONVERTED');
  // The raw engine message is never rendered.
  expect(content.textContent).not.toContain('Converted locally with LibreOffice');
  modal.close();
  const plain = new ResultsModal(createApp(), buildResultsView(decodedVariants.value, 'partial_failure'), 'ko');
  plain.open();
  const plainBadges = asFake(plain.contentEl).findAll((e) => e.hasClass('mdflow-badge-derived'));
  expect(plainBadges.map((b) => b.textContent)).toEqual([formatMessage('ko', 'shell.results.derivedBy', { tool: 'LibreOffice', version: '24.8' }), KO['shell.results.derived']]);
  plain.close();
  for (const key of ['shell.results.derived', 'shell.results.derivedBy', 'shell.results.derivedHint']) expect(KO[key]?.length).toBeGreaterThan(0);
});

it(R19('JT-SHL-19-01 the R33 codes E_CORE_CONFLICT, E_PRECONVERT and W_PRECONVERTED have independent en/ko text that names the remedy or the derived fidelity'), () => {
  expect(EN['engine.W_PRECONVERTED']).toMatch(/LibreOffice|derived/i);
  expect(EN['engine.E_PRECONVERT']).toMatch(/LibreOffice/);
  expect(EN['engine.E_CORE_CONFLICT']).toMatch(/markitdown/);
  for (const code of ['W_PRECONVERTED', 'E_PRECONVERT', 'E_CORE_CONFLICT']) {
    expect(KO[`engine.${code}`]?.length).toBeGreaterThan(0);
    expect(KO[`engine.${code}`]).not.toBe(EN[`engine.${code}`]);
  }
});

it(R17('JT-17 a blocked core_conflict gate is a RUNTIME refusal like any other blocked gate; the recorded response itself is unchanged by the guard fields'), async () => {
  const gate: VersionGate = await probeWith({ stderr: [Buffer.from(CONFLICT_STDERR, 'utf8')], exit: { code: 1, signal: null } });
  expect(gate.enabled).toBe(false);
  if (!gate.enabled) expect(gate.diagnostic).toBe('shell.RUNTIME');
  expect(evaluateVersionResponse(versionResponse({})).enabled).toBe(true);
});
