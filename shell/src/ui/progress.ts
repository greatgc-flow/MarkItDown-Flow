/**
 * Progress details from engine events and the always-visible Cancel control
 * (20_SHELL.md REQ-SHL-09/16): stage, file counts and unit outcomes, never
 * invented completed work; Cancel stays visible even with details hidden.
 */
import type { ProgressEvent, Stage } from '../pure/framing';
import { formatMessage, type UiLocale } from '../pure/i18n';

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

export type JobPhase = 'plan' | 'consent' | 'run';

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
 * empty otherwise. Renders text nodes only.
 */
export class JobStatusBar implements ProgressSink {
  private events: ProgressEvent[] = [];
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
    this.events = [];
    this.currentPhase = phase;
    this.el.empty();
    this.el.addClass('mdflow-status');
    this.textEl = this.el.createSpan({ cls: 'mdflow-status-text' });
    this.detailsEl = this.deps.showDetails() ? this.el.createSpan({ cls: 'mdflow-status-details' }) : null;
    const cancel = this.el.createEl('button', { cls: 'mdflow-status-cancel', text: this.t('shell.progress.cancel') });
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
    this.events.push(event);
    this.render();
  }

  end(): void {
    this.currentPhase = null;
    this.events = [];
    this.textEl = null;
    this.detailsEl = null;
    this.el.empty();
    this.el.removeClass('mdflow-status');
  }

  private render(): void {
    if (this.currentPhase === null || !this.textEl) return;
    this.textEl.setText(this.t(`shell.progress.phase.${this.currentPhase}`));
    if (!this.detailsEl) return;
    const s = summarizeProgress(this.events);
    this.detailsEl.setText(
      this.t('shell.progress.details', {
        stage: s.stage ?? '-',
        filesEnded: String(s.filesEnded),
        filesTotal: s.filesTotal === null ? '?' : String(s.filesTotal),
        done: String(s.unitsDone),
        pending: String(s.unitsPending),
        failed: String(s.unitsFailed),
      }),
    );
  }
}
