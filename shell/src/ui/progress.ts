/**
 * Progress details from engine events and the always-visible Cancel control
 * (20_SHELL.md REQ-SHL-09/16): stage, file counts and unit outcomes, never
 * invented completed work; Cancel stays visible even with details hidden.
 *
 * The summary is incremental and per run (M4 P-01 / M3-V03): one `run_start`
 * begins a new run and resets every count, so the `plan` process's `file_end`
 * units never add to the `run` counts of the same job, and no event history
 * is retained (O(1) work and memory per event).
 */
import type { ProgressEvent, Stage } from '../pure/framing';
import { formatMessage, type UiLocale } from '../pure/i18n';

export interface ProgressSummary {
  /** Latest `stage` event, if any. */
  stage: Stage | null;
  currentFile: string | null;
  filesTotal: number | null;
  /** `file_end` events seen in the current run. */
  filesEnded: number;
  /** Sums of `file_end.units` in the current run. */
  unitsDone: number;
  unitsPending: number;
  unitsFailed: number;
  /** `approve_required` events seen in the current run (files awaiting consent). */
  filesAwaitingConsent: number;
  /** `run_end.exit` once seen. */
  exit: number | null;
}

export function emptyProgressSummary(): ProgressSummary {
  return {
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
}

/**
 * Apply one event to the summary in place and return the same object. A
 * `run_start` resets every field: the counts shown always belong to the run
 * that announced `files`, never to an earlier `plan` of the same job.
 */
export function applyProgressEvent(summary: ProgressSummary, event: ProgressEvent): ProgressSummary {
  switch (event.ev) {
    case 'run_start':
      Object.assign(summary, emptyProgressSummary());
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
  return summary;
}

/** Whole-stream form of the reducer (tests and one-shot consumers). */
export function summarizeProgress(events: readonly ProgressEvent[]): ProgressSummary {
  const summary = emptyProgressSummary();
  for (const event of events) applyProgressEvent(summary, event);
  return summary;
}

/** `check`: admission is waiting on the engine version gate; the item and its Cancel exist from then on (M7-02). */
export type JobPhase = 'check' | 'plan' | 'consent' | 'run';

/** What the coordinator reports to the UI for the life of one job. */
export interface ProgressSink {
  begin(phase: JobPhase): void;
  phase(phase: JobPhase): void;
  event(event: ProgressEvent): void;
  end(): void;
}

export interface JobStatusBarDeps {
  locale: () => UiLocale;
  /** `enableBatchProgress`: details only; Cancel is unconditional. */
  showDetails: () => boolean;
  onCancel: () => void;
}

/**
 * Status-bar presenter: `<phase text> [details] [Cancel]` while a job is active,
 * empty otherwise. Renders text nodes only. Holds one incremental summary, not
 * the event history.
 */
export class JobStatusBar implements ProgressSink {
  private summary: ProgressSummary = emptyProgressSummary();
  private currentPhase: JobPhase | null = null;
  private textEl: HTMLElement | null = null;
  private detailsEl: HTMLElement | null = null;

  constructor(
    private readonly el: HTMLElement,
    private readonly deps: JobStatusBarDeps,
  ) {}

  get active(): boolean {
    return this.currentPhase !== null;
  }

  private t(key: string, params?: Record<string, string>): string {
    return formatMessage(this.deps.locale(), key, params);
  }

  begin(phase: JobPhase): void {
    this.summary = emptyProgressSummary();
    this.currentPhase = phase;
    this.el.empty();
    this.el.addClass('mdflow-status');
    this.textEl = this.el.createSpan({ cls: 'mdflow-status-text' });
    this.detailsEl = this.deps.showDetails() ? this.el.createSpan({ cls: 'mdflow-status-details' }) : null;
    const cancel = this.el.createEl('button', {
      cls: 'mdflow-status-cancel',
      text: this.t('shell.progress.cancel'),
      attr: { type: 'button', 'aria-label': this.t('shell.progress.cancelHint'), title: this.t('shell.progress.cancelHint') },
    });
    cancel.addEventListener('click', () => this.deps.onCancel());
    this.render();
  }

  phase(phase: JobPhase): void {
    if (this.currentPhase === null) return;
    this.currentPhase = phase;
    this.render();
  }

  event(event: ProgressEvent): void {
    if (this.currentPhase === null) return;
    applyProgressEvent(this.summary, event);
    this.render();
  }

  end(): void {
    this.currentPhase = null;
    this.summary = emptyProgressSummary();
    this.textEl = null;
    this.detailsEl = null;
    this.el.empty();
    this.el.removeClass('mdflow-status');
    this.el.setAttr('data-mdflow-phase', null);
  }

  private render(): void {
    if (this.currentPhase === null || !this.textEl) return;
    this.textEl.setText(this.t(`shell.progress.phase.${this.currentPhase}`));
    this.el.setAttr('data-mdflow-phase', this.currentPhase);
    if (!this.detailsEl) return;
    const s = this.summary;
    this.detailsEl.setText(
      this.t('shell.progress.details', {
        stage: s.stage ?? this.t('shell.progress.starting'),
        filesEnded: String(s.filesEnded),
        filesTotal: s.filesTotal === null ? '?' : String(s.filesTotal),
        done: String(s.unitsDone),
        pending: String(s.unitsPending),
        failed: String(s.unitsFailed),
      }),
    );
  }
}
