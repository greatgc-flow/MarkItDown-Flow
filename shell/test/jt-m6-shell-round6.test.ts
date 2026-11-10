/**
 * MECE round 6 shell findings (docs/renewal/review/M6_cc_cross.md):
 *  - M6-01 a `version` probe that times out is retried once with backoff and a timeout / spawn failure
 *    is never cached as the jobs gate; the Setup modal tells a timeout apart from an incompatibility;
 *  - M6-02/03 the copyable recipe quotes the migrated interpreter hint and quotes POSIX lines for `sh`;
 *  - M6-04 a finished consent job leaves no cancel waiter behind;
 *  - M6-07/08 source comments and README disclosures match the behavior.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { req } from './req';
import { createApp, mockState } from './__mocks__/obsidian';
import { loadNodeApis } from '../src/process/node-apis';
import { collectSetupDiagnostics, renderBootstrapInstructions, renderUpstreamUninstall } from '../src/process/setup';
import {
  isTransientGate,
  probeVersion,
  RELEASE_LOCK,
  VERSION_PROBE_BACKOFF_MS,
  VERSION_PROBE_TIMEOUT_MS,
  type VersionGate,
} from '../src/process/version-gate';
import { dictionary } from '../src/pure/i18n';
import { SetupModal } from '../src/ui/setup-modal';
import { ShellCoordinator, type CoordinatorDeps } from '../src/ui/coordinator';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, type ScriptedChild, subcommandOf } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit } from './fixtures/fx71';
import { dataJsonText, defaultScript, fakeApis, loadPluginWith, tick } from './fixtures/plugin-harness';
import { abs, ENGINE_PYTHON, HOME, HOST_ENV, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R17 = req('REQ-SHL-17');
const R10 = req('REQ-SHL-10');
const R16 = req('REQ-SHL-16');
const R15 = req('REQ-SHL-15');
const R12 = req('REQ-SHL-12');
const mocked = jest.mocked(loadNodeApis);
const REPO = path.resolve(__dirname, '..', '..');
const EN = dictionary('en');
const KO = dictionary('ko');

beforeEach(() => {
  mockState.reset();
  mocked.mockReset();
});

const OK: ScriptedChild = { stdout: [fx71Bytes('version.json')], exit: { code: 0, signal: null } };
const HUNG: ScriptedChild = { blocked: true, cooperative: 'ignore', exit: { code: 0, signal: null } };

function blockedReason(gate: VersionGate): string {
  if (gate.enabled) throw new Error('expected a blocked gate');
  return gate.reason;
}

/** Drive a probe whose clock is advanced by the given steps (each step settles microtasks first). */
async function probeWith(script: (index: number) => ScriptedChild, steps: number[]): Promise<{ gate: VersionGate; spawner: FakeSpawner }> {
  const spawner = new FakeSpawner((_request, index) => script(index));
  const clock = new FakeClock();
  const pending = probeVersion(ENGINE_PYTHON, { spawner, clock, hostEnv: HOST_ENV, cwd: PLUGIN_DIR, policy: RELEASE_LOCK });
  await flush();
  for (const step of steps) await clock.advance(step);
  return { gate: await pending, spawner };
}

it(R17('JT-17 M6-01 a probe that misses the first deadline is retried once after a backoff and a healthy second answer enables jobs'), async () => {
  expect(VERSION_PROBE_BACKOFF_MS).toBeGreaterThan(0);
  const { gate, spawner } = await probeWith((index) => (index === 0 ? HUNG : OK), [VERSION_PROBE_TIMEOUT_MS, VERSION_PROBE_BACKOFF_MS]);
  expect(gate.enabled).toBe(true);
  expect(spawner.requests).toHaveLength(2);
  expect(spawner.children[0].terminated).toBe(true);
  for (const request of spawner.requests) expect(request.args).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow', 'version']);
});

it(R17('JT-17 M6-01 two consecutive timeouts stay `timeout` after exactly two attempts; the second attempt gets the full budget'), async () => {
  const { gate, spawner } = await probeWith(() => HUNG, [VERSION_PROBE_TIMEOUT_MS, VERSION_PROBE_BACKOFF_MS, VERSION_PROBE_TIMEOUT_MS]);
  expect(blockedReason(gate)).toBe('timeout');
  expect(spawner.requests).toHaveLength(2);
  expect(spawner.children.every((child) => child.terminated)).toBe(true);
});

it(R17('JT-17 M6-01 only a timeout is retried: exit, spawn failure and incompatibility are answered once'), async () => {
  const exit1 = await probeWith(() => ({ stdout: [], exit: { code: 1, signal: null } }), []);
  expect(blockedReason(exit1.gate)).toBe('exit');
  expect(exit1.spawner.requests).toHaveLength(1);
  const absent = await probeWith(() => ({ spawnError: new Error('ENOENT'), exit: { code: null, signal: null } }), []);
  expect(blockedReason(absent.gate)).toBe('spawn_failed');
  expect(absent.spawner.requests).toHaveLength(1);
  const old = await probeWith(() => ({ stdout: [fx71Bytes('version.core-out-of-range.json')], exit: { code: 0, signal: null } }), []);
  expect(blockedReason(old.gate)).toBe('core');
  expect(old.spawner.requests).toHaveLength(1);
});

it(R17('JT-17 M6-01 timeout and spawn failure are transient (never cached); every compatibility verdict is definite'), () => {
  const reasons = ['timeout', 'spawn_failed'] as const;
  for (const reason of reasons) expect(isTransientGate({ enabled: false, diagnostic: 'shell.RUNTIME', reason })).toBe(true);
  for (const reason of ['exit', 'not_json', 'missing_field', 'bad_type', 'protocol', 'triage_schema', 'python', 'engine', 'core', 'pypdfium2', 'pillow', 'platform', 'core_conflict'] as const) {
    expect(isTransientGate({ enabled: false, diagnostic: 'shell.RUNTIME', reason })).toBe(false);
  }
  expect(isTransientGate(null)).toBe(false);
  expect(isTransientGate({ enabled: true, info: JSON.parse(Buffer.from(fx71Bytes('version.json')).toString('utf8')) })).toBe(false);
});

it(R17('JT-17 M6-01 plugin: a spawn failure at load is not cached; the next job re-probes and passes the gate'), async () => {
  const apis = fakeApis((request, index) => {
    if (subcommandOf(request) === 'version') return index === 0 ? { spawnError: new Error('EBUSY'), exit: { code: null, signal: null } } : OK;
    return defaultScript(request);
  });
  const { plugin } = await loadPluginWith(mocked, settingsV2(), apis);
  await tick();
  const selection = { kind: 'files' as const, paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] };
  const coordinator = plugin.coordinator;
  if (!coordinator) throw new Error('plugin not active');
  expect(apis.spawner.requests.filter((r) => subcommandOf(r) === 'version')).toHaveLength(1);
  // First job: the transient failure from load was not kept, so the probe runs again, passes, and the job is admitted.
  const first = await coordinator.submit(selection, 'command');
  expect(first.accepted).toBe(true);
  await coordinator.current;
  expect(apis.spawner.requests.filter((r) => subcommandOf(r) === 'version')).toHaveLength(2);
  // A definite verdict (enabled) is cached: a second job does not probe again.
  expect((await coordinator.submit(selection, 'command')).accepted).toBe(true);
  await coordinator.current;
  expect(apis.spawner.requests.filter((r) => subcommandOf(r) === 'version')).toHaveLength(2);
  plugin.unload();
});

it(R17('JT-17 M6-01 plugin: an incompatibility verdict stays cached (no re-probe per job)'), async () => {
  const apis = fakeApis((request) => (subcommandOf(request) === 'version' ? { stdout: [fx71Bytes('version.core-out-of-range.json')], exit: { code: 0, signal: null } } : defaultScript(request)));
  const { plugin } = await loadPluginWith(mocked, settingsV2(), apis);
  await tick();
  const selection = { kind: 'files' as const, paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] };
  const coordinator = plugin.coordinator;
  if (!coordinator) throw new Error('plugin not active');
  expect(await coordinator.submit(selection, 'command')).toEqual({ accepted: false, diagnostic: 'shell.RUNTIME' });
  expect(await coordinator.submit(selection, 'command')).toEqual({ accepted: false, diagnostic: 'shell.RUNTIME' });
  expect(apis.spawner.requests.filter((r) => subcommandOf(r) === 'version')).toHaveLength(1);
  plugin.unload();
  expect(dataJsonText()).toBeDefined();
});

it(R10('JT-10 M6-01 the Setup modal names a timeout as "no answer" (retry), not as an incompatibility, in both locales'), async () => {
  for (const locale of ['en', 'ko'] as const) {
    mockState.reset();
    const dict = locale === 'en' ? EN : KO;
    const spawner = new FakeSpawner(() => HUNG);
    const clock = new FakeClock();
    const setup = new SetupModal(createApp(), {
      spawner,
      clock,
      hostEnv: HOST_ENV,
      platform: process.platform === 'win32' ? 'win32' : 'posix',
      cwd: PLUGIN_DIR,
      enginePython: ENGINE_PYTHON,
      policy: RELEASE_LOCK,
      home: HOME,
      vault: VAULT_ROOT,
      writeClipboard: async () => undefined,
      locale,
    });
    setup.open();
    const pending = setup.refresh();
    await flush();
    await clock.advance(VERSION_PROBE_TIMEOUT_MS);
    await clock.advance(VERSION_PROBE_BACKOFF_MS);
    await clock.advance(VERSION_PROBE_TIMEOUT_MS);
    await pending;
    const text = (setup.contentEl as unknown as { textContent: string }).textContent;
    expect(dict['shell.setup.probeTimeout']).toBeTruthy();
    expect(text).toContain(dict['shell.setup.probeTimeout']);
    expect(text).not.toContain(dict['shell.setup.probeBlocked'].replace('{reason}', 'timeout'));
    expect(setup.diagnostics?.jobsEnabled).toBe(false);
    setup.close();
  }
});

it(R10('JT-10 M6-01 an incompatibility is still rendered as blocked with its reason'), async () => {
  const spawner = new FakeSpawner(() => ({ stdout: [fx71Bytes('version.core-out-of-range.json')], exit: { code: 0, signal: null } }));
  const setup = new SetupModal(createApp(), {
    spawner,
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    cwd: PLUGIN_DIR,
    enginePython: ENGINE_PYTHON,
    policy: RELEASE_LOCK,
    home: HOME,
    vault: VAULT_ROOT,
    writeClipboard: async () => undefined,
    locale: 'en',
  });
  setup.open();
  await setup.refresh();
  const text = (setup.contentEl as unknown as { textContent: string }).textContent;
  expect(text).toContain(EN['shell.setup.probeBlocked'].replace('{reason}', 'core markitdown-gc'));
  expect(text).not.toContain(EN['shell.setup.probeTimeout']);
});

it(R10('JT-10 M6-02 the migrated interpreter hint is quoted as an executable path when it is not a plain command; plain commands stay a command'), async () => {
  const spaced = 'C:\\Program Files\\Python312\\python.exe';
  const text = renderBootstrapInstructions({ downloadDir: 'C:\\Downloads\\mdflow-2.0.0', venvDir: 'C:\\mdflow-venvs\\2.0.0', bootstrapPython: spaced });
  expect(text.windows).toContain(`& '${spaced}' -m venv 'C:\\mdflow-venvs\\2.0.0'`);
  expect(text.posix).toContain(`'${spaced}' -m venv`);
  expect(text.windows).not.toContain(`\n${spaced} -m venv`);
  const unixPath = renderBootstrapInstructions({ downloadDir: '/d', venvDir: '/v', bootstrapPython: '/opt/my python/bin/python3' });
  expect(unixPath.posix).toContain("'/opt/my python/bin/python3' -m venv '/v'");
  expect(unixPath.windows).toContain("& '/opt/my python/bin/python3' -m venv '/v'");
  for (const plain of ['py -3.14', 'py -3', 'python3.14', 'python3', 'python']) {
    const rendered = renderBootstrapInstructions({ downloadDir: '/d', venvDir: '/v', bootstrapPython: plain });
    expect(rendered.posix).toContain(`\n${plain} -m venv '/v'`);
    expect(rendered.windows).toContain(`\n${plain} -m venv '/v'`);
  }
  // A hint with shell metacharacters is rendered inside quotes, never as live shell text.
  const hostile = renderBootstrapInstructions({ downloadDir: '/d', venvDir: '/v', bootstrapPython: 'python3; rm -rf ~' });
  expect(hostile.posix).toContain("'python3; rm -rf ~' -m venv '/v'");
  // End to end: the diagnostics carry the quoted hint when nothing is detected.
  const spawner = new FakeSpawner(() => ({ spawnError: new Error('ENOENT'), exit: { code: null, signal: null } }));
  const diagnostics = await collectSetupDiagnostics({
    spawner,
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: 'win32',
    cwd: PLUGIN_DIR,
    enginePython: null,
    bootstrapPythonHint: spaced,
    policy: RELEASE_LOCK,
  });
  expect(diagnostics.instructions.windows).toContain(`& '${spaced}' -m venv`);
});

it(R10('JT-10 M6-03 POSIX recipe lines and the POSIX uninstall command use sh quoting; PowerShell lines keep doubled quotes'), () => {
  const text = renderBootstrapInstructions({ downloadDir: "/Users/o'brien/dl", venvDir: "/Users/o'brien/venv", bootstrapPython: 'python3.14' });
  expect(text.posix).toContain("cd '/Users/o'\\''brien/dl'");
  expect(text.posix).toContain("python3.14 -m venv '/Users/o'\\''brien/venv'");
  expect(text.posix).toContain("'/Users/o'\\''brien/venv/bin/python' -m pip install --only-binary=:all:");
  expect(text.posix).not.toContain("o''brien");
  expect(text.windows).toContain("Set-Location -LiteralPath '/Users/o''brien/dl'");
  expect(renderUpstreamUninstall("/Users/o'brien/venv/bin/python", 'posix')).toBe("'/Users/o'\\''brien/venv/bin/python' -m pip uninstall -y markitdown");
  expect(renderUpstreamUninstall("C:\\o'brien\\venv\\Scripts\\python.exe", 'win32')).toBe("& 'C:\\o''brien\\venv\\Scripts\\python.exe' -m pip uninstall -y markitdown");
});

function consentHarness(decide: CoordinatorDeps['consent']): { coordinator: ShellCoordinator; spawner: FakeSpawner } {
  const fsys = new FakeFs({ directories: [VAULT_ROOT, abs(VAULT_ROOT, 'markitdown-output'), abs(VAULT_ROOT, 'inbox'), PLUGIN_DIR, abs(PLUGIN_DIR, 'cache')] });
  const spawner = new FakeSpawner((request) => {
    if (subcommandOf(request) === 'plan') return { stdout: chunksOf(fx71Bytes('plan-mixed.stdout.json'), 4096), exit: { code: fx71Exit('plan-mixed.stdout.json'), signal: null } };
    return { stderr: chunksOf(fx71Bytes('consent-5-approved.progress.jsonl'), 2048), stdout: chunksOf(fx71Bytes('consent-5-approved.stdout.json'), 8192), exit: { code: fx71Exit('consent-5-approved.stdout.json'), signal: null } };
  });
  const deps: CoordinatorDeps = {
    spawner,
    fs: fsys,
    spoolFs: new FakeSpoolFs(fsys, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    homeDir: HOME,
    settings: () => settingsV2({ provider: { ...OPENAI_PROVIDER } }),
    gate: () => ({ enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.7', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } }),
    consent: decide,
    notify: () => undefined,
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
  };
  return { coordinator: new ShellCoordinator(deps), spawner };
}

function retainedWaiters(coordinator: ShellCoordinator): number {
  return (coordinator as unknown as { cancelWaiters: unknown[] }).cancelWaiters.length;
}

it(R15('JT-15 M6-04 consent jobs leave no retained cancel waiter after approve, keep-pending or a later Cancel'), async () => {
  const approve = consentHarness(async (view) => ({ approved: true, hashes: view.files.filter((f) => f.requestsToSend > 0 || f.approvedBudget > 0).map((f) => f.planHash) }));
  for (let i = 0; i < 3; i++) {
    const result = await approve.coordinator.submit({ kind: 'folder', paths: [abs(VAULT_ROOT, 'inbox')] }, 'command');
    expect(result.accepted).toBe(true);
    await approve.coordinator.current;
    expect(retainedWaiters(approve.coordinator)).toBe(0);
  }
  expect(approve.spawner.commands.filter((c) => c === 'run')).toHaveLength(3);
  const dismiss = consentHarness(async () => ({ approved: false }));
  for (let i = 0; i < 3; i++) {
    await dismiss.coordinator.submit({ kind: 'folder', paths: [abs(VAULT_ROOT, 'inbox')] }, 'command');
    await dismiss.coordinator.current;
    expect(retainedWaiters(dismiss.coordinator)).toBe(0);
  }
});

it(R16('JT-16 M6-04 Cancel during the consent modal still dismisses it and drains the waiter'), async () => {
  const never = new Promise<never>(() => undefined);
  const h = consentHarness(() => never);
  await h.coordinator.submit({ kind: 'folder', paths: [abs(VAULT_ROOT, 'inbox')] }, 'command');
  await flush();
  expect(retainedWaiters(h.coordinator)).toBe(1);
  h.coordinator.cancel();
  await h.coordinator.current;
  expect(retainedWaiters(h.coordinator)).toBe(0);
  expect(h.spawner.commands).toEqual(['plan']);
});

function source(...parts: string[]): string {
  return fs.readFileSync(path.join(REPO, ...parts), 'utf8');
}

it(R12('JT-12 M6-07 source comments no longer claim an unconditional outside-vault working directory or a retired flag/module'), () => {
  expect(source('shell', 'src', 'process', 'launcher.ts')).not.toMatch(/is not vault content|a fixed cwd outside the vault/);
  expect(source('shell', 'src', 'ui', 'coordinator.ts')).not.toContain('never the vault');
  expect(source('shell', 'src', 'main.ts')).not.toContain('Never the vault or the plugin folder');
  expect(source('shell', 'src', 'pure', 'settings.ts')).not.toContain('--legacy-preconvert');
  expect(source('shell', 'test', 'jt-r33-legacy-preconvert.test.ts')).not.toContain('preconvert.prepare');
  expect(source('shell', 'test', 'jt-12-spawn-replay.test.ts')).not.toMatch(/never the vault|cwd is outside the vault|a cwd outside the vault|is not vault content/);
});

it(R17('JT-17 M6-08 README and 25_PACKAGING disclose exiftool and LibreOffice under outside-vault access and do not claim a blocked network'), () => {
  const readme = source('README.md');
  const outside = /Outside-vault access[\s\S]*?(?=\n## )/.exec(readme)?.[0] ?? '';
  expect(outside).toMatch(/exiftool/i);
  expect(outside).toMatch(/LibreOffice/);
  expect(outside).toMatch(/GPS|Author|Artist/);
  expect(readme).not.toContain('without network access');
  expect(source('docs', 'renewal', '25_PACKAGING.md')).toMatch(/exiftool[^\n]*LibreOffice|LibreOffice[^\n]*exiftool/);
});
