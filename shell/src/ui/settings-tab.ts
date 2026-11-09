/**
 * Settings tab (20_SHELL.md REQ-SHL-04/06/10): schema-2 preferences only; no
 * credential input; links the diagnostics-only SetupModal. Text fields commit
 * on blur/Enter (never per keystroke), so a partially typed interpreter path
 * is never saved or probed. Read-only when the persisted file must not be
 * written (newer schema or failed migration, REQ-SHL-03/05).
 */
import { type App, type Plugin, PluginSettingTab, Setting } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { isSafeVaultRelativePath, type RunOptions, type SettingsV2 } from '../pure/settings';
import { isAbsolutePath } from '../process/launcher';

export interface SettingsTabDeps {
  settings: () => SettingsV2;
  save: (next: SettingsV2) => Promise<void>;
  openSetup: () => void;
  locale: () => UiLocale;
  /** True when nothing may be written (REQ-SHL-03 newer schema / REQ-SHL-05 failed migration). */
  readOnly: () => boolean;
}

/** Globs: one per line or comma-separated; blanks dropped. */
export function parseSensitiveGlobs(text: string): string[] {
  return text.split(/[\r\n,]+/).map((g) => g.trim()).filter((g) => g.length > 0);
}

function parseBoundedInteger(text: string, min: number): number | null {
  if (!/^\s*\d+\s*$/.test(text)) return null;
  const value = Number(text.trim());
  return Number.isSafeInteger(value) && value >= min ? value : null;
}

export class ShellSettingsTab extends PluginSettingTab {
  constructor(
    app: App,
    plugin: Plugin,
    private readonly deps: SettingsTabDeps,
  ) {
    super(app, plugin);
  }

  /** Commit the element's current value on blur or Enter; unchanged values are ignored. */
  private committed(text: { inputEl: HTMLInputElement | HTMLTextAreaElement }, initial: string, apply: (value: string) => void): void {
    let last = initial;
    const commit = (): void => {
      const value = text.inputEl.value;
      if (value === last) return;
      last = value;
      apply(value);
    };
    text.inputEl.addEventListener('blur', commit);
    text.inputEl.addEventListener('keydown', (event: Event) => {
      if ((event as KeyboardEvent).key === 'Enter') commit();
    });
  }

  override display(): void {
    const { containerEl } = this;
    containerEl.empty();
    const t = (key: string): string => formatMessage(this.deps.locale(), key);
    const current = this.deps.settings();

    if (this.deps.readOnly()) {
      containerEl.createEl('p', { cls: 'mdflow-setup-warning', text: t('shell.settings.readOnly') });
      new Setting(containerEl).setName(t('shell.settings.openSetup')).addButton((button) => {
        button.setButtonText(t('shell.settings.openSetup')).onClick(() => this.deps.openSetup());
      });
      return;
    }

    const update = (patch: Partial<SettingsV2>): Promise<void> => this.deps.save({ ...this.deps.settings(), ...patch });
    const updateRun = (patch: Partial<RunOptions>): Promise<void> => update({ runOptions: { ...this.deps.settings().runOptions, ...patch } });

    new Setting(containerEl).setName(t('shell.settings.enginePython')).setDesc(t('shell.settings.commitNote')).addText((text) => {
      text.setValue(current.enginePython ?? '');
      this.committed(text, current.enginePython ?? '', (value) => {
        const trimmed = value.trim();
        if (trimmed.length === 0) void update({ enginePython: null });
        else if (isAbsolutePath(trimmed)) void update({ enginePython: trimmed });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.openSetup')).addButton((button) => {
      button.setButtonText(t('shell.settings.openSetup')).onClick(() => this.deps.openSetup());
    });
    new Setting(containerEl).setName(t('shell.settings.outputPath')).addText((text) => {
      text.setValue(current.outputPath);
      this.committed(text, current.outputPath, (value) => {
        if (isSafeVaultRelativePath(value)) void update({ outputPath: value });
      });
    });
    const toggles: [keyof Pick<SettingsV2, 'enableBatchProgress' | 'enableContextMenu' | 'enableRecursiveConversion' | 'enableDragDrop'>, string][] = [
      ['enableBatchProgress', 'shell.settings.enableBatchProgress'],
      ['enableContextMenu', 'shell.settings.enableContextMenu'],
      ['enableRecursiveConversion', 'shell.settings.enableRecursiveConversion'],
      ['enableDragDrop', 'shell.settings.enableDragDrop'],
    ];
    for (const [key, labelKey] of toggles) {
      new Setting(containerEl).setName(t(labelKey)).addToggle((toggle) => {
        toggle.setValue(current[key]).onChange((value) => {
          void update({ [key]: value } as Partial<SettingsV2>);
        });
      });
    }
    new Setting(containerEl).setName(t('shell.settings.locale')).addDropdown((dropdown) => {
      dropdown.addOptions({ auto: 'auto', en: 'English', ko: '한국어' }).setValue(current.locale).onChange((value) => {
        if (value === 'auto' || value === 'en' || value === 'ko') void update({ locale: value });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.provider')).setDesc(t('shell.settings.keyNote')).addDropdown((dropdown) => {
      dropdown.addOptions({ none: 'none', 'openai-compatible': 'openai-compatible' }).setValue(current.provider.name).onChange((value) => {
        if (value === 'none' || value === 'openai-compatible') void update({ provider: { ...this.deps.settings().provider, name: value } });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.model')).addText((text) => {
      text.setValue(current.provider.model);
      this.committed(text, current.provider.model, (value) => {
        void update({ provider: { ...this.deps.settings().provider, model: value.trim() } });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.baseUrl')).setDesc(t('shell.settings.baseUrlNote')).addText((text) => {
      text.setValue(current.provider.baseUrl);
      this.committed(text, current.provider.baseUrl, (value) => {
        try {
          const url = new URL(value.trim());
          if (url.protocol === 'https:' || url.protocol === 'http:') void update({ provider: { ...this.deps.settings().provider, baseUrl: value.trim() } });
        } catch {
          // Keep the previous value until the URL parses.
        }
      });
    });

    // Nonsecret run options (SPEC 10.2 bounds; REQ-SHL-04).
    new Setting(containerEl).setName(t('shell.settings.dpi')).addDropdown((dropdown) => {
      dropdown.addOptions({ '200': '200', '300': '300' }).setValue(String(current.runOptions.dpi)).onChange((value) => {
        if (value === '200' || value === '300') void updateRun({ dpi: Number(value) as RunOptions['dpi'] });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.minPriority')).addDropdown((dropdown) => {
      dropdown.addOptions({ low: 'low', normal: 'normal' }).setValue(current.runOptions.minPriority).onChange((value) => {
        if (value === 'low' || value === 'normal') void updateRun({ minPriority: value });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.maxUnits')).addText((text) => {
      text.setValue(String(current.runOptions.maxUnits));
      this.committed(text, String(current.runOptions.maxUnits), (value) => {
        const parsed = parseBoundedInteger(value, 1);
        if (parsed !== null) void updateRun({ maxUnits: parsed });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.approveThreshold')).addText((text) => {
      text.setValue(String(current.runOptions.approveThreshold));
      this.committed(text, String(current.runOptions.approveThreshold), (value) => {
        const parsed = parseBoundedInteger(value, 0);
        if (parsed !== null) void updateRun({ approveThreshold: parsed });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.sensitive')).setDesc(t('shell.settings.sensitiveNote')).setClass('mdflow-settings-sensitive').addTextArea((text) => {
      const initial = current.runOptions.sensitive.join('\n');
      text.setValue(initial);
      this.committed(text, initial, (value) => {
        void updateRun({ sensitive: parseSensitiveGlobs(value) });
      });
    });
  }
}
