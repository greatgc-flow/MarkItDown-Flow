/**
 * JT-20 / REQ-SHL-20: the frozen selftest command runs the version check then
 * SPEC 10.1 `selftest`; the spawn snapshot contains only those two, with no
 * network, no shell-created raster and no shell fixture.
 */
import { req } from './req';
import { mockState } from './__mocks__/obsidian';
import { runSelftest, type SelftestDeps } from '../src/process/selftest';
import { RELEASE_LOCK } from '../src/process/version-gate';
import type { SpawnRequest } from '../src/process/types';
import { FakeClock } from './fixtures/fake-clock';
import { FakeSpawner, type ScriptedChild, subcommandOf } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit } from './fixtures/fx71';
import { ENGINE_PYTHON, HOST_ENV, KEY_VALUE, PLUGIN_DIR } from './fixtures/shell-settings';

const R = req('REQ-SHL-20');

function script(selftestExit = fx71Exit('selftest.json')): (request: SpawnRequest) => ScriptedChild {
  return (request) => {
    if (subcommandOf(request) === 'version') return { stdout: [fx71Bytes('version.json')], exit: { code: 0, signal: null } };
    if (subcommandOf(request) === 'selftest') return { stdout: [fx71Bytes('selftest.json')], exit: { code: selftestExit, signal: null } };
    return { spawnError: new Error(`unexpected spawn ${request.args.join(' ')}`), exit: { code: null, signal: null } };
  };
}

function deps(spawner: FakeSpawner, enginePython: string | null = ENGINE_PYTHON): SelftestDeps {
  // FX-71 is recorded on a supported host (Python 3.14, M4 P-03): the release policy itself (M5 Q-04).
  return { spawner, clock: new FakeClock(), hostEnv: HOST_ENV, cwd: PLUGIN_DIR, enginePython, policy: RELEASE_LOCK };
}

beforeEach(() => mockState.reset());

it(R('JT-20 the command spawns exactly `version` then `selftest`, nothing else, with the module entry point and scrubbed env'), async () => {
  const spawner = new FakeSpawner(script());
  const outcome = await runSelftest(deps(spawner));
  expect(spawner.requests.map((r) => r.args)).toEqual([
    ['-I', '-X', 'utf8', '-m', 'mdflow', 'version'],
    ['-I', '-X', 'utf8', '-m', 'mdflow', 'selftest'],
  ]);
  for (const request of spawner.requests) {
    expect(request.command).toBe(ENGINE_PYTHON);
    expect(request.shell).toBe(false);
    expect(request.cwd).toBe(PLUGIN_DIR);
    expect(request.env).not.toHaveProperty('MDFLOW_API_KEY');
    expect(JSON.stringify(request)).not.toContain(KEY_VALUE);
    expect(request.args.some((t) => /\.(png|pdf|json)$/i.test(t))).toBe(false);
  }
  expect(outcome.ok).toBe(true);
  expect(outcome.selftestExit).toBe(0);
  expect(outcome.gate?.enabled).toBe(true);
  expect(outcome.diagnostics).toEqual([]);
  expect(mockState.network).toEqual([]);
});

it(R('JT-20 a failing selftest or version gate is reported through localized diagnostics, never as success'), async () => {
  const failing = new FakeSpawner(script(2));
  const outcome = await runSelftest(deps(failing));
  expect(outcome.ok).toBe(false);
  expect(outcome.selftestExit).toBe(2);
  expect(outcome.diagnostics.length).toBeGreaterThan(0);
  for (const key of outcome.diagnostics) expect(key).toMatch(/^(shell|engine)\./);
  const gated = new FakeSpawner((request) => (subcommandOf(request) === 'version' ? { stdout: [fx71Bytes('version.protocol-2.json')], exit: { code: 0, signal: null } } : script()(request)));
  const blocked = await runSelftest(deps(gated));
  expect(gated.commands).toEqual(['version']);
  expect(blocked.ok).toBe(false);
  expect(blocked.selftestExit).toBeNull();
  expect(blocked.diagnostics).toContain('shell.RUNTIME');
});

it(R('JT-20 without a configured interpreter nothing is spawned and the outcome is a runtime diagnostic'), async () => {
  const spawner = new FakeSpawner(script());
  const outcome = await runSelftest(deps(spawner, null));
  expect(spawner.requests).toEqual([]);
  expect(outcome.ok).toBe(false);
  expect(outcome.gate).toBeNull();
  expect(outcome.diagnostics).toContain('shell.RUNTIME');
});
