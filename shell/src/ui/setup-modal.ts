/**
 * Diagnostics-only SetupModal (20_SHELL.md REQ-SHL-10/17). Shows interpreter,
 * versions and tool status (exiftool R31, LibreOffice R33), the co-install guard
 * error with its fix command (R33c), probe status, provider/tool variable
 * presence and copyable external bootstrap instructions, in four sections.
 */
import { type App, Modal } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { collectSetupDiagnostics, type SetupDeps, type SetupDiagnostics } from '../process/setup';
import { TOOL_INFO_KEYS, type VersionInfo } from '../process/version-gate';

type OptionalTool = 'exiftool' | 'libreoffice';

/**
 * One tool line (R31/R33): the reported version (and where it was found), a too-old/unusable
 * state, missing (graceful), or not reported by this engine version. Pure; shared with the settings tab.
 */
export function toolStatusText(locale: UiLocale, info: VersionInfo | null, tool: OptionalTool): string {
  const t = (key: string, params?: Record<string, string>): string => formatMessage(locale, key, params);
  if (!info) return t(`shell.setup.${tool}Unknown`);
  const version = info[tool];
  const status = info[`${tool}_status`];
  if (version === undefined && status === undefined) return t(`shell.setup.${tool}Unknown`);
  if (status === 'too_old' || status === 'unusable') return t(`shell.setup.tool.${status}`);
  if (typeof version === 'string' && version.length > 0) {
    const source = info[`${tool}_source`];
    return typeof source === 'string' && source.length > 0 ? `${version} (${source})` : version;
  }
  return t(`shell.setup.${tool}Missing`);
}

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

  private toolText(d: SetupDiagnostics, tool: OptionalTool): string {
    return toolStatusText(this.deps.locale, d.gate?.enabled ? d.gate.info : null, tool);
  }

  private keyValue(parent: HTMLElement, key: string, value: string, cls?: string): void {
    const line = parent.createDiv({ cls: `mdflow-kv${cls ? ` ${cls}` : ''}` });
    line.createSpan({ cls: 'mdflow-kv-key', text: `${key}: ` });
    line.createSpan({ cls: 'mdflow-kv-value', text: value });
  }

  private heading(parent: HTMLElement, key: string): void {
    parent.createEl('h3', { cls: 'mdflow-section-title', text: this.t(key) });
  }

  private render(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('mdflow-setup');
    const d = this.current;

    this.heading(contentEl, 'shell.setup.section.interpreter');
    this.keyValue(contentEl, this.t('shell.setup.interpreter'), this.deps.enginePython ?? '-', 'mdflow-setup-interpreter');
    if (!this.deps.enginePython) contentEl.createEl('p', { cls: 'mdflow-setup-warning', text: this.t('shell.setup.unconfigured') });
    if (d?.gate) {
      const status = d.gate.enabled ? this.t('shell.setup.probeOk') : this.t('shell.setup.probeBlocked', { reason: `${d.gate.reason}${d.gate.field ? ` ${d.gate.field}` : ''}` });
      this.keyValue(contentEl, this.t('shell.setup.probe'), status, d.gate.enabled ? 'mdflow-setup-ok' : 'mdflow-setup-blocked');
      if (d.conflictFix !== null) {
        // R33c co-install guard: the upstream `markitdown` distribution must leave the venv; show the exact command.
        const conflict = contentEl.createDiv({ cls: 'mdflow-setup-warning mdflow-setup-conflict' });
        conflict.createEl('p', { text: this.t('shell.setup.upstreamConflict') });
        conflict.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.setup.upstreamConflictFix') });
        conflict.createEl('pre', { cls: 'mdflow-setup-commands', text: d.conflictFix });
      }
    }

    if (d) {
      this.heading(contentEl, 'shell.setup.section.versions');
      if (d.gate?.enabled) {
        const versions = contentEl.createDiv({ cls: 'mdflow-setup-versions' });
        const toolKeys = new Set<string>(TOOL_INFO_KEYS);
        for (const [key, value] of Object.entries(d.gate.info)) {
          if (toolKeys.has(key)) continue;
          this.keyValue(versions, key, String(value));
        }
      }
      this.keyValue(contentEl, this.t('shell.setup.exiftool'), this.toolText(d, 'exiftool'), 'mdflow-setup-exiftool');
      this.keyValue(contentEl, this.t('shell.setup.libreoffice'), this.toolText(d, 'libreoffice'), 'mdflow-setup-libreoffice');
      if (d.bootstrapProbes.length > 0) {
        const probes = contentEl.createDiv({ cls: 'mdflow-setup-probes' });
        probes.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.setup.bootstrapProbes') });
        for (const probe of d.bootstrapProbes) {
          this.keyValue(probes, `${probe.command} ${probe.args.join(' ')}`, `${probe.result}${probe.version ? ` ${probe.version}` : ''}`);
        }
      }

      this.heading(contentEl, 'shell.setup.section.environment');
      contentEl.createEl('p', { text: this.t('shell.setup.apiKey', { presence: d.apiKey }) });
      contentEl.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.setup.providerEnv') });
      const envList = contentEl.createDiv({ cls: 'mdflow-setup-env' });
      for (const [name, presence] of Object.entries(d.providerEnv)) this.keyValue(envList, name, presence);
      contentEl.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.setup.toolEnv') });
      const toolList = contentEl.createDiv({ cls: 'mdflow-setup-env mdflow-setup-tool-env' });
      for (const [name, presence] of Object.entries(d.toolEnv)) this.keyValue(toolList, name, presence);
      contentEl.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.setup.launchHint') });

      this.heading(contentEl, 'shell.setup.section.instructions');
      contentEl.createEl('p', { text: this.t('shell.setup.instructions') });
      contentEl.createEl('pre', { cls: 'mdflow-setup-commands', text: d.instructions.windows });
      contentEl.createEl('pre', { cls: 'mdflow-setup-commands', text: d.instructions.posix });
    }

    const buttons = contentEl.createDiv({ cls: 'mdflow-buttons mdflow-setup-buttons' });
    buttons.createEl('button', { text: this.t('shell.setup.copyWindows'), attr: { type: 'button' } }).addEventListener('click', () => {
      void this.copyInstructions('windows');
    });
    buttons.createEl('button', { text: this.t('shell.setup.copyPosix'), attr: { type: 'button' } }).addEventListener('click', () => {
      void this.copyInstructions('posix');
    });
    buttons.createEl('button', { text: this.t('shell.setup.copyDiagnostics'), attr: { type: 'button' } }).addEventListener('click', () => {
      void this.copyDiagnostics();
    });
    buttons.createEl('button', { text: this.t('shell.setup.refresh'), cls: 'mod-cta', attr: { type: 'button' } }).addEventListener('click', () => {
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
