/**
 * Export of Jest registrations/results for the R20 generator
 * (20_SHELL.md REQ-SHL-21). Manual sign-offs are never automated coverage.
 */
import { NotImplementedError } from './errors';

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

/**
 * Build the export. Throws on an unknown REQ id or a duplicate (tid, title).
 * `manualIds` are reported separately and excluded from every automated figure.
 */
export function buildTraceExport(
  _results: readonly TestResult[],
  _requirementIds: readonly string[],
  _manualIds: readonly string[],
): TraceExport {
  throw new NotImplementedError('buildTraceExport');
}
