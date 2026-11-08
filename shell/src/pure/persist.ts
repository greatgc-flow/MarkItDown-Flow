/**
 * Atomic migration persistence and the sanitized rollback snapshot
 * (20_SHELL.md REQ-SHL-05). IO is injected through `SettingsStore`.
 */
import type { MigrationResult } from './settings';
import { NotImplementedError } from './errors';

export type StoreFile = 'data.json' | 'data.v1.json';

/** Minimal plugin-data store; the Obsidian adapter implements it in step 10. */
export interface SettingsStore {
  /** Raw text or null when the file does not exist. */
  read(name: StoreFile): Promise<string | null>;
  /** Atomic whole-file replace; rejects on denial. */
  write(name: StoreFile, text: string): Promise<void>;
  /** Names of files currently present in the plugin data folder. */
  list(): Promise<string[]>;
}

export const LEGACY_HISTORY_ERROR = 'Legacy conversion failed.';

/** v1 keys allowed into `data.v1.json`; everything else is omitted. */
export type SnapshotKey =
  | 'pythonPath'
  | 'outputPath'
  | 'enableBatchProgress'
  | 'enableContextMenu'
  | 'enableRecursiveConversion'
  | 'enableDragDrop'
  | 'conversionHistory';

export interface PersistOutcome {
  ok: boolean;
  jobsBlocked: boolean;
  /** Null on failure: raw settings and credential references are dropped from memory. */
  result: MigrationResult | null;
  /** Shell diagnostic keys to display (`shell.SETTINGS` on failure). */
  noticeKeys: string[];
  /** True only after the schema-2 write actually succeeded. */
  diskSanitized: boolean;
  /** True when the original file may still contain v1 keys/credentials. */
  unsanitizedDiskWarning: boolean;
  /** Files written during this call, in order. */
  writes: StoreFile[];
}

/** Allowlisted, credential-scrubbed v1 snapshot (pure). */
export function buildSnapshot(_raw: unknown): Record<string, unknown> {
  throw new NotImplementedError('buildSnapshot');
}

/**
 * Read `data.json`, migrate, write `data.v1.json` once, then `data.json`.
 * Idempotent on schema 2; never writes a recovery placeholder.
 */
export async function persistMigration(_store: SettingsStore): Promise<PersistOutcome> {
  throw new NotImplementedError('persistMigration');
}
