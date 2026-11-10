/**
 * MECE round 7 shell findings (docs/renewal/review/M7_cc_cross.md):
 *  - M7-01 PowerShell quote() doubles the typographic single quotes U+2018/U+2019/U+201A/U+201B too;
 *  - M7-02 admission shows a status item with Cancel while it waits on the version gate;
 *  - M7-03 HANDOFF no longer states the FX-71 publication as Core 0.3.6 in the present tense.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { req } from './req';
import { renderBootstrapInstructions, renderUpstreamUninstall } from '../src/process/setup';
import type { VersionGate } from '../src/process/version-gate';
import { dictionary } from '../src/pure/i18n';
import { ShellCoordinator, type CoordinatorDeps } from '../src/ui/coordinator';
import type { JobPhase, ProgressSink } from '../src/ui/progress';
import { FakeClock, flush } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { chunksOf, FakeSpawner, subcommandOf } from './fixtures/fake-spawner';
import { fx71Bytes, fx71Exit } from './fixtures/fx71';
import { abs, HOME, HOST_ENV, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R10 = req('REQ-SHL-10');
const R16 = req('REQ-SHL-16');
const R17 = req('REQ-SHL-17');
const REPO = path.resolve(__dirname, '..', '..');

it(R10('JT-10 M7-01 PowerShell quoting doubles every single-quote character PowerShell recognizes; sh quoting is unchanged'), () => {
  for (const q of ['\u2018', '\u2019', '\u201A', '\u201B', "'"]) {
    const dir = `C:\\Users\\O${q}Brien\\venv`;
    const uninstall = renderUpstreamUninstall(`${dir}\\Scripts\\python.exe`, 'win32');
    expect(uninstall).toBe(`& 'C:\\Users\\O${q}${q}Brien\\venv\\Scripts\\python.exe' -m pip uninstall -y markitdown`);
    const text = renderBootstrapInstructions({ downloadDir: `C:\\dl${q}x`, venvDir: dir, bootstrapPython: `C:\\Py${q}s\\python.exe` });
    expect(text.windows).toContain(`Set-Location -LiteralPath 'C:\\dl${q}${q}x'`);
    expect(text.windows).toContain(`& 'C:\\Py${q}${q}s\\python.exe' -m venv 'C:\\Users\\O${q}${q}Brien\\venv'`);
  }
  // The POSIX quoter only needs the ASCII apostrophe handled; a typographic quote is a plain character for sh.
  expect(renderUpstreamUninstall('/u/O\u2019Brien/venv/bin/python', 'posix')).toBe("'/u/O\u2019Brien/venv/bin/python' -m pip uninstall -y markitdown");
});

class RecordingSink implements ProgressSink {
  readonly calls: string[] = [];
  begin(phase: JobPhase): void {
    this.calls.push(`begin:${phase}`);
  }
  phase(phase: JobPhase): void {
    this.calls.push(`phase:${phase}`);
  }
  event(): void {
    this.calls.push('event');
  }
  end(): void {
    this.calls.push('end');
  }
}

const GOOD_GATE: VersionGate = { enabled: true, info: { mdflow: '2.0.0', 'markitdown-gc': '0.3.8', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.0', platform: 'test', protocol: 1, triage_schema: 1 } };

function gateHarness(gate: CoordinatorDeps['gate'], progress: ProgressSink, notify: CoordinatorDeps['notify'] = () => undefined): { coordinator: ShellCoordinator; spawner: FakeSpawner } {
  const fsys = new FakeFs({ directories: [VAULT_ROOT, abs(VAULT_ROOT, 'markitdown-output'), abs(VAULT_ROOT, 'inbox'), PLUGIN_DIR, abs(PLUGIN_DIR, 'cache')] });
  const spawner = new FakeSpawner((request) => {
    if (subcommandOf(request) === 'plan') return { stdout: chunksOf(fx71Bytes('plan-mixed.stdout.json'), 4096), exit: { code: fx71Exit('plan-mixed.stdout.json'), signal: null } };
    return { stderr: chunksOf(fx71Bytes('consent-5-approved.progress.jsonl'), 2048), stdout: chunksOf(fx71Bytes('consent-5-approved.stdout.json'), 8192), exit: { code: fx71Exit('consent-5-approved.stdout.json'), signal: null } };
  });
  const deps: CoordinatorDeps = {
    spawner,
    fs: fsys,
    spoolFs: new FakeSpoolFs(fsys, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    homeDir: HOME,
    settings: () => settingsV2({}),
    gate,
    consent: async () => ({ approved: false }),
    notify,
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
    progress,
  };
  return { coordinator: new ShellCoordinator(deps), spawner };
}

const SELECTION = { kind: 'folder', paths: [abs(VAULT_ROOT, 'inbox')] } as const;

it(R16('JT-16 M7-02 a slow version gate shows the status item with Cancel during admission, and Cancel removes it with zero spawns'), async () => {
  const sink = new RecordingSink();
  let release: (gate: VersionGate) => void = () => undefined;
  const h = gateHarness(() => new Promise<VersionGate>((resolve) => { release = resolve; }), sink);
  const submitted = h.coordinator.submit(SELECTION, 'command');
  await flush();
  expect(sink.calls).toEqual(['begin:check']);
  h.coordinator.cancel();
  release(GOOD_GATE);
  const result = await submitted;
  expect(result.accepted).toBe(false);
  expect(sink.calls).toEqual(['begin:check', 'end']);
  expect(h.spawner.commands).toEqual([]);
});

it(R16('JT-16 M7-02 a gate that refuses ends the status item; an admitted job keeps one item that the job ends'), async () => {
  const refused = new RecordingSink();
  const blocked = gateHarness(async () => ({ enabled: false, reason: 'timeout' }) as VersionGate, refused);
  expect((await blocked.coordinator.submit(SELECTION, 'command')).accepted).toBe(false);
  expect(refused.calls).toEqual(['begin:check', 'end']);

  const admitted = new RecordingSink();
  const ok = gateHarness(async () => GOOD_GATE, admitted);
  expect((await ok.coordinator.submit(SELECTION, 'command')).accepted).toBe(true);
  await ok.coordinator.current;
  expect(admitted.calls.filter((c) => c === 'end')).toHaveLength(1);
  expect(admitted.calls[0]).toBe('begin:check');
  expect(admitted.calls.at(-1)).toBe('end');
});

it(R16('JT-16 M8-01 Cancel during the checking phase refuses the admission at once even though the version probe never settles'), async () => {
  const sink = new RecordingSink();
  const notices: string[] = [];
  const h = gateHarness(() => new Promise<VersionGate>(() => undefined), sink, (key) => notices.push(String(key)));
  let settled: { accepted: boolean } | null = null;
  void h.coordinator.submit(SELECTION, 'command').then((r) => {
    settled = r;
  });
  await flush();
  expect(sink.calls).toEqual(['begin:check']);
  expect(settled).toBeNull();
  h.coordinator.cancel();
  await flush();
  expect(settled).toEqual(expect.objectContaining({ accepted: false }));
  expect(sink.calls).toEqual(['begin:check', 'end']);
  expect(notices).toContain('shell.CANCELLED');
  expect(h.spawner.commands).toEqual([]);
  expect((h.coordinator as unknown as { cancelWaiters: unknown[] }).cancelWaiters).toHaveLength(0);
});

it(R16('JT-16 M7-02 the checking phase has text in both locales'), () => {
  for (const dict of [dictionary('en'), dictionary('ko')]) expect(dict['shell.progress.phase.check']).toBeTruthy();
});

it(R17('JT-17 M7-03 HANDOFF does not present the FX-71 publication as Core 0.3.6 without the R34 refresh'), () => {
  const handoff = fs.readFileSync(path.join(REPO, 'docs', 'renewal', 'HANDOFF.md'), 'utf8');
  const line = handoff.split('\n').find((l) => l.includes('Python 3.14.10, Core 0.3.6')) ?? '';
  expect(line).toContain('Core 0.3.7');
});
