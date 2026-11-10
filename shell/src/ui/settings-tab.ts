/**
 * Settings tab (20_SHELL.md REQ-SHL-04/06/10): schema-2 preferences only; no
 * credential input; links the diagnostics-only SetupModal. Text fields commit
 * on blur/Enter (never per keystroke), so a partially typed interpreter path
 * is never saved or probed. A refused commit is never silent: one notice and
 * the field reverts to the saved value (M4 P-05). Read-only when the persisted
 * file must not be written (newer schema or failed migration, REQ-SHL-03/05).
 *
 * Layout (R32): five Obsidian-native sections with headings and one-line
 * descriptions: Engine, Conversion, OCR provider, Consent & privacy, Advanced.
 * No markitdown LLM settings exist (R29).
 */
import { type App, Platform, type Plugin, PluginSettingTab, Setting } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import { isAbsolutePath } from '../pure/paths';
import { isAcceptableBaseUrl, isSafeVaultRelativePath, type RunOptions, type SettingsV2 } from '../pure/settings';
import type { VersionGate, VersionInfo } from '../process/version-gate';
import { toolStatusText } from './setup-modal';

/** The detected-LibreOffice phrase of the legacy toggle (R33): found with version, too old/unusable, missing, or unknown. */
export function libreofficeSettingStatus(locale: UiLocale, info: VersionInfo | null): string {
  if (!info || (info.libreoffice === undefined && info.libreoffice_status === undefined)) return formatMessage(locale, 'shell.settings.libreofficeUnknown');
  if (info.libreoffice_status === 'too_old' || info.libreoffice_status === 'unusable') return toolStatusText(locale, info, 'libreoffice');
  if (typeof info.libreoffice === 'string' && info.libreoffice.length > 0) return formatMessage(locale, 'shell.settings.libreofficeFound', { version: info.libreoffice });
  return formatMessage(locale, 'shell.settings.libreofficeMissing');
}

export interface SettingsTabDeps {
  settings: () => SettingsV2;
  save: (next: SettingsV2) => Promise<void>;
  openSetup: () => void;
  locale: () => UiLocale;
  /** True when nothing may be written (REQ-SHL-03 newer schema / REQ-SHL-05 failed migration). */
  readOnly: () => boolean;
  /** Localized notice by key (`shell.settings.rejected` for a refused commit). */
  notify: (key: string) => void;
  /** Last version gate, for the detected LibreOffice status next to the legacy toggle (R33); null before the probe. */
  gate?: () => VersionGate | null;
}

/** Section order of the tab (R32); each has `shell.settings.section.<id>` and `<id>Desc` strings. */
export const SETTINGS_SECTIONS = ['engine', 'conversion', 'provider', 'consent', 'advanced'] as const;

/** Globs: one per line or comma-separated; blanks dropped. */
export function parseSensitiveGlobs(text: string): string[] {
  return text.split(/[\r\n,]+/).map((g) => g.trim()).filter((g) => g.length > 0);
}

function parseBoundedInteger(text: string, min: number): number | null {
  if (!/^\s*\d+\s*$/.test(text)) return null;
  const value = Number(text.trim());
  return Number.isSafeInteger(value) && value >= min ? value : null;
}

type ToggleKey = keyof Pick<SettingsV2, 'enableBatchProgress' | 'enableContextMenu' | 'enableRecursiveConversion' | 'enableDragDrop' | 'enableLegacyPreconvert'>;

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
    containerEl.addClass('mdflow-settings');
    const t = (key: string): string => formatMessage(this.deps.locale(), key);
    const current = this.deps.settings();

    if (this.deps.readOnly()) {
      containerEl.createEl('p', { cls: 'mdflow-setup-warning', text: t('shell.settings.readOnly') });
      new Setting(containerEl).setName(t('shell.settings.openSetup')).setDesc(t('shell.settings.openSetupDesc')).addButton((button) => {
        button.setButtonText(t('shell.settings.openSetup')).onClick(() => this.deps.openSetup());
      });
      return;
    }

    const update = (patch: Partial<SettingsV2>): Promise<void> => this.deps.save({ ...this.deps.settings(), ...patch });
    const updateRun = (patch: Partial<RunOptions>): Promise<void> => update({ runOptions: { ...this.deps.settings().runOptions, ...patch } });
    const saved = (): SettingsV2 => this.deps.settings();
    const section = (id: (typeof SETTINGS_SECTIONS)[number]): void => {
      new Setting(containerEl).setName(t(`shell.settings.section.${id}`)).setDesc(t(`shell.settings.section.${id}Desc`)).setHeading().setClass('mdflow-settings-heading');
    };
    const toggle = (key: ToggleKey, descKeys: string[] = [], descText = ''): void => {
      const setting = new Setting(containerEl).setName(t(`shell.settings.${key}`));
      const desc = [...descKeys.map(t), descText].filter((s) => s.length > 0).join(' ');
      if (desc.length > 0) setting.setDesc(desc);
      setting.addToggle((control) => {
        control.setValue(current[key]).onChange((value) => {
          void update({ [key]: value } as Partial<SettingsV2>);
        });
      });
    };

    // --- Engine -------------------------------------------------------------------------------------------
    section('engine');
    new Setting(containerEl).setName(t('shell.settings.enginePython')).setDesc(t('shell.settings.enginePythonNote')).addText((text) => {
      // Example path in the user's OS form, matching the SetupModal's bootstrap recipe.
      text.setPlaceholder(Platform.isWin ? 'C:\\mdflow-venvs\\2.0.0\\Scripts\\python.exe' : '/path/to/mdflow-venvs/2.0.0/bin/python');
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
    new Setting(containerEl).setName(t('shell.settings.openSetup')).setDesc(t('shell.settings.openSetupDesc')).addButton((button) => {
      button.setButtonText(t('shell.settings.openSetup')).onClick(() => this.deps.openSetup());
    });

    // --- Conversion ---------------------------------------------------------------------------------------
    section('conversion');
    new Setting(containerEl).setName(t('shell.settings.outputPath')).setDesc(t('shell.settings.outputPathNote')).addText((text) => {
      text.setPlaceholder('markitdown-output');
      text.setValue(current.outputPath);
      this.committed(text, () => saved().outputPath, (value) => {
        if (!isSafeVaultRelativePath(value)) return false;
        void update({ outputPath: value });
        return true;
      });
    });
    toggle('enableRecursiveConversion');
    // R33: LibreOffice pre-convert of LEGACY formats, off by default; the description states what it does and
    // which LibreOffice the engine detected (version/source, missing, or not reported), from the last version probe.
    const gate = this.deps.gate?.() ?? null;
    const status = libreofficeSettingStatus(this.deps.locale(), gate?.enabled ? gate.info : null);
    toggle('enableLegacyPreconvert', ['shell.settings.enableLegacyPreconvertNote'], formatMessage(this.deps.locale(), 'shell.settings.libreofficeStatus', { status }));
    // Registrations made once at load (context menu, drop listener, command names) apply after a reload (M3 N-09);
    // the drop toggle also states its trade-off: every local-file drop converts instead of attaching (M3 N-08).
    toggle('enableContextMenu', ['shell.settings.reloadNote']);
    toggle('enableDragDrop', ['shell.settings.enableDragDropNote', 'shell.settings.reloadNote']);
    toggle('enableBatchProgress');
    new Setting(containerEl).setName(t('shell.settings.locale')).setDesc(t('shell.settings.reloadNote')).addDropdown((dropdown) => {
      dropdown.addOptions({ auto: t('shell.settings.locale.auto'), en: 'English', ko: '한국어' }).setValue(current.locale).onChange((value) => {
        // The tab itself follows the new language at once (other registrations still need the reload noted above).
        if (value === 'auto' || value === 'en' || value === 'ko') void update({ locale: value }).then(() => this.display());
      });
    });

    // --- OCR provider -------------------------------------------------------------------------------------
    section('provider');
    new Setting(containerEl).setName(t('shell.settings.provider')).setDesc(t('shell.settings.keyNote')).addDropdown((dropdown) => {
      dropdown.addOptions({ none: t('shell.settings.provider.none'), 'openai-compatible': t('shell.settings.provider.openai') }).setValue(current.provider.name).onChange((value) => {
        if (value === 'none' || value === 'openai-compatible') void update({ provider: { ...this.deps.settings().provider, name: value } });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.model')).setDesc(t('shell.settings.commitNote')).addText((text) => {
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

    // --- Consent & privacy (SPEC 10.2 bounds; REQ-SHL-04) -------------------------------------------------
    section('consent');
    new Setting(containerEl).setName(t('shell.settings.approveThreshold')).setDesc(`${t('shell.settings.approveThresholdNote')} ${t('shell.settings.commitNote')}`).addText((text) => {
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

    // --- Advanced -----------------------------------------------------------------------------------------
    section('advanced');
    new Setting(containerEl).setName(t('shell.settings.dpi')).setDesc(t('shell.settings.dpiNote')).addDropdown((dropdown) => {
      dropdown.addOptions({ '200': '200', '300': '300' }).setValue(String(current.runOptions.dpi)).onChange((value) => {
        if (value === '200' || value === '300') void updateRun({ dpi: Number(value) as RunOptions['dpi'] });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.minPriority')).setDesc(t('shell.settings.minPriorityNote')).addDropdown((dropdown) => {
      dropdown.addOptions({ low: t('shell.settings.minPriority.low'), normal: t('shell.settings.minPriority.normal') }).setValue(current.runOptions.minPriority).onChange((value) => {
        if (value === 'low' || value === 'normal') void updateRun({ minPriority: value });
      });
    });
    new Setting(containerEl).setName(t('shell.settings.maxUnits')).setDesc(`${t('shell.settings.maxUnitsNote')} ${t('shell.settings.commitNote')}`).addText((text) => {
      text.setValue(String(current.runOptions.maxUnits));
      this.committed(text, () => String(saved().runOptions.maxUnits), (value) => {
        const parsed = parseBoundedInteger(value, 1);
        if (parsed === null) return false;
        void updateRun({ maxUnits: parsed });
        return true;
      });
    });
  }
}
