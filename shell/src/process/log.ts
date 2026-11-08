/**
 * Plugin-local redacted logs (20_SHELL.md REQ-SHL-18): five rotated 1 MiB
 * files holding timestamp, stage, code, count and status only.
 */
import { NotImplementedError } from '../pure/errors';
import type { RedactOptions } from '../pure/redact';
import type { FileSystemOps } from './types';

export const LOG_FILE_LIMIT_BYTES = 1024 * 1024;
export const LOG_FILE_COUNT = 5;
export const LOG_DIR_NAME = 'logs';
/** `mdflow.log` is current; `mdflow.1.log` .. `mdflow.4.log` are older. */
export const LOG_FILE_NAMES: readonly string[] = ['mdflow.log', 'mdflow.1.log', 'mdflow.2.log', 'mdflow.3.log', 'mdflow.4.log'];

/** The only fields a log line may carry. */
export const LOG_RECORD_FIELDS = ['ts', 'stage', 'code', 'count', 'status'] as const;

export interface LogRecord {
  ts: string;
  stage?: string;
  code?: string;
  count?: number;
  status?: string;
}

export class RotatingLog {
  constructor(_fs: FileSystemOps, _dir: string, _redact: RedactOptions) {}

  /** Append one JSON line with allowlisted fields only; rotate when the current file would exceed the limit. */
  async write(_record: LogRecord): Promise<void> {
    throw new NotImplementedError('RotatingLog.write');
  }

  /** Absolute owned log directory (the only folder `open-log-folder` opens). */
  get directory(): string {
    throw new NotImplementedError('RotatingLog.directory');
  }
}

export interface DiagnosticsCopyInput {
  version: unknown;
  probes: unknown;
  /** Engine codes seen in the last run. */
  codes: readonly string[];
  /** Paths to identify relative to the vault or with the home prefix redacted. */
  paths: readonly string[];
}

/** Redacted text for the diagnostics copy button: versions/probe results and codes only. */
export function diagnosticsCopy(_input: DiagnosticsCopyInput, _redact: RedactOptions): string {
  throw new NotImplementedError('diagnosticsCopy');
}
