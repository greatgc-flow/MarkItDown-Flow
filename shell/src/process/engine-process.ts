/**
 * One owned engine process: framing of stderr progress, spooling of stdout,
 * cooperative-then-forced cancellation (20_SHELL.md REQ-SHL-11/13/16;
 * SPEC 7.3/7.4/10.3 and REQ-GEN-09 by reference).
 */
import { isKnownEngineCode } from '../pure/codes';
import { type FrameResult, JsonLinesFramer, type ProgressEvent } from '../pure/framing';
import { type HistoryOutcome, outcomeFor } from '../pure/history';
import { messageForCode } from '../pure/i18n';
import { type Decoded, decodeReport, parsePlanOutput, type Plan, type RunReport } from '../pure/protocol';
import { recoverableSpools, Spool, type SpoolFs } from '../pure/spool';
import type { ChildHandle, Clock, ExitStatus, Spawner, SpawnRequest } from './types';

/** REQ-SHL-16: at most five seconds between the cooperative request and forced termination. */
export const CANCEL_GRACE_MS = 5000;

/** SPEC 10.3 cooperative cancellation exit code; never synthesized by the shell. */
export const COOPERATIVE_EXIT = 130;

/** Bounded raw stderr retained only to recognise the exit-1 startup error object. */
const STARTUP_ERROR_MAX_BYTES = 65536;

export type Termination =
  /** The child exited by itself (any code, including 130 if the engine chose to). */
  | 'exited'
  /** Cancel was requested and the child exited 130 with a decodable report. */
  | 'cooperative'
  /** The child was force-terminated, or died from a signal: native status, no report expected. */
  | 'forced';

/** SPEC 7.5 startup error object printed to stderr on exit 1 (`{"error":{"code","message"}}`). */
export interface StartupError {
  code: string;
}

export interface EngineResult<TStdout> {
  status: ExitStatus;
  termination: Termination;
  cancelRequested: boolean;
  /** Decoded stdout (report or Plans); null when forced (no report) or on exit 1 startup errors. */
  stdout: Decoded<TStdout> | null;
  startupError: StartupError | null;
  events: ProgressEvent[];
  /** Visible protocol failures from the framer (never raw bytes). */
  invalid: Extract<FrameResult, { kind: 'invalid' }>[];
  ignoredEvents: string[];
  /** Nonsecret history outcome derived from the facts above, never from created files. */
  outcome: HistoryOutcome;
  /** Diagnostic keys to show (`shell.PROTOCOL`, `shell.CANCELLED`, `engine.<CODE>`). */
  diagnostics: string[];
}

export interface EngineRunOptions {
  /** Which SPEC stdout contract applies: `run` -> 7.4 report, `plan` -> 7.1 Plans. */
  stdout: 'report' | 'plan';
  spoolFs: SpoolFs;
  /** 16 lowercase hex characters; the spool file name is derived from it. */
  nonce: string;
  clock: Clock;
  /** Test override; production uses CANCEL_GRACE_MS. */
  graceMs?: number;
}

export type StdoutOf<K extends 'report' | 'plan'> = K extends 'report' ? RunReport : Plan[];

function pushUnique(list: string[], key: string): void {
  if (!list.includes(key)) list.push(key);
}

export class EngineRun<K extends 'report' | 'plan' = 'report'> {
  private readonly framer = new JsonLinesFramer();
  private readonly spool: Spool;
  private readonly events: ProgressEvent[] = [];
  private readonly invalid: Extract<FrameResult, { kind: 'invalid' }>[] = [];
  private readonly ignored: string[] = [];
  private readonly listeners: ((event: ProgressEvent) => void)[] = [];
  private readonly stderrChunks: Uint8Array[] = [];
  private stderrBytes = 0;
  private pendingWrites: Promise<void> = Promise.resolve();
  private child: ChildHandle | null = null;
  private isStarted = false;
  private isCancelRequested = false;
  private terminatedByShell = false;
  private exited = false;
  private spawnError: Error | null = null;
  private cancelGrace: (() => void) | null = null;
  private resolveDone!: (result: EngineResult<StdoutOf<K>>) => void;
  private readonly donePromise: Promise<EngineResult<StdoutOf<K>>>;

  constructor(
    private readonly spawner: Spawner,
    private readonly request: SpawnRequest,
    private readonly options: EngineRunOptions & { stdout: K },
  ) {
    this.spool = new Spool(options.spoolFs, options.nonce);
    this.donePromise = new Promise((resolve) => {
      this.resolveDone = resolve;
    });
  }

  /** Spawn the child. Throws if already started or cancelled before start. */
  start(): ChildHandle {
    if (this.isStarted) throw new Error('EngineRun.start: already started');
    if (this.isCancelRequested) throw new Error('EngineRun.start: cancelled before launch');
    this.isStarted = true;
    const child = this.spawner.spawn(this.request);
    this.child = child;
    child.onStderr((chunk) => this.onStderr(chunk));
    child.onStdout((chunk) => {
      const copy = chunk.slice();
      this.pendingWrites = this.pendingWrites.then(() => this.spool.write(copy)).catch(() => undefined);
    });
    child.onError((error) => {
      this.spawnError = error;
    });
    child.onExit((status) => {
      void this.finish(status);
    });
    return child;
  }

  /** Resolves when the child has exited and stdout has been validated and the spool removed. */
  get done(): Promise<EngineResult<StdoutOf<K>>> {
    return this.donePromise;
  }

  get started(): boolean {
    return this.isStarted;
  }

  get cancelRequested(): boolean {
    return this.isCancelRequested;
  }

  /** Before start: prevents the launch. After start: cooperative stop, forced after the grace period. */
  cancel(): void {
    if (this.isCancelRequested) return;
    this.isCancelRequested = true;
    if (!this.isStarted) {
      void this.finish({ code: null, signal: null });
      return;
    }
    if (this.exited || !this.child) return;
    const child = this.child;
    const cooperative = child.requestCooperativeStop();
    if (!cooperative) {
      this.terminatedByShell = true;
      child.terminate();
      return;
    }
    this.cancelGrace = this.options.clock.setTimeout(() => {
      this.cancelGrace = null;
      if (this.exited) return;
      this.terminatedByShell = true;
      child.terminate();
    }, this.options.graceMs ?? CANCEL_GRACE_MS);
  }

  onEvent(listener: (event: ProgressEvent) => void): void {
    this.listeners.push(listener);
  }

  private onStderr(chunk: Uint8Array): void {
    if (this.stderrBytes < STARTUP_ERROR_MAX_BYTES) {
      this.stderrChunks.push(chunk.slice());
      this.stderrBytes += chunk.length;
    }
    this.consume(this.framer.push(chunk));
  }

  private consume(results: FrameResult[]): void {
    for (const result of results) {
      if (result.kind === 'event') {
        this.events.push(result.event);
        for (const listener of this.listeners) listener(result.event);
      } else if (result.kind === 'ignored') {
        this.ignored.push(result.ev);
      } else {
        this.invalid.push(result);
      }
    }
  }

  /** Exit-1 startup errors are one JSON object on stderr, not a progress line (SPEC 7.5 / 10.3). */
  private startupErrorFromStderr(status: ExitStatus): StartupError | null {
    if (status.code !== 1 || this.events.length > 0) return null;
    try {
      const whole = new Uint8Array(this.stderrBytes);
      let position = 0;
      for (const part of this.stderrChunks) {
        whole.set(part, position);
        position += part.length;
      }
      const parsed: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(whole));
      if (typeof parsed !== 'object' || parsed === null) return null;
      const error = (parsed as { error?: unknown }).error;
      if (typeof error !== 'object' || error === null) return null;
      const code = (error as { code?: unknown }).code;
      return typeof code === 'string' ? { code } : null;
    } catch {
      return null;
    }
  }

  private async finish(status: ExitStatus): Promise<void> {
    if (this.exited) return;
    this.exited = true;
    if (this.cancelGrace) {
      this.cancelGrace();
      this.cancelGrace = null;
    }
    this.consume(this.framer.end());
    await this.pendingWrites;

    let termination: Termination;
    if (!this.isStarted || this.spawnError) {
      termination = 'forced';
    } else if (this.isCancelRequested && status.code === COOPERATIVE_EXIT && !this.terminatedByShell) {
      termination = 'cooperative';
    } else if (this.terminatedByShell || status.code === null) {
      termination = 'forced';
    } else {
      termination = 'exited';
    }

    let stdout: Decoded<StdoutOf<K>> | null = null;
    let startupError: StartupError | null = null;
    if (termination === 'forced') {
      await this.spool.discard();
    } else {
      startupError = this.startupErrorFromStderr(status);
      if (startupError) {
        await this.spool.discard();
        // The stderr object was not a progress line; it is reported by code, not as a framing fault.
        this.invalid.length = 0;
      } else if (this.options.stdout === 'plan') {
        stdout = (await this.spool.finishWith(parsePlanOutput)) as Decoded<StdoutOf<K>>;
      } else {
        stdout = (await this.spool.finishWith(decodeReport)) as Decoded<StdoutOf<K>>;
      }
    }

    const runEnd = this.events.find((e) => e.ev === 'run_end');
    const unitsPending = this.events.filter((e) => e.ev === 'file_end').reduce((n, e) => n + (e.ev === 'file_end' ? e.units.pending : 0), 0);
    let { outcome } = outcomeFor({
      exit: termination === 'forced' ? null : status.code,
      cancelled: this.isCancelRequested,
      filesOk: runEnd && runEnd.ev === 'run_end' ? runEnd.files_ok : 0,
      filesFailed: runEnd && runEnd.ev === 'run_end' ? runEnd.files_failed : 0,
      unitsPending,
    });
    if (outcome === 'complete' && (!stdout || !stdout.ok)) outcome = 'partial_failure';

    const diagnostics: string[] = [];
    if (this.spawnError) pushUnique(diagnostics, 'shell.RUNTIME');
    if (startupError) pushUnique(diagnostics, messageForCode(startupError.code).key);
    for (const event of this.events) {
      if (event.ev === 'error' && isKnownEngineCode(event.code)) pushUnique(diagnostics, `engine.${event.code}`);
    }
    // Error codes may be reported only in the 7.4 report (`files[].issues`), not as progress events.
    if (this.options.stdout === 'report' && stdout && stdout.ok) {
      for (const file of (stdout.value as RunReport).files) {
        for (const issue of file.issues) {
          if (issue.code.startsWith('E_') && isKnownEngineCode(issue.code)) pushUnique(diagnostics, `engine.${issue.code}`);
        }
      }
    }
    if (this.invalid.length > 0) pushUnique(diagnostics, 'shell.PROTOCOL');
    if (termination !== 'forced' && !startupError && stdout && !stdout.ok) pushUnique(diagnostics, 'shell.PROTOCOL');
    if (outcome === 'cancelled') pushUnique(diagnostics, 'shell.CANCELLED');

    this.resolveDone({
      status,
      termination,
      cancelRequested: this.isCancelRequested,
      stdout,
      startupError,
      events: [...this.events],
      invalid: [...this.invalid],
      ignoredEvents: [...this.ignored],
      outcome,
      diagnostics,
    });
  }
}

/** Remove verified owned stale spool files from the owned directory (recover only owned names). */
export async function recoverStaleSpools(spoolFs: SpoolFs): Promise<string[]> {
  const names = recoverableSpools(await spoolFs.list()).sort();
  for (const name of names) {
    try {
      await spoolFs.remove(name);
    } catch {
      // Not removable now: left for the next start; never read.
    }
  }
  return names;
}
