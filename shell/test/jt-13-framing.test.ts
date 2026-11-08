/**
 * JT-13 / REQ-SHL-13: incremental UTF-8/CRLF framing, 64 KiB line limit,
 * unknown events ignored, invalid known events fail without raw bytes,
 * approval events are summaries, full Plans come from `plan` stdout, raw
 * triage `corrupt` retained, mdflow codes validated only in mdflow fields,
 * spool drained with bounded reads and removed.
 *
 * Inputs are synthetic per SPEC 7.1/7.3/7.4 (FX-71 recordings pending, R7 F-04).
 */
import { req } from './req';
import { decodeEvent, type FrameResult, JsonLinesFramer, MAX_LINE_BYTES, type ProgressEvent } from '../src/pure/framing';
import { approvableHashes, decodeReport, parsePlanOutput } from '../src/pure/protocol';
import { recoverableSpools, Spool, SPOOL_NAME_PATTERN, SPOOL_READ_BUFFER_BYTES, type SpoolFs } from '../src/pure/spool';
import {
  bytes,
  CORE_TRIAGE_CORRUPT,
  events,
  HEX64_A,
  HEX64_B,
  jsonLine,
  KOREAN_FILE,
  plan,
  planStdout,
  report,
  splitAt,
} from './fixtures/protocol';

const R = req('REQ-SHL-13');

function feed(framer: JsonLinesFramer, chunks: Uint8Array[]): FrameResult[] {
  const out: FrameResult[] = [];
  for (const chunk of chunks) out.push(...framer.push(chunk));
  out.push(...framer.end());
  return out;
}

function onlyEvents(results: FrameResult[]): ProgressEvent[] {
  return results.flatMap((r) => (r.kind === 'event' ? [r.event] : []));
}

it(R('JT-13 UTF-8 split across arbitrary chunks and mixed CRLF/LF line ends decode into whole events'), () => {
  const text = jsonLine(events.fileStart()) + '\r\n' + jsonLine(events.stage()) + '\n' + jsonLine(events.fileEnd());
  const buf = bytes(text);
  // Split inside the Korean file name (multi-byte) and right between \r and \n.
  const koreanOffset = text.indexOf('보') + 1; // char index; find a byte offset inside the sequence
  const byteOffsetInsideKorean = bytes(text.slice(0, koreanOffset)).length - 1;
  const crIndex = bytes(text.slice(0, text.indexOf('\r\n') + 1)).length;
  const results = feed(new JsonLinesFramer(), splitAt(buf, [byteOffsetInsideKorean, crIndex, buf.length - 7]));
  const decoded = onlyEvents(results);
  expect(results.filter((r) => r.kind === 'invalid')).toEqual([]);
  expect(decoded.map((e) => e.ev)).toEqual(['file_start', 'stage', 'file_end']);
  const first = decoded[0];
  if (first.ev === 'file_start') {
    expect(first.file).toBe(KOREAN_FILE);
  } else {
    throw new Error(`expected file_start, got ${first.ev}`);
  }
  expect(JSON.stringify(decoded)).not.toContain('\\r');
});

it(R('JT-13 one chunk per byte yields the same events as one chunk per line'), () => {
  const text = [events.runStart(), events.classified(), events.unit(), events.runEnd()].map(jsonLine).join('\n') + '\n';
  const buf = bytes(text);
  const perByte = feed(new JsonLinesFramer(), Array.from(buf, (b) => Uint8Array.of(b)));
  const whole = feed(new JsonLinesFramer(), [buf]);
  expect(onlyEvents(perByte)).toEqual(onlyEvents(whole));
  expect(onlyEvents(whole)).toHaveLength(4);
});

it(R('JT-13 unknown event names are ignored and framing continues'), () => {
  const text = [
    { v: 1, ev: 'heartbeat', ts: 't', anything: 'goes' },
    events.unit(),
    { v: 1, ev: 'plan_chunk', ts: 't', units: [1, 2, 3] },
    events.runEnd(),
  ].map(jsonLine).join('\n') + '\n';
  const results = feed(new JsonLinesFramer(), [bytes(text)]);
  expect(results.map((r) => r.kind)).toEqual(['ignored', 'event', 'ignored', 'event']);
  expect(results[0]).toEqual({ kind: 'ignored', ev: 'heartbeat' });
  expect(results.filter((r) => r.kind === 'invalid')).toEqual([]);
});

it(R('JT-13 a line over 64 KiB is rejected as oversize without exposing its bytes; the next line still decodes'), () => {
  expect(MAX_LINE_BYTES).toBe(65536);
  const marker = 'RAW-OVERSIZE-MARKER-';
  const huge = jsonLine({ ...events.warning(), message: marker + 'x'.repeat(70_000) });
  expect(bytes(huge).length).toBeGreaterThan(MAX_LINE_BYTES);
  const results = feed(new JsonLinesFramer(), [bytes(huge + '\n' + jsonLine(events.runEnd()) + '\n')]);
  expect(results).toHaveLength(2);
  expect(results[0]).toMatchObject({ kind: 'invalid', reason: 'oversize', diagnostic: 'shell.PROTOCOL' });
  expect(JSON.stringify(results[0])).not.toContain(marker);
  expect(JSON.stringify(results[0])).not.toContain('xxxxxxxxxx');
  expect(results[1]).toMatchObject({ kind: 'event', event: { ev: 'run_end' } });
});

it(R('JT-13 exactly 64 KiB is accepted'), () => {
  const base = { ...events.warning(), message: '' };
  const overhead = bytes(jsonLine(base)).length;
  const line = jsonLine({ ...base, message: 'y'.repeat(MAX_LINE_BYTES - overhead) });
  expect(bytes(line).length).toBe(MAX_LINE_BYTES);
  const results = feed(new JsonLinesFramer(), [bytes(line + '\n')]);
  expect(results[0].kind).toBe('event');
});

it(R('JT-13 malformed JSON and wrong protocol version fail visibly without raw-byte display'), () => {
  const marker = 'RAW-MALFORMED-MARKER-9f1';
  const text = `{"v":1,"ev":"unit","ts":"${marker}",\n` + jsonLine({ ...events.unit(), v: 2 }) + '\n' + jsonLine(events.runEnd()) + '\n';
  const results = feed(new JsonLinesFramer(), [bytes(text)]);
  expect(results.map((r) => r.kind)).toEqual(['invalid', 'invalid', 'event']);
  expect(results[0]).toMatchObject({ kind: 'invalid', reason: 'malformed', diagnostic: 'shell.PROTOCOL' });
  expect(results[1]).toMatchObject({ kind: 'invalid', reason: 'version', diagnostic: 'shell.PROTOCOL' });
  expect(JSON.stringify(results)).not.toContain(marker);
});

it(R('JT-13 known events with missing or mistyped required fields are invalid, not silently accepted'), () => {
  const { plan_hash: _dropped, ...noHash } = events.approveRequired();
  void _dropped;
  const cases: unknown[] = [
    noHash,
    { ...events.fileEnd(), units: { total: '5', done: 4, pending: 1, failed: 0 } },
    { ...events.runEnd(), exit: 'zero' },
    { ...events.stage(), stage: 'teleport' },
    { ...events.unit(), state: 'maybe' },
    { v: 1, ev: 'file_start', ts: 't' },
    { v: 1, ev: 'unit', ts: 't', file: 'a', unit: 'p1', state: 'ok', code: 123 },
  ];
  for (const value of cases) {
    const result = decodeEvent(value);
    expect(result).toMatchObject({ kind: 'invalid', reason: 'schema', diagnostic: 'shell.PROTOCOL' });
  }
});

it(R('JT-13 mdflow codes in progress events are validated against SPEC 7.5; Core and deleted codes are rejected there'), () => {
  expect(decodeEvent(events.warning('W_MEDIA_UNMAPPED')).kind).toBe('event');
  expect(decodeEvent(events.error('E_CONVERT_FAIL')).kind).toBe('event');
  expect(decodeEvent({ ...events.unit(), state: 'failed', code: 'E_PROVIDER_HTTP' }).kind).toBe('event');
  for (const bad of ['E_BOGUS', 'suspect_text_layer', 'W_TRIAGE_COVERAGE', 'E_PROVIDER_INTERRUPTED', 'W_STALE_TEMP']) {
    expect(decodeEvent(events.warning(bad))).toMatchObject({ kind: 'invalid', reason: 'code' });
    expect(decodeEvent(events.error(bad))).toMatchObject({ kind: 'invalid', reason: 'code' });
    expect(decodeEvent({ ...events.unit(), state: 'failed', code: bad })).toMatchObject({ kind: 'invalid', reason: 'code' });
  }
});

it(R('JT-13 approve_required is consumed as a bounded summary without a unit list'), () => {
  const result = decodeEvent(events.approveRequired());
  expect(result.kind).toBe('event');
  if (result.kind !== 'event') return;
  const event: unknown = result.event;
  expect(event).toEqual(events.approveRequired());
  expect(event).not.toHaveProperty('units');
  // A producer that smuggles a unit list onto the summary does not create an authorization surface.
  const smuggled = decodeEvent({ ...events.approveRequired(), units: [{ source_id: 'p1' }] });
  if (smuggled.kind === 'event') {
    const smuggledEvent: unknown = smuggled.event;
    expect(smuggledEvent).not.toHaveProperty('units');
  } else {
    expect(smuggled).toMatchObject({ kind: 'invalid', reason: 'schema' });
  }
});

it(R('JT-13 full Plans come from plan stdout: a 300-unit Plan is decoded whole and hashes come only from decoded Plans'), () => {
  const plans = [plan('a.pdf', HEX64_A, 3), plan('sub/큰 문서.pdf', HEX64_B, 300)];
  const stdout = planStdout(plans);
  expect(bytes(stdout).length).toBeGreaterThan(MAX_LINE_BYTES);
  const decoded = parsePlanOutput(stdout);
  expect(decoded.ok).toBe(true);
  if (!decoded.ok) return;
  expect(decoded.value).toHaveLength(2);
  expect(decoded.value[1].approved.units).toHaveLength(300);
  expect(decoded.value[1].approved.file.path).toBe('sub/큰 문서.pdf');
  expect(decoded.value.map((p) => p.plan_hash)).toEqual([HEX64_A, HEX64_B]);
  expect(approvableHashes(decoded.value)).toEqual([HEX64_A, HEX64_B]);
});

it(R('JT-13 a truncated or inconsistent Plan output yields no approvable hash'), () => {
  const stdout = planStdout([plan('a.pdf', HEX64_A, 40)]);
  const truncated = stdout.slice(0, Math.floor(stdout.length / 2));
  expect(parsePlanOutput(truncated)).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  const inconsistent = plan('a.pdf', HEX64_A, 4);
  inconsistent.approved.units_total = 3;
  expect(parsePlanOutput(planStdout([inconsistent]))).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  const badHash = plan('a.pdf', 'not-a-hash', 2);
  expect(parsePlanOutput(planStdout([badHash]))).toMatchObject({ ok: false });
  expect(parsePlanOutput('')).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
});

it(R('JT-13 the run report keeps raw triage corrupt verbatim and validates mdflow codes only in mdflow-owned fields'), () => {
  const decoded = decodeReport(JSON.stringify(report()));
  expect(decoded.ok).toBe(true);
  if (!decoded.ok) return;
  expect(decoded.value.files[0].triage).toEqual(CORE_TRIAGE_CORRUPT);
  expect(decoded.value.files[0].issues[0].code).toBe('E_CORRUPT');
  expect(decoded.value.exit).toBe(2);
  const badIssue = report();
  badIssue.files[0].issues = [{ code: 'E_BOGUS', message: 'x' }];
  expect(decodeReport(JSON.stringify(badIssue))).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  const coreCodeInMdflowField = report();
  coreCodeInMdflowField.files[0].issues = [{ code: 'suspect_text_layer', message: 'x' }];
  expect(decodeReport(JSON.stringify(coreCodeInMdflowField))).toMatchObject({ ok: false });
  const deletedSkipped = report({ skipped: [{ path: 'x', code: 'W_TRIAGE_COVERAGE' }] });
  expect(decodeReport(JSON.stringify(deletedSkipped))).toMatchObject({ ok: false });
});

it(R('JT-13 a missing or truncated report is a visible protocol failure, never success'), () => {
  expect(decodeReport('')).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  const text = JSON.stringify(report());
  expect(decodeReport(text.slice(0, text.length - 20))).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  expect(decodeReport(JSON.stringify({ ...report(), v: 2 }))).toMatchObject({ ok: false });
  expect(decodeReport(JSON.stringify({ ...report(), exit: 'ok' }))).toMatchObject({ ok: false });
});

class FakeSpoolFs implements SpoolFs {
  readonly files = new Map<string, Uint8Array>();
  maxRead = 0;
  removed: string[] = [];
  constructor(initial: Record<string, Uint8Array> = {}) {
    for (const [k, v] of Object.entries(initial)) this.files.set(k, v);
  }
  async append(name: string, chunk: Uint8Array): Promise<void> {
    const prev = this.files.get(name) ?? new Uint8Array(0);
    const next = new Uint8Array(prev.length + chunk.length);
    next.set(prev, 0);
    next.set(chunk, prev.length);
    this.files.set(name, next);
  }
  async read(name: string, offset: number, max: number): Promise<Uint8Array> {
    this.maxRead = Math.max(this.maxRead, max);
    const data = this.files.get(name);
    if (!data) throw new Error('ENOENT');
    return data.slice(offset, offset + max);
  }
  async remove(name: string): Promise<void> {
    this.files.delete(name);
    this.removed.push(name);
  }
  async list(): Promise<string[]> {
    return [...this.files.keys()];
  }
}

const NONCE = '0123456789abcdef';

it(R('JT-13 stdout spool is drained with bounded reads, validated after exit and removed'), async () => {
  const fs = new FakeSpoolFs();
  const spool = new Spool(fs, NONCE);
  expect(spool.name).toMatch(SPOOL_NAME_PATTERN);
  const text = JSON.stringify(report());
  const buf = bytes(text);
  for (const chunk of splitAt(buf, [10, 1000, 5000])) await spool.write(chunk);
  const decoded = await spool.finish();
  expect(decoded.ok).toBe(true);
  expect(fs.maxRead).toBeGreaterThan(0);
  expect(fs.maxRead).toBeLessThanOrEqual(SPOOL_READ_BUFFER_BYTES);
  expect(await fs.list()).toEqual([]);
  expect(fs.removed).toEqual([spool.name]);
});

it(R('JT-13 an invalid spooled report is removed after the handled failure; discard removes without decoding'), async () => {
  const fs = new FakeSpoolFs();
  const spool = new Spool(fs, NONCE);
  await spool.write(bytes('{"v":1,"truncated":'));
  const decoded = await spool.finish();
  expect(decoded).toMatchObject({ ok: false, diagnostic: 'shell.PROTOCOL' });
  expect(await fs.list()).toEqual([]);
  const fs2 = new FakeSpoolFs();
  const cancelled = new Spool(fs2, 'fedcba9876543210');
  await cancelled.write(bytes(JSON.stringify(report())));
  await cancelled.discard();
  expect(await fs2.list()).toEqual([]);
});

it(R('JT-13 only verified owned stale spool files are recovered; foreign files are left alone'), () => {
  const names = [
    'mdflow-spool-0123456789abcdef.json',
    'mdflow-spool-FEDCBA9876543210.json',
    'mdflow-spool-short.json',
    'other-plugin.json',
    'data.json',
    'mdflow-spool-0123456789abcdef.json.bak',
    'report.md',
  ];
  expect(recoverableSpools(names)).toEqual(['mdflow-spool-0123456789abcdef.json']);
  expect(recoverableSpools([])).toEqual([]);
});
