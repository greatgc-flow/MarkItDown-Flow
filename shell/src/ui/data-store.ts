/**
 * `SettingsStore` over the vault adapter (20_SHELL.md REQ-SHL-05): whole-file
 * replace of `data.json` / `data.v1.json` in the plugin folder through a
 * staging sibling. Obsidian's adapter `rename` refuses an existing destination
 * ("Destination file already exists!", desktop and mobile), so the original is
 * moved aside to `<name>.bak` (never deleted first), the staging file takes its
 * place, and only then is the backup removed. Any failure restores the original;
 * an interrupted swap leaves `<name>.bak`, which `read` returns.
 */
import type { DataAdapter } from 'obsidian';
import type { SettingsStore, StoreFile } from '../pure/persist';

const STORE_FILES: readonly StoreFile[] = ['data.json', 'data.v1.json'];

export class VaultDataStore implements SettingsStore {
  private queue: Promise<void> = Promise.resolve();
  private sequence = 0;

  constructor(
    private readonly adapter: DataAdapter,
    private readonly pluginDirVaultRelative: string,
  ) {}

  private at(name: string): string {
    return `${this.pluginDirVaultRelative.replace(/\/+$/, '')}/${name}`;
  }

  /** Reads, saves and listings share one queue, so a read never observes a swap in progress. */
  read(name: StoreFile): Promise<string | null> {
    return this.queued(async () => {
      const target = this.at(name);
      const backup = this.at(`${name}.bak`);
      if (await this.adapter.exists(target)) {
        const text = await this.adapter.read(target);
        // A backup beside an installed target survived an interrupted or failed cleanup and may hold raw
        // v1 settings: remove it now; if that is impossible the read rejects (unsanitized-disk path). The
        // target is unvalidated here, so it is never copied over the backup.
        if (await this.adapter.exists(backup)) await this.adapter.remove(backup);
        return text;
      }
      return (await this.adapter.exists(backup)) ? this.adapter.read(backup) : null;
    });
  }

  write(name: StoreFile, text: string): Promise<void> {
    return this.queued(() => this.replace(name, text));
  }

  async list(): Promise<string[]> {
    return this.queued(async () => {
      const present: string[] = [];
      for (const name of STORE_FILES) {
        // A file whose swap was interrupted is still present: `read` returns its backup.
        if ((await this.adapter.exists(this.at(name))) || (await this.adapter.exists(this.at(`${name}.bak`)))) present.push(name);
      }
      return present;
    });
  }

  private queued<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.queue.then(operation);
    // A failed operation must reject its caller without poisoning later ones.
    this.queue = result.then(() => undefined, () => undefined);
    return result;
  }

  private async replace(name: StoreFile, text: string): Promise<void> {
    const target = this.at(name);
    const backup = this.at(`${name}.bak`);
    const temp = this.at(`${name}.tmp-${Date.now().toString(36)}-${++this.sequence}`);
    let movedAside = false;
    try {
      await this.adapter.write(temp, text);
      if (await this.adapter.exists(target)) {
        // A backup next to a present target is stale (an earlier cleanup failed).
        if (await this.adapter.exists(backup)) await this.adapter.remove(backup);
        await this.adapter.rename(target, backup);
        movedAside = true;
      }
      await this.adapter.rename(temp, target);
    } catch (error) {
      if (movedAside) await this.quietly(() => this.adapter.rename(backup, target));
      await this.quietly(() => this.adapter.remove(temp));
      throw error;
    }
    await this.discardBackup(backup, text);
  }

  /**
   * After a successful swap the backup (this swap's original, or one left by an interrupted swap) is obsolete.
   * It may hold raw v1 settings, which must never be kept (REQ-SHL-05): if it cannot be removed, overwrite it
   * with the just-saved text (the store only ever writes sanitized settings or snapshots); if even that fails,
   * report the save as failed so the unsanitized-disk path runs.
   */
  private async discardBackup(backup: string, text: string): Promise<void> {
    if (!(await this.adapter.exists(backup))) return;
    try {
      await this.adapter.remove(backup);
    } catch {
      await this.adapter.write(backup, text);
      await this.quietly(() => this.adapter.remove(backup));
    }
  }

  /** Best-effort step that must never mask the save outcome; `read` and the next save tolerate leftovers. */
  private async quietly(step: () => Promise<void>): Promise<void> {
    try {
      await step();
    } catch {
      // Leftover backup or staging file: harmless, retried on the next save.
    }
  }
}
