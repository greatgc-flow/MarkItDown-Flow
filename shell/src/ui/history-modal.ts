/**
 * `view-conversion-history` (20_SHELL.md REQ-SHL-02/07): display references
 * only; works without Python; clear history clears only history. Rendered as a
 * table (time, outcome, input, output) so pending, cancelled and partial runs
 * are visibly distinct from success (R32).
 */
import { type App, Modal } from 'obsidian';
import type { HistoryEntry } from '../pure/history';
import { formatMessage, type UiLocale } from '../pure/i18n';

/** Local wall-clock `YYYY-MM-DD HH:mm`; an invalid timestamp renders as `-`. */
export function formatHistoryTime(timestamp: number): string {
  if (!Number.isFinite(timestamp)) return '-';
  const d = new Date(timestamp);
  if (Number.isNaN(d.getTime())) return '-';
  const pad = (n: number): string => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export class HistoryModal extends Modal {
  constructor(
    app: App,
    private readonly entries: readonly HistoryEntry[],
    private readonly locale: UiLocale,
    private readonly onClear: () => Promise<void>,
  ) {
    super(app);
  }

  override onOpen(): void {
    const { contentEl, titleEl } = this;
    const t = (key: string, params?: Record<string, string>): string => formatMessage(this.locale, key, params);
    titleEl.setText(t('shell.history.title'));
    contentEl.empty();
    contentEl.addClass('mdflow-history');
    if (this.entries.length === 0) {
      contentEl.createEl('p', { cls: 'mdflow-muted', text: t('shell.history.empty') });
    } else {
      contentEl.createEl('p', { cls: 'mdflow-muted', text: t('shell.history.count', { count: String(this.entries.length) }) });
      const wrap = contentEl.createDiv({ cls: 'mdflow-table-scroll' });
      const table = wrap.createEl('table', { cls: 'mdflow-table mdflow-history-table' });
      const head = table.createEl('thead').createEl('tr');
      for (const column of ['time', 'outcome', 'input', 'output']) head.createEl('th', { text: t(`shell.history.col.${column}`), attr: { scope: 'col' } });
      const body = table.createEl('tbody');
      for (const entry of this.entries) {
        const outcome = entry.outcome ?? 'legacy';
        const row = body.createEl('tr');
        row.createEl('td', { cls: 'mdflow-cell-time', text: formatHistoryTime(entry.timestamp) });
        row.createEl('td', { cls: `mdflow-badge mdflow-outcome mdflow-outcome-${outcome}`, text: t(`shell.history.outcome.${outcome}`) });
        row.createEl('td', { cls: 'mdflow-cell-path', text: entry.inputFile });
        row.createEl('td', { cls: 'mdflow-cell-path', text: entry.outputFile });
      }
    }
    const buttons = contentEl.createDiv({ cls: 'mdflow-buttons mdflow-history-buttons' });
    // Clear stays the first button (destructive, secondary styling); Close is the primary action.
    const clear = buttons.createEl('button', { text: t('shell.history.clear'), cls: 'mod-warning', attr: { type: 'button' } });
    clear.addEventListener('click', () => {
      void this.onClear().then(() => this.close());
    });
    const close = buttons.createEl('button', { text: t('shell.history.close'), cls: 'mod-cta', attr: { type: 'button' } });
    close.addEventListener('click', () => this.close());
    close.focus();
  }

  override onClose(): void {
    this.contentEl.empty();
  }
}
