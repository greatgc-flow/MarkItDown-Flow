/**
 * Security/privacy review fixes for the shell (sec-shell):
 *  - JT-12 (c)/C5, owner decision R38: the plugin cache defaults to the engine's own
 *    `~/.mdflow/cache` (`Path.home() / ".mdflow/cache"`), outside the vault, with no setting;
 *  - JT-14 P3: a configured proxy is shown with the destination in the consent modal;
 *  - JT-07 P4: history entries in data.json store home-relative (`~`) paths;
 *  - JT-12 P5: `--model=<model>` and `--sensitive=<glob>` are single argv tokens.
 */
import { req } from './req';
import { asFake, createApp, mockState } from './__mocks__/obsidian';
import { loadNodeApis } from '../src/process/node-apis';
import { buildSpawnRequest, snapshotJob } from '../src/process/launcher';
import { dictionary } from '../src/pure/i18n';
import { comparablePath, homeRelativePath } from '../src/pure/paths';
import type { Plan } from '../src/pure/protocol';
import type { SettingsV2 } from '../src/pure/settings';
import { buildConsentView, ConsentModal } from '../src/ui/consent-modal';
import { defaultCacheDir } from '../src/ui/coordinator';
import { subcommandOf } from './fixtures/fake-spawner';
import { dataJsonText, loadPluginWith, tick } from './fixtures/plugin-harness';
import { HEX64_A, invocationViolations, plan as syntheticPlan, replayInvariantArgs } from './fixtures/protocol';
import { abs, HOME, HOST_ENV, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R7 = req('REQ-SHL-07');
const R12 = req('REQ-SHL-12');
const R14 = req('REQ-SHL-14');

const mocked = jest.mocked(loadNodeApis);
const PLATFORM = process.platform === 'win32' ? 'win32' : 'posix';
const ENGINE_CACHE = abs(HOME, '.mdflow', 'cache');
const OUTSIDE_INPUT = abs(HOME, 'Downloads', 'scan 1.pdf');

beforeEach(() => {
  mockState.reset();
  mocked.mockReset();
});

function under(parent: string, child: string): boolean {
  const p = comparablePath(PLATFORM, parent);
  const c = comparablePath(PLATFORM, child);
  return c === p || c.startsWith(`${p}/`);
}

it(R12('JT-12 R38 the plugin cache defaults to the engine default ~/.mdflow/cache, outside the vault and the plugin folder'), () => {
  expect(defaultCacheDir('posix', '/home/alice')).toBe('/home/alice/.mdflow/cache');
  expect(defaultCacheDir('posix', '/home/alice/')).toBe('/home/alice/.mdflow/cache');
  expect(defaultCacheDir('win32', 'C:\\Users\\alice')).toBe('C:\\Users\\alice\\.mdflow\\cache');
  // No usable home: no cache root at all (snapshotJob then refuses the job), never `/.mdflow/cache`.
  expect(defaultCacheDir('posix', '')).toBe('');
  expect(defaultCacheDir('posix', 'relative/home')).toBe('');
  expect(ENGINE_CACHE).toBe(defaultCacheDir(PLATFORM, HOME));
  expect(under(VAULT_ROOT, ENGINE_CACHE)).toBe(false);
  expect(under(PLUGIN_DIR, ENGINE_CACHE)).toBe(false);
});

it(R12('JT-12 R38 the loaded plugin passes ~/.mdflow/cache as --cache to the run spawn; no cache setting exists'), async () => {
  const { plugin, apis } = await loadPluginWith(mocked, settingsV2());
  await tick();
  const coordinator = plugin.coordinator;
  if (!coordinator) throw new Error('coordinator missing');
  expect(coordinator.buildRequest({ kind: 'files', paths: [OUTSIDE_INPUT] }).cacheDir).toBe(ENGINE_CACHE);
  const result = await coordinator.submit({ kind: 'files', paths: [OUTSIDE_INPUT] }, 'command');
  expect(result.accepted).toBe(true);
  await coordinator.current;
  const run = apis.spawner.requests.filter((r) => subcommandOf(r) === 'run');
  expect(run).toHaveLength(1);
  expect(run[0].args[run[0].args.indexOf('--cache') + 1]).toBe(ENGINE_CACHE);
  expect(under(VAULT_ROOT, run[0].args[run[0].args.indexOf('--cache') + 1])).toBe(false);
  const stored = JSON.parse(dataJsonText() ?? 'null') as Record<string, unknown>;
  expect(Object.keys(stored).filter((k) => /cache/i.test(k))).toEqual([]);
  plugin.unload();
});

it(R7('JT-07 P4 a recorded history entry stores home-relative ~ paths in data.json, never the absolute home directory'), async () => {
  const { plugin } = await loadPluginWith(mocked, settingsV2());
  await tick();
  const coordinator = plugin.coordinator;
  if (!coordinator) throw new Error('coordinator missing');
  await coordinator.submit({ kind: 'files', paths: [OUTSIDE_INPUT, abs(VAULT_ROOT, 'inbox', 'b.pdf')] }, 'command');
  await coordinator.current;
  await tick();
  const stored = JSON.parse(dataJsonText() ?? 'null') as SettingsV2;
  expect(stored.conversionHistory).toHaveLength(1);
  const entry = stored.conversionHistory[0];
  expect(entry.inputFile).toBe(`${abs('~', 'Downloads', 'scan 1.pdf')} (+1)`);
  expect(entry.outputFile).toBe(abs('~', 'Vault', 'markitdown-output'));
  expect(JSON.stringify(stored.conversionHistory)).not.toContain(JSON.stringify(HOME).slice(1, -1));
  plugin.unload();
});

it(R7('JT-07 P4 homeRelativePath replaces only a whole leading home directory (case-insensitive on Windows)'), () => {
  expect(homeRelativePath('posix', '/home/alice', '/home/alice/Vault/a.pdf')).toBe('~/Vault/a.pdf');
  expect(homeRelativePath('posix', '/home/alice/', '/home/alice/a.pdf')).toBe('~/a.pdf');
  expect(homeRelativePath('posix', '/home/alice', '/home/alice')).toBe('~');
  expect(homeRelativePath('posix', '/home/alice', '/home/alicex/a.pdf')).toBe('/home/alicex/a.pdf');
  expect(homeRelativePath('posix', '/home/alice', '/srv/home/alice/a.pdf')).toBe('/srv/home/alice/a.pdf');
  expect(homeRelativePath('posix', '/home/alice', '/HOME/alice/a.pdf')).toBe('/HOME/alice/a.pdf');
  expect(homeRelativePath('posix', '', '/home/alice/a.pdf')).toBe('/home/alice/a.pdf');
  expect(homeRelativePath('posix', '/', '/etc/a')).toBe('/etc/a');
  expect(homeRelativePath('win32', 'C:\\Users\\alice', 'c:\\users\\ALICE\\Docs\\a.pdf')).toBe('~\\Docs\\a.pdf');
  expect(homeRelativePath('win32', 'C:\\Users\\alice', 'D:\\Users\\alice\\a.pdf')).toBe('D:\\Users\\alice\\a.pdf');
  expect(homeRelativePath('win32', 'C:\\Users\\alice', '\\\\server\\share\\a.pdf')).toBe('\\\\server\\share\\a.pdf');
});

function withProxy(base: Plan, proxy: string | null): Plan {
  return { ...base, approved: { ...base.approved, provider: { ...base.approved.provider, proxy } } };
}

it(R14('JT-14 P3 a configured proxy from the Plan is shown with the destination in the summary and the details (en/ko)'), () => {
  const proxy = 'http://proxy.corp.example:3128';
  const view = buildConsentView([withProxy(syntheticPlan('reports/q3.pdf', HEX64_A, 2), proxy)], '/home/alice/Vault/out');
  expect(view.files[0].proxy).toBe(proxy);
  for (const locale of ['en', 'ko'] as const) {
    const label = dictionary(locale)['shell.consent.proxy'];
    expect(label).toBeTruthy();
    const modal = new ConsentModal(createApp(), view, locale);
    modal.open();
    const content = asFake(modal.contentEl);
    const summaryCells = content.findAll((e) => e.tagName === 'td' && e.textContent.includes(view.files[0].destination ?? '-'));
    expect(summaryCells.some((c) => c.textContent.includes(proxy))).toBe(true);
    expect(content.textContent).toContain(`${label}: ${proxy}`);
    modal.close();
  }
  expect(dictionary('ko')['shell.consent.proxy']).not.toBe(dictionary('en')['shell.consent.proxy']);
});

it(R14('JT-14 P3 without a proxy the consent modal shows no proxy line'), () => {
  const view = buildConsentView([syntheticPlan('reports/q3.pdf', HEX64_A, 2)], '/home/alice/Vault/out');
  expect(view.files[0].proxy).toBeNull();
  const modal = new ConsentModal(createApp(), view, 'en');
  modal.open();
  expect(asFake(modal.contentEl).textContent).not.toContain(`${dictionary('en')['shell.consent.proxy']}:`);
  modal.close();
});

it(R12('JT-12 P5 --model and every --sensitive glob are single --opt=value tokens, so a leading "-" is never read as an option'), () => {
  const settings = settingsV2({
    provider: { ...OPENAI_PROVIDER, model: '-dash-model' },
    runOptions: { dpi: 200, minPriority: 'low', maxUnits: 200, approveThreshold: 20, sensitive: ['*/hr/*', '-x*', 'a b=c'] },
  });
  const snap = snapshotJob({ settings, inputs: [OUTSIDE_INPUT], cwd: abs(HOME, 'venv'), outDir: abs(VAULT_ROOT, 'out'), cacheDir: ENGINE_CACHE });
  const plan = buildSpawnRequest(snap, 'plan', HOST_ENV);
  const run = buildSpawnRequest(snap, 'run', HOST_ENV);
  for (const request of [plan, run]) {
    expect(request.args).toContain('--model=-dash-model');
    expect(request.args.filter((t) => t.startsWith('--sensitive='))).toEqual(['--sensitive=*/hr/*', '--sensitive=-x*', '--sensitive=a b=c']);
    expect(request.args).not.toContain('--model');
    expect(request.args).not.toContain('--sensitive');
    expect(request.args).not.toContain('-dash-model');
    expect(request.args).not.toContain('-x*');
    expect(invocationViolations(request)).toEqual([]);
  }
  expect(replayInvariantArgs(run.args)).toEqual(replayInvariantArgs(plan.args));
  const local = buildSpawnRequest(snapshotJob({ settings: settingsV2(), inputs: [OUTSIDE_INPUT], cwd: abs(HOME, 'venv'), outDir: abs(VAULT_ROOT, 'out'), cacheDir: ENGINE_CACHE }), 'run', HOST_ENV);
  expect(local.args.some((t) => t.startsWith('--model'))).toBe(false);
  // The REQ-SHL-11 oracle still rejects an invented option written in --opt=value form.
  expect(invocationViolations({ ...run, args: [...run.args, '--invented=1'] })).toEqual([{ kind: 'option', token: '--invented' }]);
});
