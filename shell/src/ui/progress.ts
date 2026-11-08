/**
 * Progress details from engine events (20_SHELL.md REQ-SHL-09): stage, file
 * counts and unit outcomes, never invented completed work.
 */
import { NotImplementedError } from '../pure/errors';
import type { ProgressEvent, Stage } from '../pure/framing';

export interface ProgressSummary {
  /** Latest `stage` event, if any. */
  stage: Stage | null;
  currentFile: string | null;
  filesTotal: number | null;
  /** `file_end` events seen. */
  filesEnded: number;
  /** Sums of `file_end.units`. */
  unitsDone: number;
  unitsPending: number;
  unitsFailed: number;
  /** `approve_required` events seen (files awaiting consent). */
  filesAwaitingConsent: number;
  /** `run_end.exit` once seen. */
  exit: number | null;
}

export function summarizeProgress(_events: readonly ProgressEvent[]): ProgressSummary {
  throw new NotImplementedError('summarizeProgress');
}
