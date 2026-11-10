/**
 * Jest registration helper (30_TESTPLAN.md section 2.2, REQ-SHL-21).
 *
 *   it(req('REQ-SHL-03')('JT-03 missing schemaVersion identifies v1'), () => {...})
 *
 * builds the title `JT-03 REQ-SHL-03: missing schemaVersion identifies v1` and
 * throws at registration on an unknown REQ id, an unknown/misspelled test id, a
 * planned REQ missing from the marker set, or a duplicate (tid, description).
 *
 * Title format follows the orchestrator's instruction (`JT-xx REQ-SHL-yy:`);
 * see the open question in the step-8 report about TESTPLAN 2.2's order.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';

export const REPO_ROOT = path.resolve(__dirname, '..', '..');
const DOCS = path.join(REPO_ROOT, 'docs', 'renewal');

export const TEST_ID_PATTERN = /^(JT-\d{2}|JT-SHL-19-01)\b/;
const REQ_ID_PATTERN = /^REQ-[A-Z]+-\d{2}$/;

function readDoc(name: string): string {
  return fs.readFileSync(path.join(DOCS, name), 'utf8');
}

/** Definition lines `^REQ-SHL-nn MUST` in 20_SHELL.md; deleted ids are exempt. */
export function shellRequirementIds(): Set<string> {
  const ids = new Set<string>();
  for (const line of readDoc('20_SHELL.md').split(/\r?\n/)) {
    const m = /^(?:- )?(REQ-SHL-\d{2})\b(.*)$/.exec(line);
    if (m && !/^\s*\(deleted\b/i.test(m[2])) {
      ids.add(m[1]);
    }
  }
  if (ids.size === 0) {
    throw new Error('No REQ-SHL definitions found in 20_SHELL.md');
  }
  return ids;
}

/** Planned `JT-*` rows of 30_TESTPLAN.md section 4.3 -> required REQ set. */
export function plannedShellTests(): Map<string, Set<string>> {
  const text = readDoc('30_TESTPLAN.md');
  const catalog = text.split('## 4. Test catalog', 2)[1]?.split('## 5.', 2)[0] ?? '';
  const planned = new Map<string, Set<string>>();
  for (const line of catalog.split(/\r?\n/)) {
    if (!line.startsWith('| ')) continue;
    const cells = line.split('|').map((c) => c.trim());
    if (cells.length < 4 || !TEST_ID_PATTERN.test(cells[1]) || !/^(JT-\d{2}|JT-SHL-19-01)$/.test(cells[1])) continue;
    planned.set(cells[1], new Set(cells[2].match(/REQ-[A-Z]+-\d{2}/g) ?? []));
  }
  if (planned.size === 0) {
    throw new Error('No JT rows found in 30_TESTPLAN.md section 4.3');
  }
  return planned;
}

export interface Registered {
  tid: string;
  title: string;
  reqs: string[];
}

const registry: Registered[] = [];
const seen = new Set<string>();

let knownReqs: Set<string> | null = null;
let planned: Map<string, Set<string>> | null = null;

function known(): { reqs: Set<string>; planned: Map<string, Set<string>> } {
  knownReqs ??= shellRequirementIds();
  planned ??= plannedShellTests();
  return { reqs: knownReqs, planned };
}

/** Build a traceable title and register it; throws on any registration error. */
export function req(...reqIds: string[]): (title: string) => string {
  if (reqIds.length === 0) {
    throw new Error('req(): at least one REQ id is required');
  }
  const { reqs, planned: plan } = known();
  for (const id of reqIds) {
    if (!REQ_ID_PATTERN.test(id) || !reqs.has(id)) {
      throw new Error(`req(): unknown requirement id ${JSON.stringify(id)}`);
    }
  }
  if (new Set(reqIds).size !== reqIds.length) {
    throw new Error(`req(): duplicate requirement id in ${JSON.stringify(reqIds)}`);
  }
  return (title: string): string => {
    const m = TEST_ID_PATTERN.exec(title);
    if (!m) {
      throw new Error(`req(): title must start with a JT id: ${JSON.stringify(title)}`);
    }
    const tid = m[1];
    const description = title.slice(tid.length).trim();
    if (!description) {
      throw new Error(`req(): empty description for ${tid}`);
    }
    const required = plan.get(tid);
    if (!required) {
      throw new Error(`req(): test id ${tid} is not in 30_TESTPLAN.md section 4.3`);
    }
    for (const id of required) {
      if (!reqIds.includes(id)) {
        throw new Error(`req(): ${tid} must register planned requirement ${id}`);
      }
    }
    const dedupe = `${tid}\u0000${description}`;
    if (seen.has(dedupe)) {
      throw new Error(`req(): duplicate test ${tid} ${JSON.stringify(description)}`);
    }
    seen.add(dedupe);
    const full = `${tid} ${reqIds.join(' ')}: ${description}`;
    registry.push({ tid, title: full, reqs: [...reqIds] });
    return full;
  };
}

/** Snapshot of registrations made so far in this test file's module registry. */
export function registrations(): readonly Registered[] {
  return registry.slice();
}

/** Test-only: forget registrations (used by JT-21 to probe duplicate detection). */
export function resetRegistrationsForTest(): void {
  registry.length = 0;
  seen.clear();
}
