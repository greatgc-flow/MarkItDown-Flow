/**
 * JT-12 / REQ-SHL-12: executable + argument array, `shell:false`, hidden
 * window; snapshot of ordered absolute inputs, cwd, output and cache roots
 * taken once; `plan` and the authorized `run` replay are identical apart from
 * the subcommand, `-o` and the authorization arguments; nested inputs keep
 * their logical paths (FX-71 evidence).
 */
import { req } from './req';
import { scrubEngineEnv } from '../src/pure/env';
import { comparablePath } from '../src/pure/paths';
import { decodeReport, type RunReport } from '../src/pure/protocol';
import {
  APPROVED_BY_MODAL,
  buildSpawnRequest,
  buildUtilityRequest,
  ENGINE_ARGV_PREFIX,
  engineSubcommand,
  engineWorkingDirectory,
  type JobSnapshot,
  renderYesFile,
  snapshotJob,
  SUBCOMMAND_INDEX,
} from '../src/process/launcher';
import { BOOTSTRAP_PROBE_CANDIDATES, collectSetupDiagnostics } from '../src/process/setup';
import { runSelftest } from '../src/process/selftest';
import type { SpawnRequest } from '../src/process/types';
import { probeVersion, RELEASE_LOCK, type VersionPolicy } from '../src/process/version-gate';
import { type CoordinatorDeps, defaultCacheDir, ShellCoordinator } from '../src/ui/coordinator';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Lines, fx71PlanObjects, fx71Text, FX71_ROOTS } from './fixtures/fx71';
import { approvedHashesIn, replayInvariantArgs } from './fixtures/protocol';
import { abs, ENGINE_PYTHON, HOME, HOST_ENV, KEY_VALUE, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-12');

/** The job working directory is the engine venv root of the selected interpreter (M3 N-02); this fixture's venv lies outside the vault. */
const CWD = engineWorkingDirectory(process.platform === 'win32' ? 'win32' : 'posix', ENGINE_PYTHON);
const INPUT_ROOT = abs(VAULT_ROOT, 'inbox');
const PLATFORM = process.platform === 'win32' ? 'win32' : 'posix';
/** FX-71 `version.json` is recorded on a supported host (Python 3.14, X-11 closed in M4): the release policy admits it as is. */
const RELEASE_LOCK_FOR_RECORDING: VersionPolicy = RELEASE_LOCK;
const OUT_DIR = abs(VAULT_ROOT, 'markitdown-output');
/** R38: the engine default `~/.mdflow/cache`, outside the vault and the plugin folder. */
const CACHE_DIR = abs(HOME, '.mdflow', 'cache');
const HASH_A = 'e81c750520319e685f3483f10caaca33856e78dd8afb348a9e447a4b2f89695f';
const HASH_B = 'f918a5c781905fce7e7eca0c08f41192e0e2d475f2867c9ad1f1e1514eb14e84';
const YES_FILE = abs(PLUGIN_DIR, 'consent', 'yes-0123456789abcdef-1.txt');
/** The shell writes this file before the replay; the oracle reads it back. */
const yesFiles: Record<string, string> = { [YES_FILE]: renderYesFile([HASH_A, HASH_B]) };
const readYes = (path: string): string | null => yesFiles[path] ?? null;

const INPUTS = [
  abs(INPUT_ROOT, '보고서', '3분기 결산.pdf'),
  abs(INPUT_ROOT, 'dir with spaces', 'x$(rm -rf ~).docx'),
  abs(INPUT_ROOT, 'q"uote\'d; && |.pdf'),
  abs(INPUT_ROOT, 'inputs'),
];

/** True when `candidate` is the vault root or lies under it (real-path comparison form). */
function insideVault(candidate: string): boolean {
  const c = comparablePath(PLATFORM, candidate);
  const v = comparablePath(PLATFORM, VAULT_ROOT);
  return c === v || c.startsWith(v + '/');
}

/** M3 N-02 oracle: isolated interpreter, UTF-8 stdio, module entry point, in that order, before anything else. */
function expectIsolatedArgv(request: SpawnRequest, command: string): void {
  expect(request.args[0]).toBe('-I');
  expect(request.args.slice(1, 3)).toEqual(['-X', 'utf8']);
  expect(request.args.slice(3, 5)).toEqual(['-m', 'mdflow']);
  expect(request.args.indexOf('-I')).toBeLessThan(request.args.indexOf('-m'));
  expect(request.args.filter((t) => t === '-I')).toHaveLength(1);
  expect(request.args[SUBCOMMAND_INDEX]).toBe(command);
  expect(engineSubcommand(request.args)).toBe(command);
  expect(request.args).not.toContain('-P');
  expect(insideVault(request.cwd)).toBe(false);
}

function snapshot(provider = settingsV2().provider): JobSnapshot {
  return snapshotJob({ settings: settingsV2({ provider }), inputs: INPUTS, cwd: CWD, outDir: OUT_DIR, cacheDir: CACHE_DIR });
}

it(R('JT-12 snapshotJob keeps ordered absolute inputs, cwd, output and cache roots once and freezes them'), () => {
  const snap = snapshot();
  expect(snap.enginePython).toBe(ENGINE_PYTHON);
  expect([...snap.inputs]).toEqual(INPUTS);
  expect(snap.cwd).toBe(CWD);
  expect(snap.outDir).toBe(OUT_DIR);
  expect(snap.cacheDir).toBe(CACHE_DIR);
  expect(Object.isFrozen(snap)).toBe(true);
  expect(Object.isFrozen(snap.inputs)).toBe(true);
  expect(() => {
    (snap.inputs as string[]).push('late');
  }).toThrow();
  expect(() => snapshotJob({ settings: settingsV2({ enginePython: null }), inputs: INPUTS, cwd: CWD, outDir: OUT_DIR, cacheDir: CACHE_DIR })).toThrow();
  expect(() => snapshotJob({ settings: settingsV2(), inputs: ['relative/a.pdf'], cwd: CWD, outDir: OUT_DIR, cacheDir: CACHE_DIR })).toThrow();
});

it(R('JT-12 spawn request is the absolute interpreter plus an argument array, shell false, hidden window, scrubbed env'), () => {
  const request = buildSpawnRequest(snapshot(), 'run', HOST_ENV);
  expect(request.command).toBe(ENGINE_PYTHON);
  expect(request.shell).toBe(false);
  expect(request.windowsHide).toBe(true);
  expect(request.cwd).toBe(CWD);
  expect(request.args.slice(0, SUBCOMMAND_INDEX + 1)).toEqual([...ENGINE_ARGV_PREFIX, 'run']);
  expect(request.env).toEqual(scrubEngineEnv(HOST_ENV, 'none'));
  expect(request.env).not.toHaveProperty('MDFLOW_API_KEY');
  expect(request.env).not.toHaveProperty('PYTHONPATH');
  expect(JSON.stringify(request)).not.toContain(KEY_VALUE);
  const remote = buildSpawnRequest(snapshot({ ...OPENAI_PROVIDER }), 'run', HOST_ENV);
  expect(remote.env.MDFLOW_API_KEY).toBe(KEY_VALUE);
  expect(remote.args).not.toContain(KEY_VALUE);
});

it(R('JT-12 spaces, Korean and shell metacharacters remain single argument tokens in selection order'), () => {
  const request = buildSpawnRequest(snapshot(), 'run', HOST_ENV);
  const positions = INPUTS.map((input) => request.args.indexOf(input));
  for (const [i, pos] of positions.entries()) expect({ input: INPUTS[i], pos }).toEqual({ input: INPUTS[i], pos: expect.any(Number) });
  for (const pos of positions) expect(pos).toBeGreaterThan(SUBCOMMAND_INDEX);
  expect([...positions].sort((a, b) => a - b)).toEqual(positions);
  expect(positions[1] - positions[0]).toBe(1);
  expect(positions[3] - positions[2]).toBe(1);
  // No token is a quoted or split rendering of an input.
  for (const token of request.args) {
    expect(token.startsWith('"') && token.endsWith('"')).toBe(false);
    expect(token).not.toBe('&&');
  }
  expect(request.args.filter((t) => t.includes('rm -rf'))).toEqual([INPUTS[1]]);
});

it(R('JT-12 -o is the validated vault destination and --cache is the engine default ~/.mdflow/cache (R38), passed directly'), () => {
  expect(CACHE_DIR).toBe(defaultCacheDir(PLATFORM, HOME));
  expect(insideVault(CACHE_DIR)).toBe(false);
  expect(comparablePath(PLATFORM, CACHE_DIR).startsWith(comparablePath(PLATFORM, PLUGIN_DIR) + '/')).toBe(false);
  const request = buildSpawnRequest(snapshot(), 'run', HOST_ENV);
  expect(request.args[request.args.indexOf('-o') + 1]).toBe(OUT_DIR);
  expect(request.args[request.args.indexOf('--cache') + 1]).toBe(CACHE_DIR);
  expect(request.args.filter((t) => t === '-o' || t === '--out')).toHaveLength(1);
  expect(request.args.filter((t) => t === '--cache')).toHaveLength(1);
  const plan = buildSpawnRequest(snapshot(), 'plan', HOST_ENV);
  expect(plan.args).not.toContain('-o');
  expect(plan.args).not.toContain('--out');
  expect(plan.args[plan.args.indexOf('--cache') + 1]).toBe(CACHE_DIR);
});

it(R('JT-12 original plan and authorized run replay share inputs, cwd, env, output and cache; only subcommand and authorization differ'), () => {
  const snap = snapshot({ ...OPENAI_PROVIDER });
  const plan = buildSpawnRequest(snap, 'plan', HOST_ENV);
  const run = buildSpawnRequest(snap, 'run', HOST_ENV, { yesFile: YES_FILE, approvedBy: APPROVED_BY_MODAL });
  expect(run.command).toBe(plan.command);
  expect(run.cwd).toBe(plan.cwd);
  expect(run.env).toEqual(plan.env);
  expect(plan.args[SUBCOMMAND_INDEX]).toBe('plan');
  expect(run.args[SUBCOMMAND_INDEX]).toBe('run');
  expect(replayInvariantArgs(run.args)).toEqual(replayInvariantArgs(plan.args));
  expect(approvedHashesIn(run.args, readYes)).toEqual([HASH_A, HASH_B]);
  expect(run.args).not.toContain('--yes');
  expect(approvedHashesIn(plan.args, readYes)).toEqual([]);
  expect(run.args[run.args.indexOf('--approved-by') + 1]).toBe('plugin:modal');
  expect(plan.args).not.toContain('--approved-by');
  // Inputs stay in original order in both and directly follow the subcommand.
  expect(run.args.slice(SUBCOMMAND_INDEX + 1, SUBCOMMAND_INDEX + 1 + INPUTS.length)).toEqual(INPUTS);
  expect(plan.args.slice(SUBCOMMAND_INDEX + 1, SUBCOMMAND_INDEX + 1 + INPUTS.length)).toEqual(INPUTS);
  // A second build from the same snapshot is byte-identical (snapshot taken once).
  expect(buildSpawnRequest(snap, 'run', HOST_ENV, { yesFile: YES_FILE, approvedBy: APPROVED_BY_MODAL })).toEqual(run);
});

it(R('JT-12 directories are passed as roots so nested inputs/sub/a.pdf keeps logical sub/a.pdf and the same output path (FX-71)'), () => {
  // The recorder passed the roots `inputs` and `large`; the engine reports logical paths per root.
  const report = decodeReport(fx71Text('approve-required.stdout.json'));
  expect(report.ok).toBe(true);
  const files = (report as { ok: true; value: RunReport }).value.files;
  expect(files.map((f) => [f.path, f.root])).toEqual([
    ['b c.docx', 0],
    ['memo.txt', 0],
    ['sub/a.pdf', 0],
    ['보고서/3분기 결산.pdf', 0],
    ['긴 문서.pdf', 1],
  ]);
  const fileEnds = fx71Lines('approve-required.progress.jsonl').filter((e) => (e as { ev: string }).ev === 'file_end') as { file: string; outputs: string[] }[];
  expect(fileEnds.find((e) => e.file === 'sub/a.pdf')?.outputs).toEqual(['sub/a.pdf.md']);
  // The shell passes the selected directory roots verbatim, never the nested file as its own root.
  const roots = [abs(INPUT_ROOT, 'inputs'), abs(INPUT_ROOT, 'large')];
  const snap = snapshotJob({ settings: settingsV2(), inputs: roots, cwd: CWD, outDir: OUT_DIR, cacheDir: CACHE_DIR });
  const request = buildSpawnRequest(snap, 'run', HOST_ENV);
  expect(request.args.slice(SUBCOMMAND_INDEX + 1, SUBCOMMAND_INDEX + 3)).toEqual(roots);
  for (const nested of FX71_ROOTS.inputs) expect(request.args.some((t) => t.endsWith(nested))).toBe(false);
  const replay = buildSpawnRequest(snap, 'run', HOST_ENV, { yesFile: YES_FILE, approvedBy: APPROVED_BY_MODAL });
  expect(replay.args.slice(SUBCOMMAND_INDEX + 1, SUBCOMMAND_INDEX + 3)).toEqual(roots);
  expect(replay.cwd).toBe(request.cwd);
});

it(R('JT-12 every engine spawn starts with -I -X utf8 -m mdflow (isolated interpreter: the working directory is never sys.path[0]) and its cwd is the engine venv root (M3 N-02)'), async () => {
  const snap = snapshot({ ...OPENAI_PROVIDER });
  expectIsolatedArgv(buildSpawnRequest(snap, 'plan', HOST_ENV), 'plan');
  expectIsolatedArgv(buildSpawnRequest(snap, 'run', HOST_ENV, { yesFile: YES_FILE, approvedBy: APPROVED_BY_MODAL }), 'run');
  expectIsolatedArgv(buildUtilityRequest(ENGINE_PYTHON, 'version', HOST_ENV, CWD), 'version');
  expectIsolatedArgv(buildUtilityRequest(ENGINE_PYTHON, 'selftest', HOST_ENV, CWD), 'selftest');
  expect(ENGINE_ARGV_PREFIX).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow']);
  expect(SUBCOMMAND_INDEX).toBe(5);
  // The fixed job cwd is the venv root of the selected interpreter; in this fixture it is outside the vault.
  expect(CWD).toBe(process.platform === 'win32' ? 'C:\\mdflow-venvs\\2.0.0' : '/home/alice/mdflow-venvs/2.0.0');
  expect(insideVault(CWD)).toBe(false);
  expect(engineWorkingDirectory('posix', '/usr/bin/python3')).toBe('/usr');
  expect(engineWorkingDirectory('win32', 'C:\\python.exe')).toBe('C:\\');
  expect(engineWorkingDirectory('posix', '/python')).toBe('/');
  // Bootstrap `--version` probes are isolated too, so a stray `sitecustomize` in the probe cwd cannot run.
  for (const candidate of BOOTSTRAP_PROBE_CANDIDATES) {
    expect(candidate.args).toContain('-I');
    expect(candidate.args.indexOf('-I')).toBeLessThan(candidate.args.indexOf('--version'));
  }
});

it(R('JT-12 the coordinator, the version probe, the selftest command and the setup diagnostics all spawn with the isolated prefix and the engine venv root as cwd (M3 N-02)'), async () => {
  const fs = new FakeFs({ directories: [VAULT_ROOT, OUT_DIR, INPUT_ROOT, PLUGIN_DIR, CACHE_DIR] });
  const spawner = new FakeSpawner(() => ({ blocked: true, exit: { code: 0, signal: null } }));
  const deps: CoordinatorDeps = {
    spawner,
    fs,
    spoolFs: new FakeSpoolFs(fs, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: PLATFORM,
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    homeDir: HOME,
    settings: () => settingsV2({ provider: { ...OPENAI_PROVIDER } }),
    gate: () => ({ enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.7', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } }),
    consent: async () => ({ approved: false }),
    notify: () => undefined,
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
  };
  const coordinator = new ShellCoordinator(deps);
  const result = await coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  expect(result.accepted).toBe(true);
  if (result.accepted) {
    expect(result.snapshot.cwd).toBe(CWD);
    expect(insideVault(result.snapshot.cwd)).toBe(false);
    expect(result.snapshot.cacheDir).toBe(CACHE_DIR);
  }
  await flush();
  expect(spawner.requests).toHaveLength(1);
  expectIsolatedArgv(spawner.requests[0], 'plan');
  expect(spawner.requests[0].cwd).toBe(CWD);
  coordinator.cancel();
  await coordinator.current;

  const probes = new FakeSpawner(() => ({ stdout: [fx71Bytes('version.json')], exit: { code: 0, signal: null } }));
  const clock = new FakeClock();
  await probeVersion(ENGINE_PYTHON, { spawner: probes, clock, hostEnv: HOST_ENV, cwd: CWD });
  await runSelftest({ spawner: probes, clock, hostEnv: HOST_ENV, cwd: CWD, enginePython: ENGINE_PYTHON, policy: RELEASE_LOCK_FOR_RECORDING });
  await collectSetupDiagnostics({ spawner: probes, clock, hostEnv: HOST_ENV, platform: PLATFORM, cwd: CWD, enginePython: ENGINE_PYTHON, policy: RELEASE_LOCK_FOR_RECORDING });
  expect(probes.commands).toEqual(['version', 'version', 'selftest', 'version']);
  for (const request of probes.requests) {
    expectIsolatedArgv(request, request.args[SUBCOMMAND_INDEX]);
    expect(request.cwd).toBe(CWD);
  }
});

it(R('JT-12 the configured Base URL reaches the engine as MDFLOW_BASE_URL for openai-compatible (settings win over the host value); provider none forwards none; never on argv'), () => {
  const host = { ...HOST_ENV, MDFLOW_BASE_URL: 'https://host-proxy.example/v1' };
  const configured = 'http://127.0.0.1:11434/v1';
  const remote = buildSpawnRequest(snapshot({ ...OPENAI_PROVIDER, baseUrl: configured }), 'plan', host);
  expect(remote.env.MDFLOW_BASE_URL).toBe(configured);
  expect(remote.args).not.toContain(configured);
  expect(buildSpawnRequest(snapshot({ ...OPENAI_PROVIDER, baseUrl: configured }), 'run', host).env.MDFLOW_BASE_URL).toBe(configured);
  // Without a host value the setting is still forwarded.
  expect(buildSpawnRequest(snapshot({ ...OPENAI_PROVIDER }), 'plan', HOST_ENV).env.MDFLOW_BASE_URL).toBe(OPENAI_PROVIDER.baseUrl);
  const none = buildSpawnRequest(snapshot(), 'run', host);
  expect(none.env).not.toHaveProperty('MDFLOW_BASE_URL');
  expect(none.env).not.toHaveProperty('MDFLOW_API_KEY');
  // FX-71: the engine's displayed destination is the canonical endpoint under the configured base URL.
  const plans = fx71PlanObjects('plan-mixed.stdout.json') as { approved: { provider: { destination: string | null } } }[];
  expect(plans.length).toBeGreaterThan(0);
  for (const plan of plans) expect(plan.approved.provider.destination).toBe(`${OPENAI_PROVIDER.baseUrl}/chat/completions`);
});

it(R('JT-12 version and selftest utility requests use the isolated module entry point with no other arguments'), () => {
  const version = buildUtilityRequest(ENGINE_PYTHON, 'version', HOST_ENV, CWD);
  expect(version.command).toBe(ENGINE_PYTHON);
  expect(version.args).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow', 'version']);
  expect(version.shell).toBe(false);
  expect(version.windowsHide).toBe(true);
  expect(version.cwd).toBe(CWD);
  expect(version.env).toEqual(scrubEngineEnv(HOST_ENV, 'none'));
  expect(buildUtilityRequest(ENGINE_PYTHON, 'selftest', HOST_ENV, CWD).args).toEqual(['-I', '-X', 'utf8', '-m', 'mdflow', 'selftest']);
});
