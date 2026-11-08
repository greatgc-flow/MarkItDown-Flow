/**
 * FX-70 v1_settings (30_TESTPLAN.md section 3): deterministic generator, no IO.
 *
 * Clean-room: shapes are taken from the 21-key table in 20_SHELL.md section 2,
 * not from v1 code. Values are invented; credential sentinels are unique strings
 * that must never appear in any v2 artifact.
 */

export const SENTINELS = {
  docintelCredential: 'SENTINEL-DOCINTEL-CRED-7f3a9c1e',
  llmApiKey: 'sk-SENTINEL-LLM-KEY-9c2e4b7d',
  pluginArgToken: 'SENTINEL-PLUGIN-ARG-TOKEN-51d0',
  advancedConfigSecret: 'SENTINEL-ADV-CFG-SECRET-e88b',
  historyErrorKey: 'SENTINEL-HISTORY-ERR-KEY-0a42',
} as const;

export const ALL_SENTINELS: readonly string[] = Object.values(SENTINELS);

/** The 21 v1 top-level keys, in table order. */
export const V1_KEYS = [
  'pythonPath',
  'enablePlugins',
  'pluginArgs',
  'docintelEndpoint',
  'docintelCredential',
  'llmApiKey',
  'outputPath',
  'assetExtractionEnabled',
  'assetSubfolderTemplate',
  'inputBasePath',
  'enableBatchProgress',
  'enableContextMenu',
  'enableRecursiveConversion',
  'outputFilenameTemplate',
  'enableDragDrop',
  'enableAutoFrontmatter',
  'autoTags',
  'conversionHistory',
  'imagePipelineEnabled',
  'ocrLang',
  'imagePipelineAdvancedConfig',
] as const;

export type V1Key = (typeof V1_KEYS)[number];

/** Keys that have a v2 mapping (preserved or hinted); everything else is dropped. */
export const MAPPED_V1_KEYS: readonly V1Key[] = [
  'pythonPath',
  'outputPath',
  'enableBatchProgress',
  'enableContextMenu',
  'enableRecursiveConversion',
  'enableDragDrop',
  'conversionHistory',
];

export const DROPPED_V1_KEYS: readonly V1Key[] = V1_KEYS.filter((k) => !MAPPED_V1_KEYS.includes(k));

/** Nested advanced defaults that REQ-SHL-04 names explicitly. */
export const NESTED_ADVANCED_KEYS = [
  'ocr_engines',
  'ocr_confidence_threshold',
  'enable_ocr_ensemble',
  'enable_table_extraction',
  'preprocess_deskew',
  'deskew_method',
  'confidence_weight_engine_conf',
  'confidence_weight_agreement',
  'confidence_weight_length',
  'confidence_weight_cleanliness',
  'confidence_weight_stdev_inv',
] as const;

export const V1_PYTHON_PATH = 'C:\\Users\\alice\\venvs\\old\\Scripts\\python.exe';

/** Epoch ms base for deterministic history timestamps (2026-11-09T00:00:00Z). */
export const T0 = Date.UTC(2026, 10, 9);

export interface V1HistoryEntryLike {
  [k: string]: unknown;
}

/** Three v1 history entries: valid, valid-with-secret-error, invalid (missing inputFile). */
export function v1History(): V1HistoryEntryLike[] {
  return [
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
      timestamp: new Date(T0 + 1_000).toISOString(),
      success: false,
      error: `Auth failed with key ${SENTINELS.historyErrorKey}`,
      extraneous: { nested: true },
    },
    {
      outputFile: 'notes/converted/orphan.md',
      timestamp: T0,
      success: true,
    },
  ];
}

/** All 21 keys with plausible values plus every nested advanced default. */
export function v1AllKeys(): Record<string, unknown> {
  return {
    pythonPath: V1_PYTHON_PATH,
    enablePlugins: true,
    pluginArgs: ['--legacy-flag', { token: SENTINELS.pluginArgToken }, ['nested', 1]],
    docintelEndpoint: 'https://example-docintel.cognitiveservices.azure.com/',
    docintelCredential: SENTINELS.docintelCredential,
    llmApiKey: SENTINELS.llmApiKey,
    outputPath: 'notes/converted',
    assetExtractionEnabled: true,
    assetSubfolderTemplate: '{name}_assets',
    inputBasePath: 'inbox',
    enableBatchProgress: false,
    enableContextMenu: true,
    enableRecursiveConversion: false,
    outputFilenameTemplate: '{name}-{date}.md',
    enableDragDrop: true,
    enableAutoFrontmatter: true,
    autoTags: ['tag-sentinel-alpha', 'tag-sentinel-beta'],
    conversionHistory: v1History(),
    imagePipelineEnabled: true,
    ocrLang: 'kor+eng',
    imagePipelineAdvancedConfig: {
      ocr_engines: ['tesseract', 'easyocr'],
      ocr_confidence_threshold: 0.6,
      enable_ocr_ensemble: true,
      enable_table_extraction: true,
      preprocess_deskew: true,
      deskew_method: 'hough',
      confidence_weight_engine_conf: 0.3,
      confidence_weight_agreement: 0.3,
      confidence_weight_length: 0.1,
      confidence_weight_cleanliness: 0.2,
      confidence_weight_stdev_inv: 0.1,
      unknown_future_tuning: { api_key: SENTINELS.advancedConfigSecret },
    },
  };
}

/** Variant builders for REQ-SHL-03 oracles. */
export const variants = {
  missing(key: V1Key): Record<string, unknown> {
    const v = v1AllKeys();
    delete v[key];
    return v;
  },
  nulled(key: V1Key): Record<string, unknown> {
    return { ...v1AllKeys(), [key]: null };
  },
  malformed(key: V1Key): Record<string, unknown> {
    return { ...v1AllKeys(), [key]: { wrong: ['type', 42] } };
  },
  withUnknownKeys(): Record<string, unknown> {
    return {
      ...v1AllKeys(),
      someUnknownKey: 'UNKNOWN-VALUE-1',
      anotherUnknown: { deep: 'UNKNOWN-VALUE-2' },
    };
  },
  futureSchema(): Record<string, unknown> {
    return { schemaVersion: 3, enginePython: '/opt/venv/bin/python', brandNewField: true };
  },
};

/**
 * 105 history entries with timestamp ties: ts = T0 + (i % 50) * 1000, original
 * index embedded in the path so stable ordering is observable.
 */
export function history105(): V1HistoryEntryLike[] {
  const out: V1HistoryEntryLike[] = [];
  for (let i = 0; i < 105; i++) {
    out.push({
      inputFile: `inbox/file-${String(i).padStart(3, '0')}.pdf`,
      outputFile: `out/file-${String(i).padStart(3, '0')}.pdf.md`,
      timestamp: T0 + (i % 50) * 1000,
      success: i % 7 !== 0,
      processingTimeMs: 100 + i,
    });
  }
  return out;
}

/** Reference stable sort (ES2019 Array.prototype.sort is stable) for expected ordering. */
export function expectedTop100(entries: V1HistoryEntryLike[]): V1HistoryEntryLike[] {
  return entries
    .map((e) => ({ ...e }))
    .sort((a, b) => (b.timestamp as number) - (a.timestamp as number))
    .slice(0, 100);
}
