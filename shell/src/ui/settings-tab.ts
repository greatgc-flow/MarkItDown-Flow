/**
 * Settings tab (20_SHELL.md REQ-SHL-04/06): schema-2 preferences only; no
 * credential input; links the diagnostics-only SetupModal.
 */
import { type App, type Plugin, PluginSettingTab, Setting } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { isSafeVaultRelativePath, type SettingsV2 } from '../pure/settings';

export interface SettingsTabDeps {
  settings: () => SettingsV2;
  save: (next: SettingsV2) => Promise<void>;
  openSetup: () => void;
  locale: () => UiLocale;
}

export class ShellSettingsTab extends PluginSettingTab {
  constructor(
    app: App,
    plugin: Plugin,
    private readonly deps: SettingsTabDeps,
  ) {
    super(app, plugin);
  }

  override display(): void {
    const { containerEl } = this;
    containerEl.empty();
    const t = (key: string): string => formatMessage(this.deps.locale(), key);
    const current = this.deps.settings();
    const update = (patch: Partial<SettingsV2>): Promise<void> => this.deps.save({ ...this.deps.settings(), ...patch });

    new Setting(containerEl).setName(t('shell.settings.enginePython')).addText((text) => {
      text.setValue(current.enginePython ?? '').onChange((value) => {
        const trimmed = value.trim();
        void update({ enginePython: trimmed.length > 0 ? trimmed : null });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.openSetup')).addButton((button) => {
      button.setButtonText(t('shell.settings.openSetup')).onClick(() => this.deps.openSetup());
    });
    new Setting(containerEl).setName(t('shell.settings.outputPath')).addText((text) => {
      text.setValue(current.outputPath).onChange((value) => {
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
      text.setValue(current.provider.model).onChange((value) => {
        void update({ provider: { ...this.deps.settings().provider, model: value.trim() } });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.baseUrl')).addText((text) => {
      text.setValue(current.provider.baseUrl).onChange((value) => {
        try {
          const url = new URL(value);
          if (url.protocol === 'https:' || url.protocol === 'http:') void update({ provider: { ...this.deps.settings().provider, baseUrl: value } });
        } catch {
          // Keep the previous value until the URL parses.
        }
      });
    });
  }
}
