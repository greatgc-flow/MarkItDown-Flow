/**
 * M7-02 follow-up (settings-save path): an interpreter change returns from `save` at once; the new gate probe runs in
 * the background (<= about 11 s on a hung interpreter) and the next job waits on that shared probe under the
 * checking status item of the admission (see jt-m7-shell-round7).
 */
import { req } from './req';
import { asMockPlugin, mockState } from './__mocks__/obsidian';
import { loadNodeApis } from '../src/process/node-apis';
import type { SettingsV2 } from '../src/pure/settings';
import { subcommandOf } from './fixtures/fake-spawner';
import { defaultScript, fakeApis, loadPluginWith, tick } from './fixtures/plugin-harness';
import { abs, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R16 = req('REQ-SHL-16');
const mocked = jest.mocked(loadNodeApis);

beforeEach(() => {
  mockState.reset();
  mocked.mockReset();
});

type SaveFn = (next: SettingsV2) => Promise<void>;

it(R16('JT-16 M7-02 the settings tab save returns while the probe of a changed interpreter is still running; the probe is still started'), async () => {
  // The load-time probe answers; every later version probe hangs.
  const apis = fakeApis((request, index) => (subcommandOf(request) === 'version' && index > 0
    ? { blocked: true, cooperative: 'ignore', exit: { code: 0, signal: null } }
    : defaultScript(request)));
  const { plugin } = await loadPluginWith(mocked, settingsV2(), apis);
  await tick(6);
  const tab = asMockPlugin(plugin).settingTabs[0] as unknown as { deps: { save: SaveFn } };
  let saved = false;
  void tab.deps.save(settingsV2({ enginePython: abs(VAULT_ROOT, 'other-venv', 'python') })).then(() => {
    saved = true;
  });
  await tick(8);
  expect(saved).toBe(true);
  expect(apis.spawner.commands.filter((c) => c === 'version')).toHaveLength(2);
  expect(apis.spawner.children[1].alive).toBe(true);
  apis.spawner.children[1].terminate();
  await tick(6);
  plugin.unload();
});
