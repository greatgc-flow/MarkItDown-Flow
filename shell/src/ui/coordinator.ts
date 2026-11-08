/**
 * The single conversion coordinator every entry point shares (20_SHELL.md
 * REQ-SHL-08/09/14/15/16). One owned conversion per plugin instance; output
 * validation, diagnostics, consent, replay and cancellation live here.
 */
import { type Env, providerAvailability } from '../pure/env';
import { type HistoryEntry, type HistoryOutcome } from '../pure/history';
import type { UiLocale } from '../pure/i18n';
import type { Plan, RunReport } from '../pure/protocol';
import { defaultSettings, type SettingsV2 } from '../pure/settings';
import type { SpoolFs } from '../pure/spool';
import { EngineRun, type EngineResult } from '../process/engine-process';
import { APPROVED_BY_MODAL, buildSpawnRequest, type JobSnapshot, renderYesFile, snapshotJob } from '../process/launcher';
import type { RotatingLog } from '../process/log';
import type { Clock, FileSystemOps, HostPlatform, Spawner } from '../process/types';
import type { VersionGate } from '../process/version-gate';
import { buildConsentView, type ConsentDecision, type ConsentViewModel } from './consent-modal';
import { type DirEntry, joinPath, resolveDestination, selectImmediateFiles } from './output-path';

export type EntryPoint = 'command' | 'ribbon' | 'context-menu' | 'drop';

export interface Selection {
  kind: 'files' | 'folder';
  /** Absolute paths exactly as selected, in selection order. */
  paths: readonly string[];
}

/** The request every entry point produces; identical selections give identical requests. */
export interface CoordinatorRequest {
  inputs: string[];
  cwd: string;
  outDir: string;
  cacheDir: string;
  recursive: boolean;
}

export type SubmitResult =
  | { accepted: true; snapshot: JobSnapshot }
  | { accepted: false; diagnostic: 'shell.BUSY' | 'shell.DESTINATION' | 'shell.RUNTIME' | 'shell.SETTINGS' };

export interface CoordinatorDeps {
  spawner: Spawner;
  fs: FileSystemOps;
  spoolFs: SpoolFs;
  clock: Clock;
  hostEnv: Env;
  platform: HostPlatform;
  vaultRoot: string;
  pluginDir: string;
  locale: UiLocale;
  settings: () => SettingsV2;
  /** Result of the version gate taken before jobs; null blocks with `shell.RUNTIME`. */
  gate: () => VersionGate | null;
  /** Presents the single consent modal; tests inject a decision. */
  consent: (view: ConsentViewModel) => Promise<ConsentDecision>;
  notify: (key: string, params?: Record<string, string>) => void;
  /** Persist a history entry (settings owner). */
  recordHistory: (entry: HistoryEntry) => Promise<void>;
  log: RotatingLog | null;
  /** Random 16-hex nonce source for spool names. */
  nonce: () => string;
}

export interface JobReport {
  snapshot: JobSnapshot;
  plan: EngineResult<Plan[]> | null;
  run: EngineResult<RunReport> | null;
  decision: ConsentDecision | null;
  /** True when a pending/denied engine state was displayed for fresh review (never auto-approved). */
  pendingShown: boolean;
}

export const CACHE_DIR_NAME = 'cache';
export const SPOOL_DIR_NAME = 'spool';
export const CONSENT_DIR_NAME = 'consent';

const APPROVAL_CODES: ReadonlySet<string> = new Set(['E_APPROVAL_REQUIRED', 'E_APPROVAL_DENIED']);

export class ShellCoordinator {
  private job: Promise<JobReport> | null = null;
  private isActive = false;
  private cancelled = false;
  private disposed = false;
  private engine: EngineRun<'plan'> | EngineRun<'report'> | null = null;
  private cancelWaiters: (() => void)[] = [];

  constructor(private readonly deps: CoordinatorDeps) {}

  /** Pure projection used by every entry point before any work. */
  buildRequest(selection: Selection): CoordinatorRequest {
    const settings = this.deps.settings();
    return {
      inputs: [...selection.paths],
      cwd: this.deps.vaultRoot,
      outDir: joinPath(this.deps.platform, this.deps.vaultRoot, settings.outputPath),
      cacheDir: joinPath(this.deps.platform, this.deps.pluginDir, CACHE_DIR_NAME),
      recursive: selection.kind === 'folder' ? settings.enableRecursiveConversion : true,
    };
  }

  private refuse(diagnostic: Extract<SubmitResult, { accepted: false }>['diagnostic']): SubmitResult {
    this.deps.notify(diagnostic);
    return { accepted: false, diagnostic };
  }

  /** Busy check, destination validation, snapshot; then starts the job (not awaited). */
  async submit(selection: Selection, _entry: EntryPoint): Promise<SubmitResult> {
    if (this.isActive) return this.refuse('shell.BUSY');
    if (this.disposed) return this.refuse('shell.RUNTIME');
    const gate = this.deps.gate();
    if (!gate || !gate.enabled) return this.refuse('shell.RUNTIME');
    const settings = this.deps.settings();
    if (!settings.enginePython) return this.refuse('shell.RUNTIME');
    if (selection.paths.length === 0) return this.refuse('shell.DESTINATION');

    const { fs, platform } = this.deps;
    const destination = await resolveDestination(this.deps.vaultRoot, settings.outputPath, {
      realpath: (p) => fs.realpath(p),
      isDirectory: (p) => fs.isDirectory(p),
      isSymlink: (p) => fs.isSymlink(p),
      platform,
    });
    if (!destination.ok) return this.refuse('shell.DESTINATION');

    const request = this.buildRequest(selection);
    let inputs = request.inputs;
    if (selection.kind === 'folder' && !request.recursive) {
      inputs = [];
      for (const folder of selection.paths) {
        const entries: DirEntry[] = [];
        for (const name of await fs.list(folder)) {
          const full = joinPath(platform, folder, name);
          let kind: DirEntry['kind'] = 'file';
          if (await fs.isSymlink(full)) kind = 'symlink';
          else if (await fs.isDirectory(full)) kind = 'dir';
          entries.push({ name, kind });
        }
        inputs.push(...selectImmediateFiles(folder, entries, { outDir: request.outDir, cacheDir: request.cacheDir }, platform));
      }
      if (inputs.length === 0) return this.refuse('shell.DESTINATION');
    }

    // Remote work without an inherited key degrades to provider none (REQ-SHL-06).
    const availability = providerAvailability(settings, this.deps.hostEnv);
    if (availability.remoteBlocked && availability.guidanceKey) this.deps.notify(availability.guidanceKey);
    const effective: SettingsV2 = availability.effectiveProvider === 'none' && settings.provider.name !== 'none'
      ? { ...settings, provider: defaultSettings().provider }
      : settings;

    let snapshot: JobSnapshot;
    try {
      snapshot = snapshotJob({ settings: effective, inputs, cwd: request.cwd, outDir: destination.absolute, cacheDir: request.cacheDir });
    } catch {
      return this.refuse('shell.DESTINATION');
    }

    this.isActive = true;
    this.cancelled = false;
    this.job = this.runJob(snapshot).finally(() => {
      this.isActive = false;
      this.engine = null;
    });
    return { accepted: true, snapshot };
  }

  /** Resolves when the current job (if any) has finished, with its report. */
  get current(): Promise<JobReport> | null {
    return this.job;
  }

  get active(): boolean {
    return this.isActive;
  }

  /** Cancel: dismiss consent, prevent launches, cooperative-then-forced stop of the owned engine. */
  cancel(): void {
    this.cancelled = true;
    this.engine?.cancel();
    for (const waiter of this.cancelWaiters.splice(0)) waiter();
  }

  /** Unload: same as cancel plus disposal of listeners. */
  dispose(): void {
    this.disposed = true;
    this.cancel();
  }

  /** `convert-url` compatibility notice: zero engine or network work. */
  legacyUrlNotice(): void {
    this.deps.notify('shell.LEGACY_URL');
  }

  private cancelSignal(): Promise<null> {
    return new Promise((resolve) => {
      if (this.cancelled) resolve(null);
      else this.cancelWaiters.push(() => resolve(null));
    });
  }

  private async execute<K extends 'plan' | 'report'>(kind: K, request: ReturnType<typeof buildSpawnRequest>): Promise<EngineResult<K extends 'plan' ? Plan[] : RunReport> | null> {
    if (this.cancelled) return null;
    const run = new EngineRun(this.deps.spawner, request, { stdout: kind, spoolFs: this.deps.spoolFs, nonce: this.deps.nonce(), clock: this.deps.clock });
    this.engine = run as unknown as EngineRun<'plan'> | EngineRun<'report'>;
    run.start();
    const result = await run.done;
    this.engine = null;
    return result as unknown as EngineResult<K extends 'plan' ? Plan[] : RunReport>;
  }

  private async log(record: { stage?: string; code?: string; count?: number; status?: string }): Promise<void> {
    if (!this.deps.log) return;
    await this.deps.log.write({ ts: new Date(this.deps.clock.now()).toISOString(), ...record });
  }

  private async record(snapshot: JobSnapshot, outcome: HistoryOutcome): Promise<void> {
    await this.deps.recordHistory({
      inputFile: snapshot.inputs.join(', '),
      outputFile: snapshot.outDir,
      timestamp: this.deps.clock.now(),
      success: outcome === 'complete',
      outcome,
    });
  }

  private async runJob(snapshot: JobSnapshot): Promise<JobReport> {
    const report: JobReport = { snapshot, plan: null, run: null, decision: null, pendingShown: false };
    const remote = snapshot.provider.name !== 'none';
    let authorization: { yesFile: string; approvedBy: typeof APPROVED_BY_MODAL } | null = null;
    let yesFilePath: string | null = null;

    await this.log({ stage: 'submit', count: snapshot.inputs.length, status: remote ? 'plan' : 'run' });

    if (remote) {
      const plan = await this.execute('plan', buildSpawnRequest(snapshot, 'plan', this.deps.hostEnv));
      report.plan = plan;
      if (plan === null || this.cancelled) {
        await this.finishCancelled(snapshot);
        return report;
      }
      if (!plan.stdout || !plan.stdout.ok) {
        for (const key of plan.diagnostics) this.deps.notify(key);
        if (!plan.diagnostics.includes('shell.PROTOCOL')) this.deps.notify('shell.PROTOCOL');
        await this.log({ stage: 'plan', code: plan.startupError?.code, status: 'failed' });
        await this.record(snapshot, 'partial_failure');
        return report;
      }
      const plans = plan.stdout.value;
      const needingConsent = plans.filter((p) => p.approved.max_requests > 0);
      if (needingConsent.length > 0) {
        const view = buildConsentView(plans, snapshot.outDir);
        const decision = await Promise.race([this.deps.consent(view), this.cancelSignal()]);
        if (decision === null || this.cancelled) {
          await this.finishCancelled(snapshot);
          return report;
        }
        report.decision = decision;
        if (!decision.approved) {
          await this.log({ stage: 'approve', count: needingConsent.length, status: 'kept_pending' });
          await this.record(snapshot, 'pending_consent');
          return report;
        }
        const approvable = new Set(needingConsent.map((p) => p.plan_hash));
        const hashes = decision.hashes.filter((h) => approvable.has(h));
        const consentDir = joinPath(this.deps.platform, this.deps.pluginDir, CONSENT_DIR_NAME);
        yesFilePath = joinPath(this.deps.platform, consentDir, `yes-${this.deps.nonce()}-${this.deps.clock.now().toString(36)}.txt`);
        await this.deps.fs.mkdir(consentDir);
        await this.deps.fs.writeFile(yesFilePath, new TextEncoder().encode(renderYesFile(hashes)));
        authorization = { yesFile: yesFilePath, approvedBy: APPROVED_BY_MODAL };
        await this.log({ stage: 'approve', count: hashes.length, status: 'approved' });
      }
    }

    if (this.cancelled) {
      await this.removeYesFile(yesFilePath);
      await this.finishCancelled(snapshot);
      return report;
    }

    let run: EngineResult<RunReport> | null;
    try {
      run = await this.execute('report', buildSpawnRequest(snapshot, 'run', this.deps.hostEnv, authorization));
    } finally {
      await this.removeYesFile(yesFilePath);
    }
    report.run = run;
    if (run === null) {
      await this.finishCancelled(snapshot);
      return report;
    }
    report.pendingShown = run.outcome === 'pending_consent' || run.events.some((e) => (e.ev === 'error' && APPROVAL_CODES.has(e.code)) || e.ev === 'approve_required');
    for (const key of run.diagnostics) this.deps.notify(key);
    if (run.outcome === 'complete') this.deps.notify('shell.notice.jobDone', { outcome: run.outcome });
    await this.log({ stage: 'run', code: run.startupError?.code, count: run.events.filter((e) => e.ev === 'file_end').length, status: `${run.termination}:${run.outcome}` });
    await this.record(snapshot, run.outcome);
    return report;
  }

  private async removeYesFile(path: string | null): Promise<void> {
    if (!path) return;
    try {
      await this.deps.fs.remove(path);
    } catch {
      // Best effort: the file holds hashes only.
    }
  }

  private async finishCancelled(snapshot: JobSnapshot): Promise<void> {
    this.deps.notify('shell.CANCELLED');
    await this.log({ stage: 'cancel', status: 'cancelled' });
    await this.record(snapshot, 'cancelled');
  }
}
