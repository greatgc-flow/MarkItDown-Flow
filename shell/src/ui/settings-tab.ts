/**
 * Settings tab (20_SHELL.md REQ-SHL-04/06/10): schema-2 preferences only; no
 * credential input; links the diagnostics-only SetupModal. Text fields commit
 * on blur/Enter (never per keystroke), so a partially typed interpreter path
 * is never saved or probed. A refused commit is never silent: one notice and
 * the field reverts to the saved value (M4 P-05). Read-only when the persisted
 * file must not be written (newer schema or failed migration, REQ-SHL-03/05).
 */
import { type App, type Plugin, PluginSettingTab, Setting } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { isAbsolutePath } from '../pure/paths';
import { isAcceptableBaseUrl, isSafeVaultRelativePath, type RunOptions, type SettingsV2 } from '../pure/settings';

export interface SettingsTabDeps {
  settings: () => SettingsV2;
  save: (next: SettingsV2) => Promise<void>;
  openSetup: () => void;
  locale: () => UiLocale;
  /** True when nothing may be written (REQ-SHL-03 newer schema / REQ-SHL-05 failed migration). */
  readOnly: () => boolean;
  /** Localized notice by key (`shell.settings.rejected` for a refused commit). */
  notify: (key: string) => void;
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

  /**
   * Commit the element's current value on blur or Enter; unchanged values are ignored. `apply` returns
   * whether it accepted the value. A refused value is never silent (M4 P-05): one `shell.settings.rejected`
   * notice, and the field reverts to the persisted text so it never shows a value that was not saved;
   * re-entering the same refused text is reported again.
   */
  private committed(text: { inputEl: HTMLInputElement | HTMLTextAreaElement }, persisted: () => string, apply: (value: string) => boolean): void {
    let last = persisted();
    const commit = (): void => {
      const value = text.inputEl.value;
      if (value === last) return;
      if (apply(value)) {
        last = value;
        return;
      }
      this.deps.notify('shell.settings.rejected');
      last = persisted();
      text.inputEl.value = last;
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

    const saved = (): SettingsV2 => this.deps.settings();
    new Setting(containerEl).setName(t('shell.settings.enginePython')).setDesc(t('shell.settings.commitNote')).addText((text) => {
      text.setValue(current.enginePython ?? '');
      this.committed(text, () => saved().enginePython ?? '', (value) => {
        const trimmed = value.trim();
        if (trimmed.length === 0) {
          void update({ enginePython: null });
          return true;
        }
        if (!isAbsolutePath(trimmed)) return false;
        void update({ enginePython: trimmed });
        return true;
      });
    });
    new Setting(containerEl).setName(t('shell.settings.openSetup')).addButton((button) => {
      button.setButtonText(t('shell.settings.openSetup')).onClick(() => this.deps.openSetup());
    });
    new Setting(containerEl).setName(t('shell.settings.outputPath')).addText((text) => {
      text.setValue(current.outputPath);
      this.committed(text, () => saved().outputPath, (value) => {
        if (!isSafeVaultRelativePath(value)) return false;
        void update({ outputPath: value });
        return true;
      });
    });
    // Registrations made once at load (context menu, drop listener, command names) apply after a reload (M3 N-09);
    // the drop toggle also states its trade-off: every local-file drop converts instead of attaching (M3 N-08).
    const toggles: [keyof Pick<SettingsV2, 'enableBatchProgress' | 'enableContextMenu' | 'enableRecursiveConversion' | 'enableDragDrop'>, string, string[]][] = [
      ['enableBatchProgress', 'shell.settings.enableBatchProgress', []],
      ['enableContextMenu', 'shell.settings.enableContextMenu', ['shell.settings.reloadNote']],
      ['enableRecursiveConversion', 'shell.settings.enableRecursiveConversion', []],
      ['enableDragDrop', 'shell.settings.enableDragDrop', ['shell.settings.enableDragDropNote', 'shell.settings.reloadNote']],
    ];
    for (const [key, labelKey, descKeys] of toggles) {
      const setting = new Setting(containerEl).setName(t(labelKey));
      if (descKeys.length > 0) setting.setDesc(descKeys.map(t).join(' '));
      setting.addToggle((toggle) => {
        toggle.setValue(current[key]).onChange((value) => {
          void update({ [key]: value } as Partial<SettingsV2>);
        });
      });
    }
    new Setting(containerEl).setName(t('shell.settings.locale')).setDesc(t('shell.settings.reloadNote')).addDropdown((dropdown) => {
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
      this.committed(text, () => saved().provider.model, (value) => {
        void update({ provider: { ...this.deps.settings().provider, model: value.trim() } });
        return true;
      });
    });
    new Setting(containerEl).setName(t('shell.settings.baseUrl')).setDesc(t('shell.settings.baseUrlNote')).addText((text) => {
      text.setValue(current.provider.baseUrl);
      this.committed(text, () => saved().provider.baseUrl, (value) => {
        // The engine's raw-text rule (https, or http for loopback only; no credentials/query/fragment) is applied
        // here, so a value the engine would refuse at job time with E_PROVIDER_CONFIG is never persisted (M3 N-07, M4 P-06).
        const trimmed = value.trim();
        if (!isAcceptableBaseUrl(trimmed)) return false;
        void update({ provider: { ...this.deps.settings().provider, baseUrl: trimmed } });
        return true;
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
      this.committed(text, () => String(saved().runOptions.maxUnits), (value) => {
        const parsed = parseBoundedInteger(value, 1);
        if (parsed === null) return false;
        void updateRun({ maxUnits: parsed });
        return true;
      });
    });
    new Setting(containerEl).setName(t('shell.settings.approveThreshold')).addText((text) => {
      text.setValue(String(current.runOptions.approveThreshold));
      this.committed(text, () => String(saved().runOptions.approveThreshold), (value) => {
        const parsed = parseBoundedInteger(value, 0);
        if (parsed === null) return false;
        void updateRun({ approveThreshold: parsed });
        return true;
      });
    });
    new Setting(containerEl).setName(t('shell.settings.sensitive')).setDesc(t('shell.settings.sensitiveNote')).setClass('mdflow-settings-sensitive').addTextArea((text) => {
      text.setValue(current.runOptions.sensitive.join('\n'));
      this.committed(text, () => saved().runOptions.sensitive.join('\n'), (value) => {
        void updateRun({ sensitive: parseSensitiveGlobs(value) });
        return true;
      });
    });
  }
}
