/**
 * JT-02 / REQ-SHL-02: exactly the six frozen local command ids without the
 * plugin prefix; one `Platform.isDesktop` guard precedes every registration
 * and all Node API access (simulated mobile registers nothing, loads no Node
 * API, spawns nothing); `convert-url` makes zero engine/network calls;
 * history and log commands work without Python.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { req, REPO_ROOT } from './req';
import { asMockPlugin, createApp, mockState, simulateDesktop, simulateMobile, testManifest } from './__mocks__/obsidian';
import { loadNodeApis, type NodeApis } from '../src/process/node-apis';
import { dictionary } from '../src/pure/i18n';
import { COMMAND_IDS } from '../src/ui/commands';
import { HistoryModal } from '../src/ui/history-modal';
import MarkItDownFlowPlugin from '../src/main';
import { FakeFs } from './fixtures/fake-fs';
import { FakeSpawner } from './fixtures/fake-spawner';
import { HOME, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R = req('REQ-SHL-02');

interface FakeApis extends NodeApis {
  spawner: FakeSpawner;
  openedFolders: string[];
}

function fakeApis(): FakeApis {
  const openedFolders: string[] = [];
  return {
    spawner: new FakeSpawner(() => ({ exit: { code: 0, signal: null } })),
    fs: new FakeFs({ directories: [VAULT_ROOT] }),
    openFolder: async (folder) => {
      openedFolders.push(folder);
    },
    writeClipboard: async () => undefined,
    pickFiles: async () => null,
    pickFolder: async () => null,
    homeDir: () => HOME,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    openedFolders,
  };
}

const loadNodeApisMock = jest.mocked(loadNodeApis);

async function loadPlugin(settings = settingsV2()): Promise<{ plugin: MarkItDownFlowPlugin; apis: FakeApis }> {
  const apis = fakeApis();
  loadNodeApisMock.mockImplementation(() => apis);
  mockState.vaultRoot = VAULT_ROOT;
  const text = JSON.stringify(settings);
  mockState.data = JSON.parse(text);
  mockState.adapterFiles.set('.obsidian/plugins/markitdown-flow/data.json', text);
  mockState.adapterFolders.add('.obsidian/plugins/markitdown-flow');
  const plugin = new MarkItDownFlowPlugin(createApp(), testManifest());
  await plugin.onload();
  return { plugin, apis };
}

beforeEach(() => {
  mockState.reset();
  loadNodeApisMock.mockReset();
  simulateDesktop();
});

it(R('JT-02 desktop registration snapshot equals the six inventory ids with no embedded plugin prefix; manifest keeps id and isDesktopOnly'), async () => {
  const { plugin } = await loadPlugin();
  const registered = asMockPlugin(plugin).commands.map((c) => c.id);
  expect([...registered].sort()).toEqual([...COMMAND_IDS].sort());
  expect(registered).toHaveLength(6);
  for (const id of registered) {
    expect(id.startsWith('markitdown-flow:')).toBe(false);
    expect(id).not.toContain(':');
  }
  for (const command of asMockPlugin(plugin).commands) expect(typeof (command.callback ?? command.checkCallback)).toBe('function');
  expect(plugin.desktopActive).toBe(true);
  expect(plugin.coordinator).not.toBeNull();
  const manifest = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'manifest.json'), 'utf8')) as { id: string; isDesktopOnly: boolean; version: string };
  expect(manifest.id).toBe('markitdown-flow');
  expect(manifest.isDesktopOnly).toBe(true);
  expect(manifest.version).toBe('2.0.0');
  plugin.onunload();
});

it(R('JT-02 simulated mobile: no commands, ribbon, settings tab or workspace listeners; no Node API load; no spawn'), async () => {
  simulateMobile();
  const { plugin, apis } = await loadPlugin();
  const mock = asMockPlugin(plugin);
  expect(mock.commands).toEqual([]);
  expect(mock.ribbons).toEqual([]);
  expect(mock.settingTabs).toEqual([]);
  expect(mock.app.workspace.listenerCount('file-menu')).toBe(0);
  expect(mock.app.workspace.listenerCount('files-menu')).toBe(0);
  expect(loadNodeApisMock).not.toHaveBeenCalled();
  expect(apis.spawner.requests).toEqual([]);
  expect(plugin.desktopActive).toBe(false);
  expect(plugin.coordinator).toBeNull();
  expect(mockState.notices.length).toBeLessThanOrEqual(1);
  plugin.onunload();
});

it(R('JT-02 the desktop guard is a single Platform.isDesktop check in main.ts and Node APIs are loaded only through node-apis'), () => {
  const src = path.join(REPO_ROOT, 'shell', 'src');
  const stripComments = (text: string): string => text.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  const main = stripComments(fs.readFileSync(path.join(src, 'main.ts'), 'utf8'));
  expect(main.match(/Platform\.isDesktop/g) ?? []).toHaveLength(1);
  expect(main).not.toMatch(/Platform\.isMobile/);
  // No other file guards on its own: one entry guard, not one per registration (SHL-REV-01 rejected).
  const files = fs.readdirSync(src, { recursive: true, encoding: 'utf8' }).filter((f) => f.endsWith('.ts')).map((f) => path.join(src, f));
  for (const file of files) {
    if (path.basename(file) === 'main.ts') continue;
    expect({ file, guards: (stripComments(fs.readFileSync(file, 'utf8')).match(/Platform\.is(Desktop|Mobile)/g) ?? []).length }).toEqual({ file, guards: 0 });
  }
  const allowedNodeImporters = new Set([path.join(src, 'process', 'node-apis.ts'), path.join(src, 'process', 'node-spawner.ts')]);
  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8');
    if (allowedNodeImporters.has(file)) continue;
    expect({ file, nodeImport: /from\s+['"]node:|require\(\s*['"](node:|electron|child_process|fs|os)/.test(text) }).toEqual({ file, nodeImport: false });
    expect({ file, electron: /from\s+['"]electron['"]/.test(text) }).toEqual({ file, electron: false });
  }
  // Node modules are required lazily, never at module top level, so a mobile import loads nothing.
  for (const file of allowedNodeImporters) {
    const text = fs.readFileSync(file, 'utf8');
    expect({ file, topLevelNodeImport: /^import\s[^;]*from\s+['"](node:|electron)/m.test(text) }).toEqual({ file, topLevelNodeImport: false });
  }
});

it(R('JT-02 convert-url is a compatibility notice with zero engine and zero network calls'), async () => {
  const { plugin, apis } = await loadPlugin();
  const before = apis.spawner.requests.length;
  expect(asMockPlugin(plugin).runCommand('convert-url')).toBe(true);
  await new Promise<void>((resolve) => setImmediate(resolve));
  expect(mockState.notices).toContain(dictionary('en')['shell.LEGACY_URL']);
  expect(apis.spawner.requests).toHaveLength(before);
  expect(mockState.network).toEqual([]);
  expect(mockState.openModals).toEqual([]);
  plugin.onunload();
});

it(R('JT-02 history and log commands work without any Python interpreter and start no conversion'), async () => {
  const { plugin, apis } = await loadPlugin(settingsV2({
    enginePython: null,
    conversionHistory: [{ inputFile: 'old/report.pdf', outputFile: 'out/report.pdf.md', timestamp: 1700000000000, success: true }],
  }));
  expect(asMockPlugin(plugin).runCommand('view-conversion-history')).toBe(true);
  await new Promise<void>((resolve) => setImmediate(resolve));
  expect(mockState.openModals).toHaveLength(1);
  expect(mockState.openModals[0]).toBeInstanceOf(HistoryModal);
  expect((mockState.openModals[0].contentEl as unknown as { textContent: string }).textContent).toContain('old/report.pdf');
  mockState.openModals[0].close();
  expect(asMockPlugin(plugin).runCommand('open-log-folder')).toBe(true);
  await new Promise<void>((resolve) => setImmediate(resolve));
  expect(apis.openedFolders).toHaveLength(1);
  const opened = apis.openedFolders[0].replace(/\\/g, '/');
  expect(opened.startsWith(VAULT_ROOT.replace(/\\/g, '/'))).toBe(true);
  expect(opened).toContain('/plugins/markitdown-flow/');
  expect(opened.endsWith('/logs')).toBe(true);
  expect(apis.spawner.requests).toEqual([]);
  expect(mockState.network).toEqual([]);
  plugin.onunload();
});

it(R('JT-02 unload removes every registration and leaves no owned engine; a reload registers exactly once'), async () => {
  const { plugin, apis } = await loadPlugin();
  const mock = asMockPlugin(plugin);
  expect(mock.ribbons).toHaveLength(1);
  plugin.onunload();
  mock.unload();
  expect(mock.commands).toEqual([]);
  expect(mock.ribbons).toEqual([]);
  expect(mock.app.workspace.listenerCount('file-menu')).toBe(0);
  expect(apis.spawner.children.every((c) => !c.alive)).toBe(true);
  const second = await loadPlugin();
  expect(asMockPlugin(second.plugin).commands).toHaveLength(6);
  expect(asMockPlugin(second.plugin).ribbons).toHaveLength(1);
  second.plugin.onunload();
});
