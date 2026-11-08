/**
 * `view-conversion-history` (20_SHELL.md REQ-SHL-02/07): display references
 * only; works without Python; clear history clears only history.
 */
import { type App, Modal } from 'obsidian';
import { NotImplementedError } from '../pure/errors';
import type { HistoryEntry } from '../pure/history';
import type { UiLocale } from '../pure/i18n';

export class HistoryModal extends Modal {
  constructor(app: App, _entries: readonly HistoryEntry[], _locale: UiLocale, _onClear: () => Promise<void>) {
    super(app);
  }

  override onOpen(): void {
    throw new NotImplementedError('HistoryModal.onOpen');
  }

  override onClose(): void {
    throw new NotImplementedError('HistoryModal.onClose');
  }
}
