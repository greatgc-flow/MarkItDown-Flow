/**
 * Drop confirmation (20_SHELL.md REQ-SHL-08): the dropped selection is shown
 * before any work; Cancel is the default; Escape/close declines.
 */
import { type App, Modal } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import type { Selection } from './coordinator';

export class DropConfirmModal extends Modal {
  private resolveDecision!: (confirmed: boolean) => void;
  private readonly decisionPromise: Promise<boolean>;
  private settled = false;

  constructor(
    app: App,
    private readonly selection: Selection,
    private readonly locale: UiLocale,
  ) {
    super(app);
    this.decisionPromise = new Promise<boolean>((resolve) => {
      this.resolveDecision = resolve;
    });
  }

  /** Resolves once: Convert -> true; Cancel / close / Escape -> false. */
  get decision(): Promise<boolean> {
    return this.decisionPromise;
  }

  private settle(confirmed: boolean): void {
    if (this.settled) return;
    this.settled = true;
    this.resolveDecision(confirmed);
  }

  confirm(): void {
    if (this.settled) return;
    this.settle(true);
    this.close();
  }

  cancel(): void {
    this.settle(false);
    this.close();
  }

  private t(key: string, params?: Record<string, string>): string {
    return formatMessage(this.locale, key, params);
  }

  override onOpen(): void {
    const { contentEl, titleEl } = this;
    titleEl.setText(this.t('shell.drop.title'));
    contentEl.empty();
    contentEl.addClass('mdflow-drop');
    contentEl.createEl('p', { text: this.t('shell.drop.confirm', { count: String(this.selection.paths.length) }) });
    const list = contentEl.createEl('ul', { cls: 'mdflow-drop-files' });
    for (const path of this.selection.paths) list.createEl('li', { text: path });
    // Same layout as the other dialogs: the default (Cancel, mod-cta) on the right and focused, so Enter declines.
    const buttons = contentEl.createDiv({ cls: 'mdflow-buttons mdflow-drop-buttons' });
    const convert = buttons.createEl('button', { text: this.t('shell.drop.convert'), attr: { type: 'button' } });
    convert.addEventListener('click', () => this.confirm());
    const cancel = buttons.createEl('button', { text: this.t('shell.drop.cancel'), cls: 'mod-cta', attr: { type: 'button' } });
    cancel.addEventListener('click', () => this.cancel());
    cancel.focus();
  }

  override onClose(): void {
    this.settle(false);
    this.contentEl.empty();
  }
}
