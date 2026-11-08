/**
 * `SettingsStore` over the vault adapter (20_SHELL.md REQ-SHL-05): whole-file
 * replace of `data.json` / `data.v1.json` in the plugin folder through a
 * temporary sibling and rename.
 */
import type { DataAdapter } from 'obsidian';
import type { SettingsStore, StoreFile } from '../pure/persist';

const STORE_FILES: readonly StoreFile[] = ['data.json', 'data.v1.json'];

export class VaultDataStore implements SettingsStore {
  constructor(
    private readonly adapter: DataAdapter,
    private readonly pluginDirVaultRelative: string,
  ) {}

  private at(name: string): string {
    return `${this.pluginDirVaultRelative.replace(/\/+$/, '')}/${name}`;
  }

  async read(name: StoreFile): Promise<string | null> {
    const path = this.at(name);
    if (!(await this.adapter.exists(path))) return null;
    return this.adapter.read(path);
  }

  async write(name: StoreFile, text: string): Promise<void> {
    const target = this.at(name);
    const temp = this.at(`${name}.tmp-${Date.now().toString(36)}`);
    await this.adapter.write(temp, text);
    try {
      if (await this.adapter.exists(target)) await this.adapter.remove(target);
      await this.adapter.rename(temp, target);
    } catch (error) {
      try {
        await this.adapter.remove(temp);
      } catch {
        // Leave the temp file if even removal fails; it never shadows the target.
      }
      throw error;
    }
  }

  async list(): Promise<string[]> {
    const present: string[] = [];
    for (const name of STORE_FILES) {
      if (await this.adapter.exists(this.at(name))) present.push(name);
    }
    return present;
  }
}
