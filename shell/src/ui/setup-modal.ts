/**
 * Diagnostics-only SetupModal (20_SHELL.md REQ-SHL-10/17). Shows interpreter,
 * versions, probe status and copyable external bootstrap instructions.
 */
import { type App, Modal } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { collectSetupDiagnostics, type SetupDeps, type SetupDiagnostics } from '../process/setup';

export interface SetupModalDeps extends SetupDeps {
  writeClipboard: (text: string) => Promise<void>;
  locale: UiLocale;
  /** Called after each refresh so the owner can update its version gate. */
  onDiagnostics?: (diagnostics: SetupDiagnostics) => void;
}

export class SetupModal extends Modal {
  private current: SetupDiagnostics | null = null;
  private refreshing: Promise<void> | null = null;

  constructor(
    app: App,
    private readonly deps: SetupModalDeps,
  ) {
    super(app);
  }

  /** Last collected diagnostics (null before the first refresh). */
  get diagnostics(): SetupDiagnostics | null {
    return this.current;
  }

  private t(key: string, params?: Record<string, string>): string {
    return formatMessage(this.deps.locale, key, params);
  }

  /** Re-run the version probe(s) and re-render. */
  async refresh(): Promise<void> {
    if (this.refreshing) return this.refreshing;
    this.refreshing = (async () => {
      const diagnostics = await collectSetupDiagnostics(this.deps);
      this.current = diagnostics;
      this.deps.onDiagnostics?.(diagnostics);
      this.render();
    })().finally(() => {
      this.refreshing = null;
    });
    return this.refreshing;
  }

  /** Copy buttons: write the rendered instruction text to the clipboard, nothing else. */
  async copyInstructions(target: 'windows' | 'posix'): Promise<void> {
    if (!this.current) return;
    await this.deps.writeClipboard(this.current.instructions[target]);
  }

  async copyDiagnostics(): Promise<void> {
    if (!this.current) return;
    await this.deps.writeClipboard(this.current.summary);
  }

  private render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('mdflow-setup');
    const d = this.current;
    contentEl.createEl('p', { text: `${this.t('shell.setup.interpreter')}: ${this.deps.enginePython ?? '-'}` });
    if (!this.deps.enginePython) contentEl.createEl('p', { cls: 'mdflow-setup-warning', text: this.t('shell.setup.unconfigured') });
    if (d) {
      if (d.gate) {
        const status = d.gate.enabled ? this.t('shell.setup.probeOk') : this.t('shell.setup.probeBlocked', { reason: `${d.gate.reason}${d.gate.field ? ` ${d.gate.field}` : ''}` });
        contentEl.createEl('p', { text: `${this.t('shell.setup.probe')}: ${status}` });
        if (d.gate.enabled) {
          const versions = contentEl.createEl('ul', { cls: 'mdflow-setup-versions' });
          for (const [key, value] of Object.entries(d.gate.info)) versions.createEl('li', { text: `${key}: ${String(value)}` });
        }
      }
      if (d.bootstrapProbes.length > 0) {
        const probes = contentEl.createEl('ul');
        for (const probe of d.bootstrapProbes) probes.createEl('li', { text: `${probe.command} ${probe.args.join(' ')}: ${probe.result}${probe.version ? ` ${probe.version}` : ''}` });
      }
      contentEl.createEl('p', { text: this.t('shell.setup.apiKey', { presence: d.apiKey }) });
      contentEl.createEl('p', { text: this.t('shell.setup.launchHint') });
      contentEl.createEl('p', { text: this.t('shell.setup.instructions') });
      contentEl.createEl('pre', { cls: 'mdflow-setup-commands', text: d.instructions.windows });
      contentEl.createEl('pre', { cls: 'mdflow-setup-commands', text: d.instructions.posix });
    }
    const buttons = contentEl.createDiv({ cls: 'mdflow-setup-buttons' });
    buttons.createEl('button', { text: this.t('shell.setup.copyWindows') }).addEventListener('click', () => {
      void this.copyInstructions('windows');
    });
    buttons.createEl('button', { text: this.t('shell.setup.copyPosix') }).addEventListener('click', () => {
      void this.copyInstructions('posix');
    });
    buttons.createEl('button', { text: this.t('shell.setup.copyDiagnostics') }).addEventListener('click', () => {
      void this.copyDiagnostics();
    });
    buttons.createEl('button', { text: this.t('shell.setup.refresh') }).addEventListener('click', () => {
      void this.refresh();
    });
  }

  override onOpen(): void {
    this.titleEl.setText(this.t('shell.setup.title'));
    this.render();
    void this.refresh();
  }

  override onClose(): void {
    this.contentEl.empty();
  }
}
