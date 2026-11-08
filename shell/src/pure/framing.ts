/**
 * Incremental JSON-lines framing of engine progress events
 * (20_SHELL.md REQ-SHL-13; SPEC 7.3 incorporated by reference).
 */
import { NotImplementedError } from './errors';

export const PROTOCOL_VERSION = 1 as const;
/** SPEC 7.3: every line is at most 64 KiB. */
export const MAX_LINE_BYTES = 65536;

export type Stage =
  | 'sniff' | 'triage' | 'classify' | 'select' | 'convert' | 'render'
  | 'lookup' | 'plan' | 'approve' | 'transcribe' | 'assemble' | 'write';

interface EventBase { v: typeof PROTOCOL_VERSION; ts: string }

export interface RunStartEvent extends EventBase { ev: 'run_start'; files: number; provider: string }
export interface FileStartEvent extends EventBase { ev: 'file_start'; file: string; index: number; total: number }
export interface StageEvent extends EventBase { ev: 'stage'; file: string; stage: Stage; state: 'start' | 'end'; ms?: number }
export interface ClassifiedEvent extends EventBase {
  ev: 'classified'; file: string; route: string; need: string; label: string; action: string;
}
/** Bounded summary; never carries the unit list (full Plans come from `plan` stdout). */
export interface ApproveRequiredEvent extends EventBase {
  ev: 'approve_required';
  file: string;
  plan_hash: string;
  destination: string | null;
  model: string;
  keys_unique: number;
  requests_to_send: number;
  max_requests: number;
  est_max_cost: string | null;
  cost_known: boolean;
  threshold_exceeded: boolean;
  sensitive_hits: string[];
}
export interface UnitEvent extends EventBase {
  ev: 'unit'; file: string; unit: string; state: 'ok' | 'failed' | 'cached' | 'pending'; code: string | null;
}
export interface WarningEvent extends EventBase { ev: 'warning'; file: string; code: string; message: string }
export interface ErrorEvent extends EventBase { ev: 'error'; file: string; code: string; message: string }
export interface FileEndEvent extends EventBase {
  ev: 'file_end'; file: string; outputs: string[];
  units: { total: number; done: number; pending: number; failed: number };
}
export interface RunEndEvent extends EventBase {
  ev: 'run_end'; exit: number; files_ok: number; files_failed: number; provider_calls: number;
}

export type ProgressEvent =
  | RunStartEvent | FileStartEvent | StageEvent | ClassifiedEvent | ApproveRequiredEvent
  | UnitEvent | WarningEvent | ErrorEvent | FileEndEvent | RunEndEvent;

export type InvalidReason = 'oversize' | 'malformed' | 'version' | 'schema' | 'code';

export type FrameResult =
  | { kind: 'event'; event: ProgressEvent }
  /** Unknown `ev` names are ignored as SPEC 7.3 requires; the name is kept for logs. */
  | { kind: 'ignored'; ev: string }
  /** Visible failure; carries a diagnostic key and a reason, never raw bytes. */
  | { kind: 'invalid'; reason: InvalidReason; diagnostic: 'shell.PROTOCOL'; ev?: string };

/**
 * Feed arbitrary byte chunks (UTF-8 may split anywhere; `\n` or `\r\n` line ends).
 * Each `push` returns the results for lines completed by that chunk.
 */
export class JsonLinesFramer {
  constructor() {
    throw new NotImplementedError('JsonLinesFramer');
  }

  push(_chunk: Uint8Array): FrameResult[] {
    throw new NotImplementedError('JsonLinesFramer.push');
  }

  /** Flush a trailing line without a newline. */
  end(): FrameResult[] {
    throw new NotImplementedError('JsonLinesFramer.end');
  }
}

/** Decode one already-parsed JSON value into a FrameResult (used by the framer). */
export function decodeEvent(_value: unknown): FrameResult {
  throw new NotImplementedError('decodeEvent');
}
