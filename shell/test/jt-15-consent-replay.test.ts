/**
 * JT-15 / REQ-SHL-15: `plan` on the original selection, then after approval
 * one `run` replay of the exact batch/root invocation with a plugin-owned
 * `--yes-file` (SPEC 8.4/10.2, R7 F-03) and `--approved-by plugin:modal`;
 * provider none runs without a modal; cache warming keeps hashes; changed
 * content or engine denial is shown for fresh review, never auto-approved;
 * cancel prevents the replay; no authorization survives reload; no per-file
 * replay; the yes-file is deleted after the run.
 */
import { req } from './req';
import type { ConsentDecision, ConsentViewModel } from '../src/ui/consent-modal';
import { ShellCoordinator, type CoordinatorDeps, type JobReport } from '../src/ui/coordinator';
import { APPROVED_BY_MODAL, ENGINE_ARGV_PREFIX, SUBCOMMAND_INDEX } from '../src/process/launcher';
import type { SpawnRequest } from '../src/process/types';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, type ScriptedChild, subcommandOf } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit, fx71PlanObjects, fx71YesFile } from './fixtures/fx71';
import { approvedHashesIn, bytes, parseYesFile, plan as syntheticPlan, planStdout, replayInvariantArgs } from './fixtures/protocol';
import { abs, HOST_ENV, KEY_VALUE, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';
import type { SettingsV2 } from '../src/pure/settings';

const R = req('REQ-SHL-15');
const R9 = req('REQ-SHL-09');

const INPUT_ROOT = abs(VAULT_ROOT, 'inbox');
const OUT = abs(VAULT_ROOT, 'markitdown-output');
const PLAN_MIXED_HASHES = (fx71PlanObjects('plan-mixed.stdout.json') as { plan_hash: string; approved: { keys_unique: number } }[]);

type Decider = (view: ConsentViewModel) => Promise<ConsentDecision>;

interface CapturedYesFile {
  path: string;
  /** Content at spawn time (the file is deleted after the run). */
  text: string | undefined;
}

interface Harness {
  coordinator: ShellCoordinator;
  spawner: FakeSpawner;
  fs: FakeFs;
  consentCalls: ConsentViewModel[];
  notices: string[];
  history: string[];
  yesFiles: CapturedYesFile[];
  deps: CoordinatorDeps;
}

function recordedRun(stem: string): ScriptedChild {
  return {
    stderr: chunksOf(fx71Bytes(`${stem}.progress.jsonl`), 2048),
    stdout: chunksOf(fx71Bytes(`${stem}.stdout.json`), 8192),
    exit: { code: fx71Exit(`${stem}.stdout.json`), signal: null },
  };
}

function recordedPlan(name: string): ScriptedChild {
  return { stdout: chunksOf(fx71Bytes(name), 4096), exit: { code: fx71Exit(name), signal: null } };
}

function harness(
  settings: SettingsV2,
  script: (request: SpawnRequest, index: number) => ScriptedChild,
  decide: Decider = async (view) => ({ approved: true, hashes: view.files.filter((f) => f.requestsToSend > 0 || f.approvedBudget > 0).map((f) => f.planHash) }),
): Harness {
  const fs = new FakeFs({ directories: [VAULT_ROOT, OUT, INPUT_ROOT, PLUGIN_DIR, abs(PLUGIN_DIR, 'cache')] });
  const yesFiles: CapturedYesFile[] = [];
  const spawner = new FakeSpawner((request, index) => {
    const at = request.args.indexOf('--yes-file');
    if (at >= 0) yesFiles.push({ path: request.args[at + 1], text: fs.text(request.args[at + 1]) });
    return script(request, index);
  });
  const consentCalls: ConsentViewModel[] = [];
  const notices: string[] = [];
  const history: string[] = [];
  const deps: CoordinatorDeps = {
    spawner,
    fs,
    spoolFs: new FakeSpoolFs(fs, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    settings: () => settings,
    gate: () => ({ enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.5', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } }),
    consent: async (view) => {
      consentCalls.push(view);
      return decide(view);
    },
    notify: (key) => {
      notices.push(key);
    },
    recordHistory: async (entry) => {
      history.push(entry.outcome ?? 'none');
    },
    log: null,
    nonce: () => '0123456789abcdef',
  };
  return { coordinator: new ShellCoordinator(deps), spawner, fs, consentCalls, notices, history, yesFiles, deps };
}

async function runJob(h: Harness, selection = { kind: 'folder' as const, paths: [INPUT_ROOT] }): Promise<JobReport> {
  const result = await h.coordinator.submit(selection, 'command');
  if (!result.accepted) throw new Error(`submit refused: ${JSON.stringify(result)}`);
  const current = h.coordinator.current;
  if (!current) throw new Error('no current job');
  return current;
}

function normalized(p: string): string {
  return p.replace(/\\/g, '/').toLowerCase();
}

const remoteSettings = settingsV2({ provider: { ...OPENAI_PROVIDER } });

it(R('JT-15 remote work: plan on the original selection, then one run replay with an owned --yes-file of the displayed hashes and --approved-by plugin:modal'), async () => {
  const h = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  const [plan, run] = h.spawner.requests;
  expect(plan.args).not.toContain('--yes');
  expect(plan.args).not.toContain('--yes-file');
  expect(plan.args).not.toContain('-o');
  expect(replayInvariantArgs(run.args)).toEqual(replayInvariantArgs(plan.args));
  expect(run.cwd).toBe(plan.cwd);
  expect(run.env).toEqual(plan.env);
  expect(run.env.MDFLOW_API_KEY).toBe(KEY_VALUE);
  expect(run.args).not.toContain(KEY_VALUE);
  expect(run.args[run.args.indexOf('-o') + 1]).toBe(OUT);
  // SPEC 8.4/10.2: one private yes-file written by the shell, one plan_hash per line, passed once.
  expect(run.args.filter((t) => t === '--yes-file')).toHaveLength(1);
  expect(run.args).not.toContain('--yes');
  expect(h.yesFiles).toHaveLength(1);
  const yesFile = h.yesFiles[0];
  expect(normalized(yesFile.path).startsWith(normalized(PLUGIN_DIR) + '/')).toBe(true);
  expect(yesFile.text).toBeDefined();
  const displayed = h.consentCalls[0].files.filter((f) => f.approvedBudget > 0).map((f) => f.planHash);
  expect(parseYesFile(yesFile.text ?? '')).toEqual(displayed);
  expect(approvedHashesIn(run.args, () => yesFile.text ?? null)).toEqual(displayed);
  expect(displayed).toEqual(PLAN_MIXED_HASHES.filter((p) => p.approved.keys_unique > 0).map((p) => p.plan_hash));
  for (const line of (yesFile.text ?? '').split(/\r?\n/)) expect(line === '' || line.startsWith('#') || /^[0-9a-f]{64}$/.test(line)).toBe(true);
  expect(run.args[run.args.indexOf('--approved-by') + 1]).toBe(APPROVED_BY_MODAL);
  expect(run.args.filter((t) => t === '--approved-by')).toHaveLength(1);
  // No run-level hash, shell manifest or root-preserving custom flag; the yes-file is gone after the run.
  expect(run.args.some((t) => /root|manifest|batch-hash|run-hash/i.test(t))).toBe(false);
  expect(h.fs.text(yesFile.path)).toBeUndefined();
  expect(h.consentCalls).toHaveLength(1);
  expect(report.decision).toEqual({ approved: true, hashes: displayed });
  expect(report.run?.status.code).toBe(0);
  expect(h.history).toEqual(['complete']);
});

it(R('JT-15 fifty files yield one modal and one approved run; the directory root is never turned into per-file roots'), async () => {
  const fifty = Array.from({ length: 50 }, (_, i) => syntheticPlan(`sub/file-${i}.pdf`, i.toString(16).padStart(64, '0'), 2));
  const stdout = bytes(planStdout(fifty));
  const h = harness(remoteSettings, (request) =>
    subcommandOf(request) === 'plan' ? { stdout: chunksOf(stdout, 8192), exit: { code: 3, signal: null } } : recordedRun('consent-5-approved'),
  );
  await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  expect(h.consentCalls).toHaveLength(1);
  expect(h.consentCalls[0].files).toHaveLength(50);
  const run = h.spawner.requests[1];
  expect(h.yesFiles).toHaveLength(1);
  expect(parseYesFile(h.yesFiles[0].text ?? '')).toEqual(fifty.map((p) => p.plan_hash));
  expect(run.args.filter((t) => t === '--yes-file')).toHaveLength(1);
  expect(run.args.slice(SUBCOMMAND_INDEX + 1, SUBCOMMAND_INDEX + 2)).toEqual([INPUT_ROOT]);
  expect(run.args.some((t) => t.endsWith('file-7.pdf'))).toBe(false);
});

it(R('JT-15 provider none runs without a consent modal and without any authorization argument'), async () => {
  const h = harness(settingsV2(), () => recordedRun('run-mixed'));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['run']);
  expect(h.consentCalls).toEqual([]);
  expect(h.spawner.requests[0].args).not.toContain('--yes');
  expect(h.spawner.requests[0].args).not.toContain('--yes-file');
  expect(h.spawner.requests[0].args).not.toContain('--approved-by');
  expect(h.spawner.requests[0].args[h.spawner.requests[0].args.indexOf('--provider') + 1]).toBe('none');
  expect(report.decision).toBeNull();
  expect(report.run?.status.code).toBe(2);
  expect(h.history).toEqual(['partial_failure']);
});

it(R('JT-15 Keep pending / dismissal: the plan ran, no run is launched, no yes-file is written, outcome pending consent'), async () => {
  const h = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')), async () => ({ approved: false }));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan']);
  expect(h.yesFiles).toEqual([]);
  expect(h.fs.mutations.filter((m) => /yes/i.test(m))).toEqual([]);
  expect(report.decision).toEqual({ approved: false });
  expect(report.run).toBeNull();
  expect(h.history).toEqual(['pending_consent']);
  expect(h.coordinator.active).toBe(false);
});

it(R('JT-15 cache warming leaves the per-file hash stable: cold and warm Plans produce the same yes-file (FX-71 consent recordings)'), () => {
  const cold = fx71PlanObjects('consent-1-plan.stdout.json') as { plan_hash: string; approved: { keys_unique: number }; status: { units: { cached: number } } }[];
  const warm = fx71PlanObjects('consent-4-plan-warm.stdout.json') as typeof cold;
  expect(warm.map((p) => p.plan_hash)).toEqual(cold.map((p) => p.plan_hash));
  expect(cold[0].status.units.cached).toBe(0);
  expect(warm[0].status.units.cached).toBe(2);
  const approvable = (plans: typeof cold): string[] => plans.filter((p) => p.approved.keys_unique > 0).map((p) => p.plan_hash);
  expect(approvable(warm)).toEqual(approvable(cold));
  // The recorded yes-file the engine accepted for the warm run lists exactly those hashes.
  expect(fx71YesFile('consent-yes-2.txt')).toEqual(approvable(cold));
  const text = `# approved\n\n${approvable(warm).join('\n')}\n`;
  expect(parseYesFile(text)).toEqual(approvable(cold));
  expect(approvedHashesIn([...ENGINE_ARGV_PREFIX, 'run', INPUT_ROOT, '-o', OUT, '--yes-file', 'x.txt', '--approved-by', APPROVED_BY_MODAL], () => text)).toEqual(approvable(cold));
});

it(R('JT-15 a well-formed exit-1 startup error on plan is reported by its code only, never as shell.PROTOCOL; a truncated plan is a protocol failure once (M3 N-03)'), async () => {
  const usage = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan'
    ? { stderr: [fx71Bytes('usage-error.stderr.json')], stdout: [], exit: { code: 1, signal: null } }
    : recordedRun('consent-5-approved')));
  const report = await runJob(usage);
  expect(usage.spawner.commands).toEqual(['plan']);
  expect(report.plan?.startupError).toEqual({ code: 'E_USAGE' });
  expect(usage.notices).toContain('engine.E_USAGE');
  expect(usage.notices).not.toContain('shell.PROTOCOL');
  expect(usage.consentCalls).toEqual([]);
  expect(usage.history).toEqual(['partial_failure']);

  const truncated = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan'
    ? { stdout: [fx71Bytes('plan-mixed.truncated.stdout.json')], exit: { code: 3, signal: null } }
    : recordedRun('consent-5-approved')));
  await runJob(truncated);
  expect(truncated.spawner.commands).toEqual(['plan']);
  expect(truncated.notices.filter((n) => n === 'shell.PROTOCOL')).toHaveLength(1);
  expect(truncated.consentCalls).toEqual([]);

  // A plan child that dies from a signal is a forced/native termination: one honest "interrupted" notice
  // (shell.CANCELLED, SPEC 10.3 forced path), no PROTOCOL claim about its absent output, no consent, no run.
  const died = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan'
    ? { stdout: [], exit: { code: null, signal: 'SIGSEGV' } }
    : recordedRun('consent-5-approved')));
  await runJob(died);
  expect(died.spawner.commands).toEqual(['plan']);
  expect(died.notices).toEqual(['shell.CANCELLED']);
  expect(died.consentCalls).toEqual([]);
  expect(died.history).toEqual(['partial_failure']);
});

it(R('JT-15 consent is asked only for files with requests to send: a warm plan lists cached files as informational and the yes-file holds exactly the hashes that need consent'), async () => {
  const h = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('consent-4-plan-warm.stdout.json') : recordedRun('consent-6-warm')));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  expect(h.consentCalls).toHaveLength(1);
  const view = h.consentCalls[0];
  expect(view.files.map((f) => [f.path, f.needsConsent])).toEqual([['b c.docx', false], ['memo.txt', false], ['sub/a.pdf', true], ['보고서/3분기 결산.pdf', true]]);
  const warm = fx71PlanObjects('consent-4-plan-warm.stdout.json') as { plan_hash: string; approved: { provider: { egress: boolean } }; status: { requests_to_send: number } }[];
  const needed = warm.filter((p) => p.approved.provider.egress && p.status.requests_to_send > 0).map((p) => p.plan_hash);
  expect(needed).toHaveLength(2);
  expect(h.yesFiles).toHaveLength(1);
  expect(parseYesFile(h.yesFiles[0].text ?? '')).toEqual(needed);
  expect(report.run?.outcome).toBe('complete');
});

it(R('JT-15 a plan with nothing left to send opens no modal and runs without any authorization argument'), async () => {
  const cached = syntheticPlan('sub/a.pdf', 'd'.repeat(64), 2);
  cached.status.units = { ...cached.status.units, eligible: 0, cached: 2 };
  cached.status.requests_to_send = 0;
  const h = harness(remoteSettings, (request) =>
    subcommandOf(request) === 'plan' ? { stdout: chunksOf(bytes(planStdout([cached])), 4096), exit: { code: 0, signal: null } } : recordedRun('consent-6-warm'),
  );
  await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  expect(h.consentCalls).toEqual([]);
  expect(h.yesFiles).toEqual([]);
  expect(h.spawner.requests[1].args).not.toContain('--yes-file');
  expect(h.spawner.requests[1].args).not.toContain('--approved-by');
});

it(R9('JT-09 the destination is revalidated immediately before the run spawn: a destination swapped for an escaping symlink during consent refuses the run'), async () => {
  const sibling = abs(`${VAULT_ROOT}2`, 'out');
  const h: { current: Harness | null } = { current: null };
  h.current = harness(
    remoteSettings,
    (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')),
    async (view) => {
      const fs = (h.current as Harness).fs;
      fs.directories.add(fs.norm(sibling));
      fs.links.set(fs.norm(OUT), fs.norm(sibling));
      return { approved: true, hashes: view.files.map((f) => f.planHash) };
    },
  );
  const report = await runJob(h.current);
  expect(h.current.spawner.commands).toEqual(['plan']);
  expect(report.run).toBeNull();
  expect(h.current.notices).toContain('shell.DESTINATION');
  expect(h.current.yesFiles).toEqual([]);
  expect(h.current.fs.mutations.filter((m) => /yes-/.test(m) && m.startsWith('write'))).toEqual([]);
  expect(h.current.history).toEqual(['partial_failure']);
  expect(h.current.coordinator.active).toBe(false);
});

it(R('JT-15 changed approved content or engine denial is displayed as pending for fresh review, never auto-approved or retried'), async () => {
  // The engine answers the authorized run with approve_required for a new hash (source changed between plan and run).
  const h = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('approve-required')));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  expect(h.consentCalls).toHaveLength(1);
  expect(report.pendingShown).toBe(true);
  expect(report.run?.status.code).toBe(3);
  expect(report.run?.outcome).toBe('pending_consent');
  expect(h.history).toEqual(['pending_consent']);
  expect(h.notices).toContain('engine.E_APPROVAL_REQUIRED');
  expect(h.yesFiles).toHaveLength(1);
  expect(h.fs.text(h.yesFiles[0].path)).toBeUndefined();
  const denied = harness(remoteSettings, (request) =>
    subcommandOf(request) === 'plan'
      ? recordedPlan('plan-mixed.stdout.json')
      : {
          stderr: [bytes(JSON.stringify({ v: 1, ev: 'error', ts: 't', file: 'b c.docx', code: 'E_APPROVAL_DENIED', message: 'redacted' }) + '\n')],
          stdout: chunksOf(fx71Bytes('consent-2-pending.stdout.json'), 8192),
          exit: { code: 3, signal: null },
        },
  );
  const deniedReport = await runJob(denied);
  expect(denied.spawner.commands).toEqual(['plan', 'run']);
  expect(deniedReport.pendingShown).toBe(true);
  expect(denied.notices).toContain('engine.E_APPROVAL_DENIED');
});

it(R('JT-15 cancel while the modal is open prevents the replay; unload behaves the same'), async () => {
  let release: ((d: ConsentDecision) => void) | null = null;
  const h = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')), () =>
    new Promise<ConsentDecision>((resolve) => {
      release = resolve;
    }),
  );
  const result = await h.coordinator.submit({ kind: 'folder', paths: [INPUT_ROOT] }, 'ribbon');
  expect(result.accepted).toBe(true);
  for (let i = 0; i < 20 && h.consentCalls.length === 0; i++) await flush();
  expect(h.consentCalls).toHaveLength(1);
  h.coordinator.cancel();
  (release as unknown as ((d: ConsentDecision) => void) | null)?.({ approved: true, hashes: PLAN_MIXED_HASHES.map((p) => p.plan_hash) });
  const report = await (h.coordinator.current as Promise<JobReport>);
  expect(h.spawner.commands).toEqual(['plan']);
  expect(h.yesFiles).toEqual([]);
  expect(report.run).toBeNull();
  expect(h.history).toEqual(['cancelled']);
  expect(h.notices).toContain('shell.CANCELLED');

  const unloaded = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')), () =>
    new Promise<ConsentDecision>((resolve) => {
      release = resolve;
    }),
  );
  await unloaded.coordinator.submit({ kind: 'folder', paths: [INPUT_ROOT] }, 'drop');
  for (let i = 0; i < 20 && unloaded.consentCalls.length === 0; i++) await flush();
  unloaded.coordinator.dispose();
  (release as unknown as ((d: ConsentDecision) => void) | null)?.({ approved: true, hashes: PLAN_MIXED_HASHES.map((p) => p.plan_hash) });
  await (unloaded.coordinator.current as Promise<JobReport> | null);
  expect(unloaded.spawner.commands).toEqual(['plan']);
  expect(unloaded.yesFiles).toEqual([]);
});

it(R('JT-15 no authorization survives reload: a new coordinator plans again and asks again'), async () => {
  const script = (request: SpawnRequest): ScriptedChild => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved'));
  const first = harness(remoteSettings, script);
  await runJob(first);
  expect(first.consentCalls).toHaveLength(1);
  const reloaded = harness(remoteSettings, script);
  expect(reloaded.coordinator.current).toBeNull();
  await runJob(reloaded);
  expect(reloaded.spawner.commands).toEqual(['plan', 'run']);
  expect(reloaded.consentCalls).toHaveLength(1);
  expect(reloaded.yesFiles).toHaveLength(1);
});

it(R('JT-15 the modal is only ever fed decoded full Plans from plan stdout, never approve_required summaries'), async () => {
  const h = harness(remoteSettings, (request) => (subcommandOf(request) === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')));
  const report = await runJob(h);
  expect(report.plan?.stdout?.ok).toBe(true);
  expect(report.plan?.events).toEqual([]);
  const view = h.consentCalls[0];
  expect(view.files).toHaveLength(4);
  expect(view.files.map((f) => f.sha256)).toEqual((fx71PlanObjects('plan-mixed.stdout.json') as { approved: { file: { sha256: string } } }[]).map((p) => p.approved.file.sha256));
});
