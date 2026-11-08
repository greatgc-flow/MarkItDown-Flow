/**
 * Plugin entry (20_SHELL.md REQ-SHL-02/08). A single desktop guard precedes
 * every lifecycle registration and all Node API access; mobile returns without
 * registrations or engine work.
 */
import { FileSystemAdapter, Notice, Platform, Plugin } from 'obsidian';
import { clearHistory, insertHistory, type HistoryEntry } from './pure/history';
import { formatMessage, resolveLocale, type UiLocale } from './pure/i18n';
import { persistMigration, type SettingsStore } from './pure/persist';
import { defaultSettings, formatMigrationNotice, type SettingsV2 } from './pure/settings';
import type { SpoolFs } from './pure/spool';
import { recoverStaleSpools } from './process/engine-process';
import { LOG_DIR_NAME, RotatingLog } from './process/log';
import { loadNodeApis, type NodeApis } from './process/node-apis';
import { systemClock } from './process/node-spawner';
import { runSelftest } from './process/selftest';
import type { FileSystemOps, HostPlatform } from './process/types';
import { probeVersion, type VersionGate } from './process/version-gate';
import { registerCommands } from './ui/commands';
import { ConsentModal } from './ui/consent-modal';
import { ShellCoordinator, SPOOL_DIR_NAME } from './ui/coordinator';
import { VaultDataStore } from './ui/data-store';
import { registerEntryPoints } from './ui/entry-points';
import { HistoryModal } from './ui/history-modal';
import { joinPath } from './ui/output-path';
import { SetupModal } from './ui/setup-modal';
import { ShellSettingsTab } from './ui/settings-tab';

/** SpoolFs over the owned spool directory. */
class DirectorySpoolFs implements SpoolFs {
  constructor(
    private readonly fs: FileSystemOps,
    private readonly dir: string,
    private readonly platform: HostPlatform,
  ) {}

  private at(name: string): string {
    return joinPath(this.platform, this.dir, name);
  }

  async append(name: string, chunk: Uint8Array): Promise<void> {
    await this.fs.mkdir(this.dir);
    await this.fs.appendFile(this.at(name), chunk);
  }

  async read(name: string, offset: number, max: number): Promise<Uint8Array> {
    const data = await this.fs.readFile(this.at(name));
    if (!data) return new Uint8Array(0);
    return data.slice(offset, offset + max);
  }

  async remove(name: string): Promise<void> {
    await this.fs.remove(this.at(name));
  }

  async list(): Promise<string[]> {
    return this.fs.list(this.dir);
  }
}

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
  private jobsBlocked = false;
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
    this.locale = resolveLocale(this.settings.locale, hostLanguage());
    for (const key of outcome.noticeKeys) this.notify(key);
    if (outcome.result) {
      const text = formatMigrationNotice(outcome.result, this.locale);
      if (text) new Notice(text, 0);
    }

    const log = new RotatingLog(apis.fs, joinPath(platform, this.pluginDir, LOG_DIR_NAME), { home: apis.homeDir(), vault: this.vaultRoot });
    const spoolFs = new DirectorySpoolFs(apis.fs, joinPath(platform, this.pluginDir, SPOOL_DIR_NAME), platform);
    void recoverStaleSpools(spoolFs);
    await this.refreshGate();

    const coordinator = new ShellCoordinator({
      spawner: apis.spawner,
      fs: apis.fs,
      spoolFs,
      clock: systemClock,
      hostEnv: process.env,
      platform,
      vaultRoot: this.vaultRoot,
      pluginDir: this.pluginDir,
      locale: this.locale,
      settings: () => this.settings,
      gate: () => (this.jobsBlocked ? null : this.gate),
      consent: (view) => {
        const modal = new ConsentModal(this.app, view, this.locale);
        modal.open();
        return modal.decision;
      },
      notify: (key, params) => this.notify(key, params),
      recordHistory: (entry) => this.recordHistory(entry),
      log,
      nonce: randomNonce,
    });
    this.coord = coordinator;

    registerCommands(
      this,
      {
        'convert-file': async () => {
          const files = await apis.pickFiles();
          if (files && files.length > 0) await coordinator.submit({ kind: 'files', paths: files }, 'command');
        },
        'convert-folder': async () => {
          const folder = await apis.pickFolder();
          if (folder) await coordinator.submit({ kind: 'folder', paths: [folder] }, 'command');
        },
        'convert-url': () => coordinator.legacyUrlNotice(),
        'view-conversion-history': () => {
          new HistoryModal(this.app, this.settings.conversionHistory, this.locale, () => this.saveSettings(clearHistory(this.settings))).open();
        },
        'open-log-folder': async () => {
          this.notify('shell.notice.logsNote');
          await apis.openFolder(log.directory);
        },
        'run-image-pipeline-selftest': async () => {
          const result = await runSelftest({ spawner: apis.spawner, clock: systemClock, hostEnv: process.env, cwd: this.pluginDir, enginePython: this.settings.enginePython });
          if (result.ok) this.notify('shell.notice.selftestOk');
          for (const key of result.diagnostics) this.notify(key);
        },
      },
      this.locale,
    );

    registerEntryPoints(
      this,
      coordinator,
      this.settings,
      {
        pickFiles: () => apis.pickFiles(),
        pickFolder: () => apis.pickFolder(),
        confirmSelection: async (selection) => {
          // Drops are confirmed through the same consent-free selection notice; the engine Plan modal follows.
          this.notify('shell.drop.confirm', { count: String(selection.paths.length) });
          return true;
        },
      },
      this.locale,
    );

    this.addSettingTab(
      new ShellSettingsTab(this.app, this, {
        settings: () => this.settings,
        save: async (next) => {
          const interpreterChanged = next.enginePython !== this.settings.enginePython;
          await this.saveSettings(next);
          if (interpreterChanged) await this.refreshGate();
        },
        openSetup: () => this.openSetup(),
        locale: () => this.locale,
      }),
    );

    this.active = true;
    // Under the host, `load()` already marked this component loaded (no-op here). When `onload()`
    // is invoked directly, this records the loaded state so every `register*` cleanup runs on `unload()`.
    this.load();
  }

  override onunload(): void {
    this.coord?.dispose();
    this.coord = null;
    this.active = false;
  }

  private notify(key: string, params?: Record<string, string>): void {
    new Notice(formatMessage(this.locale, key, params));
  }

  private async refreshGate(): Promise<void> {
    if (!this.apis || !this.settings.enginePython) {
      this.gate = null;
      return;
    }
    this.gate = await probeVersion(this.settings.enginePython, { spawner: this.apis.spawner, clock: systemClock, hostEnv: process.env, cwd: this.pluginDir });
  }

  private openSetup(): void {
    if (!this.apis) return;
    const apis = this.apis;
    new SetupModal(this.app, {
      spawner: apis.spawner,
      clock: systemClock,
      hostEnv: process.env,
      platform: apis.platform,
      cwd: this.pluginDir,
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
