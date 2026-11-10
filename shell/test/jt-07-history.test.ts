/**
 * JT-07 / REQ-SHL-07: typed history entries, unknown fields discarded,
 * stable descending sort with ties, cap 100 on migration and insertion,
 * nonsecret outcome distinct from `success`, clear only clears history. FX-70.
 */
import { req } from './req';
import { clearHistory, HISTORY_CAP, type HistoryEntry, insertHistory, normalizeHistory, outcomeFor } from '../src/pure/history';
import type { SettingsV2 } from '../src/pure/settings';
import { expectedTop100, history105, SENTINELS, T0, v1History } from './fixtures/fx70';

const R = req('REQ-SHL-07');

const TYPED_FIELDS = ['inputFile', 'outputFile', 'timestamp', 'success', 'processingTimeMs', 'assetsExtracted', 'outcome'];

it(R('JT-07 the 105-entry fixture retains exactly 100 entries in stable descending timestamp order'), () => {
  const { entries, skipped } = normalizeHistory(history105());
  expect(HISTORY_CAP).toBe(100);
  expect(skipped).toBe(0);
  expect(entries).toHaveLength(100);
  const expected = expectedTop100(history105()).map((e) => ({
    inputFile: e.inputFile,
    outputFile: e.outputFile,
    timestamp: e.timestamp,
    success: e.success,
    processingTimeMs: e.processingTimeMs,
  }));
  expect(entries).toEqual(expected);
  for (let i = 1; i < entries.length; i++) {
    expect(entries[i - 1].timestamp).toBeGreaterThanOrEqual(entries[i].timestamp);
    if (entries[i - 1].timestamp === entries[i].timestamp) {
      // Ties keep original order: the original index is embedded in the file name.
      expect(entries[i - 1].inputFile < entries[i].inputFile).toBe(true);
    }
  }
});

it(R('JT-07 entries are typed: ISO timestamps normalized, unknown fields discarded, invalid entries skipped and counted'), () => {
  const { entries, skipped } = normalizeHistory(v1History());
  expect(skipped).toBe(1);
  expect(entries).toEqual([
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
  ]);
  const text = JSON.stringify(entries);
  expect(text).not.toContain(SENTINELS.historyErrorKey);
  expect(text).not.toContain('extraneous');
  for (const entry of entries) {
    for (const field of Object.keys(entry)) expect(TYPED_FIELDS).toContain(field);
  }
});

it(R('JT-07 wrongly typed fields invalidate the entry; non-array history yields no entries'), () => {
  const bad = [
    { inputFile: 42, outputFile: 'o', timestamp: T0, success: true },
    { inputFile: 'i', outputFile: 'o', timestamp: 'yesterday', success: true },
    { inputFile: 'i', outputFile: 'o', timestamp: T0, success: 'yes' },
    { inputFile: 'i', outputFile: 'o', timestamp: T0, success: true, processingTimeMs: '12' },
    { inputFile: 'i', outputFile: 'o', timestamp: T0, success: true, outcome: 'won' },
    'not-an-object',
    null,
  ];
  const result = normalizeHistory(bad);
  expect(result.entries).toEqual([]);
  expect(result.skipped).toBe(bad.length);
  expect(normalizeHistory({ not: 'array' })).toEqual({ entries: [], skipped: 0 });
  expect(normalizeHistory(undefined)).toEqual({ entries: [], skipped: 0 });
});

it(R('JT-07 paths are display references preserved verbatim, never resolved or executed'), () => {
  const hostile = '../../etc/passwd && rm -rf / ; $(whoami) `id` C:\\..\\x';
  const { entries } = normalizeHistory([{ inputFile: hostile, outputFile: hostile, timestamp: T0, success: true }]);
  expect(entries[0].inputFile).toBe(hostile);
  expect(entries[0].outputFile).toBe(hostile);
});

it(R('JT-07 insertion keeps newest first and re-applies the cap of 100'), () => {
  const { entries } = normalizeHistory(history105());
  const fresh: HistoryEntry = {
    inputFile: 'inbox/new.pdf',
    outputFile: 'out/new.pdf.md',
    timestamp: T0 + 10 * 60 * 1000,
    success: true,
    outcome: 'complete',
  };
  const next = insertHistory(entries, fresh);
  expect(next).toHaveLength(100);
  expect(next[0]).toEqual(fresh);
  expect(next.slice(1)).toEqual(entries.slice(0, 99));
  expect(entries).toHaveLength(100); // input not mutated
  expect(insertHistory([], fresh)).toEqual([fresh]);
});

it(R('JT-07 outcomes distinguish complete, pending consent, partial failure and cancelled; success is never inferred from created files'), () => {
  const base = { cancelled: false, filesOk: 1, filesFailed: 0, unitsPending: 0 };
  expect(outcomeFor({ ...base, exit: 0 })).toEqual({ outcome: 'complete', success: true });
  expect(outcomeFor({ ...base, exit: 3, unitsPending: 2 })).toEqual({ outcome: 'pending_consent', success: false });
  expect(outcomeFor({ ...base, exit: 2, filesFailed: 1 })).toEqual({ outcome: 'partial_failure', success: false });
  expect(outcomeFor({ ...base, exit: 4, filesFailed: 1 })).toEqual({ outcome: 'partial_failure', success: false });
  expect(outcomeFor({ ...base, exit: 130, cancelled: true })).toEqual({ outcome: 'cancelled', success: false });
  // Forced termination: no exit code, whatever is on disk, still not success.
  expect(outcomeFor({ ...base, exit: null, cancelled: true })).toEqual({ outcome: 'cancelled', success: false });
  // Created files are not an input at all: the facts carry no output count that could be mistaken for success.
  expect(Object.keys({ ...base, exit: 0 })).not.toContain('outputsCreated');
  expect(outcomeFor({ ...base, exit: 0, filesOk: 0 }).success).toBe(true);
});

it(R('JT-07 clear history clears only history and does not mutate its input'), () => {
  const { entries } = normalizeHistory(history105());
  const settings: SettingsV2 = {
    schemaVersion: 2,
    enginePython: '/venv/bin/python',
    bootstrapPythonHint: 'python3',
    outputPath: 'notes/out',
    enableBatchProgress: false,
    enableContextMenu: true,
    enableRecursiveConversion: false,
    enableDragDrop: true,
    enableLegacyPreconvert: true,
    conversionHistory: entries,
    locale: 'ko',
    provider: { name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1' },
    runOptions: { dpi: 300, minPriority: 'normal', maxUnits: 10, approveThreshold: 2, sensitive: ['*x*'] },
  };
  const before = JSON.parse(JSON.stringify(settings)) as SettingsV2;
  const cleared = clearHistory(settings);
  expect(cleared.conversionHistory).toEqual([]);
  expect({ ...cleared, conversionHistory: before.conversionHistory }).toEqual(before);
  expect(settings).toEqual(before);
});
