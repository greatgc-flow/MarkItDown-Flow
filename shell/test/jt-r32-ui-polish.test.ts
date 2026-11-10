/**
 * R32 UI polish (01_DECISIONS.md owner directives R31/R32), behaviour changes only:
 *  - JT-04: the settings tab groups every control under five headings with descriptions;
 *  - JT-14: the consent modal opens with a compact per-file summary table (file, class,
 *    units, destination, est. cost, status) and a Keep-pending primary / Approve secondary pair;
 *  - JT-09: a finished run presents one concise per-file result list from the decoded
 *    report (class label T/S/M, status, unit counts, issue codes), never success from files;
 *  - JT-07: the history modal is a readable table with distinct outcomes, Clear and Close;
 *  - JT-10/JT-17: exiftool status (R31) from an optional `version` field is surfaced in
 *    diagnostics and ignored by the gate;
 *  - JT-01: styles.css uses Obsidian CSS variables only and declares keyboard focus states.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { req } from './req';
import { asFake, asMockPlugin, createApp, fakeEl, type FakeElement, mockState } from './__mocks__/obsidian';
import { loadNodeApis } from '../src/process/node-apis';
import { dictionary, formatMessage } from '../src/pure/i18n';
import type { HistoryEntry } from '../src/pure/history';
import { parsePlanOutput, type Plan } from '../src/pure/protocol';
import type { SpawnRequest } from '../src/process/types';
import { evaluateVersionResponse, type VersionGate } from '../src/process/version-gate';
import { buildConsentView, ConsentModal } from '../src/ui/consent-modal';
import { type CoordinatorDeps, ShellCoordinator } from '../src/ui/coordinator';
import { HistoryModal } from '../src/ui/history-modal';
import { JobStatusBar } from '../src/ui/progress';
import { buildResultsView, ResultsModal, type ResultsViewModel } from '../src/ui/results-modal';
import { SetupModal } from '../src/ui/setup-modal';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit, fx71Json, fx71Manifest, fx71Text } from './fixtures/fx71';
import { loadPluginWith } from './fixtures/plugin-harness';
import { abs, ENGINE_PYTHON, HOME, HOST_ENV, KEY_VALUE, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R1 = req('REQ-SHL-01');
const R4 = req('REQ-SHL-04');
const R7 = req('REQ-SHL-07');
const R9 = req('REQ-SHL-09');
const R10 = req('REQ-SHL-10');
const R14 = req('REQ-SHL-14');
const R17 = req('REQ-SHL-17');

const EN = dictionary('en');
const KO = dictionary('ko');
const DEST = '/home/alice/Vault/markitdown-output';
const mocked = jest.mocked(loadNodeApis);

beforeEach(() => {
  mockState.reset();
  mocked.mockReset();
});

function plans(name: string): Plan[] {
  const decoded = parsePlanOutput(fx71Text(name));
  if (!decoded.ok) throw new Error(decoded.reason);
  return decoded.value;
}

function cellsOf(table: FakeElement): string[][] {
  return table
    .findAll((e) => e.tagName === 'tr' && e.children.some((c) => c.tagName === 'td'))
    .map((row) => row.findAll((c) => c.tagName === 'td').map((c) => c.textContent));
}

function headersOf(table: FakeElement): string[] {
  return table.findAll((e) => e.tagName === 'th').map((e) => e.textContent);
}

// ----------------------------------------------------------------------------- JT-04 settings sections

it(R4('JT-04 the settings tab groups every control under five headings (Engine, Conversion, OCR provider, Consent & privacy, Advanced) with short descriptions (R32)'), async () => {
  const { plugin } = await loadPluginWith(mocked, settingsV2());
  const tab = asMockPlugin(plugin).settingTabs[0];
  tab.display();
  const container = asFake(tab.containerEl);
  const items = container.findAll((e) => e.hasClass('setting-item'));
  const nameOf = (item: FakeElement): string => item.findAll((n) => n.hasClass('setting-item-name'))[0]?.textContent ?? '';
  const descOf = (item: FakeElement): string => item.findAll((n) => n.hasClass('setting-item-description'))[0]?.textContent ?? '';
  const headings = items.filter((e) => e.hasClass('setting-item-heading'));
  const sectionKeys = ['engine', 'conversion', 'provider', 'consent', 'advanced'];
  expect(headings.map(nameOf)).toEqual(sectionKeys.map((k) => EN[`shell.settings.section.${k}`]));
  for (const heading of headings) expect(descOf(heading).trim().length).toBeGreaterThan(0);
  // The first item is a heading: no control floats above its section.
  expect(items[0].hasClass('setting-item-heading')).toBe(true);
  const sectionOf = (label: string): number => {
    let section = -1;
    for (const item of items) {
      if (item.hasClass('setting-item-heading')) section += 1;
      else if (nameOf(item) === label) return section;
    }
    throw new Error(`no setting named ${label}`);
  };
  const expected: Record<string, number> = {
    enginePython: 0, openSetup: 0,
    outputPath: 1, enableRecursiveConversion: 1, enableLegacyPreconvert: 1, enableContextMenu: 1, enableDragDrop: 1, enableBatchProgress: 1, locale: 1,
    provider: 2, model: 2, baseUrl: 2,
    approveThreshold: 3, sensitive: 3,
    dpi: 4, minPriority: 4, maxUnits: 4,
  };
  for (const [key, section] of Object.entries(expected)) {
    expect({ key, section: sectionOf(EN[`shell.settings.${key}`]) }).toEqual({ key, section });
  }
  // Every non-heading item is one of the known controls; nothing new (no LLM settings, R29).
  const labels = items.filter((e) => !e.hasClass('setting-item-heading')).map(nameOf);
  expect(labels.sort()).toEqual(Object.keys(expected).map((k) => EN[`shell.settings.${k}`]).sort());
  for (const k of sectionKeys) {
    expect(KO[`shell.settings.section.${k}`]?.length).toBeGreaterThan(0);
    expect(KO[`shell.settings.section.${k}Desc`]?.length).toBeGreaterThan(0);
  }
  // R29: no markitdown LLM/caption setting exists (the migration notice for the removed v1 `llmApiKey` is not a setting).
  expect(Object.keys(EN).filter((k) => k.startsWith('shell.settings.')).join(' ').toLowerCase()).not.toMatch(/llm|caption/);
  expect(labels.join(' ').toLowerCase()).not.toMatch(/llm|caption/);
  plugin.unload();
});

// ----------------------------------------------------------------------------- JT-14 consent summary table

it(R14('JT-14 the consent modal opens with a compact per-file summary table (file, class, units, destination, est. cost, status) and a Keep-pending primary / Approve secondary pair (R32)'), () => {
  const view = buildConsentView(plans('plan-mixed.stdout.json'), DEST);
  expect(view.files.map((f) => f.label)).toEqual(['M', 'T', 'M', 'S']);
  expect(view.fileCount).toBe(4);
  expect(view.consentCount).toBe(3);
  const modal = new ConsentModal(createApp(), view, 'en');
  modal.open();
  const content = asFake(modal.contentEl);
  const tables = content.findAll((e) => e.tagName === 'table' && e.hasClass('mdflow-consent-summary'));
  expect(tables).toHaveLength(1);
  expect(headersOf(tables[0])).toEqual(['file', 'label', 'units', 'destination', 'cost', 'status'].map((k) => EN[`shell.consent.col.${k}`]));
  const cells = cellsOf(tables[0]);
  expect(cells).toHaveLength(4);
  expect(cells[0]).toEqual(['b c.docx', 'M', '2', 'https://api.openai.com/v1/chat/completions', EN['shell.consent.unknownCost'], EN['shell.consent.status.needsConsent']]);
  expect(cells[1][0]).toBe('memo.txt');
  expect(cells[1][1]).toBe('T');
  expect(cells[1][5]).toBe(EN['shell.consent.status.informational']);
  expect(cells[3][1]).toBe('S');
  expect(content.textContent).toContain(formatMessage('en', 'shell.consent.scope', { consent: '3', count: '4' }));
  // Full per-file Plan fields (hashes, DPI, budget) remain available inside collapsible details.
  expect(content.findAll((e) => e.tagName === 'details')).toHaveLength(4);
  for (const file of view.files) {
    expect(content.textContent).toContain(file.planHash);
    expect(content.textContent).toContain(file.sha256);
  }
  const buttons = content.findAll((e) => e.tagName === 'button');
  const keep = buttons.find((b) => b.textContent === EN['shell.consent.keepPending']);
  const approve = buttons.find((b) => b.textContent === EN['shell.consent.approve']);
  if (!keep || !approve) throw new Error('both decision buttons must be rendered');
  expect(keep.hasClass('mod-cta')).toBe(true);
  expect(approve.hasClass('mod-cta')).toBe(false);
  expect(approve.hasClass('mdflow-consent-approve')).toBe(true);
  // Class legend covers every SPEC 3.2 label in both languages.
  for (const label of ['T', 'S', 'M', 'U', 'C', 'L', 'P', 'X']) {
    expect(EN[`shell.label.${label}`]?.length).toBeGreaterThan(0);
    expect(KO[`shell.label.${label}`]?.length).toBeGreaterThan(0);
  }
  expect(content.textContent).toContain(EN['shell.label.M']);
  modal.close();
});

// ----------------------------------------------------------------------------- JT-09 per-file results

const INPUT_ROOT = abs(VAULT_ROOT, 'inbox');
const OUT = abs(VAULT_ROOT, 'markitdown-output');
const ENABLED_GATE: VersionGate = { enabled: true, info: { ...fx71Manifest().engine, protocol: 1, triage_schema: 1 } };

function recordedRun(stem: string): ScriptedChild {
  return {
    stderr: chunksOf(fx71Bytes(`${stem}.progress.jsonl`), 2048),
    stdout: chunksOf(fx71Bytes(`${stem}.stdout.json`), 8192),
    exit: { code: fx71Exit(`${stem}.stdout.json`), signal: null },
  };
}

function coordinatorWith(script: (request: SpawnRequest) => ScriptedChild, results: ResultsViewModel[]): { coordinator: ShellCoordinator; notices: string[]; el: FakeElement } {
  const fsOps = new FakeFs({ directories: [VAULT_ROOT, OUT, INPUT_ROOT, PLUGIN_DIR] });
  const notices: string[] = [];
  const el = asFake(fakeEl('div'));
  const deps: CoordinatorDeps = {
    spawner: new FakeSpawner(script),
    fs: fsOps,
    spoolFs: new FakeSpoolFs(fsOps, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    settings: () => settingsV2(),
    gate: () => ENABLED_GATE,
    consent: async () => ({ approved: false }),
    notify: (key) => {
      notices.push(key);
    },
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
    progress: new JobStatusBar(el as unknown as HTMLElement, { locale: () => 'en', showDetails: () => true, onCancel: () => undefined }),
    results: (view) => {
      results.push(view);
    },
  };
  return { coordinator: new ShellCoordinator(deps), notices, el };
}

it(R9('JT-09 a finished run presents one concise per-file result list from the decoded report: class label (T/S/M), status, unit counts and issue codes, never success from created files (R32)'), async () => {
  const results: ResultsViewModel[] = [];
  const h = coordinatorWith(() => recordedRun('run-mixed'), results);
  await h.coordinator.submit({ kind: 'folder', paths: [INPUT_ROOT] }, 'command');
  await h.coordinator.current;
  expect(results).toHaveLength(1);
  const view = results[0];
  expect(view.outcome).toBe('partial_failure');
  expect(view.rows.map((r) => [r.path, r.label, r.status])).toEqual([
    ['b c.docx', 'M', 'pending'],
    ['memo.txt', 'T', 'ok'],
    ['sub/a.pdf', 'M', 'pending'],
    ['보고서/3분기 결산.pdf', 'S', 'pending'],
    ['broken.pdf', 'U', 'failed'],
    ['empty.pdf', 'X', 'failed'],
    ['garbled.docx', 'U', 'failed'],
  ]);
  // Units: done = cached + transcribed (SPEC 7.4); garbled.docx has an output file yet is failed (E_CONVERT_FAIL), broken.pdf has none.
  expect(view.rows[0].units).toEqual({ done: 0, pending: 2, failed: 0 });
  expect(view.rows[6].issueCodes).toEqual(['W_UNRESOLVED_EMBED', 'W_REVIEW_PRIORITY', 'W_TRIAGE_PARTIAL', 'E_CONVERT_FAIL', 'W_MEDIA_UNMAPPED']);
  expect(view.rows[6].outputs).toBe(1);
  expect(view.rows[4].outputs).toBe(0);
  expect(view.skipped).toEqual([{ path: '.DS_Store', code: 'W_SKIPPED_HIDDEN' }]);
  // The list is derived from the report, not from progress events or disk: the pure projection agrees.
  const run = (await h.coordinator.current)?.run;
  if (!run?.stdout?.ok) throw new Error('report expected');
  expect(buildResultsView(run.stdout.value, run.outcome)).toEqual(view);
  // Status bar is empty again once the job ended (REQ-SHL-16), the list lives in its own modal.
  expect(h.el.textContent).toBe('');
  const modal = new ResultsModal(createApp(), view, 'en');
  modal.open();
  const content = asFake(modal.contentEl);
  const table = content.findAll((e) => e.tagName === 'table' && e.hasClass('mdflow-results-table'))[0];
  expect(headersOf(table)).toEqual(['file', 'label', 'status', 'units', 'issues'].map((k) => EN[`shell.results.col.${k}`]));
  const cells = cellsOf(table);
  expect(cells).toHaveLength(7);
  expect(cells[1][0]).toBe('memo.txt');
  expect(cells[1][1]).toBe('T');
  expect(cells[1][2]).toBe(EN['shell.results.status.ok']);
  expect(cells[6][2]).toBe(EN['shell.results.status.failed']);
  expect(cells[6][4]).toContain('E_CONVERT_FAIL');
  expect(content.textContent).toContain(EN['shell.history.outcome.partial_failure']);
  expect(content.textContent).toContain(formatMessage('en', 'shell.results.skipped', { count: '1' }));
  // Status is an outcome word, never a markup or a raw engine message; Korean strings exist.
  for (const key of ['shell.results.title', 'shell.results.status.ok', 'shell.results.status.pending', 'shell.results.status.failed']) {
    expect(KO[key]?.length).toBeGreaterThan(0);
  }
  modal.close();
});

it(R9('JT-09 a cancelled or report-less run presents no result list (nothing is invented) (R32)'), async () => {
  const results: ResultsViewModel[] = [];
  const h = coordinatorWith(() => ({ blocked: true, exit: { code: 0, signal: null } }), results);
  await h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  await flush();
  h.coordinator.cancel();
  await h.coordinator.current;
  expect(results).toEqual([]);
  expect(h.notices).toContain('shell.CANCELLED');
});

// ----------------------------------------------------------------------------- JT-07 history table

it(R7('JT-07 the history modal renders one row per entry with time, outcome, input and output columns, pending/cancelled visibly distinct from success, plus Clear (first) and Close (R32)'), async () => {
  const entries: HistoryEntry[] = [
    { inputFile: 'inbox/a.pdf (+2)', outputFile: 'markitdown-output', timestamp: Date.UTC(2026, 10, 9, 3, 4, 5), success: true, outcome: 'complete' },
    { inputFile: 'inbox/b.pdf', outputFile: 'markitdown-output', timestamp: Date.UTC(2026, 10, 8, 1, 2, 3), success: false, outcome: 'pending_consent' },
    { inputFile: 'inbox/c.pdf', outputFile: 'markitdown-output', timestamp: Date.UTC(2026, 10, 7, 0, 0, 0), success: false, outcome: 'cancelled' },
    { inputFile: 'old/legacy.docx', outputFile: 'notes/legacy.docx.md', timestamp: Date.UTC(2025, 0, 1), success: false },
  ];
  let cleared = 0;
  const modal = new HistoryModal(createApp(), entries, 'en', async () => {
    cleared += 1;
  });
  modal.open();
  const content = asFake(modal.contentEl);
  const table = content.findAll((e) => e.tagName === 'table' && e.hasClass('mdflow-history-table'));
  expect(table).toHaveLength(1);
  expect(headersOf(table[0])).toEqual(['time', 'outcome', 'input', 'output'].map((k) => EN[`shell.history.col.${k}`]));
  const cells = cellsOf(table[0]);
  expect(cells).toHaveLength(4);
  for (const row of cells) expect(row[0]).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  expect(cells.map((r) => r[1])).toEqual([
    EN['shell.history.outcome.complete'], EN['shell.history.outcome.pending_consent'], EN['shell.history.outcome.cancelled'], EN['shell.history.outcome.legacy'],
  ]);
  expect(cells[0][2]).toBe('inbox/a.pdf (+2)');
  expect(cells[3][3]).toBe('notes/legacy.docx.md');
  // Outcome cells carry a per-outcome class so themes can colour them without hard-coded colours.
  const outcomeCells = table[0].findAll((e) => e.tagName === 'td' && e.hasClass('mdflow-outcome'));
  expect(outcomeCells.map((c) => [...c.classes].filter((k) => k.startsWith('mdflow-outcome-')))).toEqual([
    ['mdflow-outcome-complete'], ['mdflow-outcome-pending_consent'], ['mdflow-outcome-cancelled'], ['mdflow-outcome-legacy'],
  ]);
  expect(content.textContent).toContain(formatMessage('en', 'shell.history.count', { count: '4' }));
  const buttons = content.findAll((e) => e.tagName === 'button');
  expect(buttons[0].textContent).toBe(EN['shell.history.clear']);
  expect(buttons[0].hasClass('mod-warning')).toBe(true);
  const close = buttons.find((b) => b.textContent === EN['shell.history.close']);
  if (!close) throw new Error('Close button expected');
  close.click();
  expect(mockState.openModals).not.toContain(modal);
  expect(cleared).toBe(0);
  for (const key of ['shell.history.col.time', 'shell.history.col.outcome', 'shell.history.col.input', 'shell.history.col.output', 'shell.history.close', 'shell.history.count']) {
    expect(KO[key]?.length).toBeGreaterThan(0);
  }
  const empty = new HistoryModal(createApp(), [], 'ko', async () => undefined);
  empty.open();
  expect(asFake(empty.contentEl).textContent).toContain(KO['shell.history.empty']);
  expect(asFake(empty.contentEl).findAll((e) => e.tagName === 'table')).toEqual([]);
  empty.close();
});

// ----------------------------------------------------------------------------- JT-10 / JT-17 exiftool status (R31)

function versionResponse(extra: Record<string, unknown>, omit: string[] = []): string {
  const base = { ...fx71Json<Record<string, unknown>>('version.json') };
  for (const key of ['exiftool', 'exiftool_status', 'exiftool_source', 'libreoffice', 'libreoffice_status', 'libreoffice_source']) delete base[key];
  Object.assign(base, extra);
  for (const key of omit) delete base[key];
  return JSON.stringify(base);
}

it(R17('JT-17 an optional `exiftool` field of the version response is admitted as diagnostics (string or null) and ignored by the gate; other shapes are dropped (R31)'), () => {
  const found = evaluateVersionResponse(versionResponse({ exiftool: '13.10' }));
  expect(found.enabled).toBe(true);
  if (found.enabled) expect(found.info.exiftool).toBe('13.10');
  const missing = evaluateVersionResponse(versionResponse({ exiftool: null }));
  expect(missing.enabled).toBe(true);
  if (missing.enabled) expect(missing.info.exiftool).toBeNull();
  const absent = evaluateVersionResponse(versionResponse({}, ['exiftool']));
  expect(absent.enabled).toBe(true);
  if (absent.enabled) {
    expect(absent.info).not.toHaveProperty('exiftool');
    const expected: Record<string, unknown> = { ...fx71Manifest().engine };
    for (const key of ['exiftool', 'exiftool_status', 'exiftool_source', 'libreoffice', 'libreoffice_status', 'libreoffice_source']) delete expected[key];
    expect(absent.info).toEqual(expected);
  }
  const odd = evaluateVersionResponse(versionResponse({ exiftool: 12 }));
  expect(odd.enabled).toBe(true);
  if (odd.enabled) expect(odd.info).not.toHaveProperty('exiftool');
});

function setupModalWith(stdout: string, clipboard: string[]): { modal: SetupModal; spawner: FakeSpawner } {
  const spawner = new FakeSpawner((request) => (request.command === ENGINE_PYTHON
    ? { stdout: [Buffer.from(stdout, 'utf8')], exit: { code: 0, signal: null } }
    : { spawnError: new Error('ENOENT'), exit: { code: null, signal: null } }));
  const modal = new SetupModal(createApp(), {
    spawner,
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
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

it(R10('JT-10 setup diagnostics surface the exiftool status reported by the engine: found with its version, missing (graceful), or not reported; still version probes only (R31/R32)'), async () => {
  const cases: [string, string][] = [
    [versionResponse({ exiftool: '13.10' }), '13.10'],
    [versionResponse({ exiftool: null }), EN['shell.setup.exiftoolMissing']],
    [versionResponse({}, ['exiftool']), EN['shell.setup.exiftoolUnknown']],
  ];
  for (const [stdout, expected] of cases) {
    const clipboard: string[] = [];
    const { modal, spawner } = setupModalWith(stdout, clipboard);
    modal.open();
    await modal.refresh();
    const rendered = asFake(modal.contentEl).textContent;
    const row = asFake(modal.contentEl).findAll((e) => e.hasClass('mdflow-setup-exiftool'));
    expect(row).toHaveLength(1);
    expect(row[0].textContent).toContain(EN['shell.setup.exiftool']);
    expect(row[0].textContent).toContain(expected);
    expect(rendered).not.toContain(KEY_VALUE);
    for (const request of spawner.requests) expect(request.args).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow', 'version']);
    // The copyable diagnostics mention exiftool only when the engine reported it.
    await modal.copyDiagnostics();
    expect(clipboard[0].includes('exiftool')).toBe(expected === '13.10' || expected === EN['shell.setup.exiftoolMissing']);
    modal.close();
  }
  expect(KO['shell.setup.exiftool']?.length).toBeGreaterThan(0);
  expect(KO['shell.setup.exiftoolMissing']?.length).toBeGreaterThan(0);
  expect(KO['shell.setup.exiftoolUnknown']?.length).toBeGreaterThan(0);
  // The engine runs exiftool only for standalone png/jpg/jpeg images, so the hint never promises audio metadata.
  expect(EN['shell.setup.exiftoolMissing']).toContain('image metadata');
  expect(EN['shell.setup.exiftoolMissing']).not.toMatch(/audio/i);
  expect(KO['shell.setup.exiftoolMissing']).toContain('이미지 메타데이터');
  expect(KO['shell.setup.exiftoolMissing']).not.toContain('오디오');
});

// ----------------------------------------------------------------------------- JT-01 styles

it(R1('JT-01 styles.css is Obsidian-native: colours come only from CSS variables, keyboard focus states are declared, and every rule targets plugin-prefixed classes (R32)'), () => {
  const css = fs.readFileSync(path.join(__dirname, '..', 'styles.css'), 'utf8');
  const noComments = css.replace(/\/\*[\s\S]*?\*\//g, '');
  // No hard-coded colours of any syntax.
  expect(noComments).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  expect(noComments).not.toMatch(/\b(rgb|rgba|hsl|hsla)\(/);
  expect(noComments).not.toMatch(/:\s*(white|black|red|green|blue|gray|grey|orange|yellow)\s*[;!]/i);
  for (const line of noComments.split('\n')) {
    const declaration = /^\s*(color|background(?:-color)?|border(?:-color)?|outline(?:-color)?)\s*:\s*(.+);/.exec(line);
    if (!declaration) continue;
    const value = declaration[2];
    expect({ line: line.trim(), usesVariable: /var\(--/.test(value) || /^(none|transparent|inherit|0|currentColor)\b/.test(value) }).toEqual({ line: line.trim(), usesVariable: true });
  }
  expect(noComments).toContain(':focus-visible');
  expect(noComments).toContain('--background-modifier-border-focus');
  // Every selector is scoped to the plugin (`.mdflow-…`), never to Obsidian globals or bare elements.
  const selectors = noComments.split('}').map((block) => block.split('{')[0].trim()).filter((s) => s.length > 0 && !s.startsWith('@'));
  for (const selector of selectors) {
    for (const part of selector.split(',')) {
      expect({ selector: part.trim(), scoped: /\.mdflow-/.test(part) }).toEqual({ selector: part.trim(), scoped: true });
    }
  }
  // Light and dark themes are served by the variables; no theme-specific overrides are hard-coded.
  expect(noComments).not.toMatch(/\.theme-(light|dark)/);
});
