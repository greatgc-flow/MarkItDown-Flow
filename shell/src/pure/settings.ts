/**
 * Settings schema 2 and the v1 -> v2 migration (20_SHELL.md REQ-SHL-03/04).
 *
 * Pure: accepts the parsed `data.json` value, returns an allowlisted candidate
 * plus structured notice items. Never returns raw v1 values in notices.
 */
import type { HistoryEntry } from './history';
import { NotImplementedError } from './errors';

export const SCHEMA_VERSION = 2 as const;

export type Locale = 'auto' | 'en' | 'ko';
export type ProviderName = 'none' | 'openai-compatible';
export type Dpi = 200 | 300;
export type MinPriority = 'low' | 'normal';

export interface ProviderSettings {
  name: ProviderName;
  model: string;
  baseUrl: string;
}

/** Nonsecret run options; bounds follow SPEC section 10.2. */
export interface RunOptions {
  dpi: Dpi;
  minPriority: MinPriority;
  maxUnits: number;
  approveThreshold: number;
  sensitive: string[];
}

/** The complete persisted schema-2 shape. No other key is ever persisted. */
export interface SettingsV2 {
  schemaVersion: typeof SCHEMA_VERSION;
  /** Absolute venv interpreter chosen by the user; null until configured. */
  enginePython: string | null;
  /** Prefill for terminal instructions only; never executed. */
  bootstrapPythonHint?: string;
  outputPath: string;
  enableBatchProgress: boolean;
  enableContextMenu: boolean;
  enableRecursiveConversion: boolean;
  enableDragDrop: boolean;
  conversionHistory: HistoryEntry[];
  locale: Locale;
  provider: ProviderSettings;
  runOptions: RunOptions;
}

export type MigrationAction =
  /** Preference removed in v2; notice explains the replacement. */
  | 'dropped'
  /** Present but invalid/unsafe; replaced by the default. */
  | 'reset'
  /** `pythonPath` carried into `bootstrapPythonHint` only. */
  | 'hint'
  /** Invalid history entries discarded (count). */
  | 'skipped'
  /** Unknown top-level keys discarded (count). */
  | 'discarded';

export interface MigrationItem {
  /** v1 key name, schema-2 key name, or `*unknown*` for discarded unknown keys. */
  key: string;
  action: MigrationAction;
  count: number;
}

export type MigrationSource = 'fresh' | 'v1' | 'v2' | 'newer';

export interface MigrationResult {
  source: MigrationSource;
  /** Null only when the persisted schema is newer than SCHEMA_VERSION. */
  settings: SettingsV2 | null;
  items: MigrationItem[];
  /** True when jobs must not start (newer schema). Persistence failure is REQ-SHL-05. */
  jobsBlocked: boolean;
}

/** Fresh-install defaults (used for `null` data and for every reset field). */
export function defaultSettings(): SettingsV2 {
  throw new NotImplementedError('defaultSettings');
}

/** Missing `schemaVersion` identifies v1; 2 validates in place; newer blocks. */
export function migrateSettings(_raw: unknown): MigrationResult {
  throw new NotImplementedError('migrateSettings');
}

/** One aggregated, localized notice listing keys and counts, never raw values. */
export function formatMigrationNotice(_result: MigrationResult, _locale: 'en' | 'ko'): string {
  throw new NotImplementedError('formatMigrationNotice');
}
