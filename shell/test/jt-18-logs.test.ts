/**
 * JT-18 / REQ-SHL-18: plugin-local logs bounded to five 1 MiB rotated files;
 * lines carry timestamp, stage, code, count and status only; diagnostics copy
 * is redacted (codes, versions, probe results); injected secrets and document
 * text never appear; the log command opens only the owned folder.
 */
import { req } from './req';
import {
  diagnosticsCopy,
  LOG_DIR_NAME,
  LOG_FILE_COUNT,
  LOG_FILE_LIMIT_BYTES,
  LOG_FILE_NAMES,
  LOG_RECORD_FIELDS,
  type LogRecord,
  RotatingLog,
} from '../src/process/log';
import { FakeFs } from './fixtures/fake-fs';
import { abs, HOME, KEY_VALUE, PLUGIN_DIR, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-18');

const SECRET = KEY_VALUE;
const OCR_TEXT = 'SENTINEL-OCR-TEXT 계약서 본문 전체가 여기에';
const EXCEPTION = 'Traceback (most recent call last): SENTINEL-RAW-EXCEPTION';
const REDACT = { secrets: [SECRET], home: HOME, vault: VAULT_ROOT };

function logDir(): string {
  return abs(PLUGIN_DIR, LOG_DIR_NAME);
}

function allLogText(fs: FakeFs): string {
  return LOG_FILE_NAMES.map((name) => fs.text(abs(logDir(), name)) ?? '').join('\n');
}

it(R('JT-18 bounds: five files of one MiB each, fixed owned names under <plugin-dir>/logs'), () => {
  expect(LOG_FILE_COUNT).toBe(5);
  expect(LOG_FILE_LIMIT_BYTES).toBe(1048576);
  expect(LOG_FILE_NAMES).toHaveLength(5);
  expect(new Set(LOG_FILE_NAMES).size).toBe(5);
  expect([...LOG_RECORD_FIELDS].sort()).toEqual(['code', 'count', 'stage', 'status', 'ts']);
  const log = new RotatingLog(new FakeFs({ directories: [PLUGIN_DIR] }), logDir(), REDACT);
  expect(log.directory).toBe(logDir());
});

it(R('JT-18 a log line contains only timestamp, stage, code, count and status; extra fields and raw text are dropped'), async () => {
  const fs = new FakeFs({ directories: [PLUGIN_DIR] });
  const log = new RotatingLog(fs, logDir(), REDACT);
  const smuggled = {
    ts: '2026-11-09T00:00:00Z',
    stage: 'transcribe',
    code: 'E_PROVIDER_HTTP',
    count: 2,
    status: 'failed',
    message: EXCEPTION,
    text: OCR_TEXT,
    plan: { approved: { units: [1, 2, 3] } },
    apiKey: SECRET,
  } as unknown as LogRecord;
  await log.write(smuggled);
  await log.write({ ts: '2026-11-09T00:00:01Z', stage: 'write', status: `wrote ${VAULT_ROOT}/out/a.md with ${SECRET}` });
  const lines = (fs.text(abs(logDir(), LOG_FILE_NAMES[0])) ?? '').trim().split('\n');
  expect(lines).toHaveLength(2);
  const first = JSON.parse(lines[0]) as Record<string, unknown>;
  expect(Object.keys(first).sort()).toEqual(['code', 'count', 'stage', 'status', 'ts']);
  expect(first).toEqual({ ts: '2026-11-09T00:00:00Z', stage: 'transcribe', code: 'E_PROVIDER_HTTP', count: 2, status: 'failed' });
  const second = JSON.parse(lines[1]) as Record<string, unknown>;
  expect(Object.keys(second).every((k) => (LOG_RECORD_FIELDS as readonly string[]).includes(k))).toBe(true);
  const text = allLogText(fs);
  for (const forbidden of [SECRET, OCR_TEXT, EXCEPTION, 'SENTINEL', VAULT_ROOT, HOME]) expect(text).not.toContain(forbidden);
  expect(text).toContain('***');
});

it(R('JT-18 rotation never exceeds five files or one MiB per file; the oldest content is dropped'), async () => {
  const fs = new FakeFs({ directories: [PLUGIN_DIR] });
  const log = new RotatingLog(fs, logDir(), REDACT);
  const filler = 'x'.repeat(900);
  const target = LOG_FILE_LIMIT_BYTES * (LOG_FILE_COUNT + 1);
  let written = 0;
  let i = 0;
  while (written < target) {
    const record: LogRecord = { ts: `2026-11-09T00:00:${String(i % 60).padStart(2, '0')}Z`, stage: 'sniff', count: i, status: `${i}:${filler}` };
    await log.write(record);
    written += JSON.stringify(record).length + 1;
    i += 1;
  }
  const names = await fs.list(logDir());
  expect(names.length).toBeLessThanOrEqual(LOG_FILE_COUNT);
  for (const name of names) {
    expect(LOG_FILE_NAMES).toContain(name);
    expect((await fs.size(abs(logDir(), name))) ?? 0).toBeLessThanOrEqual(LOG_FILE_LIMIT_BYTES);
  }
  const text = allLogText(fs);
  expect(text).toContain(`"count":${i - 1}`);
  expect(text).not.toContain('"count":0,');
  // No file outside the owned log directory was touched.
  for (const mutation of fs.mutations) expect(mutation).toContain(logDir());
});

it(R('JT-18 diagnostics copy carries redacted versions/probe results and codes only; paths are vault-relative or home-redacted'), () => {
  const text = diagnosticsCopy(
    {
      version: { enabled: true, info: { mdflow: '2.0.0.dev0', 'markitdown-gc': '0.3.5', pypdfium2: '5.15.1', pillow: '13.0.0', python: '3.14.2', platform: 'Windows-11', protocol: 1, triage_schema: 1 } },
      probes: [{ command: 'python3', args: ['--version'], result: 'ok', version: '3.14.2' }],
      codes: ['E_CORRUPT', 'W_SKIPPED_HIDDEN', OCR_TEXT, EXCEPTION, 'E_BOGUS_CODE'],
      paths: [`${VAULT_ROOT}/notes/out`, `${HOME}/venv/bin/python`, `${HOME}/x ${SECRET}`],
    },
    REDACT,
  );
  expect(text).toContain('2.0.0.dev0');
  expect(text).toContain('0.3.5');
  expect(text).toContain('python3');
  expect(text).toContain('E_CORRUPT');
  expect(text).toContain('W_SKIPPED_HIDDEN');
  expect(text).toContain('notes/out');
  expect(text).toContain('~/venv/bin/python');
  for (const forbidden of [SECRET, OCR_TEXT, EXCEPTION, 'E_BOGUS_CODE', VAULT_ROOT, HOME, 'SENTINEL']) expect(text).not.toContain(forbidden);
});
