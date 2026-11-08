/**
 * Atomic migration persistence and the sanitized rollback snapshot
 * (20_SHELL.md REQ-SHL-05). IO is injected through `SettingsStore`.
 */
import { redactValue } from './redact';
import { migrateSettings, type MigrationResult } from './settings';

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

const SNAPSHOT_BOOLEANS: readonly SnapshotKey[] = ['enableBatchProgress', 'enableContextMenu', 'enableRecursiveConversion', 'enableDragDrop'];
const SNAPSHOT_HISTORY_FIELDS = ['inputFile', 'outputFile', 'timestamp', 'success', 'processingTimeMs', 'assetsExtracted'] as const;
/** v1 fields whose values are credentials; collected only to scrub retained strings. */
const CREDENTIAL_KEYS = ['docintelCredential', 'llmApiKey'] as const;

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

type Raw = Record<string, unknown>;

function isRecord(value: unknown): value is Raw {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isScalar(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean';
}

/** Allowlisted, credential-scrubbed v1 snapshot (pure). */
export function buildSnapshot(raw: unknown): Record<string, unknown> {
  if (!isRecord(raw)) return {};
  const snapshot: Record<string, unknown> = {};
  if (typeof raw.pythonPath === 'string') snapshot.pythonPath = raw.pythonPath;
  if (typeof raw.outputPath === 'string') snapshot.outputPath = raw.outputPath;
  for (const key of SNAPSHOT_BOOLEANS) {
    if (typeof raw[key] === 'boolean') snapshot[key] = raw[key];
  }
  if (Array.isArray(raw.conversionHistory)) {
    snapshot.conversionHistory = raw.conversionHistory.filter(isRecord).map((entry) => {
      const safe: Record<string, unknown> = {};
      for (const field of SNAPSHOT_HISTORY_FIELDS) {
        if (isScalar(entry[field])) safe[field] = entry[field];
      }
      // Legacy error text can embed secrets; keep only the fact that it failed.
      if (entry.error !== undefined && entry.error !== null) safe.error = LEGACY_HISTORY_ERROR;
      return safe;
    });
  }
  const secrets = CREDENTIAL_KEYS.map((k) => raw[k]).filter((v): v is string => typeof v === 'string' && v.length > 0);
  return redactValue(snapshot, { secrets });
}

function serialize(value: unknown): string {
  return JSON.stringify(value, null, 2) + '\n';
}

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((v, i) => deepEqual(v, b[i]));
  if (isRecord(a) && isRecord(b)) {
    const ka = Object.keys(a).filter((k) => a[k] !== undefined);
    const kb = Object.keys(b).filter((k) => b[k] !== undefined);
    return ka.length === kb.length && ka.every((k) => deepEqual(a[k], b[k]));
  }
  return false;
}

function failure(writes: StoreFile[]): PersistOutcome {
  return {
    ok: false,
    jobsBlocked: true,
    result: null,
    noticeKeys: ['shell.SETTINGS'],
    diskSanitized: false,
    unsanitizedDiskWarning: true,
    writes,
  };
}

/**
 * Read `data.json`, migrate, write `data.v1.json` once, then `data.json`.
 * Idempotent on schema 2; never writes a recovery placeholder.
 */
export async function persistMigration(store: SettingsStore): Promise<PersistOutcome> {
  const text = await store.read('data.json');
  let raw: unknown = null;
  if (text !== null) {
    try {
      raw = JSON.parse(text);
    } catch {
      // Unparseable disk state: never overwrite it; the user must repair or remove it.
      return failure([]);
    }
  }
  const result = migrateSettings(raw);
  const writes: StoreFile[] = [];
  if (result.source === 'newer' || result.settings === null) {
    return { ok: false, jobsBlocked: true, result, noticeKeys: ['shell.SETTINGS'], diskSanitized: false, unsanitizedDiskWarning: false, writes };
  }
  try {
    if (result.source === 'v1') {
      const files = await store.list();
      if (!files.includes('data.v1.json')) {
        await store.write('data.v1.json', serialize(buildSnapshot(raw)));
        writes.push('data.v1.json');
      }
      await store.write('data.json', serialize(result.settings));
      writes.push('data.json');
    } else if (result.source === 'fresh' || result.items.length > 0 || !deepEqual(raw, result.settings)) {
      await store.write('data.json', serialize(result.settings));
      writes.push('data.json');
    }
  } catch {
    return failure(writes);
  }
  return { ok: true, jobsBlocked: false, result, noticeKeys: [], diskSanitized: true, unsanitizedDiskWarning: false, writes };
}
