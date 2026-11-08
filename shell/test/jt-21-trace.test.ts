/**
 * JT-21 / REQ-SHL-21: `req()` rejects unknown/duplicate ids and unregistered
 * planned requirements; the trace export rejects unknown ids, reports
 * zero-test requirements and keeps manual sign-offs out of automated totals.
 */
import { plannedShellTests, registrations, req, shellRequirementIds } from './req';
import { buildTraceExport, type TestResult } from '../src/pure/trace';

const R = req('REQ-SHL-21');

function asResults(status: TestResult['status'] = 'passed'): TestResult[] {
  return registrations().map((r) => ({ ...r, status }));
}

it(R('JT-21 req() rejects unknown requirement ids, unknown test ids and empty marker sets'), () => {
  expect(() => req('REQ-SHL-99')).toThrow(/unknown requirement/);
  expect(() => req('REQ-GEN-01')).toThrow(/unknown requirement/);
  expect(() => req('REQ-SHL-3')).toThrow(/unknown requirement/);
  expect(() => req()).toThrow(/at least one/);
  expect(() => req('REQ-SHL-21', 'REQ-SHL-21')).toThrow(/duplicate requirement/);
  expect(() => req('REQ-SHL-21')('JT-99 invented test')).toThrow(/not in 30_TESTPLAN/);
  expect(() => req('REQ-SHL-21')('T-GEN-01 wrong grammar')).toThrow(/must start with a JT id/);
  expect(() => req('REQ-SHL-21')('JT-21')).toThrow(/empty description/);
  // Planned registration must be a superset: JT-03 requires REQ-SHL-03.
  expect(() => req('REQ-SHL-21')('JT-03 mislabelled')).toThrow(/must register planned requirement REQ-SHL-03/);
  const exported = buildTraceExport(asResults(), [...shellRequirementIds()], []);
  expect(exported.automated.tests.length).toBeGreaterThan(0);
});

it(R('JT-21 req() rejects a duplicate (test id, description) registration'), () => {
  const existing = registrations().find((r) => r.tid === 'JT-21');
  expect(existing).toBeDefined();
  const description = (existing as { title: string }).title.split(': ').slice(1).join(': ');
  expect(() => req('REQ-SHL-21')(`JT-21 ${description}`)).toThrow(/duplicate test JT-21/);
  // A distinct description for the same id is allowed, and the title carries every REQ.
  const title = req('REQ-SHL-21')('JT-21 probe registration for duplicate detection');
  expect(title).toBe('JT-21 REQ-SHL-21: probe registration for duplicate detection');
  const exported = buildTraceExport(asResults(), [...shellRequirementIds()], []);
  expect(exported.automated.tests.some((t) => t.title === title)).toBe(true);
});

it(R('JT-21 planned catalog and 20_SHELL.md definitions agree on the 21 shell requirement ids'), () => {
  const defined = shellRequirementIds();
  const planned = new Set([...plannedShellTests().values()].flatMap((s) => [...s]));
  expect([...defined].sort()).toEqual([...planned].sort());
  expect(defined.size).toBe(21);
  const exported = buildTraceExport(asResults(), [...defined], []);
  expect(exported.v).toBe(1);
});

it(R('JT-21 trace export rejects unknown ids and duplicate registrations'), () => {
  const results = asResults();
  const ids = [...shellRequirementIds()];
  expect(() => buildTraceExport([...results, { tid: 'JT-21', title: 'JT-21 REQ-SHL-99: x', reqs: ['REQ-SHL-99'], status: 'passed' }], ids, [])).toThrow(/REQ-SHL-99/);
  expect(() => buildTraceExport([...results, results[0]], ids, [])).toThrow(/duplicate/i);
  expect(() => buildTraceExport([{ tid: 'JT-21', title: 'JT-21 REQ-SHL-21: x', reqs: [], status: 'passed' }], ids, [])).toThrow();
});

it(R('JT-21 zero-test requirements are reported as uncovered; only passing tests cover a requirement'), () => {
  const ids = ['REQ-SHL-03', 'REQ-SHL-07', 'REQ-SHL-21'];
  const results: TestResult[] = [
    { tid: 'JT-03', title: 'JT-03 REQ-SHL-03: a', reqs: ['REQ-SHL-03'], status: 'passed' },
    { tid: 'JT-07', title: 'JT-07 REQ-SHL-07: a', reqs: ['REQ-SHL-07'], status: 'passed' },
    { tid: 'JT-07', title: 'JT-07 REQ-SHL-07: b', reqs: ['REQ-SHL-07'], status: 'failed' },
  ];
  const exported = buildTraceExport(results, ids, []);
  expect(exported.automated.covered).toEqual(['REQ-SHL-03']);
  expect(exported.automated.uncovered).toEqual(['REQ-SHL-21']);
  const skipped = buildTraceExport([{ ...results[0], status: 'skipped' }], ['REQ-SHL-03'], []);
  expect(skipped.automated.covered).toEqual([]);
});

it(R('JT-21 manual sign-offs are passed through separately and never counted as automated coverage'), () => {
  const ids = ['REQ-SHL-01', 'REQ-SHL-19', 'REQ-SHL-21'];
  const results: TestResult[] = [{ tid: 'JT-21', title: 'JT-21 REQ-SHL-21: a', reqs: ['REQ-SHL-21'], status: 'passed' }];
  const exported = buildTraceExport(results, ids, ['MAN-01', 'MAN-03']);
  expect(exported.manual).toEqual(['MAN-01', 'MAN-03']);
  expect(exported.automated.tests).toHaveLength(1);
  expect(exported.automated.covered).toEqual(['REQ-SHL-21']);
  expect(exported.automated.uncovered).toEqual(['REQ-SHL-01', 'REQ-SHL-19']);
  const text = JSON.stringify(exported.automated);
  expect(text).not.toContain('MAN-');
  // A manual id smuggled in as a test registration is rejected.
  expect(() => buildTraceExport([{ tid: 'MAN-01', title: 'MAN-01 REQ-SHL-01: attest', reqs: ['REQ-SHL-01'], status: 'passed' }], ids, [])).toThrow();
});
