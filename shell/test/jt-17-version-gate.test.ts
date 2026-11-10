/**
 * JT-17 / REQ-SHL-17: the complete SPEC 10.1 `version` response gates jobs.
 * FX-71 `version.json` is the actual packaged response; derived variants
 * remove or alter one field each. Protocol 2, schema 2, out-of-range
 * Pillow/renderer (R27 compatibility ranges) and every missing field block
 * before conversion.
 */
import { req } from './req';
import {
  evaluateVersionResponse,
  probeVersion,
  RELEASE_LOCK,
  releaseSegment,
  VERSION_PROBE_BACKOFF_MS,
  VERSION_PROBE_TIMEOUT_MS,
  VERSION_REQUIRED_FIELDS,
  type VersionGate,
} from '../src/process/version-gate';
import { ShellCoordinator, type CoordinatorDeps } from '../src/ui/coordinator';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Manifest, fx71Text } from './fixtures/fx71';
import { abs, ENGINE_PYTHON, HOME, HOST_ENV, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-17');

// FX-71 was re-recorded on a supported host (Python 3.14, Core 0.3.7; M4 P-03 / X-11), so every
// "actual response" check below runs against `RELEASE_LOCK` itself; no widened or aliased policy remains (M5 Q-04).

function blocked(gate: VersionGate): { reason: string; field?: string } {
  if (gate.enabled) throw new Error('expected a blocked gate');
  return { reason: gate.reason, field: gate.field };
}

it(R('JT-17 the actual packaged version response passes the complete gate and matches the recorded engine identity'), () => {
  expect([...VERSION_REQUIRED_FIELDS].sort()).toEqual(['markitdown-gc', 'mdflow', 'pillow', 'platform', 'protocol', 'pypdfium2', 'python', 'triage_schema']);
  const gate = evaluateVersionResponse(fx71Text('version.json'), RELEASE_LOCK);
  expect(gate.enabled).toBe(true);
  if (!gate.enabled) return;
  expect(gate.info).toMatchObject(Object.fromEntries(VERSION_REQUIRED_FIELDS.map((key) => [key, fx71Manifest().engine[key]])));
  // Supported recording host (M4 P-03): Python 3.14.x inside the 3.10-3.14 policy, Core 0.3.7 reference baseline.
  expect(releaseSegment(gate.info.python)).toEqual([3, 14, expect.any(Number)]);
  expect(gate.info['markitdown-gc']).toBe('0.3.7');
  expect(evaluateVersionResponse(fx71Text('version.json')).enabled).toBe(true);
  expect(gate.info.protocol).toBe(1);
  expect(gate.info.triage_schema).toBe(1);
  // R27: renderer/Pillow are compatibility ranges, not exact lock pins; the recorded CI identity lies inside them
  // and the exact installed versions are still carried in `info` for diagnosis.
  expect(gate.info.pypdfium2).toBe('5.15.1');
  expect(gate.info.pillow).toBe('13.0.0');
  expect(releaseSegment(gate.info.pypdfium2)).toEqual([5, 15, 1]);
  expect(releaseSegment(gate.info.pillow)).toEqual([13, 0, 0]);
  expect(RELEASE_LOCK.pypdfium2Min).toEqual([5, 0, 0]);
  expect(RELEASE_LOCK.pypdfium2MaxExclusive).toEqual([6, 0, 0]);
  expect(RELEASE_LOCK.pillowMin).toEqual([11, 0, 0]);
  expect(RELEASE_LOCK.pillowMaxExclusive).toEqual([14, 0, 0]);
});

it(R('JT-17 R27 range-resolved renderer/Pillow installs are admitted inside the compatibility ranges and blocked outside them'), () => {
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  const withField = (key: string, value: unknown): string => JSON.stringify({ ...base, [key]: value });
  for (const good of ['5.0.0', '5.15.1', '5.99.9']) expect(evaluateVersionResponse(withField('pypdfium2', good), RELEASE_LOCK).enabled).toBe(true);
  for (const bad of ['4.30.0', '6.0.0', '6.15.1', 'latest']) expect(blocked(evaluateVersionResponse(withField('pypdfium2', bad), RELEASE_LOCK))).toEqual({ reason: 'pypdfium2', field: 'pypdfium2' });
  for (const good of ['11.0.0', '12.1.0', '13.0.0', '13.9.9']) expect(evaluateVersionResponse(withField('pillow', good), RELEASE_LOCK).enabled).toBe(true);
  for (const bad of ['10.4.0', '14.0.0', '15.0.0', '']) expect(blocked(evaluateVersionResponse(withField('pillow', bad), RELEASE_LOCK))).toEqual({ reason: 'pillow', field: 'pillow' });
});

it(R('JT-17 the default policy admits Python 3.10-3.14 only; the derived 3.15 variant is blocked as unsupported'), () => {
  expect(blocked(evaluateVersionResponse(fx71Text('version.python-3.15.json')))).toEqual({ reason: 'python', field: 'python' });
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  const withPython = (python: string): string => JSON.stringify({ ...base, python });
  for (const good of ['3.10.0', '3.11.9', '3.12.4', '3.13.1', '3.14.2']) expect(evaluateVersionResponse(withPython(good)).enabled).toBe(true);
  for (const bad of ['3.9.19', '3.15.0', '2.7.18', 'three', '']) expect(blocked(evaluateVersionResponse(withPython(bad))).reason).toBe('python');
});

it(R('JT-17 each missing required field blocks and names the field; an additional optional field is ignored'), () => {
  for (const field of VERSION_REQUIRED_FIELDS) {
    const gate = evaluateVersionResponse(fx71Text(`version.missing-${field}.json`), RELEASE_LOCK);
    expect(blocked(gate)).toEqual({ reason: 'missing_field', field });
  }
  const extra = evaluateVersionResponse(fx71Text('version.unknown-optional-field.json'), RELEASE_LOCK);
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
    ['version.core-unavailable.json', 'core', 'markitdown-gc'],
  ];
  for (const [name, reason, field] of cases) {
    const gate = evaluateVersionResponse(fx71Text(name), RELEASE_LOCK);
    expect({ name, ...blocked(gate) }).toEqual({ name, reason, field });
    if (!gate.enabled) expect(gate.diagnostic).toBe('shell.RUNTIME');
  }
});

it(R('JT-17 engine and Core ranges follow SPEC (engine >=2.0,<2.1 on the release segment; Core >=0.3.7,<0.4); malformed text blocks'), () => {
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  const withField = (key: string, value: unknown): string => JSON.stringify({ ...base, [key]: value });
  expect(evaluateVersionResponse(withField('mdflow', '2.0.0'), RELEASE_LOCK).enabled).toBe(true);
  expect(evaluateVersionResponse(withField('mdflow', '2.0.3'), RELEASE_LOCK).enabled).toBe(true);
  expect(evaluateVersionResponse(withField('mdflow', '2.0.0.dev0'), RELEASE_LOCK).enabled).toBe(true);
  for (const bad of ['2.1.0', '1.9.9', '3.0.0', 'latest']) expect(blocked(evaluateVersionResponse(withField('mdflow', bad), RELEASE_LOCK)).reason).toBe('engine');
  expect(evaluateVersionResponse(withField('markitdown-gc', '0.3.9'), RELEASE_LOCK).enabled).toBe(true);
  for (const bad of ['0.3.4', '0.3.5', '0.3.6', '0.4.0', '1.0.0']) expect(blocked(evaluateVersionResponse(withField('markitdown-gc', bad), RELEASE_LOCK)).reason).toBe('core');
  expect(blocked(evaluateVersionResponse(withField('platform', ''), RELEASE_LOCK)).reason).toBe('platform');
  expect(blocked(evaluateVersionResponse(withField('pillow', 13), RELEASE_LOCK))).toEqual({ reason: 'bad_type', field: 'pillow' });
  for (const text of ['', 'not json', '[]', 'null', '{"mdflow": "2.0.0"} trailing']) expect(blocked(evaluateVersionResponse(text, RELEASE_LOCK)).reason).toMatch(/not_json|missing_field/);
});

it(R('JT-17 version syntax matches both steps of the package gate (test_pt_release.py: character regex, then packaging.Version): PEP 440 public versions are admitted, anything else is rejected (M4 P-02 / M3-V04 / M5 Q-01)'), () => {
  // Same release segment on both sides for valid spellings (`version_tuple` takes the leading dotted integers).
  for (const [text, segment] of [
    ['5.15.1', [5, 15, 1]],
    ['5.15.1rc1', [5, 15, 1]],
    ['5.15.1.post1', [5, 15, 1]],
    ['2.0.0.dev0', [2, 0, 0]],
    ['3.14', [3, 14, 0]],
    ['13.0.0+local', [13, 0, 0]],
    ['1.2.3a1.dev4', [1, 2, 3]],
    ['3.14.0rc1', [3, 14, 0]],
    ['0.3.6rc1', [0, 3, 6]],
    ['5.15.1-1', [5, 15, 1]], // implicit post release
    ['5.15.1.post', [5, 15, 1]], // implicit post number
    ['5.15.1rc', [5, 15, 1]], // implicit pre-release number
    ['5.15.1b2.post1.dev3+ubuntu.1', [5, 15, 1]],
    ['5.15.1RC1', [5, 15, 1]], // packaging is case-insensitive
    ['5.15.1.alpha.2', [5, 15, 1]],
    ['3.14.10.1', [3, 14, 10]], // release segments beyond the third are ignored
  ] as const) {
    expect({ text, segment: releaseSegment(text) }).toEqual({ text, segment });
  }
  // Rejected by `re.fullmatch(r"[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)")` and therefore by the shell too.
  for (const bad of ['5.15.1???', ' 5.15.1', '5.15.1 ', '5', 'v5.15.1', '5.15.1!', '5.15.1/2', '5..1', '', 'latest', '5.15.1\n', '1!5.15.1', '5.15.1_1']) {
    expect({ bad, segment: releaseSegment(bad) }).toEqual({ bad, segment: null });
  }
  // Admitted by the character regex but rejected by `packaging.version.Version(text)` (InvalidVersion): the shell
  // must agree with the second step as well (M5 Q-01).
  for (const bad of ['3.14garbage', '5.15.1abc', '5.15.1..1', '5.15.1+', '5.15.1a1b2', '5.15.1.', '5.15.1-', '5.15.1+local..x', '5.15.1.dev0.dev0', '5.15.1.post1rc1', '5.15.1+l_x']) {
    expect({ bad, segment: releaseSegment(bad) }).toEqual({ bad, segment: null });
  }
  // The twelve T-GEN-96 parameters of the package oracle, field by field, with the field's own blocked reason.
  const base = JSON.parse(fx71Text('version.json')) as Record<string, unknown>;
  const withField = (key: string, value: unknown): string => JSON.stringify({ ...base, [key]: value });
  const reasonOf: Record<string, string> = { python: 'python', mdflow: 'engine', 'markitdown-gc': 'core', pypdfium2: 'pypdfium2', pillow: 'pillow' };
  const tGen96: [string, string, boolean][] = [
    ['python', '3.14garbage', false], ['python', '3.14.0rc1', true],
    ['mdflow', '2.0.0???', false], ['mdflow', '2.0.0.dev0', true],
    ['markitdown-gc', '0.3.6???', false], ['markitdown-gc', '0.3.7rc1', true],
    ['pypdfium2', '5.15.1???', false], ['pypdfium2', ' 5.15.1', false],
    ['pypdfium2', '5.15.1rc1', true], ['pypdfium2', '5.15.1.post1', true],
    ['pillow', '13.0.0???', false], ['pillow', '13.0.0+local', true],
  ];
  for (const [field, value, enabled] of tGen96) {
    const gate = evaluateVersionResponse(withField(field, value));
    expect({ field, value, enabled: gate.enabled }).toEqual({ field, value, enabled });
    if (!gate.enabled) expect({ value, blocked: blocked(gate) }).toEqual({ value, blocked: { reason: reasonOf[field], field } });
  }
  for (const [field, value] of [['pypdfium2', '5.15.1abc'], ['pillow', '13.0.0..1'], ['mdflow', '2.0.0+'], ['markitdown-gc', '0.3.6a1b2'], ['python', '3.14.2garbage']]) {
    expect(blocked(evaluateVersionResponse(withField(field, value)))).toEqual({ reason: reasonOf[field], field });
  }
  for (const [field, value] of [['pypdfium2', '5.15.1-1'], ['pillow', '13.0.0+local'], ['mdflow', '2.0.0rc1'], ['markitdown-gc', '0.3.7.post1'], ['python', '3.14.0rc1']]) {
    expect({ field, value, enabled: evaluateVersionResponse(withField(field, value)).enabled }).toEqual({ field, value, enabled: true });
  }
});

async function probe(script: ScriptedChild, ...advanceSteps: number[]): Promise<{ gate: VersionGate; spawner: FakeSpawner; clock: FakeClock }> {
  const spawner = new FakeSpawner(() => script);
  const clock = new FakeClock();
  const pending = probeVersion(ENGINE_PYTHON, { spawner, clock, hostEnv: HOST_ENV, cwd: PLUGIN_DIR, policy: RELEASE_LOCK });
  await flush();
  for (const ms of advanceSteps) await clock.advance(ms);
  const gate = await pending;
  return { gate, spawner, clock };
}

it(R('JT-17 the version probe spawns exactly `-I -X utf8 -m mdflow version`, decodes stdout and times out after five seconds'), async () => {
  const good = await probe({ stdout: [fx71Bytes('version.json')], exit: { code: 0, signal: null } });
  expect(good.spawner.requests).toHaveLength(1);
  expect(good.spawner.requests[0].command).toBe(ENGINE_PYTHON);
  expect(good.spawner.requests[0].args).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow', 'version']);
  expect(good.spawner.requests[0].shell).toBe(false);
  expect(good.gate.enabled).toBe(true);
  expect(VERSION_PROBE_TIMEOUT_MS).toBe(5000);
  // M6-01: a timeout is retried once after a backoff; both attempts are terminated at five seconds.
  const hung = await probe({ blocked: true, exit: { code: 0, signal: null }, cooperative: 'ignore' }, VERSION_PROBE_TIMEOUT_MS, VERSION_PROBE_BACKOFF_MS, VERSION_PROBE_TIMEOUT_MS);
  expect(blocked(hung.gate).reason).toBe('timeout');
  expect(hung.spawner.requests).toHaveLength(2);
  expect(hung.spawner.children.every((child) => child.terminated)).toBe(true);
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
    homeDir: HOME,
    settings: () => settingsV2(),
    gate: () => evaluateVersionResponse(fx71Text('version.protocol-2.json'), RELEASE_LOCK),
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
