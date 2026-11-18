/**
 * `SettingsStore` over the vault adapter (20_SHELL.md REQ-SHL-05): whole-file
 * replace of `data.json` / `data.v1.json` in the plugin folder through a
 * temporary sibling and rename.
 */
import type { DataAdapter } from 'obsidian';
import type { SettingsStore, StoreFile } from '../pure/persist';

const STORE_FILES: readonly StoreFile[] = ['data.json', 'data.v1.json'];

export class VaultDataStore implements SettingsStore {
  private writes: Promise<void> = Promise.resolve();
  private sequence = 0;

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

  write(name: StoreFile, text: string): Promise<void> {
    const write = this.writes.then(() => this.replace(name, text));
    // A failed save must reject its caller without poisoning subsequent saves.
    this.writes = write.catch(() => undefined);
    return write;
  }

  private async replace(name: StoreFile, text: string): Promise<void> {
    const target = this.at(name);
    const temp = this.at(`${name}.tmp-${Date.now().toString(36)}-${++this.sequence}`);
    try {
      await this.adapter.write(temp, text);
      // Desktop rename replaces the destination. Never remove the original first:
      // an adapter that cannot replace must fail with the old settings intact.
      await this.adapter.rename(temp, target);
    } catch (error) {
      try {
        await this.adapter.remove(temp);
      } catch {
        // A leftover staging file must never mask the original save error.
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
