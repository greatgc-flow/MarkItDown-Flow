/**
 * Per-file results of one finished run (20_SHELL.md REQ-SHL-09 and section 6:
 * "show file/unit issues and pending work even when the exit code alone is
 * insufficient"; R32 owner directive). Everything is projected from the decoded
 * SPEC 7.4 report: classification label, unit counts (`done = cached +
 * transcribed`) and SPEC 7.5 issue codes. Status is never inferred from a
 * created output file (REQ-SHL-07).
 */
import { type App, Modal } from 'obsidian';
import type { HistoryOutcome } from '../pure/history';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { DERIVED_FIDELITY, PRECONVERTED_CODE, type RunReport } from '../pure/protocol';
import { labelLegendKey } from './consent-modal';

export type ResultStatus = 'ok' | 'pending' | 'failed';

const APPROVAL_REQUIRED_CODE = 'E_APPROVAL_REQUIRED';

export interface ResultRow {
  path: string;
  /** SPEC 3.2 classification label (`T`/`S`/`M`/...). */
  label: string;
  status: ResultStatus;
  units: { done: number; pending: number; failed: number };
  /** SPEC 7.5 codes of `files[].issues`, in report order. */
  issueCodes: string[];
  /** Number of published outputs (display only; never a success signal). */
  outputs: number;
  /** R33: converted from a LibreOffice pre-converted copy (`W_PRECONVERTED`, or `fidelity: DERIVED`), never native. */
  derived: boolean;
  /** The pre-converting tool and version from the `W_PRECONVERTED` issue (`LibreOffice 24.8`), when reported. */
  derivedBy: { tool: string; version: string } | null;
}

export interface ResultsViewModel {
  outcome: HistoryOutcome;
  rows: ResultRow[];
  skipped: { path: string; code: string }[];
}

/** Pure projection of a decoded report into the result list. */
export function buildResultsView(report: RunReport, outcome: HistoryOutcome): ResultsViewModel {
  const rows: ResultRow[] = report.files.map((file) => {
    const issueCodes = file.issues.map((issue) => issue.code);
    // E_APPROVAL_REQUIRED is pending OCR awaiting consent (SPEC REQ-APR-03; Keep pending, R37), not a failed conversion.
    const failed = issueCodes.some((code) => code.startsWith('E_') && code !== APPROVAL_REQUIRED_CODE) || file.units.failed > 0;
    const status: ResultStatus = failed ? 'failed' : file.units.pending > 0 ? 'pending' : 'ok';
    const preconverted = file.issues.find((issue) => issue.code === PRECONVERTED_CODE);
    return {
      path: file.path,
      label: file.label,
      status,
      units: { done: file.units.cached + file.units.transcribed, pending: file.units.pending, failed: file.units.failed },
      issueCodes,
      outputs: file.outputs.length,
      derived: file.fidelity === DERIVED_FIDELITY || preconverted !== undefined,
      derivedBy: preconverted?.tool && preconverted.version ? { tool: preconverted.tool, version: preconverted.version } : null,
    };
  });
  return { outcome, rows, skipped: report.skipped.map((s) => ({ path: s.path, code: s.code })) };
}

export class ResultsModal extends Modal {
  constructor(
    app: App,
    private readonly view: ResultsViewModel,
    private readonly locale: UiLocale,
  ) {
    super(app);
  }

  private t(key: string, params?: Record<string, string>): string {
    return formatMessage(this.locale, key, params);
  }

  override onOpen(): void {
    const { contentEl, titleEl } = this;
    titleEl.setText(this.t('shell.results.title'));
    contentEl.empty();
    contentEl.addClass('mdflow-results');
    const outcomeText = this.t(`shell.history.outcome.${this.view.outcome}`);
    const summary = contentEl.createEl('p', { cls: 'mdflow-results-summary' });
    summary.createSpan({ cls: `mdflow-badge mdflow-outcome mdflow-outcome-${this.view.outcome}`, text: outcomeText });
    summary.createSpan({ text: ` ${this.t('shell.results.summary', { outcome: outcomeText, files: String(this.view.rows.length) })}` });
    if (this.view.rows.length === 0) {
      contentEl.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.results.empty') });
    } else {
      const wrap = contentEl.createDiv({ cls: 'mdflow-table-scroll' });
      const table = wrap.createEl('table', { cls: 'mdflow-table mdflow-results-table' });
      const head = table.createEl('thead').createEl('tr');
      for (const column of ['file', 'label', 'status', 'units', 'issues']) {
        head.createEl('th', { text: this.t(`shell.results.col.${column}`), attr: { scope: 'col' } });
      }
      const body = table.createEl('tbody');
      for (const row of this.view.rows) {
        const tr = body.createEl('tr', { cls: `mdflow-result-${row.status}` });
        tr.createEl('td', { cls: 'mdflow-cell-path', text: row.path });
        const legend = labelLegendKey(row.label);
        const labelCell = tr.createEl('td', { cls: 'mdflow-cell-label', text: row.label });
        if (legend) labelCell.setAttr('title', this.t(legend));
        if (row.derived) {
          // R33: a pre-converted file is shown as derived (with the tool and version when reported) next to its
          // class; the W_PRECONVERTED code stays in Issues.
          const text = row.derivedBy ? this.t('shell.results.derivedBy', row.derivedBy) : this.t('shell.results.derived');
          labelCell.createSpan({ cls: 'mdflow-badge mdflow-badge-derived', text, attr: { title: this.t('shell.results.derivedHint') } });
        }
        tr.createEl('td', { cls: `mdflow-badge mdflow-status-${row.status}`, text: this.t(`shell.results.status.${row.status}`) });
        tr.createEl('td', {
          cls: 'mdflow-cell-number',
          text: this.t('shell.results.units', { done: String(row.units.done), pending: String(row.units.pending), failed: String(row.units.failed) }),
        });
        tr.createEl('td', { cls: 'mdflow-cell-codes', text: row.issueCodes.length > 0 ? row.issueCodes.join(', ') : '-' });
      }
    }
    if (this.view.skipped.length > 0) {
      const skipped = contentEl.createDiv({ cls: 'mdflow-muted mdflow-results-skipped' });
      skipped.createEl('p', { text: this.t('shell.results.skipped', { count: String(this.view.skipped.length) }) });
      const list = skipped.createEl('ul');
      for (const entry of this.view.skipped) list.createEl('li', { text: `${entry.path} – ${entry.code}` });
    }
    const buttons = contentEl.createDiv({ cls: 'mdflow-buttons' });
    const close = buttons.createEl('button', { text: this.t('shell.results.close'), cls: 'mod-cta', attr: { type: 'button' } });
    close.addEventListener('click', () => this.close());
    close.focus();
  }

  override onClose(): void {
    this.contentEl.empty();
  }
}
