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
import { summarizeProgress } from '../src/ui/progress';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner } from './fixtures/fake-spawner';
import { fx71Bytes } from './fixtures/fx71';
import { abs, HOST_ENV, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

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

const ENABLED_GATE: VersionGate = { enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.5', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } };

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
