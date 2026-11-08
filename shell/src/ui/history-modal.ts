/**
 * `view-conversion-history` (20_SHELL.md REQ-SHL-02/07): display references
 * only; works without Python; clear history clears only history.
 */
import { type App, Modal } from 'obsidian';
import type { HistoryEntry } from '../pure/history';
import { formatMessage, type UiLocale } from '../pure/i18n';

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
    const t = (key: string): string => formatMessage(this.locale, key);
    titleEl.setText(t('shell.history.title'));
    contentEl.empty();
    contentEl.addClass('mdflow-history');
    if (this.entries.length === 0) {
      contentEl.createEl('p', { text: t('shell.history.empty') });
    } else {
      const list = contentEl.createEl('ul');
      for (const entry of this.entries) {
        const outcome = entry.outcome ? t(`shell.history.outcome.${entry.outcome}`) : t('shell.history.outcome.legacy');
        const when = Number.isFinite(entry.timestamp) ? new Date(entry.timestamp).toISOString() : '';
        list.createEl('li', { text: `${when} ${entry.inputFile} -> ${entry.outputFile} (${outcome}${entry.success ? '' : ', !'})` });
      }
    }
    const clear = contentEl.createEl('button', { text: t('shell.history.clear') });
    clear.addEventListener('click', () => {
      void this.onClear().then(() => this.close());
    });
  }

  override onClose(): void {
    this.contentEl.empty();
  }
}
