/**
 * Conversion history (20_SHELL.md REQ-SHL-07).
 *
 * Pure: no IO, no clock. Paths are display references only.
 */
import type { SettingsV2 } from './settings';

/** Maximum retained entries, enforced on migration and on insertion. */
export const HISTORY_CAP = 100;

/** Nonsecret outcome of a shell-owned run; never inferred from a created file alone. */
export type HistoryOutcome = 'complete' | 'pending_consent' | 'partial_failure' | 'cancelled';

const OUTCOMES: ReadonlySet<string> = new Set<HistoryOutcome>(['complete', 'pending_consent', 'partial_failure', 'cancelled']);

export interface HistoryEntry {
  inputFile: string;
  outputFile: string;
  /** Epoch milliseconds. ISO-8601 strings from v1 are accepted on input and normalized. */
  timestamp: number;
  success: boolean;
  processingTimeMs?: number;
  assetsExtracted?: number;
  outcome?: HistoryOutcome;
}

export interface NormalizedHistory {
  entries: HistoryEntry[];
  /** Count of invalid entries discarded (for the aggregated migration notice). */
  skipped: number;
}

/** Facts the coordinator knows after a run ends; used to derive the outcome. */
export interface RunFacts {
  /** Engine exit per SPEC 10.3, or null when the process was force-terminated. */
  exit: number | null;
  cancelled: boolean;
  filesOk: number;
  filesFailed: number;
  unitsPending: number;
  /** Outputs created on disk. Must never by itself produce `complete`. */
  outputsCreated: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeTimestamp(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) && value >= 0 ? value : null;
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function isCount(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0;
}

/** Validate one raw entry; null when invalid. Unknown fields are dropped. */
export function validateHistoryEntry(raw: unknown): HistoryEntry | null {
  if (!isRecord(raw)) return null;
  const { inputFile, outputFile, success } = raw;
  const timestamp = normalizeTimestamp(raw.timestamp);
  if (typeof inputFile !== 'string' || typeof outputFile !== 'string' || typeof success !== 'boolean' || timestamp === null) {
    return null;
  }
  const entry: HistoryEntry = { inputFile, outputFile, timestamp, success };
  if (raw.processingTimeMs !== undefined) {
    if (!isCount(raw.processingTimeMs)) return null;
    entry.processingTimeMs = raw.processingTimeMs;
  }
  if (raw.assetsExtracted !== undefined) {
    if (!isCount(raw.assetsExtracted)) return null;
    entry.assetsExtracted = raw.assetsExtracted;
  }
  if (raw.outcome !== undefined) {
    if (typeof raw.outcome !== 'string' || !OUTCOMES.has(raw.outcome)) return null;
    entry.outcome = raw.outcome as HistoryOutcome;
  }
  return entry;
}

/** Stable sort by descending timestamp (Array.prototype.sort is stable), then cap. */
function order(entries: readonly HistoryEntry[]): HistoryEntry[] {
  return entries
    .slice()
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, HISTORY_CAP);
}

/** Validate, strip unknown fields, stable-sort by descending timestamp, cap at HISTORY_CAP. */
export function normalizeHistory(raw: unknown): NormalizedHistory {
  if (!Array.isArray(raw)) return { entries: [], skipped: 0 };
  const entries: HistoryEntry[] = [];
  let skipped = 0;
  for (const item of raw) {
    const entry = validateHistoryEntry(item);
    if (entry) entries.push(entry);
    else skipped += 1;
  }
  return { entries: order(entries), skipped };
}

/** Insert a new entry (newest first) and re-apply the cap. Returns a new array. */
export function insertHistory(entries: readonly HistoryEntry[], entry: HistoryEntry): HistoryEntry[] {
  return order([{ ...entry }, ...entries]);
}

/** Clear history only: every other setting is returned unchanged; input is not mutated. */
export function clearHistory(settings: SettingsV2): SettingsV2 {
  return { ...settings, conversionHistory: [] };
}

/** Map run facts to a nonsecret outcome and the derived `success` flag. */
export function outcomeFor(facts: RunFacts): { outcome: HistoryOutcome; success: boolean } {
  let outcome: HistoryOutcome;
  if (facts.cancelled || facts.exit === null || facts.exit === 130) outcome = 'cancelled';
  else if (facts.exit === 3) outcome = 'pending_consent';
  else if (facts.exit === 0) outcome = 'complete';
  else outcome = 'partial_failure';
  return { outcome, success: outcome === 'complete' };
}
