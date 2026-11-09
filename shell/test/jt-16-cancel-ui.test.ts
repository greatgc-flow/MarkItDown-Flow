/**
 * JT-16 / REQ-SHL-16 (M2 X-01): a Cancel control is visible for the whole life
 * of a job (plan, consent, run) and is bound to the coordinator's cancel, with
 * progress details hidden or shown; JT-09 / REQ-SHL-09: progress details come
 * from engine events through `EngineRun.onEvent`; JT-07 / REQ-SHL-07 (X-18):
 * history stores a count plus the first path, not every absolute input.
 */
import { req } from './req';
import { asFake, asMockPlugin, createApp, fakeEl, mockState } from './__mocks__/obsidian';
import type { ProgressEvent } from '../src/pure/framing';
import { JsonLinesFramer } from '../src/pure/framing';
import { dictionary, formatMessage } from '../src/pure/i18n';
import type { HistoryEntry } from '../src/pure/history';
import type { SpawnRequest } from '../src/process/types';
import type { VersionGate } from '../src/process/version-gate';
import type { ConsentDecision } from '../src/ui/consent-modal';
import { type CoordinatorDeps, type JobReport, ShellCoordinator } from '../src/ui/coordinator';
import { JobStatusBar, type ProgressSink, summarizeProgress } from '../src/ui/progress';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, type ScriptedChild, subcommandOf } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit, fx71Lines } from './fixtures/fx71';
import { defaultScript, fakeApis, loadPluginWith, tick } from './fixtures/plugin-harness';
import { abs, HOST_ENV, OPENAI_PROVIDER, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';
import { loadNodeApis } from '../src/process/node-apis';

jest.mock('../src/process/node-apis', () => ({
  loadNodeApis: jest.fn(),
}));

const R16 = req('REQ-SHL-16');
const R9 = req('REQ-SHL-09');
const R7 = req('REQ-SHL-07');

const INPUT_ROOT = abs(VAULT_ROOT, 'inbox');
const OUT = abs(VAULT_ROOT, 'markitdown-output');
const EN = dictionary('en');

interface Harness {
  coordinator: ShellCoordinator;
  spawner: FakeSpawner;
  el: ReturnType<typeof asFake>;
  bar: JobStatusBar;
  notices: string[];
  history: HistoryEntry[];
  showDetails: boolean;
}

function recordedRun(stem: string, blocked = false): ScriptedChild {
  return {
    stderr: chunksOf(fx71Bytes(`${stem}.progress.jsonl`), 2048),
    stdout: blocked ? [] : chunksOf(fx71Bytes(`${stem}.stdout.json`), 8192),
    exit: { code: fx71Exit(`${stem}.stdout.json`), signal: null },
    blocked,
  };
}

const ENABLED_GATE: VersionGate = { enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.5', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } };

function harness(
  settings = settingsV2(),
  script: (request: SpawnRequest) => ScriptedChild = () => ({ blocked: true, exit: { code: 0, signal: null } }),
  consent: (view: unknown) => Promise<ConsentDecision> = async () => ({ approved: false }),
  showDetails = true,
  gate: CoordinatorDeps['gate'] = () => ENABLED_GATE,
): Harness {
  const fs = new FakeFs({ directories: [VAULT_ROOT, OUT, INPUT_ROOT, PLUGIN_DIR] });
  const spawner = new FakeSpawner(script);
  const notices: string[] = [];
  const history: HistoryEntry[] = [];
  const el = asFake(fakeEl('div'));
  const state: Harness = { coordinator: null as unknown as ShellCoordinator, spawner, el, bar: null as unknown as JobStatusBar, notices, history, showDetails };
  const bar = new JobStatusBar(el as unknown as HTMLElement, {
    locale: () => 'en',
    showDetails: () => state.showDetails,
    onCancel: () => state.coordinator.cancel(),
  });
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
    gate,
    consent,
    notify: (key) => {
      notices.push(key);
    },
    recordHistory: async (entry) => {
      history.push(entry);
    },
    log: null,
    nonce: () => '0123456789abcdef',
    progress: bar,
  };
  state.coordinator = new ShellCoordinator(deps);
  state.bar = bar;
  return state;
}

function cancelButtons(el: ReturnType<typeof asFake>): ReturnType<typeof asFake>[] {
  return el.findAll((e) => e.tagName === 'button' && e.textContent === EN['shell.progress.cancel']);
}

beforeEach(() => mockState.reset());

it(R16('JT-16 Cancel is absent while idle, visible during a running job, bound to coordinator.cancel, and removed when the job ends'), async () => {
  const h = harness();
  expect(cancelButtons(h.el)).toEqual([]);
  const result = await h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  expect(result.accepted).toBe(true);
  await flush();
  expect(h.spawner.commands).toEqual(['run']);
  expect(h.spawner.children[0].alive).toBe(true);
  const buttons = cancelButtons(h.el);
  expect(buttons).toHaveLength(1);
  buttons[0].click();
  const report = await (h.coordinator.current as Promise<JobReport>);
  expect(h.spawner.children[0].cooperativeRequests).toBe(1);
  expect(report.run?.outcome).toBe('cancelled');
  expect(h.notices).toContain('shell.CANCELLED');
  expect(h.history.map((e) => e.outcome)).toEqual(['cancelled']);
  expect(cancelButtons(h.el)).toEqual([]);
  expect(h.coordinator.active).toBe(false);
});

it(R16('JT-16 Cancel is visible while the consent modal is open and prevents the replay when clicked'), async () => {
  let release: ((d: ConsentDecision) => void) | null = null;
  const h = harness(
    settingsV2({ provider: { ...OPENAI_PROVIDER } }),
    (request) => (subcommandOf(request) === 'plan'
      ? { stdout: chunksOf(fx71Bytes('plan-mixed.stdout.json'), 4096), exit: { code: fx71Exit('plan-mixed.stdout.json'), signal: null } }
      : recordedRun('consent-5-approved')),
    () => new Promise<ConsentDecision>((resolve) => {
      release = resolve;
    }),
  );
  await h.coordinator.submit({ kind: 'folder', paths: [INPUT_ROOT] }, 'ribbon');
  for (let i = 0; i < 20 && release === null; i++) await flush();
  expect(h.spawner.commands).toEqual(['plan']);
  expect(h.el.textContent).toContain(EN['shell.progress.phase.consent']);
  const buttons = cancelButtons(h.el);
  expect(buttons).toHaveLength(1);
  buttons[0].click();
  (release as unknown as ((d: ConsentDecision) => void) | null)?.({ approved: true, hashes: ['a'.repeat(64)] });
  const report = await (h.coordinator.current as Promise<JobReport>);
  expect(h.spawner.commands).toEqual(['plan']);
  expect(report.run).toBeNull();
  expect(h.history.map((e) => e.outcome)).toEqual(['cancelled']);
  expect(cancelButtons(h.el)).toEqual([]);
});

it(R16('JT-16 hiding progress details never hides Cancel'), async () => {
  const h = harness(settingsV2(), undefined, undefined, false);
  await h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  await flush();
  expect(cancelButtons(h.el)).toHaveLength(1);
  expect(h.el.findAll((e) => e.hasClass('mdflow-status-details'))).toEqual([]);
  h.coordinator.cancel();
  await h.coordinator.current;
});

it(R9('JT-09 progress details render engine stage, file counts and unit outcomes from forwarded events, never inventing completed work'), async () => {
  const forwarded: ProgressEvent[] = [];
  const h = harness(settingsV2(), () => recordedRun('run-mixed', true));
  const original = h.bar.event.bind(h.bar);
  h.bar.event = (event) => {
    forwarded.push(event);
    original(event);
  };
  await h.coordinator.submit({ kind: 'folder', paths: [INPUT_ROOT] }, 'command');
  for (let i = 0; i < 40 && forwarded.length < fx71Lines('run-mixed.progress.jsonl').length; i++) await flush();
  const framer = new JsonLinesFramer();
  const expected = [...framer.push(fx71Bytes('run-mixed.progress.jsonl')), ...framer.end()].flatMap((r) => (r.kind === 'event' ? [r.event] : []));
  expect(forwarded).toEqual(expected);
  const summary = summarizeProgress(expected);
  const details = h.el.findAll((e) => e.hasClass('mdflow-status-details'));
  expect(details).toHaveLength(1);
  const text = details[0].textContent;
  expect(text).toContain(String(summary.filesEnded));
  expect(text).toContain(String(summary.filesTotal));
  expect(text).toContain(String(summary.unitsDone));
  expect(text).toContain(String(summary.unitsPending));
  expect(text).toContain(summary.stage as string);
  h.coordinator.cancel();
  await h.coordinator.current;
});

/** Progress a `plan` child reports on stderr before the job's `run` starts (distinctive counts: 7 files, 9 pending units). */
const PLAN_PROGRESS = Buffer.from([
  '{"v":1,"ev":"run_start","ts":"2026-11-09T00:00:00+00:00","files":7,"provider":"openai-compatible"}',
  '{"v":1,"ev":"file_start","ts":"2026-11-09T00:00:00+00:00","file":"x.pdf","index":1,"total":7}',
  '{"v":1,"ev":"file_end","ts":"2026-11-09T00:00:00+00:00","file":"x.pdf","outputs":[],"units":{"total":9,"done":0,"pending":9,"failed":0}}',
  '{"v":1,"ev":"run_end","ts":"2026-11-09T00:00:00+00:00","exit":3,"files_ok":0,"files_failed":0,"provider_calls":0}',
  '',
].join('\n'));

it(R9('JT-09 the status bar shows the current run only: Plan file_end units are discarded at the run_start of the same job, and no event history is kept (M4 P-01 / M3-V03)'), async () => {
  let release: ((d: ConsentDecision) => void) | null = null;
  const forwarded: ProgressEvent[] = [];
  const h = harness(
    settingsV2({ provider: { ...OPENAI_PROVIDER } }),
    (request) => (subcommandOf(request) === 'plan'
      ? { stderr: [new Uint8Array(PLAN_PROGRESS)], stdout: chunksOf(fx71Bytes('plan-mixed.stdout.json'), 4096), exit: { code: fx71Exit('plan-mixed.stdout.json'), signal: null } }
      : recordedRun('consent-5-approved', true)),
    () => new Promise<ConsentDecision>((resolve) => {
      release = resolve;
    }),
  );
  const original = h.bar.event.bind(h.bar);
  h.bar.event = (event) => {
    forwarded.push(event);
    original(event);
  };
  await h.coordinator.submit({ kind: 'folder', paths: [INPUT_ROOT] }, 'ribbon');
  for (let i = 0; i < 20 && release === null; i++) await flush();
  expect(h.spawner.commands).toEqual(['plan']);
  // The Plan phase displayed its own pending work; nothing was invented as done.
  const planDetails = h.el.findAll((e) => e.hasClass('mdflow-status-details'))[0].textContent;
  expect(planDetails).toContain('pending 9');
  (release as unknown as ((d: ConsentDecision) => void) | null)?.({ approved: true, hashes: ['a'.repeat(64)] });
  const runLines = fx71Lines('consent-5-approved.progress.jsonl').length;
  for (let i = 0; i < 40 && forwarded.length < 4 + runLines; i++) await flush();
  expect(h.spawner.commands).toEqual(['plan', 'run']);
  const framer = new JsonLinesFramer();
  const runEvents = [...framer.push(fx71Bytes('consent-5-approved.progress.jsonl')), ...framer.end()].flatMap((r) => (r.kind === 'event' ? [r.event] : []));
  const run = summarizeProgress(runEvents);
  expect(run).toMatchObject({ filesTotal: 4, filesEnded: 4, unitsPending: 0 });
  const expectedText = formatMessage('en', 'shell.progress.details', {
    stage: run.stage ?? '-',
    filesEnded: String(run.filesEnded),
    filesTotal: String(run.filesTotal),
    done: String(run.unitsDone),
    pending: String(run.unitsPending),
    failed: String(run.unitsFailed),
  });
  const details = h.el.findAll((e) => e.hasClass('mdflow-status-details'));
  expect(details).toHaveLength(1);
  // Run-only counts (4/4, pending 0), not Plan + Run (5/4, pending 9).
  expect(details[0].textContent).toBe(expectedText);
  expect(details[0].textContent).not.toContain('files 5/');
  // The presenter keeps an incremental summary, never the whole event history (bounded memory, linear work).
  expect(Object.keys(h.bar)).not.toContain('events');
  expect(cancelButtons(h.el)).toHaveLength(1);
  h.coordinator.cancel();
  await h.coordinator.current;
});

function deferredGate(): { gate: () => Promise<VersionGate>; release: (gate: VersionGate) => void } {
  let release: ((gate: VersionGate) => void) | null = null;
  const pending = new Promise<VersionGate>((resolve) => {
    release = resolve;
  });
  return { gate: () => pending, release: (gate) => (release as unknown as (g: VersionGate) => void)(gate) };
}

it(R16('JT-16 Cancel while the admission still awaits the version gate prevents the launch: no spawn, not active, and a later submission is accepted (M4-V01)'), async () => {
  const { gate, release } = deferredGate();
  const h = harness(settingsV2(), undefined, undefined, true, gate);
  const pending = h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  await flush();
  expect(h.spawner.requests).toEqual([]);
  h.coordinator.cancel();
  release(ENABLED_GATE);
  const result = await pending;
  await flush();
  expect(result).toEqual({ accepted: false, diagnostic: 'shell.CANCELLED' });
  expect(h.spawner.requests).toEqual([]);
  expect(h.coordinator.active).toBe(false);
  expect(cancelButtons(h.el)).toEqual([]);
  expect(h.history).toEqual([]);
  // The cancelled admission does not poison the next one.
  const later = await h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'b.pdf')] }, 'command');
  expect(later.accepted).toBe(true);
  await flush();
  expect(h.spawner.requests).toHaveLength(1);
  h.coordinator.cancel();
  await h.coordinator.current;
  expect(h.coordinator.active).toBe(false);
});

it(R16('JT-16 unload (dispose) while the admission still awaits the version gate prevents the launch and keeps the coordinator disposed (M4-V01)'), async () => {
  const { gate, release } = deferredGate();
  const h = harness(settingsV2(), undefined, undefined, true, gate);
  const pending = h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  await flush();
  h.coordinator.dispose();
  release(ENABLED_GATE);
  const result = await pending;
  await flush();
  expect(result).toEqual({ accepted: false, diagnostic: 'shell.RUNTIME' });
  expect(h.spawner.requests).toEqual([]);
  expect(h.coordinator.active).toBe(false);
  expect(cancelButtons(h.el)).toEqual([]);
  const afterDispose = await h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'b.pdf')] }, 'command');
  expect(afterDispose).toEqual({ accepted: false, diagnostic: 'shell.RUNTIME' });
  expect(h.spawner.requests).toEqual([]);
});

it(R16('JT-16 the control case: without Cancel the same deferred admission launches exactly one engine (M4-V01)'), async () => {
  const { gate, release } = deferredGate();
  const h = harness(settingsV2(), undefined, undefined, true, gate);
  const pending = h.coordinator.submit({ kind: 'files', paths: [abs(INPUT_ROOT, 'a.pdf')] }, 'command');
  await flush();
  release(ENABLED_GATE);
  const result = await pending;
  await flush();
  expect(result.accepted).toBe(true);
  expect(h.spawner.requests).toHaveLength(1);
  expect(h.coordinator.active).toBe(true);
  h.coordinator.cancel();
  await h.coordinator.current;
});

it(R16('JT-16 the loaded plugin owns one status-bar Cancel control wired to its coordinator'), async () => {
  const apis = fakeApis((request) => (subcommandOf(request) === 'run' ? { blocked: true, exit: { code: 0, signal: null } } : defaultScript(request)));
  const { plugin } = await loadPluginWith(jest.mocked(loadNodeApis), settingsV2(), apis);
  await tick();
  const coordinator = plugin.coordinator;
  if (!coordinator) throw new Error('coordinator missing');
  const result = await coordinator.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command');
  expect(result).toMatchObject({ accepted: true });
  await tick();
  const items = asMockPlugin(plugin).statusBarItems;
  expect(items).toHaveLength(1);
  const buttons = cancelButtons(asFake(items[0]));
  expect(buttons).toHaveLength(1);
  buttons[0].click();
  const report = await (coordinator.current as Promise<JobReport>);
  expect(report.run?.outcome).toBe('cancelled');
  expect(apis.spawner.children.every((c) => !c.alive)).toBe(true);
  expect(cancelButtons(asFake(items[0]))).toEqual([]);
  plugin.unload();
});

it(R7('JT-07 a multi-input job records one history entry with the input count and the first path, not every absolute path'), async () => {
  const h = harness(settingsV2(), () => recordedRun('run-mixed'));
  const first = abs(INPUT_ROOT, 'a.pdf');
  const second = abs(INPUT_ROOT, 'b.docx');
  const third = abs(INPUT_ROOT, 'c.pdf');
  await h.coordinator.submit({ kind: 'files', paths: [first, second, third] }, 'command');
  await h.coordinator.current;
  expect(h.history).toHaveLength(1);
  expect(h.history[0].inputFile.startsWith(first)).toBe(true);
  expect(h.history[0].inputFile).toContain('+2');
  expect(h.history[0].inputFile).not.toContain(second);
  expect(h.history[0].inputFile).not.toContain(third);
  expect(h.history[0].outputFile).toBe(OUT);
  const single = harness(settingsV2(), () => recordedRun('run-mixed'));
  await single.coordinator.submit({ kind: 'files', paths: [first] }, 'command');
  await single.coordinator.current;
  expect(single.history[0].inputFile).toBe(first);
});

// ProgressSink is the seam main.ts wires; keep its shape explicit so a future refactor cannot drop Cancel silently.
const _sinkShape: ProgressSink = { begin: () => undefined, phase: () => undefined, event: () => undefined, end: () => undefined };
void _sinkShape;
void createApp;
