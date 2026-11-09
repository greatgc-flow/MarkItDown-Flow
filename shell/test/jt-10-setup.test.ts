/**
 * JT-10 / REQ-SHL-10: diagnostics-only SetupModal. Probes are version probes
 * only (configured interpreter first, five-second timeout; optional
 * `python3`/`python`/`py -3` version probes only when unconfigured, never an
 * execution fallback); zero dependency mutations or network calls; copy
 * buttons write clipboard text only; a missing engine leaves settings/history
 * available.
 */
import { req } from './req';
import { createApp, mockState } from './__mocks__/obsidian';
import { BOOTSTRAP_PROBE_CANDIDATES, collectSetupDiagnostics, CORE_REQUIREMENT, ENGINE_WHEEL, renderBootstrapInstructions, type SetupDeps } from '../src/process/setup';
import { RELEASE_LOCK, VERSION_PROBE_TIMEOUT_MS, type VersionPolicy } from '../src/process/version-gate';
import type { SpawnRequest } from '../src/process/types';
import { SetupModal } from '../src/ui/setup-modal';
import { HistoryModal } from '../src/ui/history-modal';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Manifest } from './fixtures/fx71';
import { ENGINE_PYTHON, HOME, HOST_ENV, KEY_VALUE, PLUGIN_DIR, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-10');
const POLICY: VersionPolicy = { ...RELEASE_LOCK, pythonMaxExclusive: [3, 16, 0] };

const FORBIDDEN_TOKENS = ['pip', 'venv', 'install', 'download', 'curl', 'wget', 'Invoke-WebRequest', 'selftest', 'run', 'plan'];

function versionOnly(request: SpawnRequest): boolean {
  if (request.command === ENGINE_PYTHON) return request.args.join(' ') === '-m mdflow version';
  return BOOTSTRAP_PROBE_CANDIDATES.some((c) => c.command === request.command && c.args.join(' ') === request.args.join(' '));
}

function script(request: SpawnRequest): ScriptedChild {
  if (request.command === ENGINE_PYTHON) return { stdout: [fx71Bytes('version.json')], exit: { code: 0, signal: null } };
  if (request.command === 'python3') return { stdout: [Buffer.from('Python 3.14.2\n')], exit: { code: 0, signal: null } };
  return { spawnError: new Error('ENOENT'), exit: { code: null, signal: null } };
}

function deps(spawner: FakeSpawner, clock: FakeClock, enginePython: string | null): SetupDeps {
  return {
    spawner,
    clock,
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    cwd: PLUGIN_DIR,
    enginePython,
    paths: { downloadDir: '/downloads/mdflow-2.0.0', venvDir: '/venvs/mdflow 2.0.0' },
    policy: POLICY,
    home: HOME,
    vault: VAULT_ROOT,
  };
}

beforeEach(() => mockState.reset());

it(R('JT-10 configured interpreter: exactly one version probe, no bootstrap probes, no network, jobs enabled'), async () => {
  const spawner = new FakeSpawner(script);
  const diagnostics = await collectSetupDiagnostics(deps(spawner, new FakeClock(), ENGINE_PYTHON));
  expect(spawner.requests).toHaveLength(1);
  expect(spawner.requests[0].command).toBe(ENGINE_PYTHON);
  expect(spawner.requests[0].args).toEqual(['-m', 'mdflow', 'version']);
  expect(diagnostics.gate?.enabled).toBe(true);
  expect(diagnostics.bootstrapProbes).toEqual([]);
  expect(diagnostics.jobsEnabled).toBe(true);
  expect(diagnostics.apiKey).toBe('present');
  expect(mockState.network).toEqual([]);
  expect(JSON.stringify(diagnostics)).not.toContain(KEY_VALUE);
});

it(R('JT-10 unconfigured interpreter: only `--version` bootstrap probes run, they prefill instructions and never become an execution fallback'), async () => {
  const spawner = new FakeSpawner(script);
  const diagnostics = await collectSetupDiagnostics(deps(spawner, new FakeClock(), null));
  expect(spawner.requests.length).toBeGreaterThan(0);
  for (const request of spawner.requests) {
    expect(versionOnly(request)).toBe(true);
    expect(request.command).not.toBe(ENGINE_PYTHON);
    expect(request.args).not.toContain('mdflow');
    expect(request.shell).toBe(false);
  }
  expect(diagnostics.gate).toBeNull();
  expect(diagnostics.jobsEnabled).toBe(false);
  const detected = diagnostics.bootstrapProbes.find((p) => p.result === 'ok');
  expect(detected).toMatchObject({ command: 'python3', version: '3.14.2' });
  expect(diagnostics.instructions.posix).toContain('python3');
  expect(diagnostics.instructions.posix).toContain('-m venv');
  for (const probe of diagnostics.bootstrapProbes) expect(BOOTSTRAP_PROBE_CANDIDATES.map((c) => c.command)).toContain(probe.command);
});

it(R('JT-10 the version probe is bounded by five seconds; a hung interpreter blocks jobs and is terminated'), async () => {
  const spawner = new FakeSpawner(() => ({ blocked: true, cooperative: 'ignore', exit: { code: 0, signal: null } }));
  const clock = new FakeClock();
  const pending = collectSetupDiagnostics(deps(spawner, clock, ENGINE_PYTHON));
  await flush();
  await clock.advance(VERSION_PROBE_TIMEOUT_MS);
  const diagnostics = await pending;
  expect(diagnostics.gate).toMatchObject({ enabled: false, reason: 'timeout' });
  expect(diagnostics.jobsEnabled).toBe(false);
  expect(spawner.requests).toHaveLength(1);
  expect(spawner.children[0].terminated).toBe(true);
});

it(R('JT-10 bootstrap instructions are the R27 25_PACKAGING section 2 commands with substituted paths: venv, wheel-only install of the release wheel plus Core from PyPI, check, probe; no plugin-side execution'), () => {
  const text = renderBootstrapInstructions({ downloadDir: 'C:\\Downloads\\mdflow 2.0.0', venvDir: 'C:\\mdflow-venvs\\2.0.0', bootstrapPython: 'py -3.14' });
  expect(text.windows).toContain("Set-Location -LiteralPath 'C:\\Downloads\\mdflow 2.0.0'");
  expect(text.windows).toContain("py -3.14 -m venv 'C:\\mdflow-venvs\\2.0.0'");
  expect(text.windows).toContain(`-m pip install --only-binary=:all: '.\\${ENGINE_WHEEL}' '${CORE_REQUIREMENT}'`);
  expect(text.windows).toContain('-m pip check');
  expect(text.windows).toContain('-m mdflow version');
  expect(text.windows).toContain("'C:\\mdflow-venvs\\2.0.0\\Scripts\\python.exe'");
  const posix = renderBootstrapInstructions({ downloadDir: '/path/to/mdflow-2.0.0', venvDir: '/path/to/mdflow-venvs/2.0.0', bootstrapPython: 'python3.14' });
  expect(posix.posix).toContain("cd '/path/to/mdflow-2.0.0'");
  expect(posix.posix).toContain("python3.14 -m venv '/path/to/mdflow-venvs/2.0.0'");
  expect(posix.posix).toContain(`'/path/to/mdflow-venvs/2.0.0/bin/python' -m pip install --only-binary=:all: './${ENGINE_WHEEL}' '${CORE_REQUIREMENT}'`);
  expect(posix.posix).toContain("'/path/to/mdflow-venvs/2.0.0/bin/python' -m mdflow version");
  expect(ENGINE_WHEEL).toMatch(/^mdflow-2\.0\.0-py3-none-any\.whl$/);
  expect(CORE_REQUIREMENT).toBe('markitdown-gc>=0.3.5,<0.4');
  for (const block of [text.windows, text.posix, posix.windows, posix.posix]) {
    // Every install is wheel-only; no source builds, no upgrades, no extras, no lock files or hash manifests remain (R27).
    expect(block).not.toMatch(/pip install(?! --only-binary=:all:)/);
    expect(block).not.toContain('--upgrade');
    expect(block).not.toContain('[all]');
    expect(block).not.toContain('--require-hashes');
    expect(block).not.toContain('engine.lock');
    expect(block).not.toContain('--find-links');
  }
});

function modal(spawner: FakeSpawner, clock: FakeClock, enginePython: string | null, clipboard: string[]): SetupModal {
  return new SetupModal(createApp(), { ...deps(spawner, clock, enginePython), writeClipboard: async (text) => { clipboard.push(text); }, locale: 'en' });
}

it(R('JT-10 SetupModal open and refresh spawn only version probes; nothing is installed, downloaded or fetched'), async () => {
  const spawner = new FakeSpawner(script);
  const clipboard: string[] = [];
  const setup = modal(spawner, new FakeClock(), ENGINE_PYTHON, clipboard);
  setup.open();
  await setup.refresh();
  await setup.refresh();
  expect(spawner.requests.length).toBeGreaterThanOrEqual(2);
  for (const request of spawner.requests) {
    expect(versionOnly(request)).toBe(true);
    for (const token of request.args) for (const forbidden of FORBIDDEN_TOKENS) expect(token).not.toBe(forbidden);
  }
  expect(mockState.network).toEqual([]);
  expect(setup.diagnostics?.gate?.enabled).toBe(true);
  expect(clipboard).toEqual([]);
  const rendered = (setup.contentEl as unknown as { textContent: string }).textContent;
  expect(rendered).toContain(ENGINE_PYTHON);
  expect(rendered).toContain(fx71Manifest().engine.mdflow);
  expect(rendered).toContain('0.3.5');
  expect(rendered).not.toContain(KEY_VALUE);
  setup.close();
});

it(R('JT-10 copy buttons write only the instruction or redacted diagnostics text to the clipboard'), async () => {
  const spawner = new FakeSpawner(script);
  const clipboard: string[] = [];
  const setup = modal(spawner, new FakeClock(), ENGINE_PYTHON, clipboard);
  setup.open();
  await setup.refresh();
  const spawnsBefore = spawner.requests.length;
  await setup.copyInstructions('posix');
  await setup.copyInstructions('windows');
  await setup.copyDiagnostics();
  expect(clipboard).toHaveLength(3);
  expect(clipboard[0]).toBe(setup.diagnostics?.instructions.posix);
  expect(clipboard[1]).toBe(setup.diagnostics?.instructions.windows);
  expect(clipboard[2]).toContain(fx71Manifest().engine.mdflow);
  expect(clipboard[2]).not.toContain(KEY_VALUE);
  expect(clipboard[2]).not.toContain(HOME);
  expect(spawner.requests).toHaveLength(spawnsBefore);
  expect(mockState.network).toEqual([]);
});

it(R('JT-10 a missing engine blocks jobs but the modal still renders, and history stays available without Python'), async () => {
  const spawner = new FakeSpawner(() => ({ spawnError: new Error('ENOENT: no such interpreter'), exit: { code: null, signal: null } }));
  const clipboard: string[] = [];
  const setup = modal(spawner, new FakeClock(), ENGINE_PYTHON, clipboard);
  setup.open();
  await setup.refresh();
  expect(setup.diagnostics?.gate).toMatchObject({ enabled: false, reason: 'spawn_failed', diagnostic: 'shell.RUNTIME' });
  expect(setup.diagnostics?.jobsEnabled).toBe(false);
  expect((setup.contentEl as unknown as { textContent: string }).textContent.length).toBeGreaterThan(0);
  const history = new HistoryModal(createApp(), [{ inputFile: 'a.pdf', outputFile: 'a.pdf.md', timestamp: 1, success: true, outcome: 'complete' }], 'en', async () => undefined);
  history.open();
  expect(mockState.openModals).toContain(history);
  expect((history.contentEl as unknown as { textContent: string }).textContent).toContain('a.pdf');
  expect(spawner.requests).toHaveLength(1);
});
