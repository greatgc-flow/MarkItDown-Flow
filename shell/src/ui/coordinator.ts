/**
 * The single conversion coordinator every entry point shares (20_SHELL.md
 * REQ-SHL-08/09/14/15/16). One owned conversion per plugin instance; output
 * validation (before submit and again immediately before the `run` spawn),
 * diagnostics, consent, replay, progress reporting and cancellation live here.
 */
import { type Env, providerAvailability } from '../pure/env';
import { type HistoryEntry, type HistoryOutcome } from '../pure/history';
import { isAbsolutePath, joinPath } from '../pure/paths';
import type { Plan, RunReport } from '../pure/protocol';
import { defaultSettings, type SettingsV2 } from '../pure/settings';
import type { SpoolFs } from '../pure/spool';
import { EngineRun, type EngineResult } from '../process/engine-process';
import { APPROVED_BY_MODAL, type Authorization, buildSpawnRequest, engineWorkingDirectory, type JobSnapshot, renderYesFile, snapshotJob } from '../process/launcher';
import type { RotatingLog } from '../process/log';
import type { Clock, FileSystemOps, HostPlatform, Spawner } from '../process/types';
import type { VersionGate } from '../process/version-gate';
import { buildConsentView, type ConsentDecision, type ConsentViewModel } from './consent-modal';
import { type DirEntry, resolveDestination, selectImmediateFiles } from './output-path';
import type { ProgressSink } from './progress';
import { buildResultsView, type ResultsViewModel } from './results-modal';

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
  | { accepted: false; diagnostic: 'shell.BUSY' | 'shell.CANCELLED' | 'shell.DESTINATION' | 'shell.RUNTIME' | 'shell.SETTINGS' };

export interface CoordinatorDeps {
  spawner: Spawner;
  fs: FileSystemOps;
  spoolFs: SpoolFs;
  clock: Clock;
  hostEnv: Env;
  platform: HostPlatform;
  vaultRoot: string;
  pluginDir: string;
  settings: () => SettingsV2;
  /** Result of the version gate taken before jobs (may be probed lazily); null blocks with `shell.RUNTIME`. */
  gate: () => VersionGate | null | Promise<VersionGate | null>;
  /** Presents the single consent modal; tests inject a decision. */
  consent: (view: ConsentViewModel) => Promise<ConsentDecision>;
  notify: (key: string, params?: Record<string, string>) => void;
  /** Persist a history entry (settings owner). */
  recordHistory: (entry: HistoryEntry) => Promise<void>;
  log: RotatingLog | null;
  /** Random 16-hex nonce source for spool names. */
  nonce: () => string;
  /** Progress/Cancel presenter (REQ-SHL-09/16); null in headless tests. */
  progress?: ProgressSink | null;
  /** Per-file result list of a run that produced a decoded report (R32); omitted in headless tests. */
  results?: ((view: ResultsViewModel) => void) | null;
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

/** SPEC 8.4 / approve.py: consent is required only when the provider has egress and requests remain to send. */
export function needsConsent(plan: Plan): boolean {
  return plan.approved.provider.egress && plan.status.requests_to_send > 0;
}

/** History display reference: the first path plus a count; never every absolute path (REQ-SHL-07). */
export function historyInputLabel(inputs: readonly string[]): string {
  if (inputs.length <= 1) return inputs[0] ?? '';
  return `${inputs[0]} (+${inputs.length - 1})`;
}

export class ShellCoordinator {
  private job: Promise<JobReport> | null = null;
  private isActive = false;
  /** Synchronous admission reservation held across the awaits of `submit` (REQ-SHL-09; M3 N-01). */
  private reserved = false;
  /** Set by `cancel()`/`dispose()`; a pending admission re-checks it after each await and never launches (M4-V01). */
  private admissionCancelled = false;
  private cancelled = false;
  private disposed = false;
  private engine: EngineRun<'plan'> | EngineRun<'report'> | null = null;
  private cancelWaiters: (() => void)[] = [];

  constructor(private readonly deps: CoordinatorDeps) {}

  /** Pure projection used by every entry point before any work. The cwd is the engine venv root, never the vault (M3 N-02). */
  buildRequest(selection: Selection): CoordinatorRequest {
    const settings = this.deps.settings();
    return {
      inputs: [...selection.paths],
      cwd: settings.enginePython ? engineWorkingDirectory(this.deps.platform, settings.enginePython) : '',
      outDir: joinPath(this.deps.platform, this.deps.vaultRoot, settings.outputPath),
      cacheDir: joinPath(this.deps.platform, this.deps.pluginDir, CACHE_DIR_NAME),
      recursive: selection.kind === 'folder' ? settings.enableRecursiveConversion : true,
    };
  }

  private refuse(diagnostic: Extract<SubmitResult, { accepted: false }>['diagnostic']): SubmitResult {
    this.deps.notify(diagnostic);
    return { accepted: false, diagnostic };
  }

  private async validateDestination(outputPath: string): Promise<string | null> {
    const { fs, platform } = this.deps;
    const destination = await resolveDestination(this.deps.vaultRoot, outputPath, {
      realpath: (p) => fs.realpath(p),
      isDirectory: (p) => fs.isDirectory(p),
      isSymlink: (p) => fs.isSymlink(p),
      platform,
    });
    return destination.ok ? destination.absolute : null;
  }

  /**
   * Busy check, version gate, destination validation, snapshot; then starts the job (not awaited).
   * Admission is atomic: the reservation is taken synchronously before the first await and
   * released on every refusal path, so two overlapping submissions never both pass (M3 N-01).
   * A Cancel or unload that arrives while the admission awaits the gate, the destination or a
   * folder listing refuses the launch instead of being overwritten by it (M4-V01).
   */
  async submit(selection: Selection, entry: EntryPoint): Promise<SubmitResult> {
    if (this.isActive || this.reserved) return this.refuse('shell.BUSY');
    this.reserved = true;
    this.admissionCancelled = false;
    try {
      return await this.admit(selection, entry);
    } finally {
      this.reserved = false;
    }
  }

  /** After each await of `admit`: unload refuses with `shell.RUNTIME`, Cancel with `shell.CANCELLED`; null continues. */
  private admissionInterrupted(): SubmitResult | null {
    if (this.disposed) return this.refuse('shell.RUNTIME');
    if (this.admissionCancelled) return this.refuse('shell.CANCELLED');
    return null;
  }

  private async admit(selection: Selection, entry: EntryPoint): Promise<SubmitResult> {
    if (this.disposed) return this.refuse('shell.RUNTIME');
    const settings = this.deps.settings();
    // REQ-SHL-04/12: only a committed absolute interpreter is ever spawned; a relative value that reached the
    // settings (hand-edited or synced data.json) is a runtime configuration problem, not a destination one (M4 P-04).
    if (!settings.enginePython || !isAbsolutePath(settings.enginePython)) return this.refuse('shell.RUNTIME');
    if (selection.paths.length === 0) return this.refuse('shell.DESTINATION');
    const gate = await this.deps.gate();
    const afterGate = this.admissionInterrupted();
    if (afterGate) return afterGate;
    if (!gate || !gate.enabled) return this.refuse('shell.RUNTIME');

    const { fs, platform } = this.deps;
    const outDir = await this.validateDestination(settings.outputPath);
    const afterDestination = this.admissionInterrupted();
    if (afterDestination) return afterDestination;
    if (outDir === null) return this.refuse('shell.DESTINATION');

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
      const afterListing = this.admissionInterrupted();
      if (afterListing) return afterListing;
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
      snapshot = snapshotJob({ settings: effective, inputs, cwd: request.cwd, outDir, cacheDir: request.cacheDir });
    } catch {
      return this.refuse('shell.DESTINATION');
    }

    this.isActive = true;
    this.cancelled = false;
    this.deps.progress?.begin(snapshot.provider.name !== 'none' ? 'plan' : 'run');
    this.job = this.runJob(snapshot, entry).finally(() => {
      this.isActive = false;
      this.engine = null;
      this.deps.progress?.end();
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

  /** Cancel: dismiss consent, prevent launches (including a pending admission), cooperative-then-forced stop of the owned engine. */
  cancel(): void {
    this.cancelled = true;
    this.admissionCancelled = true;
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
    const progress = this.deps.progress;
    if (progress) run.onEvent((event) => progress.event(event));
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
      inputFile: historyInputLabel(snapshot.inputs),
      outputFile: snapshot.outDir,
      timestamp: this.deps.clock.now(),
      success: outcome === 'complete',
      outcome,
    });
  }

  private async runJob(snapshot: JobSnapshot, entry: EntryPoint): Promise<JobReport> {
    const report: JobReport = { snapshot, plan: null, run: null, decision: null, pendingShown: false };
    const remote = snapshot.provider.name !== 'none';
    let authorization: Authorization | null = null;
    let yesFilePath: string | null = null;

    await this.log({ stage: 'submit', count: snapshot.inputs.length, status: `${entry}:${remote ? 'plan' : 'run'}` });

    if (remote) {
      const plan = await this.execute('plan', buildSpawnRequest(snapshot, 'plan', this.deps.hostEnv));
      report.plan = plan;
      if (plan === null || this.cancelled) {
        await this.finishCancelled(snapshot);
        return report;
      }
      if (!plan.stdout || !plan.stdout.ok) {
        // EngineRun already names decode/framing failures `shell.PROTOCOL` and startup errors by their SPEC 7.5
        // code; the coordinator adds PROTOCOL only when the engine left no visible diagnostic at all (M3 N-03).
        for (const key of plan.diagnostics) this.deps.notify(key);
        if (plan.diagnostics.length === 0) this.deps.notify('shell.PROTOCOL');
        await this.log({ stage: 'plan', code: plan.startupError?.code, status: 'failed' });
        await this.record(snapshot, 'partial_failure');
        return report;
      }
      const plans = plan.stdout.value;
      const needingConsent = plans.filter(needsConsent);
      if (needingConsent.length > 0) {
        this.deps.progress?.phase('consent');
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
        authorization = { yesFile: yesFilePath, approvedBy: APPROVED_BY_MODAL };
        await this.log({ stage: 'approve', count: hashes.length, status: 'approved' });
        // REQ-SHL-09: revalidate the destination immediately before the spawn; the plan/modal may have taken minutes.
        if (!(await this.destinationStillValid(snapshot))) return this.refuseRun(snapshot, report);
        await this.deps.fs.mkdir(consentDir);
        await this.deps.fs.writeFile(yesFilePath, new TextEncoder().encode(renderYesFile(hashes)));
      }
    }

    if (this.cancelled) {
      await this.removeYesFile(yesFilePath);
      await this.finishCancelled(snapshot);
      return report;
    }
    if (!authorization && !(await this.destinationStillValid(snapshot))) return this.refuseRun(snapshot, report);

    this.deps.progress?.phase('run');
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
    // Concise per-file list from the decoded report only (R32); a forced or report-less end shows nothing invented.
    if (run.stdout?.ok) this.deps.results?.(buildResultsView(run.stdout.value, run.outcome));
    await this.log({ stage: 'run', code: run.startupError?.code, count: run.events.filter((e) => e.ev === 'file_end').length, status: `${run.termination}:${run.outcome}` });
    await this.record(snapshot, run.outcome);
    return report;
  }

  /** The destination resolved at submit must still resolve to the same real vault location. */
  private async destinationStillValid(snapshot: JobSnapshot): Promise<boolean> {
    const outDir = await this.validateDestination(this.deps.settings().outputPath);
    return outDir !== null && outDir === snapshot.outDir;
  }

  private async refuseRun(snapshot: JobSnapshot, report: JobReport): Promise<JobReport> {
    this.deps.notify('shell.DESTINATION');
    await this.log({ stage: 'run', status: 'destination_refused' });
    await this.record(snapshot, 'partial_failure');
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
