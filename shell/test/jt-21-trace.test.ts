/**
 * JT-21 / REQ-SHL-21: `req()` rejects unknown/duplicate ids, unregistered
 * planned requirements and manual-gate ids; registrations reach R20's
 * generator (`tools/trace.py`) through the jest-junit export whose titles
 * carry the REQ ids; manual sign-offs are never test registrations.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { plannedShellTests, registrations, req, REPO_ROOT, shellRequirementIds, TEST_ID_PATTERN } from './req';

const R = req('REQ-SHL-21');

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
  expect(registrations().length).toBeGreaterThan(0);
});

it(R('JT-21 req() rejects a duplicate (test id, description) registration'), () => {
  const existing = registrations().find((r) => r.tid === 'JT-21');
  expect(existing).toBeDefined();
  const description = (existing as { title: string }).title.split(': ').slice(1).join(': ');
  expect(() => req('REQ-SHL-21')(`JT-21 ${description}`)).toThrow(/duplicate test JT-21/);
  // A distinct description for the same id is allowed, and the title carries every REQ.
  const title = req('REQ-SHL-21')('JT-21 probe registration for duplicate detection');
  expect(title).toBe('JT-21 REQ-SHL-21: probe registration for duplicate detection');
  expect(registrations().some((r) => r.title === title && r.reqs.includes('REQ-SHL-21'))).toBe(true);
});

it(R('JT-21 planned catalog and 20_SHELL.md definitions agree on the 21 shell requirement ids'), () => {
  const defined = shellRequirementIds();
  const planned = new Set([...plannedShellTests().values()].flatMap((s) => [...s]));
  expect([...defined].sort()).toEqual([...planned].sort());
  expect(defined.size).toBe(21);
});

it(R('JT-21 manual gates are never test registrations: MAN-* ids are rejected by the marker grammar'), () => {
  expect(TEST_ID_PATTERN.test('MAN-01 attestation')).toBe(false);
  expect(() => req('REQ-SHL-01')('MAN-01 R15 attestation present')).toThrow(/must start with a JT id/);
  for (const registered of registrations()) {
    expect(registered.tid).toMatch(/^(JT-\d{2}|JT-SHL-19-01)$/);
    expect(registered.reqs.length).toBeGreaterThan(0);
    expect(registered.title).not.toMatch(/MAN-\d{2}/);
  }
});

it(R('JT-21 registrations reach the R20 generator through the jest-junit export with REQ-bearing titles'), () => {
  const config = fs.readFileSync(path.join(REPO_ROOT, 'shell', 'jest.config.js'), 'utf8');
  expect(config).toContain('jest-junit');
  expect(config).toContain("outputName: 'junit-shell.xml'");
  expect(config).toContain("titleTemplate: '{title}'");
  // Every registered title starts with its JT id and names each REQ so `trace.py` can parse it from the XML.
  for (const registered of registrations()) {
    expect(registered.title.startsWith(`${registered.tid} `)).toBe(true);
    for (const id of registered.reqs) expect(registered.title).toContain(id);
  }
  const trace = fs.readFileSync(path.join(REPO_ROOT, 'tools', 'trace.py'), 'utf8');
  expect(trace).toContain('junit-shell');
});
