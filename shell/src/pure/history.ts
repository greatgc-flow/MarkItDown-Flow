/**
 * Conversion history (20_SHELL.md REQ-SHL-07).
 *
 * Pure: no IO, no clock. Paths are display references only.
 */
import type { SettingsV2 } from './settings';
import { NotImplementedError } from './errors';

/** Maximum retained entries, enforced on migration and on insertion. */
export const HISTORY_CAP = 100;

/** Nonsecret outcome of a shell-owned run; never inferred from a created file alone. */
export type HistoryOutcome = 'complete' | 'pending_consent' | 'partial_failure' | 'cancelled';

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

/** Validate, strip unknown fields, stable-sort by descending timestamp, cap at HISTORY_CAP. */
export function normalizeHistory(_raw: unknown): NormalizedHistory {
  throw new NotImplementedError('normalizeHistory');
}

/** Insert a new entry (newest first) and re-apply the cap. Returns a new array. */
export function insertHistory(_entries: readonly HistoryEntry[], _entry: HistoryEntry): HistoryEntry[] {
  throw new NotImplementedError('insertHistory');
}

/** Clear history only: every other setting is returned unchanged; input is not mutated. */
export function clearHistory(_settings: SettingsV2): SettingsV2 {
  throw new NotImplementedError('clearHistory');
}

/** Map run facts to a nonsecret outcome and the derived `success` flag. */
export function outcomeFor(_facts: RunFacts): { outcome: HistoryOutcome; success: boolean } {
  throw new NotImplementedError('outcomeFor');
}
