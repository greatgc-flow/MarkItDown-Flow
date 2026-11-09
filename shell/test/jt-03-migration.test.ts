/**
 * JT-03 / REQ-SHL-03: v1 detection, allowlisted schema-2 candidate, type
 * validation, aggregated notice without raw values, unknown keys discarded,
 * newer schema read-only and blocking. Fixture FX-70.
 */
import { req } from './req';
import { formatMigrationNotice, migrateSettings, type MigrationResult, type SettingsV2 } from '../src/pure/settings';
import {
  ALL_SENTINELS,
  DROPPED_V1_KEYS,
  MAPPED_V1_KEYS,
  V1_KEYS,
  V1_PYTHON_PATH,
  v1AllKeys,
  variants,
  type V1Key,
} from './fixtures/fx70';

const R = req('REQ-SHL-03');

export const ALLOWLISTED_KEYS = [
  'schemaVersion',
  'enginePython',
  'bootstrapPythonHint',
  'outputPath',
  'enableBatchProgress',
  'enableContextMenu',
  'enableRecursiveConversion',
  'enableDragDrop',
  'enableLegacyPreconvert',
  'conversionHistory',
  'locale',
  'provider',
  'runOptions',
].sort();

export const DEFAULTS: SettingsV2 = {
  schemaVersion: 2,
  enginePython: null,
  outputPath: 'markitdown-output',
  enableBatchProgress: true,
  enableContextMenu: true,
  enableRecursiveConversion: true,
  enableDragDrop: false,
  enableLegacyPreconvert: false,
  conversionHistory: [],
  locale: 'auto',
  provider: { name: 'none', model: '', baseUrl: 'https://api.openai.com/v1' },
  runOptions: { dpi: 200, minPriority: 'low', maxUnits: 200, approveThreshold: 20, sensitive: [] },
};

export function sentinelsIn(value: unknown): string[] {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  return ALL_SENTINELS.filter((s) => text.includes(s));
}

function settingsOf(result: MigrationResult): SettingsV2 {
  expect(result.settings).not.toBeNull();
  return result.settings as SettingsV2;
}

const RAW_V1_VALUES = ['kor+eng', '{name}_assets', '{name}-{date}.md', 'example-docintel', 'hough', 'tag-sentinel-alpha'];

it(R('JT-03 missing schemaVersion identifies v1 and yields an allowlisted schema-2 candidate'), () => {
  const result = migrateSettings(v1AllKeys());
  expect(result.source).toBe('v1');
  expect(result.jobsBlocked).toBe(false);
  const settings = settingsOf(result);
  expect(settings.schemaVersion).toBe(2);
  expect(Object.keys(settings).sort()).toEqual(ALLOWLISTED_KEYS);
  expect(settings.enginePython).toBeNull();
  expect(settings.bootstrapPythonHint).toBe(V1_PYTHON_PATH);
  expect(sentinelsIn(result)).toEqual([]);
});

it(R('JT-03 null data is a fresh install: defaults, no notice items, jobs not blocked'), () => {
  const result = migrateSettings(null);
  expect(result.source).toBe('fresh');
  expect(result.items).toEqual([]);
  expect(result.jobsBlocked).toBe(false);
  expect(result.settings).toEqual(DEFAULTS);
});

it(R('JT-03 a valid schema-2 document validates in place without notice items'), () => {
  const v2: SettingsV2 = {
    ...DEFAULTS,
    enginePython: '/home/alice/venvs/mdflow/bin/python',
    outputPath: 'converted',
    locale: 'ko',
    provider: { name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1' },
    runOptions: { dpi: 300, minPriority: 'normal', maxUnits: 50, approveThreshold: 5, sensitive: ['*secret*'] },
  };
  const result = migrateSettings(JSON.parse(JSON.stringify(v2)));
  expect(result.source).toBe('v2');
  expect(result.items).toEqual([]);
  expect(result.jobsBlocked).toBe(false);
  expect(result.settings).toEqual(v2);
});

it.each(V1_KEYS)(R('JT-03 missing v1 key %s takes the schema-2 default and never blocks'), (key: V1Key) => {
  const result = migrateSettings(variants.missing(key));
  expect(result.source).toBe('v1');
  expect(result.jobsBlocked).toBe(false);
  const settings = settingsOf(result);
  expect(Object.keys(settings).sort()).toEqual(
    key === 'pythonPath' ? ALLOWLISTED_KEYS.filter((k) => k !== 'bootstrapPythonHint') : ALLOWLISTED_KEYS,
  );
  if (key === 'outputPath') expect(settings.outputPath).toBe(DEFAULTS.outputPath);
  if (key === 'enableDragDrop') expect(settings.enableDragDrop).toBe(false);
  if (key === 'enableBatchProgress') expect(settings.enableBatchProgress).toBe(true);
  if (key === 'enableContextMenu') expect(settings.enableContextMenu).toBe(true);
  if (key === 'enableRecursiveConversion') expect(settings.enableRecursiveConversion).toBe(true);
  if (key === 'conversionHistory') expect(settings.conversionHistory).toEqual([]);
  if (key === 'pythonPath') expect(settings.bootstrapPythonHint).toBeUndefined();
  expect(sentinelsIn(result)).toEqual([]);
});

it.each(V1_KEYS)(R('JT-03 null v1 key %s is treated as missing'), (key: V1Key) => {
  const nulled = migrateSettings(variants.nulled(key));
  const missing = migrateSettings(variants.missing(key));
  expect(nulled.jobsBlocked).toBe(false);
  expect(nulled.settings).toEqual(missing.settings);
});

it.each(MAPPED_V1_KEYS)(R('JT-03 malformed mapped key %s resets to the default with a reset item'), (key: V1Key) => {
  const result = migrateSettings(variants.malformed(key));
  expect(result.jobsBlocked).toBe(false);
  const settings = settingsOf(result);
  const fresh = migrateSettings(variants.missing(key)).settings as SettingsV2;
  expect(settings).toEqual(fresh);
  expect(result.items).toContainEqual({ key, action: 'reset', count: 1 });
});

it.each(DROPPED_V1_KEYS)(R('JT-03 malformed dropped key %s is still dropped with one item'), (key: V1Key) => {
  const result = migrateSettings(variants.malformed(key));
  expect(result.items).toContainEqual({ key, action: 'dropped', count: 1 });
  expect(JSON.stringify(result.settings)).not.toContain('"wrong"');
});

it(R('JT-03 unknown top-level keys are discarded and counted, values never surface'), () => {
  const result = migrateSettings(variants.withUnknownKeys());
  const settings = settingsOf(result);
  expect(Object.keys(settings).sort()).toEqual(ALLOWLISTED_KEYS);
  expect(result.items).toContainEqual({ key: '*unknown*', action: 'discarded', count: 2 });
  const everything = JSON.stringify(result) + formatMigrationNotice(result, 'en') + formatMigrationNotice(result, 'ko');
  expect(everything).not.toContain('UNKNOWN-VALUE');
});

it(R('JT-03 newer schema is read-only: no candidate, jobs blocked, incompatibility notice'), () => {
  const result = migrateSettings(variants.futureSchema());
  expect(result.source).toBe('newer');
  expect(result.settings).toBeNull();
  expect(result.jobsBlocked).toBe(true);
  for (const locale of ['en', 'ko'] as const) {
    const notice = formatMigrationNotice(result, locale);
    expect(notice.trim().length).toBeGreaterThan(0);
    expect(notice).not.toContain('/opt/venv/bin/python');
  }
});

it(R('JT-03 one aggregated notice lists dropped and reset preference names with counts, never raw values'), () => {
  const result = migrateSettings({ ...v1AllKeys(), outputPath: '../escape', enableDragDrop: 'yes' });
  for (const locale of ['en', 'ko'] as const) {
    const notice = formatMigrationNotice(result, locale);
    expect(typeof notice).toBe('string');
    for (const key of DROPPED_V1_KEYS) expect(notice).toContain(key);
    expect(notice).toContain('outputPath');
    expect(notice).toContain('enableDragDrop');
    expect(notice).toMatch(/\d/);
    expect(sentinelsIn(notice)).toEqual([]);
    for (const raw of RAW_V1_VALUES) expect(notice).not.toContain(raw);
    expect(notice).not.toContain('../escape');
  }
});

it(R('JT-03 no raw v1 value appears in the candidate or the items'), () => {
  const result = migrateSettings(v1AllKeys());
  const text = JSON.stringify({ settings: result.settings, items: result.items });
  for (const raw of RAW_V1_VALUES) expect(text).not.toContain(raw);
  expect(sentinelsIn(text)).toEqual([]);
  for (const item of result.items) {
    expect(Object.keys(item).sort()).toEqual(['action', 'count', 'key']);
    expect(Number.isInteger(item.count) && item.count >= 1).toBe(true);
  }
});
