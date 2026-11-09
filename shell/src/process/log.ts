/**
 * Plugin-local redacted logs (20_SHELL.md REQ-SHL-18): five rotated 1 MiB
 * files holding timestamp, stage, code, count and status only.
 */
import { isKnownEngineCode } from '../pure/codes';
import { joinPath } from '../pure/paths';
import { type RedactOptions, redactText } from '../pure/redact';
import type { FileSystemOps, HostPlatform } from './types';

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

const encoder = new TextEncoder();

export class RotatingLog {
  private queue: Promise<void> = Promise.resolve();
  private dirReady = false;

  constructor(
    private readonly fs: FileSystemOps,
    private readonly dir: string,
    private readonly redact: RedactOptions,
    private readonly platform: HostPlatform = process.platform === 'win32' ? 'win32' : 'posix',
  ) {}

  private at(name: string): string {
    return joinPath(this.platform, this.dir, name);
  }

  /** Absolute owned log directory (the only folder `open-log-folder` opens). */
  get directory(): string {
    return this.dir;
  }

  /** Allowlisted, redacted line (pure). */
  line(record: LogRecord): string {
    const out: Record<string, string | number> = {};
    const raw = record as unknown as Record<string, unknown>;
    if (typeof raw.ts === 'string') out.ts = redactText(raw.ts, this.redact);
    if (typeof raw.stage === 'string') out.stage = redactText(raw.stage, this.redact);
    if (typeof raw.code === 'string') out.code = redactText(raw.code, this.redact);
    if (typeof raw.count === 'number' && Number.isFinite(raw.count)) out.count = raw.count;
    if (typeof raw.status === 'string') out.status = redactText(raw.status, this.redact);
    return JSON.stringify(out) + '\n';
  }

  /** Append one JSON line with allowlisted fields only; rotate when the current file would exceed the limit. */
  write(record: LogRecord): Promise<void> {
    const line = this.line(record);
    this.queue = this.queue.then(() => this.append(line)).catch(() => undefined);
    return this.queue;
  }

  private async append(line: string): Promise<void> {
    const bytes = encoder.encode(line);
    if (!this.dirReady) {
      await this.fs.mkdir(this.dir);
      this.dirReady = true;
    }
    const current = this.at(LOG_FILE_NAMES[0]);
    const size = (await this.fs.size(current)) ?? 0;
    if (size > 0 && size + bytes.length > LOG_FILE_LIMIT_BYTES) await this.rotate();
    await this.fs.appendFile(current, bytes);
  }

  private async rotate(): Promise<void> {
    const oldest = this.at(LOG_FILE_NAMES[LOG_FILE_COUNT - 1]);
    if ((await this.fs.size(oldest)) !== null) await this.fs.remove(oldest);
    for (let i = LOG_FILE_COUNT - 2; i >= 0; i--) {
      const from = this.at(LOG_FILE_NAMES[i]);
      if ((await this.fs.size(from)) === null) continue;
      await this.fs.rename(from, this.at(LOG_FILE_NAMES[i + 1]));
    }
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Redacted text for the diagnostics copy button: versions/probe results and codes only. */
export function diagnosticsCopy(input: DiagnosticsCopyInput, redact: RedactOptions): string {
  const lines: string[] = ['MarkItDown Flow diagnostics'];
  const version = input.version;
  if (isRecord(version)) {
    if (version.enabled === true && isRecord(version.info)) {
      for (const [key, value] of Object.entries(version.info)) {
        if (typeof value === 'string' || typeof value === 'number') lines.push(`version.${key}: ${redactText(String(value), redact)}`);
        else if (value === null) lines.push(`version.${key}: missing`);
      }
    } else if (version.enabled === false) {
      lines.push(`version: blocked (${String(version.reason ?? 'unknown')}${typeof version.field === 'string' ? ` ${version.field}` : ''})`);
    }
  } else {
    lines.push('version: not probed');
  }
  if (Array.isArray(input.probes)) {
    for (const probe of input.probes) {
      if (!isRecord(probe)) continue;
      const command = typeof probe.command === 'string' ? probe.command : '?';
      const args = Array.isArray(probe.args) ? probe.args.filter((a): a is string => typeof a === 'string').join(' ') : '';
      const result = typeof probe.result === 'string' ? probe.result : '?';
      const found = typeof probe.version === 'string' ? ` ${probe.version}` : '';
      lines.push(`probe: ${command} ${args} -> ${result}${found}`.replace(/\s+/g, ' '));
    }
  }
  const codes = input.codes.filter(isKnownEngineCode);
  lines.push(`codes: ${codes.length > 0 ? codes.join(' ') : '-'}`);
  for (const path of input.paths) lines.push(`path: ${redactText(path, redact)}`);
  return lines.join('\n') + '\n';
}
