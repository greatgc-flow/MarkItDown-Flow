/**
 * Settings schema 2 and the v1 -> v2 migration (20_SHELL.md REQ-SHL-03/04).
 *
 * Pure: accepts the parsed `data.json` value, returns an allowlisted candidate
 * plus structured notice items. Never returns raw v1 values in notices.
 */
import { type HistoryEntry, normalizeHistory } from './history';
import { formatMessage, type UiLocale } from './i18n';
import { isAbsolutePath } from './paths';

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
  /**
   * R33: pre-convert LEGACY formats (.doc/.ppt/.rtf/HWP<5.0) through a user-installed LibreOffice
   * (`SOFFICE_PATH`/PATH) before Core. Off by default; passed to the engine as `--legacy-preconvert`.
   */
  enableLegacyPreconvert: boolean;
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

export const UNKNOWN_KEYS_ITEM = '*unknown*';
export const DEFAULT_OUTPUT_PATH = 'markitdown-output';
export const DEFAULT_BASE_URL = 'https://api.openai.com/v1';

/** v1 keys with a v2 mapping (preserved or hinted). */
const V1_MAPPED = ['pythonPath', 'outputPath', 'enableBatchProgress', 'enableContextMenu', 'enableRecursiveConversion', 'enableDragDrop', 'conversionHistory'] as const;
/** v1 keys dropped with a notice (20_SHELL.md section 2 table). */
export const V1_DROPPED = [
  'enablePlugins', 'pluginArgs', 'docintelEndpoint', 'docintelCredential', 'llmApiKey', 'assetExtractionEnabled',
  'assetSubfolderTemplate', 'inputBasePath', 'outputFilenameTemplate', 'enableAutoFrontmatter', 'autoTags',
  'imagePipelineEnabled', 'ocrLang', 'imagePipelineAdvancedConfig',
] as const;
const V1_KEYS: ReadonlySet<string> = new Set<string>([...V1_MAPPED, ...V1_DROPPED]);

const V2_KEYS: ReadonlySet<string> = new Set<string>([
  'schemaVersion', 'enginePython', 'bootstrapPythonHint', 'outputPath', 'enableBatchProgress', 'enableContextMenu',
  'enableRecursiveConversion', 'enableDragDrop', 'enableLegacyPreconvert', 'conversionHistory', 'locale', 'provider', 'runOptions',
]);

/** The four retained v1 UI booleans (20_SHELL.md section 2 table); a v1 file is migrated with these only. */
const V1_BOOLEANS = [
  ['enableBatchProgress', true],
  ['enableContextMenu', true],
  ['enableRecursiveConversion', true],
  ['enableDragDrop', false],
] as const;

/** Every schema-2 boolean: the retained v1 four plus `enableLegacyPreconvert` (R33, off by default). */
const BOOLEANS = [...V1_BOOLEANS, ['enableLegacyPreconvert', false]] as const;

type Raw = Record<string, unknown>;

function isRecord(value: unknown): value is Raw {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

const isMissing = (v: unknown): boolean => v === undefined || v === null;

/** Fresh-install defaults (used for `null` data and for every reset field). */
export function defaultSettings(): SettingsV2 {
  return {
    schemaVersion: SCHEMA_VERSION,
    enginePython: null,
    outputPath: DEFAULT_OUTPUT_PATH,
    enableBatchProgress: true,
    enableContextMenu: true,
    enableRecursiveConversion: true,
    enableDragDrop: false,
    enableLegacyPreconvert: false,
    conversionHistory: [],
    locale: 'auto',
    provider: { name: 'none', model: '', baseUrl: DEFAULT_BASE_URL },
    runOptions: { dpi: 200, minPriority: 'low', maxUnits: 200, approveThreshold: 20, sensitive: [] },
  };
}

/** A path string usable as an interpreter hint: printable, no line breaks, bounded. */
function isPathString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 4096 && !/[\u0000-\u001f\u007f]/.test(value);
}

/** Vault-relative directory: no absolute/drive/UNC form, no `..` segment, no control characters. */
export function isSafeVaultRelativePath(value: string): boolean {
  if (value.length === 0 || value.length > 1024) return false;
  if (/[\u0000-\u001f\u007f]/.test(value)) return false;
  if (value.startsWith('/') || value.startsWith('\\')) return false;
  if (/^[A-Za-z]:/.test(value)) return false;
  if (value.includes('\\')) return false;
  if (value.split('/').some((segment) => segment === '..' || segment === '.' || segment.trim().length === 0)) return false;
  return true;
}

/**
 * Hosts for which the engine accepts plain `http` (openai_compat.canonical_destination
 * `_LOCAL_HOSTS`), spelled exactly as the raw host token must appear (lower-cased).
 */
const LOOPBACK_HOSTS: ReadonlySet<string> = new Set(['localhost', '127.0.0.1', '[::1]']);

/** The raw authority of a URL text as `urllib.parse.urlsplit` sees it: between `scheme://` and the first `/`, `?` or `#`. */
function rawAuthority(value: string): string | null {
  const match = /^[A-Za-z][A-Za-z0-9+.-]*:\/\/([^/?#]*)/.exec(value);
  return match ? match[1] : null;
}

/** The literal host token of a raw authority without its port (`[::1]:8080` -> `[::1]`, `Host:8080` -> `Host`). */
function rawHost(authority: string): string {
  if (authority.startsWith('[')) {
    const end = authority.indexOf(']');
    return end < 0 ? authority : authority.slice(0, end + 1);
  }
  const colon = authority.lastIndexOf(':');
  return colon < 0 ? authority : authority.slice(0, colon);
}

/**
 * The engine's Base URL rule, applied before persisting (M3 N-07): `https`, or
 * `http` for loopback hosts only; no credentials, query or fragment. A value the
 * engine would refuse at startup (`E_PROVIDER_CONFIG`) is never saved.
 *
 * The engine (`canonical_destination`) checks the raw text, not a WHATWG-normalised
 * URL: any `@` in the authority is refused (an empty userinfo included) and the
 * loopback rule compares the literal host token, so `127.1`, `2130706433`,
 * `0x7f000001` or `127.0.0.1.` are refused here as well instead of failing only
 * at job time (M4 P-06 / M4-V03).
 */
export function isAcceptableBaseUrl(value: string): boolean {
  if (value.trim() !== value || value.length === 0 || /[\u0000- \u007f]/.test(value)) return false;
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    return false;
  }
  if (url.username || url.password || url.search || url.hash || value.includes('?') || value.includes('#')) return false;
  if (url.hostname.length === 0) return false;
  const authority = rawAuthority(value);
  if (authority === null || authority.includes('@')) return false;
  if (url.protocol === 'https:') return true;
  return url.protocol === 'http:' && LOOPBACK_HOSTS.has(rawHost(authority).toLowerCase());
}

function isHttpUrl(value: unknown): value is string {
  return typeof value === 'string' && isAcceptableBaseUrl(value);
}

class ItemCollector {
  readonly items: MigrationItem[] = [];

  add(key: string, action: MigrationAction, count = 1): void {
    const existing = this.items.find((i) => i.key === key && i.action === action);
    if (existing) existing.count += count;
    else this.items.push({ key, action, count });
  }
}

function pickOutputPath(value: unknown, items: ItemCollector): string {
  if (isMissing(value)) return DEFAULT_OUTPUT_PATH;
  if (typeof value === 'string') {
    if (value === '') return DEFAULT_OUTPUT_PATH;
    if (isSafeVaultRelativePath(value)) return value;
  }
  items.add('outputPath', 'reset');
  return DEFAULT_OUTPUT_PATH;
}

function pickBoolean(raw: Raw, key: (typeof BOOLEANS)[number][0], fallback: boolean, items: ItemCollector): boolean {
  const value = raw[key];
  if (isMissing(value)) return fallback;
  if (typeof value === 'boolean') return value;
  items.add(key, 'reset');
  return fallback;
}

function pickHistory(value: unknown, items: ItemCollector): HistoryEntry[] {
  if (isMissing(value)) return [];
  if (!Array.isArray(value)) {
    items.add('conversionHistory', 'reset');
    return [];
  }
  const { entries, skipped } = normalizeHistory(value);
  if (skipped > 0) items.add('conversionHistory', 'skipped', skipped);
  return entries;
}

function pickProvider(value: unknown, items: ItemCollector): ProviderSettings {
  const fallback = defaultSettings().provider;
  if (isMissing(value)) return fallback;
  if (!isRecord(value) || (value.name !== 'none' && value.name !== 'openai-compatible')) {
    items.add('provider', 'reset');
    return fallback;
  }
  let invalid = false;
  let model = '';
  if (typeof value.model === 'string') model = value.model;
  else if (!isMissing(value.model)) invalid = true;
  let baseUrl = DEFAULT_BASE_URL;
  if (isHttpUrl(value.baseUrl)) baseUrl = value.baseUrl;
  else if (!isMissing(value.baseUrl)) invalid = true;
  if (invalid) items.add('provider', 'reset');
  // Allowlisted fields only: any key-like extra field is never retained.
  return { name: value.name, model, baseUrl };
}

function pickRunOptions(value: unknown, items: ItemCollector): RunOptions {
  const fallback = defaultSettings().runOptions;
  if (isMissing(value)) return fallback;
  if (!isRecord(value)) {
    items.add('runOptions', 'reset');
    return fallback;
  }
  let invalid = false;
  const out: RunOptions = { ...fallback, sensitive: [] };
  if (value.dpi === 200 || value.dpi === 300) out.dpi = value.dpi;
  else if (!isMissing(value.dpi)) invalid = true;
  if (value.minPriority === 'low' || value.minPriority === 'normal') out.minPriority = value.minPriority;
  else if (!isMissing(value.minPriority)) invalid = true;
  if (typeof value.maxUnits === 'number' && Number.isInteger(value.maxUnits) && value.maxUnits >= 1) out.maxUnits = value.maxUnits;
  else if (!isMissing(value.maxUnits)) invalid = true;
  if (typeof value.approveThreshold === 'number' && Number.isInteger(value.approveThreshold) && value.approveThreshold >= 0) out.approveThreshold = value.approveThreshold;
  else if (!isMissing(value.approveThreshold)) invalid = true;
  if (Array.isArray(value.sensitive) && value.sensitive.every((g) => typeof g === 'string' && g.length > 0)) out.sensitive = [...(value.sensitive as string[])];
  else if (!isMissing(value.sensitive)) invalid = true;
  if (invalid) items.add('runOptions', 'reset');
  return out;
}

function countUnknownKeys(raw: Raw, allowed: ReadonlySet<string>, items: ItemCollector): void {
  const unknown = Object.keys(raw).filter((k) => !allowed.has(k));
  if (unknown.length > 0) items.add(UNKNOWN_KEYS_ITEM, 'discarded', unknown.length);
}

function migrateV1(raw: Raw): MigrationResult {
  const items = new ItemCollector();
  const settings = defaultSettings();
  // pythonPath -> hint only; never an interpreter to execute.
  if (!isMissing(raw.pythonPath)) {
    if (isPathString(raw.pythonPath)) {
      settings.bootstrapPythonHint = raw.pythonPath;
      items.add('pythonPath', 'hint');
    } else {
      items.add('pythonPath', 'reset');
    }
  }
  for (const key of V1_DROPPED) {
    if (!isMissing(raw[key])) items.add(key, 'dropped');
  }
  settings.outputPath = pickOutputPath(raw.outputPath, items);
  for (const [key, fallback] of V1_BOOLEANS) settings[key] = pickBoolean(raw, key, fallback, items);
  settings.conversionHistory = pickHistory(raw.conversionHistory, items);
  countUnknownKeys(raw, new Set<string>([...V1_KEYS, 'schemaVersion']), items);
  return { source: 'v1', settings, items: items.items, jobsBlocked: false };
}

function validateV2(raw: Raw): MigrationResult {
  const items = new ItemCollector();
  const settings = defaultSettings();
  // REQ-SHL-04: only an absolute interpreter is ever executed. A relative value from a hand-edited or synced
  // data.json is reset exactly like the settings tab refuses it; the notice item never carries the value (M4 P-04).
  if (typeof raw.enginePython === 'string' && isPathString(raw.enginePython) && isAbsolutePath(raw.enginePython)) settings.enginePython = raw.enginePython;
  else if (!isMissing(raw.enginePython)) items.add('enginePython', 'reset');
  if (isPathString(raw.bootstrapPythonHint)) settings.bootstrapPythonHint = raw.bootstrapPythonHint;
  else if (!isMissing(raw.bootstrapPythonHint)) items.add('bootstrapPythonHint', 'reset');
  settings.outputPath = pickOutputPath(raw.outputPath, items);
  for (const [key, fallback] of BOOLEANS) settings[key] = pickBoolean(raw, key, fallback, items);
  settings.conversionHistory = pickHistory(raw.conversionHistory, items);
  if (raw.locale === 'auto' || raw.locale === 'en' || raw.locale === 'ko') settings.locale = raw.locale;
  else if (!isMissing(raw.locale)) items.add('locale', 'reset');
  settings.provider = pickProvider(raw.provider, items);
  settings.runOptions = pickRunOptions(raw.runOptions, items);
  countUnknownKeys(raw, V2_KEYS, items);
  return { source: 'v2', settings, items: items.items, jobsBlocked: false };
}

/** Missing `schemaVersion` identifies v1; 2 validates in place; newer blocks. */
export function migrateSettings(raw: unknown): MigrationResult {
  if (raw === null || raw === undefined) {
    return { source: 'fresh', settings: defaultSettings(), items: [], jobsBlocked: false };
  }
  if (!isRecord(raw)) return migrateV1({});
  const version = raw.schemaVersion;
  if (typeof version === 'number' && version > SCHEMA_VERSION) {
    return { source: 'newer', settings: null, items: [], jobsBlocked: true };
  }
  if (version === SCHEMA_VERSION) return validateV2(raw);
  return migrateV1(raw);
}

/** One aggregated, localized notice listing keys and counts, never raw values. */
export function formatMigrationNotice(result: MigrationResult, locale: UiLocale): string {
  if (result.source === 'newer') return formatMessage(locale, 'shell.migration.incompatible');
  if (result.items.length === 0) return '';
  const lines: string[] = [formatMessage(locale, 'shell.migration.header', { count: String(result.items.length) })];
  for (const item of result.items) {
    const count = String(item.count);
    if (item.key === UNKNOWN_KEYS_ITEM) {
      lines.push(formatMessage(locale, 'shell.migration.unknownKeys', { count }));
      continue;
    }
    const actionText = formatMessage(locale, `shell.migration.action.${item.action}`, { key: item.key, count });
    const explanationKey = `shell.migration.key.${item.key}`;
    const explanation = item.action === 'dropped' || item.action === 'hint' ? formatMessage(locale, explanationKey) : '';
    lines.push(explanation ? `- ${actionText} ${explanation}` : `- ${actionText}`);
  }
  return lines.join('\n');
}
