/**
 * Plugin entry (20_SHELL.md REQ-SHL-02/08/09/16). A single desktop guard
 * precedes every lifecycle registration and all Node API access; mobile
 * returns without registrations or engine work. The version probe runs in the
 * background and is awaited lazily by the first job, never by `onload`.
 */
import { FileSystemAdapter, Notice, Platform, Plugin } from 'obsidian';
import { clearHistory, insertHistory, type HistoryEntry } from './pure/history';
import { formatMessage, resolveLocale, type UiLocale } from './pure/i18n';
import { joinPath } from './pure/paths';
import { persistMigration, type SettingsStore } from './pure/persist';
import { defaultSettings, formatMigrationNotice, type SettingsV2 } from './pure/settings';
import type { PickOutcome } from './process/dom-picker';
import { recoverStaleSpools } from './process/engine-process';
import { engineWorkingDirectory } from './process/launcher';
import { LOG_DIR_NAME, RotatingLog } from './process/log';
import { loadNodeApis, type NodeApis } from './process/node-apis';
import { systemClock } from './process/node-spawner';
import { runSelftest } from './process/selftest';
import { DirectorySpoolFs } from './process/spool-fs';
import { probeVersion, type VersionGate } from './process/version-gate';
import { registerCommands } from './ui/commands';
import { ConsentModal } from './ui/consent-modal';
import { type Selection, ShellCoordinator, SPOOL_DIR_NAME } from './ui/coordinator';
import { VaultDataStore } from './ui/data-store';
import { DropConfirmModal } from './ui/drop-confirm-modal';
import { type FilePicker, registerEntryPoints } from './ui/entry-points';
import { HistoryModal } from './ui/history-modal';
import { JobStatusBar } from './ui/progress';
import { SetupModal } from './ui/setup-modal';
import { ShellSettingsTab } from './ui/settings-tab';

function randomNonce(): string {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

function hostLanguage(): string | undefined {
  return typeof navigator !== 'undefined' ? navigator.language : undefined;
}

export default class MarkItDownFlowPlugin extends Plugin {
  private coord: ShellCoordinator | null = null;
  private active = false;
  /** Obsidian 1.13+ `Plugin.settings` slot, typed here (schema 2). */
  override settings: SettingsV2 = defaultSettings();
  private store: SettingsStore | null = null;
  private apis: NodeApis | null = null;
  private gate: VersionGate | null = null;
  /** In-flight version probe; jobs await it instead of `onload` (REQ-SHL-10/17). */
  private gateProbe: Promise<VersionGate | null> | null = null;
  private jobsBlocked = false;
  /** REQ-SHL-03/05: a newer schema or a failed migration leaves the disk file untouched by every later save. */
  private settingsReadOnly = false;
  private locale: UiLocale = 'en';
  private pluginDir = '';
  private vaultRoot = '';

  /** Null on mobile and before `onload` completes. */
  get coordinator(): ShellCoordinator | null {
    return this.coord;
  }

  /** True when the desktop guard passed and registrations were made. */
  get desktopActive(): boolean {
    return this.active;
  }

  override async onload(): Promise<void> {
    if (this.active) return;
    if (!Platform.isDesktop) return;

    const apis = loadNodeApis();
    this.apis = apis;
    const platform = apis.platform;
    const adapter = this.app.vault.adapter;
    this.vaultRoot = adapter instanceof FileSystemAdapter ? adapter.getBasePath() : '';
    const pluginDirRel = this.manifest.dir ?? `${this.app.vault.configDir}/plugins/${this.manifest.id}`;
    this.pluginDir = joinPath(platform, this.vaultRoot, pluginDirRel);

    const store = new VaultDataStore(adapter, pluginDirRel);
    this.store = store;
    const outcome = await persistMigration(store);
    this.settings = outcome.result?.settings ?? defaultSettings();
    this.jobsBlocked = outcome.jobsBlocked;
    this.settingsReadOnly = outcome.jobsBlocked || outcome.result === null;
    this.locale = resolveLocale(this.settings.locale, hostLanguage());
    for (const key of outcome.noticeKeys) this.notify(key);
    if (outcome.result) {
      const text = formatMigrationNotice(outcome.result, this.locale);
      if (text) new Notice(text, 0);
    }

    const log = new RotatingLog(apis.fs, joinPath(platform, this.pluginDir, LOG_DIR_NAME), { home: apis.homeDir(), vault: this.vaultRoot }, platform);
    const spoolFs = new DirectorySpoolFs(apis.fs, joinPath(platform, this.pluginDir, SPOOL_DIR_NAME), platform);
    void recoverStaleSpools(spoolFs);
    // Background probe: never awaited here (X-15); the first job awaits it through `currentGate`.
    void this.refreshGate();

    const statusBar = new JobStatusBar(this.addStatusBarItem(), {
      locale: () => this.locale,
      showDetails: () => this.settings.enableBatchProgress,
      onCancel: () => this.coord?.cancel(),
    });

    const coordinator = new ShellCoordinator({
      spawner: apis.spawner,
      fs: apis.fs,
      spoolFs,
      clock: systemClock,
      hostEnv: process.env,
      platform,
      vaultRoot: this.vaultRoot,
      pluginDir: this.pluginDir,
      settings: () => this.settings,
      gate: () => this.currentGate(),
      consent: (view) => {
        const modal = new ConsentModal(this.app, view, this.locale);
        modal.open();
        return modal.decision;
      },
      notify: (key, params) => this.notify(key, params),
      recordHistory: (entry) => this.recordHistory(entry),
      log,
      nonce: randomNonce,
      progress: statusBar,
    });
    this.coord = coordinator;

    const picker: FilePicker = {
      pickFiles: async () => {
        if (!apis.pickerAvailable) {
          this.notify('shell.notice.pickerUnavailable');
          return null;
        }
        return this.pickedPaths(await apis.pickFiles());
      },
      pickFolder: async () => {
        if (!apis.pickerAvailable) {
          this.notify('shell.notice.pickerUnavailable');
          return null;
        }
        return this.pickedPaths(await apis.pickFolder())?.[0] ?? null;
      },
      confirmSelection: (selection: Selection) => {
        const modal = new DropConfirmModal(this.app, selection, this.locale);
        modal.open();
        return modal.decision;
      },
      pathOf: (file) => apis.filePath(file),
    };

    registerCommands(
      this,
      {
        'convert-file': async () => {
          const files = await picker.pickFiles();
          if (files && files.length > 0) await coordinator.submit({ kind: 'files', paths: files }, 'command');
        },
        'convert-folder': async () => {
          const folder = await picker.pickFolder();
          if (folder) await coordinator.submit({ kind: 'folder', paths: [folder] }, 'command');
        },
        'convert-url': () => coordinator.legacyUrlNotice(),
        'view-conversion-history': () => {
          new HistoryModal(this.app, this.settings.conversionHistory, this.locale, () => this.saveSettings(clearHistory(this.settings))).open();
        },
        'open-log-folder': async () => {
          this.notify('shell.notice.logsNote');
          // The log directory is created lazily by the first log line; make sure it exists before revealing it (M3 N-11).
          await apis.fs.mkdir(log.directory);
          await apis.openFolder(log.directory);
        },
        'run-image-pipeline-selftest': async () => {
          // REQ-SHL-02 inventory row: explain the router retirement, then run SPEC's offline selftest.
          this.notify('shell.notice.selftestRouter');
          const result = await runSelftest({ spawner: apis.spawner, clock: systemClock, hostEnv: process.env, cwd: this.probeCwd(), enginePython: this.settings.enginePython });
          if (result.ok) this.notify('shell.notice.selftestOk');
          for (const key of result.diagnostics) this.notify(key);
        },
      },
      this.locale,
    );

    registerEntryPoints(this, coordinator, this.settings, picker, this.locale);

    this.addSettingTab(
      new ShellSettingsTab(this.app, this, {
        settings: () => this.settings,
        save: async (next) => {
          const interpreterChanged = next.enginePython !== this.settings.enginePython;
          await this.saveSettings(next);
          if (interpreterChanged && !this.settingsReadOnly) {
            this.gate = null;
            this.gateProbe = null;
            await this.refreshGate();
          }
        },
        openSetup: () => this.openSetup(),
        locale: () => this.locale,
        readOnly: () => this.settingsReadOnly,
      }),
    );

    this.active = true;
  }

  override onunload(): void {
    this.coord?.dispose();
    this.coord = null;
    this.active = false;
  }

  private notify(key: string, params?: Record<string, string>): void {
    new Notice(formatMessage(this.locale, key, params));
  }

  /** Picker outcome -> paths; empty and blocked outcomes are reported, never silent (M3 N-05/N-06). */
  private pickedPaths(outcome: PickOutcome): string[] | null {
    switch (outcome.kind) {
      case 'selected':
        return outcome.paths;
      case 'empty':
        this.notify('shell.notice.pickerEmpty');
        return null;
      case 'blocked':
        this.notify('shell.notice.pickerUnavailable');
        return null;
      case 'cancelled':
        return null;
    }
  }

  /**
   * Working directory for probes and the selftest: the engine venv root, or the
   * user's home directory when no interpreter is configured yet. Never the vault
   * or the plugin folder inside it (M3 N-02).
   */
  private probeCwd(): string {
    if (!this.apis) return '';
    return this.settings.enginePython ? engineWorkingDirectory(this.apis.platform, this.settings.enginePython) : this.apis.homeDir();
  }

  /** The gate for the next job: the finished probe, or the in-flight one (started at load or after an interpreter change). */
  private currentGate(): Promise<VersionGate | null> {
    if (this.jobsBlocked) return Promise.resolve(null);
    if (this.gate) return Promise.resolve(this.gate);
    return this.refreshGate();
  }

  /** Probe `<enginePython> -m mdflow version` once; concurrent callers share the in-flight probe. */
  private refreshGate(): Promise<VersionGate | null> {
    if (this.gateProbe) return this.gateProbe;
    if (!this.apis || !this.settings.enginePython) {
      this.gate = null;
      return Promise.resolve(null);
    }
    const apis = this.apis;
    const enginePython = this.settings.enginePython;
    const probe = probeVersion(enginePython, { spawner: apis.spawner, clock: systemClock, hostEnv: process.env, cwd: engineWorkingDirectory(apis.platform, enginePython) })
      .then((gate) => {
        // A later interpreter change supersedes this probe's result.
        if (this.settings.enginePython === enginePython) this.gate = gate;
        return this.settings.enginePython === enginePython ? gate : null;
      })
      .finally(() => {
        if (this.gateProbe === probe) this.gateProbe = null;
      });
    this.gateProbe = probe;
    return probe;
  }

  private openSetup(): void {
    if (!this.apis) return;
    const apis = this.apis;
    new SetupModal(this.app, {
      spawner: apis.spawner,
      clock: systemClock,
      hostEnv: process.env,
      platform: apis.platform,
      cwd: this.probeCwd(),
      enginePython: this.settings.enginePython,
      bootstrapPythonHint: this.settings.bootstrapPythonHint,
      home: apis.homeDir(),
      vault: this.vaultRoot,
      writeClipboard: (text) => apis.writeClipboard(text),
      locale: this.locale,
      onDiagnostics: (diagnostics) => {
        this.gate = diagnostics.gate;
      },
    }).open();
  }

  private async saveSettings(next: SettingsV2): Promise<void> {
    if (this.settingsReadOnly) {
      // REQ-SHL-03/05: never overwrite a newer schema or an unmigrated original.
      this.notify('shell.SETTINGS');
      return;
    }
    this.settings = next;
    this.locale = resolveLocale(next.locale, hostLanguage());
    if (!this.store) return;
    try {
      await this.store.write('data.json', JSON.stringify(next, null, 2) + '\n');
    } catch {
      this.notify('shell.SETTINGS');
    }
  }

  private async recordHistory(entry: HistoryEntry): Promise<void> {
    await this.saveSettings({ ...this.settings, conversionHistory: insertHistory(this.settings.conversionHistory, entry) });
  }
}
