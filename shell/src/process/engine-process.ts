/**
 * One owned engine process: framing of stderr progress, spooling of stdout,
 * cooperative-then-forced cancellation (20_SHELL.md REQ-SHL-11/13/16;
 * SPEC 7.3/7.4/10.3 and REQ-GEN-09 by reference).
 */
import { NotImplementedError } from '../pure/errors';
import type { FrameResult, ProgressEvent } from '../pure/framing';
import type { HistoryOutcome } from '../pure/history';
import type { Decoded, Plan, RunReport } from '../pure/protocol';
import type { SpoolFs } from '../pure/spool';
import type { ChildHandle, Clock, ExitStatus, Spawner, SpawnRequest } from './types';

/** REQ-SHL-16: at most five seconds between the cooperative request and forced termination. */
export const CANCEL_GRACE_MS = 5000;

/** SPEC 10.3 cooperative cancellation exit code; never synthesized by the shell. */
export const COOPERATIVE_EXIT = 130;

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

export class EngineRun<K extends 'report' | 'plan' = 'report'> {
  constructor(_spawner: Spawner, _request: SpawnRequest, _options: EngineRunOptions & { stdout: K }) {}

  /** Spawn the child. Throws if already started or cancelled before start. */
  start(): ChildHandle {
    throw new NotImplementedError('EngineRun.start');
  }

  /** Resolves when the child has exited and stdout has been validated and the spool removed. */
  get done(): Promise<EngineResult<StdoutOf<K>>> {
    throw new NotImplementedError('EngineRun.done');
  }

  get started(): boolean {
    throw new NotImplementedError('EngineRun.started');
  }

  get cancelRequested(): boolean {
    throw new NotImplementedError('EngineRun.cancelRequested');
  }

  /** Before start: prevents the launch. After start: cooperative stop, forced after the grace period. */
  cancel(): void {
    throw new NotImplementedError('EngineRun.cancel');
  }

  onEvent(_listener: (event: ProgressEvent) => void): void {
    throw new NotImplementedError('EngineRun.onEvent');
  }
}

/** Remove verified owned stale spool files from the owned directory (recover only owned names). */
export async function recoverStaleSpools(_spoolFs: SpoolFs): Promise<string[]> {
  throw new NotImplementedError('recoverStaleSpools');
}
