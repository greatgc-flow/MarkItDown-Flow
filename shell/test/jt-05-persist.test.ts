/**
 * JT-05 / REQ-SHL-05: atomic persistence before jobs, one sanitized
 * allowlisted snapshot, idempotence, interrupted/denied writes leave valid
 * old-or-new JSON, block jobs and show the unsanitized-disk warning. FX-70.
 */
import { req } from './req';
import { buildSnapshot, LEGACY_HISTORY_ERROR, persistMigration } from '../src/pure/persist';
import { FakeStore, parseJson } from './fixtures/fake-store';
import { ALL_SENTINELS, MAPPED_V1_KEYS, SENTINELS, V1_PYTHON_PATH, v1AllKeys } from './fixtures/fx70';

const R = req('REQ-SHL-05');

const SNAPSHOT_ALLOWLIST = new Set<string>(MAPPED_V1_KEYS);

function v1Text(): string {
  return JSON.stringify(v1AllKeys(), null, 2);
}

function sentinelsIn(text: string | undefined): string[] {
  return text === undefined ? [] : ALL_SENTINELS.filter((s) => text.includes(s));
}

function assertValidJsonFiles(store: FakeStore): void {
  for (const [name, text] of store.files) {
    expect(() => JSON.parse(text)).not.toThrow();
    expect(['data.json', 'data.v1.json']).toContain(name);
  }
}

it(R('JT-05 buildSnapshot keeps only mapped preference names and safe history; credentials, endpoint, args and advanced config are omitted'), () => {
  const snapshot = buildSnapshot(v1AllKeys());
  for (const key of Object.keys(snapshot)) expect(SNAPSHOT_ALLOWLIST.has(key)).toBe(true);
  expect(snapshot.pythonPath).toBe(V1_PYTHON_PATH);
  expect(snapshot.outputPath).toBe('notes/converted');
  for (const gone of ['docintelCredential', 'docintelEndpoint', 'llmApiKey', 'pluginArgs', 'imagePipelineAdvancedConfig']) {
    expect(snapshot).not.toHaveProperty(gone);
  }
  const text = JSON.stringify(snapshot);
  expect(sentinelsIn(text)).toEqual([]);
  const history = snapshot.conversionHistory as Record<string, unknown>[];
  expect(Array.isArray(history)).toBe(true);
  const failed = history.find((h) => h.success === false);
  expect(failed?.error).toBe(LEGACY_HISTORY_ERROR);
  expect(text).not.toContain('Auth failed');
});

it(R('JT-05 successful migration writes the snapshot once, then schema 2; both files are sentinel-free'), async () => {
  const store = new FakeStore({ 'data.json': v1Text() });
  const outcome = await persistMigration(store);
  expect(outcome.ok).toBe(true);
  expect(outcome.jobsBlocked).toBe(false);
  expect(outcome.diskSanitized).toBe(true);
  expect(outcome.unsanitizedDiskWarning).toBe(false);
  expect(outcome.writes).toEqual(['data.v1.json', 'data.json']);
  const data = parseJson(store.text('data.json')) as { schemaVersion: number };
  expect(data.schemaVersion).toBe(2);
  expect(sentinelsIn(store.text('data.json'))).toEqual([]);
  expect(sentinelsIn(store.text('data.v1.json'))).toEqual([]);
  expect(await store.list()).toEqual(['data.json', 'data.v1.json']);
  assertValidJsonFiles(store);
});

it(R('JT-05 repeat migration is idempotent: no further writes, identical bytes, snapshot untouched'), async () => {
  const store = new FakeStore({ 'data.json': v1Text() });
  await persistMigration(store);
  const dataBytes = store.text('data.json');
  const snapshotBytes = store.text('data.v1.json');
  const second = await persistMigration(store);
  expect(second.ok).toBe(true);
  expect(second.jobsBlocked).toBe(false);
  expect(second.writes).toEqual([]);
  expect(store.text('data.json')).toBe(dataBytes);
  expect(store.text('data.v1.json')).toBe(snapshotBytes);
});

it(R('JT-05 an existing snapshot is never overwritten by a later migration attempt'), async () => {
  const marker = '{"marker":"earlier-snapshot"}';
  const store = new FakeStore({ 'data.json': v1Text(), 'data.v1.json': marker });
  const outcome = await persistMigration(store);
  expect(outcome.ok).toBe(true);
  expect(store.text('data.v1.json')).toBe(marker);
  expect(outcome.writes).toEqual(['data.json']);
});

it(R('JT-05 write denied on the snapshot: original bytes unchanged, no extra file, jobs blocked, warning shown, memory cleared'), async () => {
  const original = v1Text();
  const store = new FakeStore({ 'data.json': original }, { denyWriteNumber: 1 });
  const outcome = await persistMigration(store);
  expect(outcome.ok).toBe(false);
  expect(outcome.jobsBlocked).toBe(true);
  expect(outcome.result).toBeNull();
  expect(outcome.noticeKeys).toContain('shell.SETTINGS');
  expect(outcome.diskSanitized).toBe(false);
  expect(outcome.unsanitizedDiskWarning).toBe(true);
  expect(outcome.writes).toEqual([]);
  expect(store.text('data.json')).toBe(original);
  expect(await store.list()).toEqual(['data.json']);
  expect(sentinelsIn(JSON.stringify(outcome))).toEqual([]);
});

it(R('JT-05 interrupted after the snapshot: data.json keeps original bytes, snapshot is valid and sanitized, no placeholder'), async () => {
  const original = v1Text();
  const store = new FakeStore({ 'data.json': original }, { denyFile: 'data.json' });
  const outcome = await persistMigration(store);
  expect(outcome.ok).toBe(false);
  expect(outcome.jobsBlocked).toBe(true);
  expect(outcome.unsanitizedDiskWarning).toBe(true);
  expect(outcome.diskSanitized).toBe(false);
  expect(store.text('data.json')).toBe(original);
  expect(sentinelsIn(store.text('data.v1.json'))).toEqual([]);
  assertValidJsonFiles(store);
  expect(outcome.result).toBeNull();
});

it(R('JT-05 a retry after a denied write completes the same migration (old or new JSON at every step)'), async () => {
  const original = v1Text();
  const store = new FakeStore({ 'data.json': original }, { denyWriteNumber: 2 });
  const first = await persistMigration(store);
  expect(first.ok).toBe(false);
  assertValidJsonFiles(store);
  const second = await persistMigration(store);
  expect(second.ok).toBe(true);
  expect(second.jobsBlocked).toBe(false);
  expect((parseJson(store.text('data.json')) as { schemaVersion: number }).schemaVersion).toBe(2);
  assertValidJsonFiles(store);
  const reference = new FakeStore({ 'data.json': original });
  await persistMigration(reference);
  expect(parseJson(store.text('data.json'))).toEqual(parseJson(reference.text('data.json')));
});

it(R('JT-05 already schema 2: no snapshot is created and nothing is rewritten'), async () => {
  const v2 = JSON.stringify({
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
  });
  const store = new FakeStore({ 'data.json': v2 });
  const outcome = await persistMigration(store);
  expect(outcome.ok).toBe(true);
  expect(outcome.jobsBlocked).toBe(false);
  expect(outcome.writes).toEqual([]);
  expect(await store.list()).toEqual(['data.json']);
  expect(store.text('data.json')).toBe(v2);
});

it(R('JT-05 newer schema on disk is left untouched and blocks jobs'), async () => {
  const future = JSON.stringify({ schemaVersion: 3, enginePython: '/opt/venv/bin/python' });
  const store = new FakeStore({ 'data.json': future });
  const outcome = await persistMigration(store);
  expect(outcome.jobsBlocked).toBe(true);
  expect(outcome.writes).toEqual([]);
  expect(store.text('data.json')).toBe(future);
  expect(await store.list()).toEqual(['data.json']);
});

it(R('JT-05 retained strings in the snapshot have known credential values removed'), () => {
  const raw = {
    ...v1AllKeys(),
    pythonPath: `C:\\tools\\${SENTINELS.llmApiKey}\\python.exe`,
    outputPath: `out/${SENTINELS.docintelCredential}`,
  };
  const text = JSON.stringify(buildSnapshot(raw));
  expect(sentinelsIn(text)).toEqual([]);
});
