/**
 * Export of Jest registrations/results for the R20 generator
 * (20_SHELL.md REQ-SHL-21). Manual sign-offs are never automated coverage.
 */

export interface Registration {
  /** `JT-nn` or `JT-SHL-19-01`. */
  tid: string;
  title: string;
  reqs: string[];
}

export interface TestResult extends Registration {
  status: 'passed' | 'failed' | 'skipped';
}

export interface TraceExport {
  v: 1;
  automated: {
    tests: TestResult[];
    /** REQ ids with >= 1 passing test and no failing/skipped test. */
    covered: string[];
    /** REQ ids with zero registered tests; non-empty is a gate failure. */
    uncovered: string[];
  };
  /** Named manual gates (`MAN-nn`) passed through, never counted above. */
  manual: string[];
}

const TEST_ID = /^(JT-\d{2}|JT-SHL-19-01)$/;

/**
 * Build the export. Throws on an unknown REQ id or a duplicate (tid, title).
 * `manualIds` are reported separately and excluded from every automated figure.
 */
export function buildTraceExport(
  results: readonly TestResult[],
  requirementIds: readonly string[],
  manualIds: readonly string[],
): TraceExport {
  const known = new Set(requirementIds);
  const seen = new Set<string>();
  const passes = new Map<string, number>();
  const failures = new Map<string, number>();
  for (const result of results) {
    if (!TEST_ID.test(result.tid)) {
      throw new Error(`trace export: invalid test id ${JSON.stringify(result.tid)} (manual gates are not tests)`);
    }
    if (result.reqs.length === 0) {
      throw new Error(`trace export: ${result.tid} registers no requirement`);
    }
    const key = `${result.tid}\u0000${result.title}`;
    if (seen.has(key)) {
      throw new Error(`trace export: duplicate registration ${result.tid} ${JSON.stringify(result.title)}`);
    }
    seen.add(key);
    for (const req of result.reqs) {
      if (!known.has(req)) {
        throw new Error(`trace export: unknown requirement id ${req} in ${result.tid}`);
      }
      const bucket = result.status === 'passed' ? passes : failures;
      bucket.set(req, (bucket.get(req) ?? 0) + 1);
    }
  }
  const covered = requirementIds.filter((id) => (passes.get(id) ?? 0) > 0 && !failures.has(id));
  const uncovered = requirementIds.filter((id) => !passes.has(id) && !failures.has(id));
  return {
    v: 1,
    automated: { tests: results.map((r) => ({ ...r, reqs: [...r.reqs] })), covered, uncovered },
    manual: [...manualIds],
  };
}
