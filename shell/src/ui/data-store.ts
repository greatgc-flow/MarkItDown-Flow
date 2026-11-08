/**
 * `SettingsStore` over the vault adapter (20_SHELL.md REQ-SHL-05): atomic
 * whole-file replace of `data.json` / `data.v1.json` in the plugin folder.
 */
import type { DataAdapter } from 'obsidian';
import { NotImplementedError } from '../pure/errors';
import type { SettingsStore, StoreFile } from '../pure/persist';

export class VaultDataStore implements SettingsStore {
  constructor(_adapter: DataAdapter, _pluginDirVaultRelative: string) {}

  async read(_name: StoreFile): Promise<string | null> {
    throw new NotImplementedError('VaultDataStore.read');
  }

  async write(_name: StoreFile, _text: string): Promise<void> {
    throw new NotImplementedError('VaultDataStore.write');
  }

  async list(): Promise<string[]> {
    throw new NotImplementedError('VaultDataStore.list');
  }
}
