/**
 * JT-12 / REQ-SHL-12: executable + argument array, `shell:false`, hidden
 * window; snapshot of ordered absolute inputs, cwd, output and cache roots
 * taken once; `plan` and the authorized `run` replay are identical apart from
 * the subcommand, `-o` and the authorization arguments; nested inputs keep
 * their logical paths (FX-71 evidence).
 */
import { req } from './req';
import { scrubEngineEnv } from '../src/pure/env';
import { decodeReport, type RunReport } from '../src/pure/protocol';
import { APPROVED_BY_MODAL, buildSpawnRequest, buildUtilityRequest, type JobSnapshot, renderYesFile, snapshotJob } from '../src/process/launcher';
import { fx71Lines, fx71PlanObjects, fx71Text, FX71_ROOTS } from './fixtures/fx71';
import { approvedHashesIn, replayInvariantArgs } from './fixtures/protocol';
import { abs, ENGINE_PYTHON, HOST_ENV, KEY_VALUE, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-12');

const CWD = abs(VAULT_ROOT, 'inbox');
const OUT_DIR = abs(VAULT_ROOT, 'markitdown-output');
const CACHE_DIR = abs(PLUGIN_DIR, 'cache');
const HASH_A = 'a80d66b3fa9f7d95ecc3dba770b6eaf01cd8ddd4934e5d0c66d31ea703b5efda';
const HASH_B = 'f918a5c781905fce7e7eca0c08f41192e0e2d475f2867c9ad1f1e1514eb14e84';
const YES_FILE = abs(PLUGIN_DIR, 'consent', 'yes-0123456789abcdef-1.txt');
/** The shell writes this file before the replay; the oracle reads it back. */
const yesFiles: Record<string, string> = { [YES_FILE]: renderYesFile([HASH_A, HASH_B]) };
const readYes = (path: string): string | null => yesFiles[path] ?? null;

const INPUTS = [
  abs(CWD, '보고서', '3분기 결산.pdf'),
  abs(CWD, 'dir with spaces', 'x$(rm -rf ~).docx'),
  abs(CWD, 'q"uote\'d; && |.pdf'),
  abs(CWD, 'inputs'),
];

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
  expect(request.args.slice(0, 3)).toEqual(['-m', 'mdflow', 'run']);
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
  for (const pos of positions) expect(pos).toBeGreaterThan(2);
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

it(R('JT-12 -o is the validated vault destination and --cache is <plugin-dir>/cache, passed directly'), () => {
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
  expect(plan.args[2]).toBe('plan');
  expect(run.args[2]).toBe('run');
  expect(replayInvariantArgs(run.args)).toEqual(replayInvariantArgs(plan.args));
  expect(approvedHashesIn(run.args, readYes)).toEqual([HASH_A, HASH_B]);
  expect(run.args).not.toContain('--yes');
  expect(approvedHashesIn(plan.args, readYes)).toEqual([]);
  expect(run.args[run.args.indexOf('--approved-by') + 1]).toBe('plugin:modal');
  expect(plan.args).not.toContain('--approved-by');
  // Inputs stay in original order in both and directly follow the subcommand.
  expect(run.args.slice(3, 3 + INPUTS.length)).toEqual(INPUTS);
  expect(plan.args.slice(3, 3 + INPUTS.length)).toEqual(INPUTS);
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
  const roots = [abs(CWD, 'inputs'), abs(CWD, 'large')];
  const snap = snapshotJob({ settings: settingsV2(), inputs: roots, cwd: CWD, outDir: OUT_DIR, cacheDir: CACHE_DIR });
  const request = buildSpawnRequest(snap, 'run', HOST_ENV);
  expect(request.args.slice(3, 5)).toEqual(roots);
  for (const nested of FX71_ROOTS.inputs) expect(request.args.some((t) => t.endsWith(nested))).toBe(false);
  const replay = buildSpawnRequest(snap, 'run', HOST_ENV, { yesFile: YES_FILE, approvedBy: APPROVED_BY_MODAL });
  expect(replay.args.slice(3, 5)).toEqual(roots);
  expect(replay.cwd).toBe(request.cwd);
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

it(R('JT-12 version and selftest utility requests use the module entry point with no other arguments'), () => {
  const version = buildUtilityRequest(ENGINE_PYTHON, 'version', HOST_ENV, PLUGIN_DIR);
  expect(version.command).toBe(ENGINE_PYTHON);
  expect(version.args).toEqual(['-m', 'mdflow', 'version']);
  expect(version.shell).toBe(false);
  expect(version.windowsHide).toBe(true);
  expect(version.cwd).toBe(PLUGIN_DIR);
  expect(version.env).toEqual(scrubEngineEnv(HOST_ENV, 'none'));
  expect(buildUtilityRequest(ENGINE_PYTHON, 'selftest', HOST_ENV, PLUGIN_DIR).args).toEqual(['-m', 'mdflow', 'selftest']);
});
