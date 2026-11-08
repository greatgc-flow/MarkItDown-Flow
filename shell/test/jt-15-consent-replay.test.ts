/**
 * JT-15 / REQ-SHL-15: `plan` on the original selection, then after approval
 * one `run` replay of the exact batch/root invocation with repeated
 * `--yes <file-hash>` and `--approved-by plugin:modal`; provider none runs
 * without a modal; cache warming keeps hashes; changed content or engine
 * denial is shown for fresh review, never auto-approved; cancel prevents the
 * replay; no authorization survives reload; no per-file replay.
 */
import { req } from './req';
import type { ConsentDecision, ConsentViewModel } from '../src/ui/consent-modal';
import { ShellCoordinator, type CoordinatorDeps, type JobReport } from '../src/ui/coordinator';
import { APPROVED_BY_MODAL, approvedHashesIn, replayInvariantArgs } from '../src/process/launcher';
import type { SpawnRequest } from '../src/process/types';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit, fx71PlanObjects } from './fixtures/fx71';
import { bytes, plan as syntheticPlan, planStdout } from './fixtures/protocol';
import { abs, HOST_ENV, KEY_VALUE, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';
import type { SettingsV2 } from '../src/pure/settings';

const R = req('REQ-SHL-15');

const INPUT_ROOT = abs(VAULT_ROOT, 'inbox');
const OUT = abs(VAULT_ROOT, 'markitdown-output');
const PLAN_MIXED_HASHES = (fx71PlanObjects('plan-mixed.stdout.json') as { plan_hash: string; approved: { keys_unique: number } }[]);

type Decider = (view: ConsentViewModel) => Promise<ConsentDecision>;

interface Harness {
  coordinator: ShellCoordinator;
  spawner: FakeSpawner;
  consentCalls: ConsentViewModel[];
  notices: string[];
  history: string[];
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
  const spawner = new FakeSpawner(script);
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
    locale: 'en',
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
  return { coordinator: new ShellCoordinator(deps), spawner, consentCalls, notices, history, deps };
}

async function runJob(h: Harness, selection = { kind: 'folder' as const, paths: [INPUT_ROOT] }): Promise<JobReport> {
  const result = await h.coordinator.submit(selection, 'command');
  if (!result.accepted) throw new Error(`submit refused: ${JSON.stringify(result)}`);
  const current = h.coordinator.current;
  if (!current) throw new Error('no current job');
  return current;
}

const remoteSettings = settingsV2({ provider: { ...OPENAI_PROVIDER } });

it(R('JT-15 remote work: plan on the original selection, then one run replay with repeated --yes <file-hash> and --approved-by plugin:modal'), async () => {
  const h = harness(remoteSettings, (request) => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  const [plan, run] = h.spawner.requests;
  expect(plan.args).not.toContain('--yes');
  expect(plan.args).not.toContain('-o');
  expect(replayInvariantArgs(run.args)).toEqual(replayInvariantArgs(plan.args));
  expect(run.cwd).toBe(plan.cwd);
  expect(run.env).toEqual(plan.env);
  expect(run.env.MDFLOW_API_KEY).toBe(KEY_VALUE);
  expect(run.args).not.toContain(KEY_VALUE);
  expect(run.args[run.args.indexOf('-o') + 1]).toBe(OUT);
  const displayed = h.consentCalls[0].files.filter((f) => f.approvedBudget > 0).map((f) => f.planHash);
  expect(approvedHashesIn(run.args)).toEqual(displayed);
  expect(displayed).toEqual(PLAN_MIXED_HASHES.filter((p) => p.approved.keys_unique > 0).map((p) => p.plan_hash));
  expect(run.args[run.args.indexOf('--approved-by') + 1]).toBe(APPROVED_BY_MODAL);
  expect(run.args.filter((t) => t === '--approved-by')).toHaveLength(1);
  // No run-level hash, bare --yes, --yes-file written by the shell or custom root flag.
  const yesIndexes = run.args.map((t, i) => (t === '--yes' ? i : -1)).filter((i) => i >= 0);
  for (const i of yesIndexes) expect(run.args[i + 1]).toMatch(/^[0-9a-f]{64}$/);
  expect(run.args).not.toContain('--yes-file');
  expect(run.args.some((t) => /root|manifest|batch-hash|run-hash/i.test(t))).toBe(false);
  expect(h.consentCalls).toHaveLength(1);
  expect(report.decision).toEqual({ approved: true, hashes: displayed });
  expect(report.run?.status.code).toBe(0);
  expect(h.history).toEqual(['complete']);
});

it(R('JT-15 fifty files yield one modal and one approved run; the directory root is never turned into per-file roots'), async () => {
  const fifty = Array.from({ length: 50 }, (_, i) => syntheticPlan(`sub/file-${i}.pdf`, i.toString(16).padStart(64, '0'), 2));
  const stdout = bytes(planStdout(fifty));
  const h = harness(remoteSettings, (request) =>
    request.args[2] === 'plan' ? { stdout: chunksOf(stdout, 8192), exit: { code: 3, signal: null } } : recordedRun('consent-5-approved'),
  );
  await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  expect(h.consentCalls).toHaveLength(1);
  expect(h.consentCalls[0].files).toHaveLength(50);
  const run = h.spawner.requests[1];
  expect(approvedHashesIn(run.args)).toEqual(fifty.map((p) => p.plan_hash));
  expect(run.args.slice(3, 4)).toEqual([INPUT_ROOT]);
  expect(run.args.some((t) => t.endsWith('file-7.pdf'))).toBe(false);
});

it(R('JT-15 provider none runs without a consent modal and without --yes'), async () => {
  const h = harness(settingsV2(), () => recordedRun('run-mixed'));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['run']);
  expect(h.consentCalls).toEqual([]);
  expect(h.spawner.requests[0].args).not.toContain('--yes');
  expect(h.spawner.requests[0].args).not.toContain('--approved-by');
  expect(h.spawner.requests[0].args[h.spawner.requests[0].args.indexOf('--provider') + 1]).toBe('none');
  expect(report.decision).toBeNull();
  expect(report.run?.status.code).toBe(2);
  expect(h.history).toEqual(['partial_failure']);
});

it(R('JT-15 Keep pending / dismissal: the plan ran, no run is launched, no egress, outcome pending consent'), async () => {
  const h = harness(remoteSettings, (request) => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')), async () => ({ approved: false }));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan']);
  expect(report.decision).toEqual({ approved: false });
  expect(report.run).toBeNull();
  expect(h.history).toEqual(['pending_consent']);
  expect(h.coordinator.active).toBe(false);
});

it(R('JT-15 cache warming leaves the per-file hash stable: cold and warm Plans authorize identically'), () => {
  const cold = fx71PlanObjects('consent-1-plan.stdout.json') as { plan_hash: string; status: { units: { cached: number } } }[];
  const warm = fx71PlanObjects('consent-4-plan-warm.stdout.json') as { plan_hash: string; status: { units: { cached: number } } }[];
  expect(warm.map((p) => p.plan_hash)).toEqual(cold.map((p) => p.plan_hash));
  expect(cold[0].status.units.cached).toBe(0);
  expect(warm[0].status.units.cached).toBe(2);
  const coldArgs = ['-m', 'mdflow', 'run', INPUT_ROOT, '-o', OUT, ...cold.flatMap((p) => ['--yes', p.plan_hash]), '--approved-by', APPROVED_BY_MODAL];
  const warmArgs = ['-m', 'mdflow', 'run', INPUT_ROOT, '-o', OUT, ...warm.flatMap((p) => ['--yes', p.plan_hash]), '--approved-by', APPROVED_BY_MODAL];
  expect(approvedHashesIn(warmArgs)).toEqual(approvedHashesIn(coldArgs));
});

it(R('JT-15 changed approved content or engine denial is displayed as pending for fresh review, never auto-approved or retried'), async () => {
  // The engine answers the authorized run with approve_required for a new hash (source changed between plan and run).
  const h = harness(remoteSettings, (request) => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('approve-required')));
  const report = await runJob(h);
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  expect(h.consentCalls).toHaveLength(1);
  expect(report.pendingShown).toBe(true);
  expect(report.run?.status.code).toBe(3);
  expect(report.run?.outcome).toBe('pending_consent');
  expect(h.history).toEqual(['pending_consent']);
  expect(h.notices).toContain('engine.E_APPROVAL_REQUIRED');
  const denied = harness(remoteSettings, (request) =>
    request.args[2] === 'plan'
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
  const h = harness(remoteSettings, (request) => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')), () =>
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
  expect(report.run).toBeNull();
  expect(h.history).toEqual(['cancelled']);
  expect(h.notices).toContain('shell.CANCELLED');

  const unloaded = harness(remoteSettings, (request) => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')), () =>
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
});

it(R('JT-15 no authorization survives reload: a new coordinator plans again and asks again'), async () => {
  const script = (request: SpawnRequest): ScriptedChild => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved'));
  const first = harness(remoteSettings, script);
  await runJob(first);
  expect(first.consentCalls).toHaveLength(1);
  const reloaded = harness(remoteSettings, script);
  expect(reloaded.coordinator.current).toBeNull();
  await runJob(reloaded);
  expect(reloaded.spawner.commands).toEqual(['plan', 'run']);
  expect(reloaded.consentCalls).toHaveLength(1);
});

it(R('JT-15 the modal is only ever fed decoded full Plans from plan stdout, never approve_required summaries'), async () => {
  const h = harness(remoteSettings, (request) => (request.args[2] === 'plan' ? recordedPlan('plan-mixed.stdout.json') : recordedRun('consent-5-approved')));
  const report = await runJob(h);
  expect(report.plan?.stdout?.ok).toBe(true);
  expect(report.plan?.events).toEqual([]);
  const view = h.consentCalls[0];
  expect(view.files).toHaveLength(4);
  expect(view.files.map((f) => f.sha256)).toEqual((fx71PlanObjects('plan-mixed.stdout.json') as { approved: { file: { sha256: string } } }[]).map((p) => p.approved.file.sha256));
});
