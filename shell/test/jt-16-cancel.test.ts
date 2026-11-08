/**
 * JT-16 / REQ-SHL-16: cancel before launch / in modal / during a blocked
 * request / on unload prevents replay; cooperative stop (SIGTERM) then forced
 * termination after at most five seconds; cooperative POSIX exit 130 with a
 * report is distinguished from forced/native termination (no report); exit
 * 130 or success is never synthesized; restart recovers owned stale spools;
 * no owned live process remains. Real OS children (FX-63 style `node -e`)
 * plus scripted fakes.
 */
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { req } from './req';
import { CANCEL_GRACE_MS, COOPERATIVE_EXIT, EngineRun, type EngineResult, recoverStaleSpools } from '../src/process/engine-process';
import { NodeSpawner, systemClock } from '../src/process/node-spawner';
import type { SpawnRequest } from '../src/process/types';
import type { RunReport } from '../src/pure/protocol';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner, type ScriptedChild } from './fixtures/fake-spawner';
import { fx71Bytes } from './fixtures/fx71';
import { abs, ENGINE_PYTHON, HOST_ENV, PLUGIN_DIR } from './fixtures/shell-settings';

const R = req('REQ-SHL-16');
const NONCE = 'fedcba9876543210';
const POSIX = process.platform !== 'win32';
const WINDOWS = process.platform === 'win32';

const REPORT_130 = {
  v: 1, mdflow: '2.0.0', started: 't', finished: 't',
  options: { provider: 'none' }, files: [], skipped: [], exit: 130,
};
const REPORT_0 = { ...REPORT_130, exit: 0 };

function fakeRequest(): SpawnRequest {
  return { command: ENGINE_PYTHON, args: ['-m', 'mdflow', 'run', 'x', '-o', 'y'], cwd: PLUGIN_DIR, env: { PATH: HOST_ENV.PATH }, shell: false, windowsHide: true };
}

function setup(script: ScriptedChild, graceMs?: number): { run: EngineRun<'report'>; spawner: FakeSpawner; clock: FakeClock; spoolFs: FakeSpoolFs } {
  const ffs = new FakeFs({ directories: [PLUGIN_DIR] });
  const spoolFs = new FakeSpoolFs(ffs, abs(PLUGIN_DIR, 'spool'));
  const spawner = new FakeSpawner(() => script);
  const clock = new FakeClock();
  const run = new EngineRun(spawner, fakeRequest(), { stdout: 'report', spoolFs, nonce: NONCE, clock, graceMs });
  return { run, spawner, clock, spoolFs };
}

function pidAlive(pid: number | null): boolean {
  if (pid === null) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

it(R('JT-16 the grace period constant is five seconds and 130 is never synthesized before launch: cancel before start spawns nothing'), async () => {
  expect(CANCEL_GRACE_MS).toBe(5000);
  expect(COOPERATIVE_EXIT).toBe(130);
  const { run, spawner } = setup({ exit: { code: 0, signal: null } });
  run.cancel();
  expect(() => run.start()).toThrow();
  expect(spawner.requests).toEqual([]);
  const result = await run.done;
  expect(result.outcome).toBe('cancelled');
  expect(result.cancelRequested).toBe(true);
  expect(result.status.code).not.toBe(130);
  expect(result.stdout).toBeNull();
  expect(result.termination).toBe('forced');
});

it(R('JT-16 cooperative stop: the child exits 130 with a report -> termination cooperative, no forced kill, outcome cancelled'), async () => {
  const { run, spawner } = setup({
    stderr: [Buffer.from('{"v":1,"ev":"run_start","ts":"t","files":1,"provider":"none"}\n')],
    blocked: true,
    cooperative: 'exit130',
    cooperativeStdout: Buffer.from(JSON.stringify(REPORT_130)),
    exit: { code: 0, signal: null },
  });
  run.start();
  await flush();
  run.cancel();
  const result = await run.done;
  expect(spawner.children[0].cooperativeRequests).toBe(1);
  expect(spawner.children[0].terminated).toBe(false);
  expect(result.termination).toBe('cooperative');
  expect(result.status).toEqual({ code: 130, signal: null });
  expect(result.stdout?.ok).toBe(true);
  expect((result.stdout as { ok: true; value: RunReport }).value.exit).toBe(130);
  expect(result.outcome).toBe('cancelled');
  expect(result.diagnostics).toContain('shell.CANCELLED');
  expect(result.events.map((e) => e.ev)).toEqual(['run_start']);
});

it(R('JT-16 a child that ignores the cooperative request is force-terminated after the grace period, never earlier, and reported as interrupted'), async () => {
  const { run, spawner, clock } = setup({ blocked: true, cooperative: 'ignore', exit: { code: 0, signal: null } });
  run.start();
  await flush();
  run.cancel();
  await clock.advance(CANCEL_GRACE_MS - 1);
  expect(spawner.children[0].alive).toBe(true);
  expect(spawner.children[0].terminated).toBe(false);
  await clock.advance(1);
  const result = await run.done;
  expect(spawner.children[0].terminated).toBe(true);
  expect(result.termination).toBe('forced');
  expect(result.status).toEqual({ code: null, signal: 'SIGKILL' });
  expect(result.stdout).toBeNull();
  expect(result.outcome).toBe('cancelled');
  expect(result.status.code).not.toBe(130);
  // The shell did not wait for a 120 s provider timeout or retry backoff.
  expect(clock.pendingCount).toBe(0);
});

it(R('JT-16 when the platform cannot deliver a cooperative signal the shell terminates and records the native status (no exit 130)'), async () => {
  const { run, spawner } = setup({ blocked: true, cooperative: 'unsupported', exit: { code: 0, signal: null } });
  run.start();
  await flush();
  run.cancel();
  const result = await run.done;
  expect(spawner.children[0].terminated).toBe(true);
  expect(result.termination).toBe('forced');
  expect(result.stdout).toBeNull();
  expect(result.outcome).toBe('cancelled');
  expect(result.status.code).not.toBe(130);
});

it(R('JT-16 an externally killed child (no cancel request) is interrupted, not cancelled by the shell and never success'), async () => {
  const { run } = setup({ stderr: [], blocked: true, exit: { code: 0, signal: null } });
  const child = run.start();
  await flush();
  child.terminate();
  const result = await run.done;
  expect(result.cancelRequested).toBe(false);
  expect(result.termination).toBe('forced');
  expect(result.stdout).toBeNull();
  expect(result.outcome).toBe('cancelled');
  expect(result.diagnostics).toContain('shell.CANCELLED');
});

it(R('JT-16 a child that finishes by itself is exited with its real status; committed results are preserved in the report'), async () => {
  const { run } = setup({ stdout: [fx71Bytes('consent-5-approved.stdout.json')], exit: { code: 0, signal: null } });
  run.start();
  const result = await run.done;
  expect(result.termination).toBe('exited');
  expect(result.status).toEqual({ code: 0, signal: null });
  expect(result.outcome).toBe('complete');
  expect((result.stdout as { ok: true; value: RunReport }).value.files.filter((f) => f.consent !== null)).toHaveLength(1);
});

it(R('JT-16 restart recovers only verified owned stale spool files and leaves foreign files alone'), async () => {
  const ffs = new FakeFs({ directories: [PLUGIN_DIR] });
  const dir = abs(PLUGIN_DIR, 'spool');
  await ffs.writeFile(abs(dir, 'mdflow-spool-0123456789abcdef.json'), Buffer.from('{"v":1'));
  await ffs.writeFile(abs(dir, 'mdflow-spool-FEDCBA9876543210.json'), Buffer.from('x'));
  await ffs.writeFile(abs(dir, 'notes.md'), Buffer.from('keep'));
  await ffs.writeFile(abs(dir, 'data.json'), Buffer.from('{}'));
  const spoolFs = new FakeSpoolFs(ffs, dir);
  const removed = await recoverStaleSpools(spoolFs);
  expect(removed).toEqual(['mdflow-spool-0123456789abcdef.json']);
  expect(await spoolFs.list()).toEqual(['data.json', 'mdflow-spool-FEDCBA9876543210.json', 'notes.md']);
});

// ---------------------------------------------------------------------------- real OS processes

function nodeChild(script: string): SpawnRequest {
  return { command: process.execPath, args: ['-e', script], cwd: os.tmpdir(), env: { PATH: process.env.PATH ?? '' }, shell: false, windowsHide: true };
}

const COOPERATIVE_CHILD = `
process.stderr.write(JSON.stringify({v:1,ev:"run_start",ts:"t",files:1,provider:"none"})+"\\n");
process.on("SIGTERM", () => { process.stdout.write(${JSON.stringify(JSON.stringify(REPORT_130))}); process.exit(130); });
setInterval(() => {}, 1000);
`;
const STUBBORN_CHILD = `process.on("SIGTERM", () => {}); process.on("SIGINT", () => {}); setInterval(() => {}, 1000);`;
const QUICK_CHILD = `process.stdout.write(${JSON.stringify(JSON.stringify(REPORT_0))}); process.exit(0);`;

async function realRun(request: SpawnRequest, graceMs: number): Promise<{ run: EngineRun<'report'>; result: Promise<EngineResult<RunReport>>; pid: number | null; spoolDir: string }> {
  const spoolDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mdflow-jt16-'));
  const ffs = new FakeFs({ directories: [spoolDir] });
  const spoolFs = new FakeSpoolFs(ffs, spoolDir);
  const run = new EngineRun(new NodeSpawner(), request, { stdout: 'report', spoolFs, nonce: NONCE, clock: systemClock, graceMs });
  const child = run.start();
  await new Promise<void>((resolve) => setTimeout(resolve, 300));
  return { run, result: run.done, pid: child.pid, spoolDir };
}

it(R('JT-16 real child: a quick cooperative-free exit is reported with its native status and report'), async () => {
  const { result, pid } = await realRun(nodeChild(QUICK_CHILD), 1000);
  const outcome = await result;
  expect(outcome.termination).toBe('exited');
  expect(outcome.status.code).toBe(0);
  expect(outcome.stdout?.ok).toBe(true);
  expect(pidAlive(pid)).toBe(false);
});

if (POSIX) {
  it(R('JT-16 real POSIX child: cancel during a blocked request -> SIGTERM -> exit 130 with report within the grace period; process gone'), async () => {
    const started = Date.now();
    const { run, result, pid } = await realRun(nodeChild(COOPERATIVE_CHILD), CANCEL_GRACE_MS);
    expect(pidAlive(pid)).toBe(true);
    run.cancel();
    const outcome = await result;
    expect(Date.now() - started).toBeLessThan(CANCEL_GRACE_MS);
    expect(outcome.termination).toBe('cooperative');
    expect(outcome.status.code).toBe(130);
    expect((outcome.stdout as { ok: true; value: RunReport }).value.exit).toBe(130);
    expect(outcome.outcome).toBe('cancelled');
    expect(pidAlive(pid)).toBe(false);
  });

  it(R('JT-16 real POSIX child ignoring SIGTERM is SIGKILLed after the grace period: native status, no report, process gone'), async () => {
    const { run, result, pid } = await realRun(nodeChild(STUBBORN_CHILD), 500);
    run.cancel();
    const outcome = await result;
    expect(outcome.termination).toBe('forced');
    expect(outcome.status.signal).toBe('SIGKILL');
    expect(outcome.status.code).not.toBe(130);
    expect(outcome.stdout).toBeNull();
    expect(outcome.outcome).toBe('cancelled');
    expect(pidAlive(pid)).toBe(false);
  });
}

if (WINDOWS) {
  it(R('JT-16 real Windows child: cancel records the actual native termination status, no report and no synthesized 130; process gone'), async () => {
    const { run, result, pid } = await realRun(nodeChild(STUBBORN_CHILD), 500);
    expect(pidAlive(pid)).toBe(true);
    run.cancel();
    const outcome = await result;
    expect(outcome.termination).toBe('forced');
    expect(outcome.status.code).not.toBe(130);
    expect(outcome.stdout).toBeNull();
    expect(outcome.outcome).toBe('cancelled');
    expect(pidAlive(pid)).toBe(false);
  });
}
