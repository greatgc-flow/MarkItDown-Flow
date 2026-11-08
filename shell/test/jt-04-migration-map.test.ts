/**
 * JT-04 / REQ-SHL-04: every row of the 21-key map, nested advanced defaults
 * dropped, exact allowlisted result, provider/bounds validation, argv shows
 * no template/tag/media-toggle effects. Fixture FX-70.
 */
import { req } from './req';
import { migrateSettings, type SettingsV2 } from '../src/pure/settings';
import { engineArgv } from '../src/pure/argv';
import {
  ALL_SENTINELS,
  DROPPED_V1_KEYS,
  NESTED_ADVANCED_KEYS,
  SENTINELS,
  T0,
  V1_PYTHON_PATH,
  v1AllKeys,
} from './fixtures/fx70';

const R = req('REQ-SHL-04');

const DEFAULT_PROVIDER = { name: 'none', model: '', baseUrl: 'https://api.openai.com/v1' } as const;
const DEFAULT_RUN_OPTIONS = { dpi: 200, minPriority: 'low', maxUnits: 200, approveThreshold: 20, sensitive: [] } as const;

/** The exact expected result for the all-21-keys fixture (hand-derived from the table). */
const EXPECTED_ALL_KEYS: SettingsV2 = {
  schemaVersion: 2,
  enginePython: null,
  bootstrapPythonHint: V1_PYTHON_PATH,
  outputPath: 'notes/converted',
  enableBatchProgress: false,
  enableContextMenu: true,
  enableRecursiveConversion: false,
  enableDragDrop: true,
  conversionHistory: [
    {
      inputFile: 'inbox/report.pdf',
      outputFile: 'notes/converted/report.pdf.md',
      timestamp: T0 + 2_000,
      success: true,
      processingTimeMs: 1234,
      assetsExtracted: 2,
    },
    {
      inputFile: 'inbox/보고서 3분기.docx',
      outputFile: 'notes/converted/보고서 3분기.docx.md',
      timestamp: T0 + 1_000,
      success: false,
    },
  ],
  locale: 'auto',
  provider: { ...DEFAULT_PROVIDER },
  runOptions: { ...DEFAULT_RUN_OPTIONS, sensitive: [] },
};

function settings(raw: unknown): SettingsV2 {
  const result = migrateSettings(raw);
  expect(result.settings).not.toBeNull();
  return result.settings as SettingsV2;
}

it(R('JT-04 all 21 keys with nested advanced defaults yield the exact allowlisted result'), () => {
  const result = migrateSettings(v1AllKeys());
  expect(result.settings).toEqual(EXPECTED_ALL_KEYS);
  expect(result.items).toContainEqual({ key: 'conversionHistory', action: 'skipped', count: 1 });
  expect(result.items).toContainEqual({ key: 'pythonPath', action: 'hint', count: 1 });
});

it(R('JT-04 every dropped row produces exactly one dropped item'), () => {
  const result = migrateSettings(v1AllKeys());
  for (const key of DROPPED_V1_KEYS) {
    const items = result.items.filter((i) => i.key === key);
    expect(items).toEqual([{ key, action: 'dropped', count: 1 }]);
  }
});

it(R('JT-04 credentials are dropped from the candidate and from every notice item; provider stays none'), () => {
  const result = migrateSettings(v1AllKeys());
  const text = JSON.stringify(result);
  expect(text).not.toContain(SENTINELS.docintelCredential);
  expect(text).not.toContain(SENTINELS.llmApiKey);
  expect(result.settings?.provider).toEqual(DEFAULT_PROVIDER);
  expect(result.items).toContainEqual({ key: 'docintelCredential', action: 'dropped', count: 1 });
  expect(result.items).toContainEqual({ key: 'llmApiKey', action: 'dropped', count: 1 });
});

it(R('JT-04 docintelEndpoint is never reinterpreted as a provider base URL'), () => {
  const s = settings(v1AllKeys());
  expect(s.provider.baseUrl).toBe(DEFAULT_PROVIDER.baseUrl);
  expect(JSON.stringify(s)).not.toContain('example-docintel');
});

it(R('JT-04 the whole imagePipelineAdvancedConfig object including unknown nested keys is dropped'), () => {
  const result = migrateSettings(v1AllKeys());
  const text = JSON.stringify(result);
  for (const nested of NESTED_ADVANCED_KEYS) expect(text).not.toContain(nested);
  expect(text).not.toContain('unknown_future_tuning');
  expect(text).not.toContain(SENTINELS.advancedConfigSecret);
});

it(R('JT-04 pluginArgs array and nested values are dropped entirely'), () => {
  const text = JSON.stringify(migrateSettings(v1AllKeys()));
  expect(text).not.toContain('--legacy-flag');
  expect(text).not.toContain(SENTINELS.pluginArgToken);
});

it(R('JT-04 pythonPath becomes bootstrapPythonHint only; enginePython is never set from it'), () => {
  const valid = settings(v1AllKeys());
  expect(valid.bootstrapPythonHint).toBe(V1_PYTHON_PATH);
  expect(valid.enginePython).toBeNull();
  const invalid = settings({ ...v1AllKeys(), pythonPath: 42 });
  expect(invalid.bootstrapPythonHint).toBeUndefined();
  expect(invalid.enginePython).toBeNull();
  const newline = settings({ ...v1AllKeys(), pythonPath: 'python\n--evil' });
  expect(newline.bootstrapPythonHint).toBeUndefined();
});

it(R('JT-04 outputPath: valid vault-relative kept, empty defaults, unsafe values default with a reset item'), () => {
  expect(settings({ ...v1AllKeys(), outputPath: 'notes/converted' }).outputPath).toBe('notes/converted');
  expect(settings({ ...v1AllKeys(), outputPath: '' }).outputPath).toBe('markitdown-output');
  for (const unsafe of ['../outside', '/abs/path', 'C:\\vault\\out', 'notes/../../x', 'a\u0000b']) {
    const result = migrateSettings({ ...v1AllKeys(), outputPath: unsafe });
    expect(result.settings?.outputPath).toBe('markitdown-output');
    expect(result.items).toContainEqual({ key: 'outputPath', action: 'reset', count: 1 });
    if (!unsafe.includes('\u0000')) expect(JSON.stringify(result)).not.toContain(unsafe);
  }
});

it(R('JT-04 the four UI booleans are preserved, non-booleans reset to defaults true/true/true/false'), () => {
  const kept = settings(v1AllKeys());
  expect([kept.enableBatchProgress, kept.enableContextMenu, kept.enableRecursiveConversion, kept.enableDragDrop]).toEqual([
    false, true, false, true,
  ]);
  const bad = migrateSettings({
    ...v1AllKeys(),
    enableBatchProgress: 'yes',
    enableContextMenu: 1,
    enableRecursiveConversion: 'false',
    enableDragDrop: {},
  });
  const s = bad.settings as SettingsV2;
  expect([s.enableBatchProgress, s.enableContextMenu, s.enableRecursiveConversion, s.enableDragDrop]).toEqual([
    true, true, true, false,
  ]);
  for (const key of ['enableBatchProgress', 'enableContextMenu', 'enableRecursiveConversion', 'enableDragDrop']) {
    expect(bad.items).toContainEqual({ key, action: 'reset', count: 1 });
  }
});

it(R('JT-04 schema-2 persisted keys are exactly the allowlist; trust/approval/consent are never migrated'), () => {
  const result = migrateSettings({
    schemaVersion: 2,
    enginePython: null,
    outputPath: 'out',
    enableBatchProgress: true,
    enableContextMenu: true,
    enableRecursiveConversion: true,
    enableDragDrop: false,
    conversionHistory: [],
    locale: 'en',
    provider: { ...DEFAULT_PROVIDER },
    runOptions: { ...DEFAULT_RUN_OPTIONS, sensitive: [] },
    trustedCommands: ['rm -rf'],
    approvedHashes: ['f'.repeat(64)],
    consent: { completed: true },
    commandTemplate: 'ocr {input}',
  });
  const s = result.settings as SettingsV2;
  expect(Object.keys(s).sort()).toEqual(
    ['schemaVersion', 'enginePython', 'outputPath', 'enableBatchProgress', 'enableContextMenu',
      'enableRecursiveConversion', 'enableDragDrop', 'conversionHistory', 'locale', 'provider', 'runOptions'].sort(),
  );
  const text = JSON.stringify(result);
  for (const gone of ['trustedCommands', 'approvedHashes', 'consent', 'commandTemplate', 'rm -rf']) {
    expect(text).not.toContain(gone);
  }
  expect(result.items).toContainEqual({ key: '*unknown*', action: 'discarded', count: 4 });
});

it(R('JT-04 unsupported persisted provider choices reset to none with a notice item'), () => {
  for (const name of ['command', 'azure-docintel', 'anthropic', '', 42]) {
    const result = migrateSettings({
      schemaVersion: 2,
      provider: { name, model: 'x', baseUrl: 'https://api.openai.com/v1' },
    });
    expect(result.settings?.provider).toEqual(DEFAULT_PROVIDER);
    expect(result.items).toContainEqual({ key: 'provider', action: 'reset', count: 1 });
  }
  const ok = settings({ schemaVersion: 2, provider: { name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1' } });
  expect(ok.provider).toEqual({ name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1' });
});

it(R('JT-04 provider object never retains secret-looking fields'), () => {
  const result = migrateSettings({
    schemaVersion: 2,
    provider: { name: 'openai-compatible', model: 'm', baseUrl: 'https://api.openai.com/v1', apiKey: SENTINELS.llmApiKey },
  });
  expect(Object.keys(result.settings?.provider ?? {}).sort()).toEqual(['baseUrl', 'model', 'name']);
  expect(JSON.stringify(result)).not.toContain(SENTINELS.llmApiKey);
});

it(R('JT-04 runOptions and locale use SPEC 10.2 validation; invalid values reset to defaults'), () => {
  const result = migrateSettings({
    schemaVersion: 2,
    locale: 'fr',
    runOptions: { dpi: 150, minPriority: 'high', maxUnits: -5, approveThreshold: 'x', sensitive: 'notarray' },
  });
  const s = result.settings as SettingsV2;
  expect(s.locale).toBe('auto');
  expect(s.runOptions).toEqual(DEFAULT_RUN_OPTIONS);
  expect(result.items).toContainEqual({ key: 'locale', action: 'reset', count: 1 });
  expect(result.items.some((i) => i.key === 'runOptions' && i.action === 'reset')).toBe(true);
  const valid = settings({ schemaVersion: 2, locale: 'ko', runOptions: { dpi: 300, minPriority: 'normal', maxUnits: 1, approveThreshold: 0, sensitive: ['*.pdf'] } });
  expect(valid.locale).toBe('ko');
  expect(valid.runOptions).toEqual({ dpi: 300, minPriority: 'normal', maxUnits: 1, approveThreshold: 0, sensitive: ['*.pdf'] });
});

const SPEC_10_2_SHELL_OPTIONS = new Set([
  '-o', '--out', '--provider', '--model', '--dpi', '--prompt-version', '--yes', '--yes-file', '--approved-by',
  '--approve-threshold', '--sensitive', '--min-priority', '--max-units', '--max-bytes', '--max-pixels',
  '--zip-depth', '--zip-entries', '--zip-total-bytes', '--force', '--cache', '--progress', '--report', '--cost-hint',
]);

it(R('JT-04 argv snapshot contains no template, tag, media-toggle or OCR-language flags and only SPEC 10.2 options'), () => {
  const s = settings(v1AllKeys());
  const argv = engineArgv(s, {
    command: 'run',
    inputs: ['D:\\vault\\inbox\\보고서 3분기.pdf', '/home/a/dir with spaces/x$(rm).docx'],
    outDir: 'D:\\vault\\notes\\converted',
    cacheDir: 'D:\\vault\\.obsidian\\plugins\\markitdown-flow\\cache',
  });
  expect(argv.slice(0, 3)).toEqual(['-m', 'mdflow', 'run']);
  expect(argv).toContain('D:\\vault\\inbox\\보고서 3분기.pdf');
  expect(argv).toContain('/home/a/dir with spaces/x$(rm).docx');
  for (const token of argv.filter((t) => t.startsWith('-'))) {
    expect(SPEC_10_2_SHELL_OPTIONS.has(token)).toBe(true);
  }
  const joined = argv.join('\u0000');
  // Option tokens only: input/output/cache paths may legitimately contain these words.
  const optionTokens = argv.filter((t) => t.startsWith('-')).join('\u0000').toLowerCase();
  for (const forbidden of ['template', 'tag', 'asset', 'frontmatter', 'ocr-lang', 'command', 'trust', 'plugin', 'mirror']) {
    expect(optionTokens).not.toContain(forbidden);
  }
  for (const rawValue of ['kor+eng', 'tag-sentinel-alpha', '{name}_assets', '{name}-{date}.md']) {
    expect(joined).not.toContain(rawValue);
  }
  expect(argv[argv.indexOf('--provider') + 1]).toBe('none');
  expect(argv).not.toContain('--model');
  for (const sentinel of ALL_SENTINELS) expect(joined).not.toContain(sentinel);
});
