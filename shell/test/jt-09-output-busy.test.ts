/**
 * JT-09 / REQ-SHL-09: output resolved against the vault with platform-aware
 * real paths (no bare string-prefix check); absolute/traversing/symlink
 * escapes rejected; nonexistent destination resolved via the nearest existing
 * ancestor; nonrecursive selection excludes hidden entries, symlinks, output
 * and cache locations; one active conversion per plugin instance; progress
 * details never invent completed work.
 */
import { req } from './req';
import { JsonLinesFramer, type ProgressEvent } from '../src/pure/framing';
import type { VersionGate } from '../src/process/version-gate';
import { ShellCoordinator, type CoordinatorDeps } from '../src/ui/coordinator';
import { resolveDestination, selectImmediateFiles, type DirEntry } from '../src/ui/output-path';
import { applyProgressEvent, emptyProgressSummary, summarizeProgress } from '../src/ui/progress';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner } from './fixtures/fake-spawner';
import { fx71Bytes } from './fixtures/fx71';
import { abs, HOME, HOST_ENV, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-09');

// Platform-neutral POSIX layout for the path oracle; the Windows case/separator oracle uses a win32 FakeFs.
const V = '/home/alice/Vault';
const SIBLING = '/home/alice/Vault2';

function posixFs(): FakeFs {
  return new FakeFs({
    platform: 'posix',
    directories: [V, `${V}/notes`, `${V}/notes/out`, `${V}/new`, SIBLING, `${SIBLING}/out`, '/etc', `${V}/.obsidian`],
    links: { [`${V}/notes/link-out`]: `${SIBLING}/out`, [`${V}/notes/link-in`]: `${V}/notes/out` },
  });
}

function ops(fs: FakeFs): { realpath: FakeFs['realpath']; isDirectory: FakeFs['isDirectory']; isSymlink: FakeFs['isSymlink']; platform: FakeFs['platform'] } {
  return { realpath: (p) => fs.realpath(p), isDirectory: (p) => fs.isDirectory(p), isSymlink: (p) => fs.isSymlink(p), platform: fs.platform };
}

it(R('JT-09 a vault-relative existing directory resolves to its real absolute path inside the vault'), async () => {
  const result = await resolveDestination(V, 'notes/out', ops(posixFs()));
  expect(result).toEqual({ ok: true, absolute: `${V}/notes/out`, existing: true });
});

it(R('JT-09 absolute and traversing destinations are rejected with shell.DESTINATION even when they point inside the vault'), async () => {
  const fs = posixFs();
  for (const [value, reason] of [
    ['/etc', 'absolute'],
    [`${V}/notes/out`, 'absolute'],
    ['C:\\Users\\alice\\Vault\\notes', 'absolute'],
    ['../Vault2/out', 'traversal'],
    ['notes/../../Vault2/out', 'traversal'],
    ['notes/../notes/out', 'traversal'],
    ['', 'invalid'],
    ['notes/\u0000x', 'invalid'],
  ] as const) {
    const result = await resolveDestination(V, value, ops(fs));
    expect({ value, result }).toEqual({ value, result: { ok: false, diagnostic: 'shell.DESTINATION', reason } });
  }
});

it(R('JT-09 sibling-prefix and symlink escapes are detected through real paths, not string prefixes'), async () => {
  const fs = posixFs();
  // `/home/alice/Vault2/out` starts with the string `/home/alice/Vault`: a prefix check would accept it.
  const viaLink = await resolveDestination(V, 'notes/link-out', ops(fs));
  expect(viaLink).toMatchObject({ ok: false, diagnostic: 'shell.DESTINATION' });
  expect(['escape', 'symlink']).toContain((viaLink as { reason: string }).reason);
  const nestedUnderLink = await resolveDestination(V, 'notes/link-out/deeper', ops(fs));
  expect(nestedUnderLink).toMatchObject({ ok: false, diagnostic: 'shell.DESTINATION' });
  // A symlink that stays inside the vault is still refused as a destination component.
  const inside = await resolveDestination(V, 'notes/link-in', ops(fs));
  expect(inside).toMatchObject({ ok: false, diagnostic: 'shell.DESTINATION', reason: 'symlink' });
  // The config directory is not a destination.
  expect(await resolveDestination(V, '.obsidian/out', ops(fs))).toMatchObject({ ok: false, diagnostic: 'shell.DESTINATION' });
});

it(R('JT-09 a nonexistent destination resolves through its nearest existing ancestor and is reported as not yet existing'), async () => {
  const result = await resolveDestination(V, 'new/deeper/out', ops(posixFs()));
  expect(result).toEqual({ ok: true, absolute: `${V}/new/deeper/out`, existing: false });
  const escapingParent = await resolveDestination(V, 'notes/link-out/new/out', ops(posixFs()));
  expect(escapingParent).toMatchObject({ ok: false, diagnostic: 'shell.DESTINATION' });
});

it(R('JT-09 Windows case and separator variants resolve to one real destination; drive-absolute values are rejected'), async () => {
  const root = 'C:\\Users\\Alice\\Vault';
  const fs = new FakeFs({ platform: 'win32', directories: [root, `${root}\\Notes`, `${root}\\Notes\\Out`] });
  const a = await resolveDestination(root, 'Notes\\Out', ops(fs));
  const b = await resolveDestination(root, 'notes/out', ops(fs));
  expect(a.ok && b.ok).toBe(true);
  if (a.ok && b.ok) expect(a.absolute.toLowerCase().replace(/\\/g, '/')).toBe(b.absolute.toLowerCase().replace(/\\/g, '/'));
  expect(await resolveDestination(root, 'c:/users/alice/vault/notes/out', ops(fs))).toMatchObject({ ok: false, reason: 'absolute' });
  expect(await resolveDestination(root, '\\\\server\\share\\out', ops(fs))).toMatchObject({ ok: false, reason: 'absolute' });
  expect(await resolveDestination(root, 'Notes\\..\\..\\Other', ops(fs))).toMatchObject({ ok: false, reason: 'traversal' });
});

it(R('JT-09 nonrecursive folder selection keeps immediate regular files only and excludes hidden, symlink, output and cache entries'), () => {
  const folder = `${V}/inbox`;
  const entries: DirEntry[] = [
    { name: 'b.docx', kind: 'file' },
    { name: 'a.pdf', kind: 'file' },
    { name: '.DS_Store', kind: 'file' },
    { name: '.hidden.pdf', kind: 'file' },
    { name: 'link.pdf', kind: 'symlink' },
    { name: 'sub', kind: 'dir' },
    { name: 'markitdown-output', kind: 'dir' },
    { name: 'cache', kind: 'dir' },
    { name: 'socket', kind: 'other' },
    { name: '보고서 3분기.pdf', kind: 'file' },
  ];
  const selected = selectImmediateFiles(folder, entries, { outDir: `${folder}/markitdown-output`, cacheDir: `${folder}/cache` }, 'posix');
  expect(selected).toEqual([`${folder}/b.docx`, `${folder}/a.pdf`, `${folder}/보고서 3분기.pdf`]);
  const win = selectImmediateFiles('C:\\Vault\\Inbox', [{ name: 'A.PDF', kind: 'file' }, { name: 'Out', kind: 'dir' }], { outDir: 'c:/vault/inbox/out', cacheDir: 'C:\\x' }, 'win32');
  expect(win).toEqual(['C:\\Vault\\Inbox\\A.PDF']);
});

const ENABLED_GATE: VersionGate = { enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.7', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } };

function coordinator(spawner: FakeSpawner, outputPath = 'markitdown-output', gate?: CoordinatorDeps['gate']): { coordinator: ShellCoordinator; notices: string[] } {
  const fs = new FakeFs({ directories: [VAULT_ROOT, abs(VAULT_ROOT, 'markitdown-output'), abs(VAULT_ROOT, 'inbox'), PLUGIN_DIR, abs(PLUGIN_DIR, 'cache')] });
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
    settings: () => settingsV2({ outputPath }),
    gate: gate ?? (() => ENABLED_GATE),
    consent: async () => ({ approved: false }),
    notify: (key) => {
      notices.push(key);
    },
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
  };
  return { coordinator: new ShellCoordinator(deps), notices };
}

it(R('JT-09 a second request while one conversion is active reports busy and launches nothing'), async () => {
  const spawner = new FakeSpawner(() => ({ blocked: true, exit: { code: 0, signal: null } }));
  const { coordinator: c, notices } = coordinator(spawner);
  const first = await c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command');
  expect(first.accepted).toBe(true);
  await flush();
  expect(c.active).toBe(true);
  const second = await c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'b.pdf')] }, 'ribbon');
  expect(second).toEqual({ accepted: false, diagnostic: 'shell.BUSY' });
  expect(notices).toContain('shell.BUSY');
  expect(spawner.requests).toHaveLength(1);
  c.cancel();
  await c.current;
  expect(c.active).toBe(false);
});

it(R('JT-09 busy admission is atomic: two submits in the same tick while the version gate is still pending start one engine and refuse the other with shell.BUSY (M3 N-01)'), async () => {
  let releaseGate: ((gate: VersionGate) => void) | null = null;
  const pendingGate = new Promise<VersionGate>((resolve) => {
    releaseGate = resolve;
  });
  const spawner = new FakeSpawner(() => ({ blocked: true, exit: { code: 0, signal: null } }));
  const { coordinator: c, notices } = coordinator(spawner, 'markitdown-output', () => pendingGate);
  // Both requests pass the synchronous checks before either has awaited the gate (first job after load: probe of up to 5 s).
  const first = c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'context-menu');
  const second = c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'b.pdf')] }, 'drop');
  await flush();
  expect(spawner.requests).toEqual([]);
  (releaseGate as unknown as ((gate: VersionGate) => void) | null)?.(ENABLED_GATE);
  const results = await Promise.all([first, second]);
  await flush();
  expect(results.map((r) => r.accepted)).toEqual([true, false]);
  expect(results[1]).toEqual({ accepted: false, diagnostic: 'shell.BUSY' });
  expect(notices.filter((n) => n === 'shell.BUSY')).toHaveLength(1);
  expect(spawner.requests).toHaveLength(1);
  expect(spawner.requests[0].args).toContain(abs(VAULT_ROOT, 'inbox', 'a.pdf'));
  expect(c.active).toBe(true);
  // Cancel stops the one owned engine and the coordinator becomes free again.
  c.cancel();
  await c.current;
  expect(c.active).toBe(false);
  expect(spawner.children.every((child) => !child.alive)).toBe(true);
  const third = await c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'c.pdf')] }, 'command');
  expect(third.accepted).toBe(true);
  c.cancel();
  await c.current;
});

it(R('JT-09 a refused submission releases the reservation: a destination refusal is followed by an accepted request, never a stale busy'), async () => {
  const spawner = new FakeSpawner(() => ({ blocked: true, exit: { code: 0, signal: null } }));
  const { coordinator: c, notices } = coordinator(spawner, '../outside');
  const refusedTogether = await Promise.all([
    c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command'),
    c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'b.pdf')] }, 'ribbon'),
  ]);
  expect(refusedTogether[0]).toEqual({ accepted: false, diagnostic: 'shell.DESTINATION' });
  expect(refusedTogether[1]).toEqual({ accepted: false, diagnostic: 'shell.BUSY' });
  expect(spawner.requests).toEqual([]);
  expect(c.active).toBe(false);
  const empty = await c.submit({ kind: 'files', paths: [] }, 'command');
  expect(empty).toEqual({ accepted: false, diagnostic: 'shell.DESTINATION' });
  expect(notices.filter((n) => n === 'shell.BUSY')).toHaveLength(1);
  // The reservation is gone: a fresh coordinator state accepts the next valid request.
  const ok = coordinator(spawner);
  const accepted = await ok.coordinator.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command');
  expect(accepted.accepted).toBe(true);
  ok.coordinator.cancel();
  await ok.coordinator.current;
});

it(R('JT-09 an unsafe destination refuses the request before any spawn'), async () => {
  const spawner = new FakeSpawner(() => ({ exit: { code: 0, signal: null } }));
  const { coordinator: c, notices } = coordinator(spawner, '../outside');
  const result = await c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command');
  expect(result).toEqual({ accepted: false, diagnostic: 'shell.DESTINATION' });
  expect(notices).toContain('shell.DESTINATION');
  expect(spawner.requests).toEqual([]);
});

it(R('JT-09 progress details show stage, file counts and unit outcomes from events without inventing completed work'), () => {
  const framer = new JsonLinesFramer();
  const events: ProgressEvent[] = [...framer.push(fx71Bytes('approve-required.progress.jsonl')), ...framer.end()].flatMap((r) => (r.kind === 'event' ? [r.event] : []));
  const summary = summarizeProgress(events);
  expect(summary.filesTotal).toBe(5);
  expect(summary.filesEnded).toBe(5);
  expect(summary.filesAwaitingConsent).toBe(4);
  // Outputs with pending markers were written, but no unit was completed: nothing is counted as done.
  expect(summary.unitsDone).toBe(0);
  expect(summary.unitsPending).toBe(2 + 2 + 3 + 200);
  expect(summary.unitsFailed).toBe(0);
  expect(summary.exit).toBe(3);
  expect(summary.stage).toBe('write');
  const partial = summarizeProgress(events.slice(0, 5));
  expect(partial.exit).toBeNull();
  expect(partial.filesEnded).toBe(0);
  expect(partial.currentFile).toBe('b c.docx');
  expect(summarizeProgress([])).toEqual({ stage: null, currentFile: null, filesTotal: null, filesEnded: 0, unitsDone: 0, unitsPending: 0, unitsFailed: 0, filesAwaitingConsent: 0, exit: null });
});

const T = '2026-11-09T00:00:00+00:00';
/** A `plan` process reports its own file_end units (pending work) before the `run` of the same job starts. */
const PLAN_EVENTS: ProgressEvent[] = [
  { v: 1, ev: 'run_start', ts: T, files: 7, provider: 'openai-compatible' },
  { v: 1, ev: 'file_start', ts: T, file: 'x.pdf', index: 1, total: 7 },
  { v: 1, ev: 'stage', ts: T, file: 'x.pdf', stage: 'plan', state: 'end' },
  { v: 1, ev: 'file_end', ts: T, file: 'x.pdf', outputs: [], units: { total: 9, done: 0, pending: 9, failed: 0 } },
  { v: 1, ev: 'run_end', ts: T, exit: 3, files_ok: 0, files_failed: 0, provider_calls: 0 },
] as ProgressEvent[];
const RUN_EVENTS: ProgressEvent[] = [
  { v: 1, ev: 'run_start', ts: T, files: 1, provider: 'openai-compatible' },
  { v: 1, ev: 'file_start', ts: T, file: 'x.pdf', index: 1, total: 1 },
  { v: 1, ev: 'stage', ts: T, file: 'x.pdf', stage: 'write', state: 'end' },
  { v: 1, ev: 'file_end', ts: T, file: 'x.pdf', outputs: ['x.pdf.md'], units: { total: 1, done: 1, pending: 0, failed: 0 } },
] as ProgressEvent[];

it(R('JT-09 a run_start resets the summary: Plan file_end units never leak into the Run counts of the same job (M4 P-01 / M3-V03)'), () => {
  const mixed = summarizeProgress([...PLAN_EVENTS, ...RUN_EVENTS]);
  const runOnly = summarizeProgress(RUN_EVENTS);
  expect(runOnly).toEqual({ stage: 'write', currentFile: 'x.pdf', filesTotal: 1, filesEnded: 1, unitsDone: 1, unitsPending: 0, unitsFailed: 0, filesAwaitingConsent: 0, exit: null });
  // Files ended can never exceed the files announced by the current run.
  expect(mixed).toEqual(runOnly);
  expect(mixed.filesEnded).toBeLessThanOrEqual(mixed.filesTotal as number);
  // The Plan-only prefix still reports its own pending work (nothing is invented as done).
  expect(summarizeProgress(PLAN_EVENTS)).toMatchObject({ filesTotal: 7, filesEnded: 1, unitsDone: 0, unitsPending: 9, exit: 3 });
});

it(R('JT-09 the incremental reducer applied event by event equals the whole-stream summary: no event history is needed to render progress (M4 P-01)'), () => {
  const framer = new JsonLinesFramer();
  const events: ProgressEvent[] = [...framer.push(fx71Bytes('approve-required.progress.jsonl')), ...framer.end()].flatMap((r) => (r.kind === 'event' ? [r.event] : []));
  const incremental = emptyProgressSummary();
  for (const [i, event] of events.entries()) {
    const returned = applyProgressEvent(incremental, event);
    // In-place, O(1) per event: the same object is returned and equals the reduce of the prefix.
    expect(returned).toBe(incremental);
    if (i % 17 === 0 || i === events.length - 1) expect(incremental).toEqual(summarizeProgress(events.slice(0, i + 1)));
  }
  expect(incremental).toEqual(summarizeProgress(events));
  expect(emptyProgressSummary()).toEqual(summarizeProgress([]));
});

it(R('JT-09 a relative enginePython is refused as shell.RUNTIME before any spawn, never reported as a destination problem (M4 P-04)'), async () => {
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
    settings: () => settingsV2({ enginePython: 'venv/bin/python' }),
    gate: () => ENABLED_GATE,
    consent: async () => ({ approved: false }),
    notify: (key) => {
      notices.push(key);
    },
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
  };
  const c = new ShellCoordinator(deps);
  const result = await c.submit({ kind: 'files', paths: [abs(VAULT_ROOT, 'inbox', 'a.pdf')] }, 'command');
  expect(result).toEqual({ accepted: false, diagnostic: 'shell.RUNTIME' });
  expect(notices).toEqual(['shell.RUNTIME']);
  expect(spawner.requests).toEqual([]);
  expect(c.active).toBe(false);
});
