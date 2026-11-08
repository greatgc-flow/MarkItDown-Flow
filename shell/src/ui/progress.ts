/**
 * Progress details from engine events (20_SHELL.md REQ-SHL-09): stage, file
 * counts and unit outcomes, never invented completed work.
 */
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

export function summarizeProgress(events: readonly ProgressEvent[]): ProgressSummary {
  const summary: ProgressSummary = {
    stage: null,
    currentFile: null,
    filesTotal: null,
    filesEnded: 0,
    unitsDone: 0,
    unitsPending: 0,
    unitsFailed: 0,
    filesAwaitingConsent: 0,
    exit: null,
  };
  for (const event of events) {
    switch (event.ev) {
      case 'run_start':
        summary.filesTotal = event.files;
        break;
      case 'file_start':
        summary.currentFile = event.file;
        summary.filesTotal = event.total;
        break;
      case 'stage':
        summary.stage = event.stage;
        summary.currentFile = event.file;
        break;
      case 'approve_required':
        summary.filesAwaitingConsent += 1;
        break;
      case 'file_end':
        summary.filesEnded += 1;
        summary.unitsDone += event.units.done;
        summary.unitsPending += event.units.pending;
        summary.unitsFailed += event.units.failed;
        break;
      case 'run_end':
        summary.exit = event.exit;
        break;
      default:
        break;
    }
  }
  return summary;
}
