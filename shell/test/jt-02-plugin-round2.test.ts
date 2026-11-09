/**
 * Whole-plugin behaviour fixed in MECE round 2 (Fable M2):
 *  - JT-03/JT-05 X-03: a newer or unparseable settings file is read-only; no
 *    settings-tab or history write ever overwrites it;
 *  - JT-10 X-04: the interpreter field commits on blur/Enter, requires an
 *    absolute path and probes once (never partial paths while typing);
 *  - JT-04 X-13: run options (dpi, priority, max units, threshold, sensitive
 *    globs) are editable with SPEC 10.2 validation;
 *  - JT-02 X-05: a missing picker is reported, never a silent no-op;
 *  - JT-02 X-12: the selftest command explains the router retirement;
 *  - JT-02 X-15: onload does not block on the version probe;
 *  - JT-08 X-06: a drop opens the confirmation modal before any work.
 */
import { req } from './req';
import { asFake, asMockPlugin, type FakeElement, mockState } from './__mocks__/obsidian';
import { loadNodeApis } from '../src/process/node-apis';
import { dictionary } from '../src/pure/i18n';
import type { SettingsV2 } from '../src/pure/settings';
import { DropConfirmModal } from '../src/ui/drop-confirm-modal';
import { HistoryModal } from '../src/ui/history-modal';
import { dataJsonText, defaultScript, fakeApis, loadPluginWith, tick } from './fixtures/plugin-harness';
import { abs, ENGINE_PYTHON, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R2 = req('REQ-SHL-02');
const R3 = req('REQ-SHL-03');
const R4 = req('REQ-SHL-04');
const R5 = req('REQ-SHL-05');
const R8 = req('REQ-SHL-08');
const R10 = req('REQ-SHL-10');

const EN = dictionary('en');
const mocked = jest.mocked(loadNodeApis);

/** A read-only plugin keeps default settings (`locale: auto`), so its texts follow the host language: accept either dictionary. */
function anyLocale(key: string): string[] {
  return [dictionary('en')[key], dictionary('ko')[key]];
}
function containsAnyLocale(text: string, key: string): boolean {
  return anyLocale(key).some((t) => text.includes(t));
}
function noticesWith(key: string): string[] {
  return mockState.notices.filter((n) => anyLocale(key).includes(n));
}
const OTHER_PYTHON = process.platform === 'win32' ? 'C:\\mdflow-venvs\\2.0.1\\Scripts\\python.exe' : '/home/alice/mdflow-venvs/2.0.1/bin/python';

beforeEach(() => {
  mockState.reset();
  mocked.mockReset();
});

function displayTab(plugin: Parameters<typeof asMockPlugin>[0]): FakeElement {
  const tab = asMockPlugin(plugin).settingTabs[0];
  tab.display();
  return asFake(tab.containerEl);
}

/** The first control element of the setting whose name equals `label`. */
function controlFor(container: FakeElement, label: string): FakeElement {
  const item = container.findAll((e) => e.hasClass('setting-item') && e.findAll((n) => n.hasClass('setting-item-name') && n.textContent === label).length > 0)[0];
  if (!item) throw new Error(`no setting named ${label}`);
  const control = item.findAll((e) => e.hasClass('setting-item-control'))[0];
  const el = control?.children[0];
  if (!el) throw new Error(`no control for ${label}`);
  return el;
}

function persisted(): SettingsV2 {
  return JSON.parse(dataJsonText() ?? 'null') as SettingsV2;
}

it(R3('JT-03 a newer settings schema is read-only in the UI: the tab shows the incompatibility notice and offers no editable control'), async () => {
  const future = JSON.stringify({ schemaVersion: 3, enginePython: '/opt/venv/bin/python', future: true });
  const { plugin } = await loadPluginWith(mocked, future);
  expect(noticesWith('shell.migration.incompatible')).toHaveLength(1);
  const container = displayTab(plugin);
  expect(containsAnyLocale(container.textContent, 'shell.settings.readOnly')).toBe(true);
  expect(container.findAll((e) => e.tagName === 'input' || e.tagName === 'select')).toEqual([]);
  expect(dataJsonText()).toBe(future);
  plugin.unload();
});

it(R3('JT-03 clearing history while a newer schema is on disk refuses with shell.SETTINGS and leaves the file byte-identical'), async () => {
  const future = JSON.stringify({ schemaVersion: 3, conversionHistory: [{ inputFile: 'x', outputFile: 'y', timestamp: 1, success: true }] });
  const { plugin } = await loadPluginWith(mocked, future);
  expect(asMockPlugin(plugin).runCommand('view-conversion-history')).toBe(true);
  await tick();
  const modal = mockState.openModals[0];
  expect(modal).toBeInstanceOf(HistoryModal);
  const before = noticesWith('shell.SETTINGS').length;
  asFake(modal.contentEl).findAll((e) => e.tagName === 'button')[0]?.click();
  await tick();
  expect(dataJsonText()).toBe(future);
  expect(noticesWith('shell.SETTINGS')).toHaveLength(before + 1);
  plugin.unload();
});

it(R5('JT-05 an unparseable settings file is never overwritten by a later settings-tab or history write'), async () => {
  const broken = '{ "schemaVersion": 2, "enginePython": "/opt/venv/bin/python", ';
  const { plugin } = await loadPluginWith(mocked, broken);
  expect(noticesWith('shell.SETTINGS')).toHaveLength(1);
  const container = displayTab(plugin);
  expect(containsAnyLocale(container.textContent, 'shell.settings.readOnly')).toBe(true);
  expect(container.findAll((e) => e.tagName === 'input' || e.tagName === 'select')).toEqual([]);
  expect(asMockPlugin(plugin).runCommand('view-conversion-history')).toBe(true);
  await tick();
  asFake(mockState.openModals[0].contentEl).findAll((e) => e.tagName === 'button')[0]?.click();
  await tick();
  expect(dataJsonText()).toBe(broken);
  expect(noticesWith('shell.SETTINGS')).toHaveLength(2);
  plugin.unload();
});

it(R10('JT-10 the interpreter field never saves or probes while typing; it commits on blur or Enter, only for an absolute path, with exactly one version probe'), async () => {
  const { plugin, apis } = await loadPluginWith(mocked, settingsV2());
  await tick();
  const baselineSpawns = apis.spawner.requests.length;
  const container = displayTab(plugin);
  const input = controlFor(container, EN['shell.settings.enginePython']);
  expect(input.tagName).toBe('input');
  for (const partial of [OTHER_PYTHON.slice(0, 3), OTHER_PYTHON.slice(0, 12), OTHER_PYTHON.slice(0, -4)]) {
    input.value = partial;
    input.dispatchEvent({ type: 'input' });
    await tick();
  }
  expect(apis.spawner.requests).toHaveLength(baselineSpawns);
  expect(persisted().enginePython).toBe(ENGINE_PYTHON);
  // Relative values are refused even on commit.
  input.value = 'venv/bin/python';
  input.dispatchEvent({ type: 'blur' });
  await tick();
  expect(apis.spawner.requests).toHaveLength(baselineSpawns);
  expect(persisted().enginePython).toBe(ENGINE_PYTHON);
  // Absolute value committed on blur: one save, one `version` probe of exactly that interpreter.
  input.value = OTHER_PYTHON;
  input.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().enginePython).toBe(OTHER_PYTHON);
  const probes = apis.spawner.requests.slice(baselineSpawns);
  expect(probes).toHaveLength(1);
  expect(probes[0].command).toBe(OTHER_PYTHON);
  expect(probes[0].args).toEqual(['-m', 'mdflow', 'version']);
  // Enter commits too; an unchanged value does not probe again.
  input.dispatchEvent({ type: 'keydown', key: 'Enter' });
  await tick();
  expect(apis.spawner.requests).toHaveLength(baselineSpawns + 1);
  input.value = ENGINE_PYTHON;
  input.dispatchEvent({ type: 'keydown', key: 'Enter' });
  await tick();
  expect(persisted().enginePython).toBe(ENGINE_PYTHON);
  expect(apis.spawner.requests).toHaveLength(baselineSpawns + 2);
  for (const request of apis.spawner.requests) expect(request.args).toEqual(['-m', 'mdflow', 'version']);
  plugin.unload();
});

it(R10('JT-10 the output folder commits on blur with vault-relative validation and never while typing'), async () => {
  const { plugin } = await loadPluginWith(mocked, settingsV2());
  const container = displayTab(plugin);
  const input = controlFor(container, EN['shell.settings.outputPath']);
  input.value = 'notes/conv';
  input.dispatchEvent({ type: 'input' });
  await tick();
  expect(persisted().outputPath).toBe('markitdown-output');
  input.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().outputPath).toBe('notes/conv');
  input.value = '../outside';
  input.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().outputPath).toBe('notes/conv');
  plugin.unload();
});

it(R4('JT-04 run options are editable in the settings tab with SPEC 10.2 validation: dpi, priority, max units, threshold and sensitive globs'), async () => {
  const { plugin } = await loadPluginWith(mocked, settingsV2());
  const container = displayTab(plugin);
  const dpi = controlFor(container, EN['shell.settings.dpi']);
  expect(dpi.tagName).toBe('select');
  dpi.value = '300';
  dpi.dispatchEvent({ type: 'change' });
  await tick();
  expect(persisted().runOptions.dpi).toBe(300);
  const priority = controlFor(container, EN['shell.settings.minPriority']);
  priority.value = 'normal';
  priority.dispatchEvent({ type: 'change' });
  await tick();
  expect(persisted().runOptions.minPriority).toBe('normal');
  const maxUnits = controlFor(container, EN['shell.settings.maxUnits']);
  maxUnits.value = '50';
  maxUnits.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().runOptions.maxUnits).toBe(50);
  maxUnits.value = '-5';
  maxUnits.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().runOptions.maxUnits).toBe(50);
  const threshold = controlFor(container, EN['shell.settings.approveThreshold']);
  threshold.value = '0';
  threshold.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().runOptions.approveThreshold).toBe(0);
  threshold.value = 'ten';
  threshold.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().runOptions.approveThreshold).toBe(0);
  const sensitive = controlFor(container, EN['shell.settings.sensitive']);
  sensitive.value = ' */hr/* \n*.key,  ';
  sensitive.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().runOptions.sensitive).toEqual(['*/hr/*', '*.key']);
  sensitive.value = '';
  sensitive.dispatchEvent({ type: 'blur' });
  await tick();
  expect(persisted().runOptions.sensitive).toEqual([]);
  // Persisted keys stay the schema-2 allowlist; nothing else was added.
  expect(Object.keys(persisted().runOptions).sort()).toEqual(['approveThreshold', 'dpi', 'maxUnits', 'minPriority', 'sensitive']);
  plugin.unload();
});

it(R2('JT-02 when no file picker is available the convert commands and the ribbon report it instead of doing nothing'), async () => {
  const apis = fakeApis(defaultScript, { pickerAvailable: false });
  const { plugin } = await loadPluginWith(mocked, settingsV2(), apis);
  await tick();
  const before = apis.spawner.requests.length;
  const mock = asMockPlugin(plugin);
  expect(mock.runCommand('convert-file')).toBe(true);
  await tick();
  expect(mock.runCommand('convert-folder')).toBe(true);
  await tick();
  asFake(mock.ribbons[0].el).click();
  await tick();
  expect(mockState.notices.filter((n) => n === EN['shell.notice.pickerUnavailable'])).toHaveLength(3);
  expect(apis.spawner.requests).toHaveLength(before);
  expect(plugin.coordinator?.active).toBe(false);
  plugin.unload();
});

it(R2('JT-02 the selftest command explains the router retirement before invoking the engine selftest'), async () => {
  const { plugin } = await loadPluginWith(mocked, settingsV2());
  expect(asMockPlugin(plugin).runCommand('run-image-pipeline-selftest')).toBe(true);
  await tick();
  expect(mockState.notices).toContain(EN['shell.notice.selftestRouter']);
  expect(dictionary('ko')['shell.notice.selftestRouter']?.length).toBeGreaterThan(0);
  plugin.unload();
});

it(R2('JT-02 onload completes and registers every command while the version probe is still running'), async () => {
  const apis = fakeApis((request) => (request.args[2] === 'version' ? { blocked: true, cooperative: 'ignore', exit: { code: 0, signal: null } } : defaultScript(request)));
  const started = Date.now();
  const { plugin } = await loadPluginWith(mocked, settingsV2(), apis);
  expect(Date.now() - started).toBeLessThan(1000);
  expect(asMockPlugin(plugin).commands).toHaveLength(6);
  expect(apis.spawner.requests.map((r) => r.args[2])).toEqual(['version']);
  expect(apis.spawner.children[0].alive).toBe(true);
  apis.spawner.children[0].terminate();
  await tick();
  plugin.unload();
});

it(R8('JT-08 a local-file drop opens the confirmation modal and submits only after Convert'), async () => {
  const { plugin, apis } = await loadPluginWith(mocked, settingsV2({ enableDragDrop: true }));
  await tick();
  const before = apis.spawner.requests.length;
  const container = asFake(asMockPlugin(plugin).app.workspace.containerEl);
  const file = abs(VAULT_ROOT, 'inbox', 'a.pdf');
  container.dispatchEvent({ type: 'drop', dataTransfer: { files: [{ path: file, name: 'a.pdf' }], types: ['Files'] } });
  await tick();
  expect(mockState.openModals).toHaveLength(1);
  const modal = mockState.openModals[0];
  expect(modal).toBeInstanceOf(DropConfirmModal);
  expect(asFake(modal.contentEl).textContent).toContain(file);
  expect(apis.spawner.requests).toHaveLength(before);
  asFake(modal.contentEl).findAll((e) => e.tagName === 'button' && e.textContent === EN['shell.drop.convert'])[0]?.click();
  await tick();
  expect(apis.spawner.requests.slice(before).map((r) => r.args[2])).toEqual(['run']);
  expect(apis.spawner.requests[before].args).toContain(file);
  await plugin.coordinator?.current;
  plugin.unload();
});
