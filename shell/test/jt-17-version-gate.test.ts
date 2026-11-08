/**
 * JT-17 / REQ-SHL-17: the complete SPEC 10.1 `version` response gates jobs.
 * FX-71 `version.json` is the actual packaged response; derived variants
 * remove or alter one field each. Protocol 2, schema 2, wrong Pillow/renderer
 * and every missing field block before conversion.
 */
import { req } from './req';
import {
  evaluateVersionResponse,
  probeVersion,
  RELEASE_LOCK,
  VERSION_PROBE_TIMEOUT_MS,
  VERSION_REQUIRED_FIELDS,
  type VersionGate,
  type VersionPolicy,
} from '../src/process/version-gate';
import { ShellCoordinator, type CoordinatorDeps } from '../src/ui/coordinator';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Manifest, fx71Text } from './fixtures/fx71';
import { abs, ENGINE_PYTHON, HOST_ENV, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-17');

/** The recording host ran Python 3.15 (experimental per REQ-GEN-03); this policy admits it for the "actual response" checks. */
const RECORDING_HOST_POLICY: VersionPolicy = { ...RELEASE_LOCK, pythonMaxExclusive: [3, 16, 0] };

function blocked(gate: VersionGate): { reason: string; field?: string } {
  if (gate.enabled) throw new Error('expected a blocked gate');
  return { reason: gate.reason, field: gate.field };
}

it(R('JT-17 the actual packaged version response passes the complete gate and matches the recorded engine identity'), () => {
  expect([...VERSION_REQUIRED_FIELDS].sort()).toEqual(['markitdown-gc', 'mdflow', 'pillow', 'platform', 'protocol', 'pypdfium2', 'python', 'triage_schema']);
  const gate = evaluateVersionResponse(fx71Text('version.json'), RECORDING_HOST_POLICY);
  expect(gate.enabled).toBe(true);
  if (!gate.enabled) return;
  expect(gate.info).toEqual(fx71Manifest().engine);
  expect(gate.info.protocol).toBe(1);
  expect(gate.info.triage_schema).toBe(1);
  // Release lock values are exact lock entries equal to the packaged response, not SPEC examples.
  expect(RELEASE_LOCK.pypdfium2).toBe(gate.info.pypdfium2);
  expect(RELEASE_LOCK.pillow).toBe(gate.info.pillow);
  expect(RELEASE_LOCK.pillow).not.toBe('11.0.0');
  expect(RELEASE_LOCK.pypdfium2).not.toBe('4.30.0');
});

it(R('JT-17 the default policy admits Python 3.10-3.14 only; the 3.15 recording host is blocked as unsupported'), () => {
  expect(blocked(evaluateVersionResponse(fx71Text('version.json')))).toEqual({ reason: 'python', field: 'python' });
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  const withPython = (python: string): string => JSON.stringify({ ...base, python });
  for (const good of ['3.10.0', '3.11.9', '3.12.4', '3.13.1', '3.14.2']) expect(evaluateVersionResponse(withPython(good)).enabled).toBe(true);
  for (const bad of ['3.9.19', '3.15.0', '2.7.18', 'three', '']) expect(blocked(evaluateVersionResponse(withPython(bad))).reason).toBe('python');
});

it(R('JT-17 each missing required field blocks and names the field; an additional optional field is ignored'), () => {
  for (const field of VERSION_REQUIRED_FIELDS) {
    const gate = evaluateVersionResponse(fx71Text(`version.missing-${field}.json`), RECORDING_HOST_POLICY);
    expect(blocked(gate)).toEqual({ reason: 'missing_field', field });
  }
  const extra = evaluateVersionResponse(fx71Text('version.unknown-optional-field.json'), RECORDING_HOST_POLICY);
  expect(extra.enabled).toBe(true);
  if (extra.enabled) expect(extra.info).not.toHaveProperty('future_optional');
});

it(R('JT-17 protocol 2, schema 2, string protocol, wrong Pillow, wrong renderer and out-of-range Core each block with the exact reason'), () => {
  const cases: [string, string, string | undefined][] = [
    ['version.protocol-2.json', 'protocol', 'protocol'],
    ['version.schema-2.json', 'triage_schema', 'triage_schema'],
    ['version.protocol-string.json', 'bad_type', 'protocol'],
    ['version.wrong-pillow.json', 'pillow', 'pillow'],
    ['version.wrong-renderer.json', 'pypdfium2', 'pypdfium2'],
    ['version.core-out-of-range.json', 'core', 'markitdown-gc'],
  ];
  for (const [name, reason, field] of cases) {
    const gate = evaluateVersionResponse(fx71Text(name), RECORDING_HOST_POLICY);
    expect({ name, ...blocked(gate) }).toEqual({ name, reason, field });
    if (!gate.enabled) expect(gate.diagnostic).toBe('shell.RUNTIME');
  }
});

it(R('JT-17 engine and Core ranges follow SPEC (engine >=2.0,<2.1 on the release segment; Core >=0.3.5,<0.4); malformed text blocks'), () => {
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  const withField = (key: string, value: unknown): string => JSON.stringify({ ...base, [key]: value });
  expect(evaluateVersionResponse(withField('mdflow', '2.0.0'), RECORDING_HOST_POLICY).enabled).toBe(true);
  expect(evaluateVersionResponse(withField('mdflow', '2.0.3'), RECORDING_HOST_POLICY).enabled).toBe(true);
  expect(evaluateVersionResponse(withField('mdflow', '2.0.0.dev0'), RECORDING_HOST_POLICY).enabled).toBe(true);
  for (const bad of ['2.1.0', '1.9.9', '3.0.0', 'latest']) expect(blocked(evaluateVersionResponse(withField('mdflow', bad), RECORDING_HOST_POLICY)).reason).toBe('engine');
  expect(evaluateVersionResponse(withField('markitdown-gc', '0.3.9'), RECORDING_HOST_POLICY).enabled).toBe(true);
  for (const bad of ['0.3.4', '0.4.0', '1.0.0']) expect(blocked(evaluateVersionResponse(withField('markitdown-gc', bad), RECORDING_HOST_POLICY)).reason).toBe('core');
  expect(blocked(evaluateVersionResponse(withField('platform', ''), RECORDING_HOST_POLICY)).reason).toBe('platform');
  expect(blocked(evaluateVersionResponse(withField('pillow', 13), RECORDING_HOST_POLICY))).toEqual({ reason: 'bad_type', field: 'pillow' });
  for (const text of ['', 'not json', '[]', 'null', '{"mdflow": "2.0.0"} trailing']) expect(blocked(evaluateVersionResponse(text, RECORDING_HOST_POLICY)).reason).toMatch(/not_json|missing_field/);
});

async function probe(script: ScriptedChild, advanceMs = 0): Promise<{ gate: VersionGate; spawner: FakeSpawner; clock: FakeClock }> {
  const spawner = new FakeSpawner(() => script);
  const clock = new FakeClock();
  const pending = probeVersion(ENGINE_PYTHON, { spawner, clock, hostEnv: HOST_ENV, cwd: PLUGIN_DIR, policy: RECORDING_HOST_POLICY });
  await flush();
  if (advanceMs > 0) await clock.advance(advanceMs);
  const gate = await pending;
  return { gate, spawner, clock };
}

it(R('JT-17 the version probe spawns exactly `-m mdflow version`, decodes stdout and times out after five seconds'), async () => {
  const good = await probe({ stdout: [fx71Bytes('version.json')], exit: { code: 0, signal: null } });
  expect(good.spawner.requests).toHaveLength(1);
  expect(good.spawner.requests[0].command).toBe(ENGINE_PYTHON);
  expect(good.spawner.requests[0].args).toEqual(['-m', 'mdflow', 'version']);
  expect(good.spawner.requests[0].shell).toBe(false);
  expect(good.gate.enabled).toBe(true);
  expect(VERSION_PROBE_TIMEOUT_MS).toBe(5000);
  const hung = await probe({ blocked: true, exit: { code: 0, signal: null }, cooperative: 'ignore' }, VERSION_PROBE_TIMEOUT_MS);
  expect(blocked(hung.gate).reason).toBe('timeout');
  expect(hung.spawner.children[0].terminated).toBe(true);
  const failed = await probe({ stdout: [], exit: { code: 1, signal: null } });
  expect(blocked(failed.gate).reason).toBe('exit');
  const absent = await probe({ spawnError: new Error('ENOENT'), exit: { code: null, signal: null } });
  expect(blocked(absent.gate).reason).toBe('spawn_failed');
});

it(R('JT-17 a blocked gate yields zero conversions: submit is refused with shell.RUNTIME and nothing is spawned'), async () => {
  const spawner = new FakeSpawner(() => ({ exit: { code: 0, signal: null } }));
  const fs = new FakeFs({ directories: [VAULT_ROOT, abs(VAULT_ROOT, 'markitdown-output'), abs(VAULT_ROOT, 'inbox'), PLUGIN_DIR] });
  const notices: string[] = [];
  const deps: CoordinatorDeps = {
    spawner,
    fs,
    spoolFs: new FakeSpoolFs(fs, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    locale: 'en',
    settings: () => settingsV2(),
    gate: () => evaluateVersionResponse(fx71Text('version.protocol-2.json'), RECORDING_HOST_POLICY),
    consent: async () => ({ approved: false }),
    notify: (key) => {
      notices.push(key);
    },
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
  };
  const coordinator = new ShellCoordinator(deps);
  const result = await coordinator.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command');
  expect(result).toEqual({ accepted: false, diagnostic: 'shell.RUNTIME' });
  expect(spawner.requests).toEqual([]);
  expect(notices).toContain('shell.RUNTIME');
  expect(coordinator.active).toBe(false);
});
