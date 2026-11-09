/**
 * Incremental JSON-lines framing of engine progress events
 * (20_SHELL.md REQ-SHL-13; SPEC 7.3 incorporated by reference).
 */
import { isKnownEngineCode } from './codes';

export const PROTOCOL_VERSION = 1 as const;
/** SPEC 7.3: every line is at most 64 KiB. */
export const MAX_LINE_BYTES = 65536;

export type Stage =
  | 'sniff' | 'triage' | 'classify' | 'select' | 'convert' | 'render'
  | 'lookup' | 'plan' | 'approve' | 'transcribe' | 'assemble' | 'write';

const STAGES: ReadonlySet<string> = new Set<Stage>([
  'sniff', 'triage', 'classify', 'select', 'convert', 'render',
  'lookup', 'plan', 'approve', 'transcribe', 'assemble', 'write',
]);
const UNIT_STATES: ReadonlySet<string> = new Set(['ok', 'failed', 'cached', 'pending']);
const HEX64 = /^[0-9a-f]{64}$/;

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
/** `file` is null for run-level issues (engine `orchestrate.py`/`cli.py` emit `file: None`). */
export interface WarningEvent extends EventBase { ev: 'warning'; file: string | null; code: string; message: string }
export interface ErrorEvent extends EventBase { ev: 'error'; file: string | null; code: string; message: string }
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

const KNOWN_EVENTS: ReadonlySet<string> = new Set([
  'run_start', 'file_start', 'stage', 'classified', 'approve_required',
  'unit', 'warning', 'error', 'file_end', 'run_end',
]);

type Raw = Record<string, unknown>;

function isRecord(value: unknown): value is Raw {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
const isString = (v: unknown): v is string => typeof v === 'string';
const isNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isBoolean = (v: unknown): v is boolean => typeof v === 'boolean';
const isStringArray = (v: unknown): v is string[] => Array.isArray(v) && v.every(isString);

function invalid(reason: InvalidReason, ev?: string): FrameResult {
  return ev === undefined ? { kind: 'invalid', reason, diagnostic: 'shell.PROTOCOL' } : { kind: 'invalid', reason, diagnostic: 'shell.PROTOCOL', ev };
}

/** Field-by-field decoding; returns null on a schema violation, 'code' on a vocabulary violation. */
function decodeKnown(ev: string, r: Raw, base: EventBase): ProgressEvent | null | 'code' {
  const file = r.file;
  switch (ev) {
    case 'run_start':
      return isNumber(r.files) && isString(r.provider) ? { ...base, ev, files: r.files, provider: r.provider } : null;
    case 'file_start':
      return isString(file) && isNumber(r.index) && isNumber(r.total)
        ? { ...base, ev, file, index: r.index, total: r.total }
        : null;
    case 'stage': {
      if (!isString(file) || !isString(r.stage) || !STAGES.has(r.stage) || (r.state !== 'start' && r.state !== 'end')) return null;
      if (r.ms !== undefined && !isNumber(r.ms)) return null;
      const event: StageEvent = { ...base, ev, file, stage: r.stage as Stage, state: r.state };
      if (r.ms !== undefined) event.ms = r.ms;
      return event;
    }
    case 'classified':
      return isString(file) && isString(r.route) && isString(r.need) && isString(r.label) && isString(r.action)
        ? { ...base, ev, file, route: r.route, need: r.need, label: r.label, action: r.action }
        : null;
    case 'approve_required': {
      if (
        !isString(file) || !isString(r.plan_hash) || !HEX64.test(r.plan_hash) ||
        !(r.destination === null || isString(r.destination)) || !isString(r.model) ||
        !isNumber(r.keys_unique) || !isNumber(r.requests_to_send) || !isNumber(r.max_requests) ||
        !(r.est_max_cost === null || isString(r.est_max_cost)) || !isBoolean(r.cost_known) ||
        !isBoolean(r.threshold_exceeded) || !isStringArray(r.sensitive_hits)
      ) return null;
      // Summary only: any smuggled unit list is dropped here, never displayed or authorized.
      return {
        ...base, ev, file, plan_hash: r.plan_hash, destination: r.destination, model: r.model,
        keys_unique: r.keys_unique, requests_to_send: r.requests_to_send, max_requests: r.max_requests,
        est_max_cost: r.est_max_cost, cost_known: r.cost_known, threshold_exceeded: r.threshold_exceeded,
        sensitive_hits: [...r.sensitive_hits],
      };
    }
    case 'unit': {
      if (!isString(file) || !isString(r.unit) || !isString(r.state) || !UNIT_STATES.has(r.state)) return null;
      if (r.code !== null && !isString(r.code)) return null;
      if (r.code !== null && !isKnownEngineCode(r.code)) return 'code';
      return { ...base, ev, file, unit: r.unit, state: r.state as UnitEvent['state'], code: r.code };
    }
    case 'warning':
    case 'error': {
      // Run-level issues carry `file: null`; file-scoped ones a string. Anything else is a schema violation.
      if (!(isString(file) || file === null) || !isString(r.code) || !isString(r.message)) return null;
      if (!isKnownEngineCode(r.code)) return 'code';
      return { ...base, ev, file, code: r.code, message: r.message };
    }
    case 'file_end': {
      const u = r.units;
      if (!isString(file) || !isStringArray(r.outputs) || !isRecord(u)) return null;
      if (!isNumber(u.total) || !isNumber(u.done) || !isNumber(u.pending) || !isNumber(u.failed)) return null;
      return { ...base, ev, file, outputs: [...r.outputs], units: { total: u.total, done: u.done, pending: u.pending, failed: u.failed } };
    }
    case 'run_end':
      return isNumber(r.exit) && isNumber(r.files_ok) && isNumber(r.files_failed) && isNumber(r.provider_calls)
        ? { ...base, ev, exit: r.exit, files_ok: r.files_ok, files_failed: r.files_failed, provider_calls: r.provider_calls }
        : null;
    default:
      return null;
  }
}

/** Decode one already-parsed JSON value into a FrameResult (used by the framer). */
export function decodeEvent(value: unknown): FrameResult {
  if (!isRecord(value)) return invalid('malformed');
  if (value.v !== PROTOCOL_VERSION) return invalid('version');
  const ev = value.ev;
  if (!isString(ev)) return invalid('schema');
  if (!KNOWN_EVENTS.has(ev)) return { kind: 'ignored', ev };
  if (!isString(value.ts)) return invalid('schema', ev);
  const decoded = decodeKnown(ev, value, { v: PROTOCOL_VERSION, ts: value.ts });
  if (decoded === null) return invalid('schema', ev);
  if (decoded === 'code') return invalid('code', ev);
  return { kind: 'event', event: decoded };
}

const NEWLINE = 0x0a;
const CARRIAGE_RETURN = 0x0d;

/**
 * Feed arbitrary byte chunks (UTF-8 may split anywhere; `\n` or `\r\n` line ends).
 * Each `push` returns the results for lines completed by that chunk.
 */
export class JsonLinesFramer {
  private pending: Uint8Array[] = [];
  private pendingBytes = 0;
  /** Set once the current line exceeded MAX_LINE_BYTES; bytes are dropped until the newline. */
  private overflow = false;
  private readonly decoder = new TextDecoder('utf-8', { fatal: true });

  push(chunk: Uint8Array): FrameResult[] {
    const results: FrameResult[] = [];
    let start = 0;
    for (let i = 0; i < chunk.length; i++) {
      if (chunk[i] !== NEWLINE) continue;
      this.append(chunk.subarray(start, i));
      results.push(...this.completeLine());
      start = i + 1;
    }
    if (start < chunk.length) this.append(chunk.subarray(start));
    return results;
  }

  /** Flush a trailing line without a newline. */
  end(): FrameResult[] {
    if (this.pendingBytes === 0 && !this.overflow) return [];
    return this.completeLine();
  }

  private append(segment: Uint8Array): void {
    if (segment.length === 0) return;
    if (this.overflow) return;
    if (this.pendingBytes + segment.length > MAX_LINE_BYTES + 1) {
      // +1 tolerates a trailing \r that is stripped below; anything beyond is oversize.
      this.overflow = true;
      this.pending = [];
      this.pendingBytes = 0;
      return;
    }
    this.pending.push(segment.slice());
    this.pendingBytes += segment.length;
  }

  private completeLine(): FrameResult[] {
    const overflow = this.overflow;
    const parts = this.pending;
    const total = this.pendingBytes;
    this.overflow = false;
    this.pending = [];
    this.pendingBytes = 0;
    if (overflow) return [invalid('oversize')];
    let line = new Uint8Array(total);
    let position = 0;
    for (const part of parts) {
      line.set(part, position);
      position += part.length;
    }
    if (line.length > 0 && line[line.length - 1] === CARRIAGE_RETURN) line = line.subarray(0, line.length - 1);
    if (line.length === 0) return [];
    if (line.length > MAX_LINE_BYTES) return [invalid('oversize')];
    let parsed: unknown;
    try {
      parsed = JSON.parse(this.decoder.decode(line));
    } catch {
      return [invalid('malformed')];
    }
    return [decodeEvent(parsed)];
  }
}
