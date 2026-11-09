/**
 * JT-13 / REQ-SHL-13 re-run against FX-71 (30_TESTPLAN.md open item 2): the
 * step-8 framer was written against synthetic SPEC-shaped lines; these cases
 * replay the streams recorded from the real engine and their derived split,
 * CRLF, unknown-event, boundary and oversize variants. Expected to pass on the
 * step-8 implementation; they are regression evidence, not new red tests.
 */
import { req } from './req';
import { type FrameResult, JsonLinesFramer, type ProgressEvent } from '../src/pure/framing';
import { chunksOf } from './fixtures/fake-spawner';
import { concat, fx71Bytes, fx71Chunks, fx71Lines } from './fixtures/fx71';

const R = req('REQ-SHL-13');

function frame(chunks: Uint8Array[]): FrameResult[] {
  const framer = new JsonLinesFramer();
  const out: FrameResult[] = [];
  for (const chunk of chunks) out.push(...framer.push(chunk));
  out.push(...framer.end());
  return out;
}

function events(results: FrameResult[]): ProgressEvent[] {
  return results.flatMap((r) => (r.kind === 'event' ? [r.event] : []));
}

it(R('JT-13 FX-71 split chunks (LF and CRLF, cuts inside UTF-8 sequences and between CR/LF) decode to the same events as the whole stream'), () => {
  const whole = events(frame([fx71Bytes('approve-required.progress.jsonl')]));
  expect(whole).toHaveLength(fx71Lines('approve-required.progress.jsonl').length);
  for (const name of ['approve-required.split.json', 'approve-required.crlf.split.json']) {
    const chunks = fx71Chunks(name);
    expect(chunks.length).toBeGreaterThan(10);
    expect(events(frame(chunks))).toEqual(whole);
  }
  expect(concat(fx71Chunks('approve-required.crlf.split.json'))).toEqual(fx71Bytes('approve-required.crlf.jsonl'));
  expect(events(frame([fx71Bytes('approve-required.crlf.jsonl')]))).toEqual(whole);
  expect(JSON.stringify(whole)).not.toContain('\\r');
});

it(R('JT-13 FX-71 unknown events and additive fields are ignored; the 64 KiB boundary and oversize lines behave per SPEC 7.3'), () => {
  const base = events(frame([fx71Bytes('approve-required.progress.jsonl')]));
  const results = frame([fx71Bytes('approve-required.unknown-events.jsonl')]);
  expect(results.filter((r) => r.kind === 'invalid')).toEqual([]);
  const ignored = results.filter((r): r is Extract<FrameResult, { kind: 'ignored' }> => r.kind === 'ignored').map((r) => r.ev);
  expect(new Set(ignored)).toEqual(new Set(['heartbeat', 'x_vendor_event', 'future_stage_detail']));
  const decoded = events(results);
  expect(decoded).toHaveLength(base.length);
  expect(decoded[1].ev).toBe('file_start');
  expect(decoded[1]).not.toHaveProperty('future_field');
  const exact = frame([fx71Bytes('approve-required.line-65536.jsonl')]);
  expect(exact.filter((r) => r.kind === 'invalid')).toEqual([]);
  expect(events(exact)).toHaveLength(base.length + 1);
  const over = frame([fx71Bytes('approve-required.line-65537.jsonl')]);
  expect(over.filter((r) => r.kind === 'invalid')).toEqual([{ kind: 'invalid', reason: 'oversize', diagnostic: 'shell.PROTOCOL' }]);
  expect(events(over)).toHaveLength(base.length);
  const unterminated = frame(chunksOf(fx71Bytes('approve-required.unterminated-70000.jsonl'), 1024));
  expect(events(unterminated)).toHaveLength(2);
  expect(unterminated[unterminated.length - 1]).toMatchObject({ kind: 'invalid', reason: 'oversize' });
  expect(JSON.stringify(unterminated)).not.toContain('xxxxxxxx');
});
