/**
 * Whole-plugin harness over the obsidian mock: fake Node APIs (scripted spawner,
 * in-memory fs) and a loader that places `data.json` in the fake vault adapter.
 * Test files still call `jest.mock('../src/process/node-apis')` themselves.
 */
import type { NodeApis } from '../../src/process/node-apis';
import type { SpawnRequest } from '../../src/process/types';
import type { SettingsV2 } from '../../src/pure/settings';
import MarkItDownFlowPlugin from '../../src/main';
import { createApp, mockState, testManifest } from '../__mocks__/obsidian';
import { FakeFs } from './fake-fs';
import { FakeSpawner, type ScriptedChild, subcommandOf } from './fake-spawner';
import { fx71Text } from './fx71';
import { HOME, VAULT_ROOT } from './shell-settings';

export const PLUGIN_DATA_PATH = '.obsidian/plugins/markitdown-flow/data.json';

export interface FakeApis extends NodeApis {
  spawner: FakeSpawner;
  openedFolders: string[];
}

/** The recorded `version` response with the interpreter inside the tested 3.10-3.14 policy range. */
export function versionWithinPolicy(): Uint8Array {
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  return new TextEncoder().encode(JSON.stringify({ ...base, python: '3.14.2' }));
}

/** `version` -> policy-admitted response; anything else exits 0 without output unless overridden. */
export function defaultScript(request: SpawnRequest): ScriptedChild {
  if (subcommandOf(request) === 'version') return { stdout: [versionWithinPolicy()], exit: { code: 0, signal: null } };
  return { exit: { code: 0, signal: null } };
}

export function fakeApis(script: (request: SpawnRequest, index: number) => ScriptedChild = defaultScript, overrides: Partial<FakeApis> = {}): FakeApis {
  const openedFolders: string[] = [];
  return {
    spawner: new FakeSpawner(script),
    fs: new FakeFs({ directories: [VAULT_ROOT] }),
    openFolder: async (folder) => {
      openedFolders.push(folder);
    },
    writeClipboard: async () => undefined,
    pickerAvailable: true,
    pickFiles: async () => ({ kind: 'cancelled' }),
    pickFolder: async () => ({ kind: 'cancelled' }),
    filePath: (file) => (typeof (file as { path?: unknown }).path === 'string' ? ((file as { path: string }).path) : null),
    homeDir: () => HOME,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    openedFolders,
    ...overrides,
  };
}

/** Place `data.json` (object or raw text) in the fake vault and load the plugin through `Plugin.load()`. */
export async function loadPluginWith(
  loadNodeApisMock: jest.MockedFunction<() => NodeApis>,
  data: SettingsV2 | Record<string, unknown> | string | null,
  apis: FakeApis = fakeApis(),
): Promise<{ plugin: MarkItDownFlowPlugin; apis: FakeApis }> {
  loadNodeApisMock.mockImplementation(() => apis);
  mockState.vaultRoot = VAULT_ROOT;
  mockState.adapterFolders.add('.obsidian/plugins/markitdown-flow');
  if (data !== null) {
    const text = typeof data === 'string' ? data : JSON.stringify(data);
    mockState.adapterFiles.set(PLUGIN_DATA_PATH, text);
    try {
      mockState.data = JSON.parse(text);
    } catch {
      mockState.data = null;
    }
  }
  const plugin = new MarkItDownFlowPlugin(createApp(), testManifest());
  await plugin.load();
  return { plugin, apis };
}

export function dataJsonText(): string | undefined {
  return mockState.adapterFiles.get(PLUGIN_DATA_PATH);
}

export const tick = (turns = 3): Promise<void> => new Promise((resolve) => {
  let left = turns;
  const step = (): void => {
    if (--left <= 0) resolve();
    else setImmediate(step);
  };
  setImmediate(step);
});
