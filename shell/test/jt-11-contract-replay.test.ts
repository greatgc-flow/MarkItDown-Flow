/**
 * JT-11 / REQ-SHL-11 (+ REQ-SHL-13 framing replay): engine-produced FX-71
 * streams are replayed through the shell; invocations and decoded values are
 * compared with SPEC 7.3/7.4/7.5/8.4/10; an invented command or option fails.
 */
import { req } from './req';
import type { ApproveRequiredEvent, FrameResult, ProgressEvent } from '../src/pure/framing';
import { JsonLinesFramer, MAX_LINE_BYTES } from '../src/pure/framing';
import type { Plan, RunReport } from '../src/pure/protocol';
import { EngineRun, type EngineResult } from '../src/process/engine-process';
import { APPROVED_BY_MODAL, buildSpawnRequest, buildUtilityRequest, ENGINE_ARGV_PREFIX, snapshotJob, SUBCOMMAND_INDEX } from '../src/process/launcher';
import type { SpawnRequest } from '../src/process/types';
import { FakeClock } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Args, fx71Bytes, fx71Chunks, fx71Exit, fx71Lines, fx71Manifest, fx71Text } from './fixtures/fx71';
import { invocationViolations, SPEC_COMMANDS, SPEC_OPTIONS } from './fixtures/protocol';
import { abs, ENGINE_PYTHON, HOST_ENV, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-11');
const R13 = req('REQ-SHL-11', 'REQ-SHL-13');

const CWD = abs(VAULT_ROOT, 'work');
const NONCE = '0123456789abcdef';

interface Replay<K extends 'report' | 'plan'> {
  result: EngineResult<K extends 'report' ? RunReport : Plan[]>;
  spawner: FakeSpawner;
  spoolFs: FakeSpoolFs;
}

async function replay<K extends 'report' | 'plan'>(kind: K, script: ScriptedChild, request?: SpawnRequest): Promise<Replay<K>> {
  const fs = new FakeFs({ directories: [PLUGIN_DIR] });
  const spoolFs = new FakeSpoolFs(fs, abs(PLUGIN_DIR, 'spool'));
  const spawner = new FakeSpawner(() => script);
  const clock = new FakeClock();
  const spawnRequest = request ?? buildUtilityRequest(ENGINE_PYTHON, 'version', HOST_ENV, CWD);
  const run = new EngineRun<K>(spawner, spawnRequest, { stdout: kind, spoolFs, nonce: NONCE, clock });
  run.start();
  const result = (await run.done) as EngineResult<K extends 'report' ? RunReport : Plan[]>;
  return { result, spawner, spoolFs };
}

function recorded(stem: string): ScriptedChild {
  const manifest = fx71Manifest().files;
  const stderrName = `${stem}.progress.jsonl`;
  const stdoutName = `${stem}.stdout.json`;
  const exit = fx71Exit(stdoutName in manifest ? stdoutName : stderrName);
  return {
    stderr: stderrName in manifest ? chunksOf(fx71Bytes(stderrName), 777) : [],
    stdout: stdoutName in manifest ? chunksOf(fx71Bytes(stdoutName), 4096) : [],
    exit: { code: exit, signal: null },
  };
}

function ok<T>(decoded: { ok: true; value: T } | { ok: false } | null): T {
  if (!decoded || !decoded.ok) throw new Error(`expected decoded value, got ${JSON.stringify(decoded)}`);
  return decoded.value;
}

function events(results: FrameResult[]): ProgressEvent[] {
  return results.flatMap((r) => (r.kind === 'event' ? [r.event] : []));
}

function frame(chunks: Uint8Array[]): FrameResult[] {
  const framer = new JsonLinesFramer();
  const out: FrameResult[] = [];
  for (const chunk of chunks) out.push(...framer.push(chunk));
  out.push(...framer.end());
  return out;
}

it(R('JT-11 every recorded FX-71 invocation and every shell-built invocation uses SPEC 10.1 commands and 10.2 options only'), () => {
  const files = fx71Manifest().files;
  const optionSet = new Set(SPEC_OPTIONS);
  const withOptionValue = new Set(SPEC_OPTIONS.filter((o) => !['--force', '--trust-command'].includes(o)));
  for (const [name, entry] of Object.entries(files)) {
    if (!entry.argv) continue;
    // `usage-error` deliberately passes an invented option to record the exit-1 E_USAGE response.
    if (entry.exit === 1) {
      expect(fx71Args(name)).toContain('--no-such-flag');
      continue;
    }
    const args = fx71Args(name);
    expect(['plan', 'run', 'version', 'selftest', 'providers', 'classify', 'cache']).toContain(args[0]);
    for (let i = 1; i < args.length; i++) {
      const token = args[i];
      if (!token.startsWith('-')) continue;
      expect({ name, token, known: optionSet.has(token) }).toEqual({ name, token, known: true });
      if (withOptionValue.has(token)) i += 1; // skip the value
    }
  }
  const snap = snapshotJob({ settings: settingsV2({ provider: { ...OPENAI_PROVIDER } }), inputs: [abs(CWD, 'inputs')], cwd: CWD, outDir: abs(VAULT_ROOT, 'out'), cacheDir: abs(PLUGIN_DIR, 'cache') });
  for (const request of [
    buildSpawnRequest(snap, 'plan', HOST_ENV),
    buildSpawnRequest(snap, 'run', HOST_ENV, { yesFile: abs(PLUGIN_DIR, 'consent', 'yes-0123456789abcdef.txt'), approvedBy: APPROVED_BY_MODAL }),
    buildUtilityRequest(ENGINE_PYTHON, 'version', HOST_ENV, CWD),
    buildUtilityRequest(ENGINE_PYTHON, 'selftest', HOST_ENV, CWD),
  ]) {
    expect(invocationViolations(request)).toEqual([]);
    expect(SPEC_COMMANDS).toContain(request.args[SUBCOMMAND_INDEX]);
  }
});

it(R('JT-11 an invented command, option, module or shell string is a contract violation'), () => {
  const base = buildUtilityRequest(ENGINE_PYTHON, 'version', HOST_ENV, CWD);
  const violations = (args: string[], extra: Partial<SpawnRequest> = {}): string[] =>
    invocationViolations({ ...base, args, ...extra } as SpawnRequest).map((v) => `${v.kind}:${v.token}`);
  const P = [...ENGINE_ARGV_PREFIX];
  expect(violations([...P, 'handshake'])).toContain('command:handshake');
  expect(violations([...P, 'run', 'x', '-o', 'y', '--staging-dir', 'z'])).toContain('option:--staging-dir');
  expect(violations([...P, 'run', 'x', '-o', 'y', '--api-key', 'sk-x'])).toContain('option:--api-key');
  expect(violations([...P, 'run', 'x', '-o', 'y', '--tag', 'ocr'])).toContain('option:--tag');
  expect(violations([...P, 'run', 'x', '-o', 'y', '--no-media'])).toContain('option:--no-media');
  expect(violations(['-I', '-X', 'utf8', '-m', 'other_module', 'run'])).toContain('module:other_module');
  expect(violations(['mdflow', 'run', 'x'])).not.toEqual([]);
  // An interpreter launched without isolation (M3 N-02) or without UTF-8 stdio is a contract violation too.
  expect(violations(['-m', 'mdflow', 'run', 'x', '-o', 'y'])).toContain('module:-m');
  expect(violations(['-X', 'utf8', '-m', 'mdflow', 'run', 'x', '-o', 'y'])).toContain('module:-X');
  expect(violations(['-I', '-m', 'mdflow', 'run', 'x', '-o', 'y'])).toContain('module:-m');
  expect(violations([...P, 'run', 'x', '-o', 'y'], { shell: true as unknown as false })).toContain('shell:true');
  // Legitimate SPEC options are not violations, including repeatable ones.
  expect(violations([...P, 'run', 'x', '-o', 'y', '--yes', 'a'.repeat(64), '--yes', 'b'.repeat(64), '--approved-by', 'plugin:modal', '--sensitive', '*/hr/*', '--sensitive', '*.key'])).toEqual([]);
});

it(R('JT-11 run-mixed replays into 7.3 events and a 7.4 report whose values match the recording (provider none, exit 2)'), async () => {
  const { result, spoolFs } = await replay('report', recorded('run-mixed'));
  const lines = fx71Lines('run-mixed.progress.jsonl');
  expect(result.events).toHaveLength(lines.length);
  expect(result.invalid).toEqual([]);
  expect(result.ignoredEvents).toEqual([]);
  expect(result.status).toEqual({ code: 2, signal: null });
  expect(result.termination).toBe('exited');
  expect(result.cancelRequested).toBe(false);
  const report = ok(result.stdout);
  expect(report.exit).toBe(2);
  expect(report.options.provider).toBe('none');
  expect(report.files.map((f) => [f.path, f.root])).toEqual([
    ['b c.docx', 0], ['memo.txt', 0], ['sub/a.pdf', 0], ['보고서/3분기 결산.pdf', 0], ['broken.pdf', 1], ['empty.pdf', 1], ['garbled.docx', 1],
  ]);
  expect(report.skipped).toEqual([{ path: '.DS_Store', code: 'W_SKIPPED_HIDDEN' }]);
  const runEnd = result.events.find((e) => e.ev === 'run_end');
  expect(runEnd).toMatchObject({ exit: 2, files_ok: 4, files_failed: 3, provider_calls: 0 });
  expect(result.outcome).toBe('partial_failure');
  expect(result.diagnostics).toContain('engine.E_CORRUPT');
  expect(result.diagnostics).not.toContain('shell.PROTOCOL');
  // The spool was consumed and removed.
  expect(await spoolFs.list()).toEqual([]);
});

it(R('JT-11 approve-required replays as pending consent: one bounded approve_required summary per file, hashes equal to the report (8.4)'), async () => {
  const { result } = await replay('report', recorded('approve-required'));
  expect(result.status.code).toBe(3);
  expect(result.outcome).toBe('pending_consent');
  const approvals = result.events.filter((e): e is ApproveRequiredEvent => e.ev === 'approve_required');
  expect(approvals.map((a) => a.file)).toEqual(['b c.docx', 'sub/a.pdf', '보고서/3분기 결산.pdf', '긴 문서.pdf']);
  const report = ok(result.stdout);
  for (const approval of approvals) {
    const file = report.files.find((f) => f.path === approval.file);
    expect(file?.plan_hash).toBe(approval.plan_hash);
    expect(file?.consent).toBeNull();
    expect(approval).not.toHaveProperty('units');
    expect(approval.destination).toBe('https://api.openai.com/v1/chat/completions');
    expect(approval.model).toBe('gpt-4.1-mini');
    expect(approval.est_max_cost).toBeNull();
    expect(approval.cost_known).toBe(false);
  }
  const large = approvals.find((a) => a.file === '긴 문서.pdf');
  expect(large?.keys_unique).toBe(1);
  expect(large?.max_requests).toBe(3);
  expect(result.diagnostics).toContain('engine.E_APPROVAL_REQUIRED');
  // Every recorded line is within the SPEC 7.3 limit, including the 200-unit file's summary.
  for (const line of fx71Text('approve-required.progress.jsonl').split(/\r?\n/)) expect(Buffer.byteLength(line, 'utf8')).toBeLessThanOrEqual(MAX_LINE_BYTES);
});

it(R('JT-11 approved runs decode consent objects by plugin:modal and warm reruns follow 10.4 (provider_calls 0, exit 0)'), async () => {
  const partial = await replay('report', recorded('consent-3-partial'));
  const partialReport = ok(partial.result.stdout);
  const approved = partialReport.files.find((f) => f.path === 'b c.docx');
  expect(approved?.consent).toMatchObject({ plan_hash: '6b717f27e4135ef393326b01ec95d137c4f6181f0316e2397d9400399794d03e', by: 'plugin:modal' });
  expect(partialReport.files.filter((f) => f.consent === null).map((f) => f.path)).toEqual(['memo.txt', 'sub/a.pdf', '보고서/3분기 결산.pdf']);
  expect(partial.result.outcome).toBe('pending_consent');
  const warm = await replay('report', recorded('consent-6-warm'));
  expect(warm.result.status.code).toBe(0);
  expect(warm.result.events.find((e) => e.ev === 'run_end')).toMatchObject({ exit: 0, provider_calls: 0, files_ok: 4, files_failed: 0 });
  expect(warm.result.events.some((e) => e.ev === 'approve_required')).toBe(false);
  expect(warm.result.outcome).toBe('complete');
  expect(warm.result.diagnostics).toEqual([]);
});

it(R('JT-11 plan stdout replays into full 7.1 Plans whose hashes equal the run approve_required hashes (cache-independent)'), async () => {
  const planScript: ScriptedChild = { stdout: chunksOf(fx71Bytes('plan-mixed.stdout.json'), 1000), exit: { code: fx71Exit('plan-mixed.stdout.json'), signal: null } };
  const { result } = await replay('plan', planScript);
  const plans = ok(result.stdout);
  expect(plans.map((p) => p.approved.file.path)).toEqual(['b c.docx', 'memo.txt', 'sub/a.pdf', '보고서/3분기 결산.pdf']);
  const fromRun = new Map(
    (fx71Lines('approve-required.progress.jsonl') as { ev: string; file?: string; plan_hash?: string }[])
      .filter((e) => e.ev === 'approve_required')
      .map((e) => [e.file as string, e.plan_hash as string]),
  );
  for (const plan of plans) {
    if (plan.approved.keys_unique === 0) continue; // memo.txt needs no consent
    expect(fromRun.get(plan.approved.file.path)).toBe(plan.plan_hash);
  }
  expect(result.events).toEqual([]);
  expect(result.outcome).toBe('pending_consent');
  const large = await replay('plan', { stdout: chunksOf(fx71Bytes('plan-large.stdout.json'), 60000), exit: { code: 3, signal: null } });
  const largePlans = ok(large.result.stdout);
  expect(largePlans).toHaveLength(1);
  expect(largePlans[0].approved.units).toHaveLength(200);
  expect(fx71Bytes('plan-large.stdout.json').length).toBeGreaterThan(MAX_LINE_BYTES);
});

it(R('JT-11 a startup usage error (exit 1, 7.5 E_USAGE) is reported by code, never as success and never as raw stderr'), async () => {
  const script: ScriptedChild = { stderr: [fx71Bytes('usage-error.stderr.json')], stdout: [], exit: { code: 1, signal: null } };
  const { result } = await replay('report', script);
  expect(result.status.code).toBe(1);
  expect(result.startupError).toEqual({ code: 'E_USAGE' });
  expect(result.stdout).toBeNull();
  expect(result.outcome).toBe('partial_failure');
  expect(result.diagnostics).toContain('engine.E_USAGE');
  expect(JSON.stringify(result.diagnostics)).not.toContain('use --help');
});

it(R('JT-11 missing or truncated reports and malformed stdout are shell.PROTOCOL failures, not success (FX-71 derived)'), async () => {
  const truncated = await replay('report', { stdout: [fx71Bytes('run-mixed.truncated.stdout.json')], exit: { code: 2, signal: null } });
  expect(truncated.result.stdout).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  expect(truncated.result.diagnostics).toContain('shell.PROTOCOL');
  expect(truncated.result.outcome).not.toBe('complete');
  const missing = await replay('report', { stdout: [], exit: { code: 0, signal: null } });
  expect(missing.result.stdout).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  expect(missing.result.outcome).not.toBe('complete');
  const planTruncated = await replay('plan', { stdout: [fx71Bytes('plan-mixed.truncated.stdout.json')], exit: { code: 3, signal: null } });
  expect(planTruncated.result.stdout).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
});

it(R('JT-11 raw Core triage is kept verbatim including unknown Core fields (R5-N08)'), async () => {
  const { result } = await replay('report', { stdout: [fx71Bytes('run-corrupt.triage-extra.stdout.json')], exit: { code: 2, signal: null } });
  const report = ok(result.stdout);
  const garbled = report.files.find((f) => f.path === 'garbled.docx');
  expect(garbled?.triage).toMatchObject({ future_core_field: { kept: 'verbatim', ko: '한국어' } });
  expect(report.files.find((f) => f.path === 'broken.pdf')?.triage).toBeNull();
  expect(report.files.find((f) => f.path === 'broken.pdf')?.issues.map((i) => i.code)).toEqual(['E_CORRUPT']);
});

it(R13('JT-11 the framed FX-71 stream and the EngineRun replay agree event for event, so the process layer adds no decoding of its own'), async () => {
  const framed = events(frame(fx71Chunks('approve-required.split.json')));
  expect(framed).toHaveLength(fx71Lines('approve-required.progress.jsonl').length);
  const { result } = await replay('report', {
    stderr: fx71Chunks('approve-required.crlf.split.json'),
    stdout: chunksOf(fx71Bytes('approve-required.stdout.json'), 4096),
    exit: { code: 3, signal: null },
  });
  expect(result.events).toEqual(framed);
  expect(result.invalid).toEqual([]);
  expect(result.ignoredEvents).toEqual([]);
  const withUnknown = await replay('report', {
    stderr: chunksOf(fx71Bytes('approve-required.unknown-events.jsonl'), 1500),
    stdout: chunksOf(fx71Bytes('approve-required.stdout.json'), 4096),
    exit: { code: 3, signal: null },
  });
  expect(withUnknown.result.events).toEqual(framed);
  expect(new Set(withUnknown.result.ignoredEvents)).toEqual(new Set(['heartbeat', 'x_vendor_event', 'future_stage_detail']));
  const oversize = await replay('report', {
    stderr: chunksOf(fx71Bytes('approve-required.line-65537.jsonl'), 1500),
    stdout: chunksOf(fx71Bytes('approve-required.stdout.json'), 4096),
    exit: { code: 3, signal: null },
  });
  expect(oversize.result.invalid).toEqual([{ kind: 'invalid', reason: 'oversize', diagnostic: 'shell.PROTOCOL' }]);
  expect(oversize.result.diagnostics).toContain('shell.PROTOCOL');
  expect(oversize.result.events).toEqual(framed);
  expect(JSON.stringify(oversize.result)).not.toContain('xxxxxxxx');
});
