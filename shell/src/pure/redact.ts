/**
 * Shell-side redaction for notices, logs and diagnostics
 * (20_SHELL.md REQ-SHL-05/06/18; SPEC section 9 REQ-SEC-02).
 */
import { NotImplementedError } from './errors';

export interface RedactOptions {
  /** Known credential values; every occurrence becomes `***`. */
  secrets?: readonly string[];
  /** Home directory prefix; replaced by `~`. */
  home?: string;
  /** Vault root; paths under it become vault-relative. */
  vault?: string;
}

export const REDACTED = '***';

export function redactText(_text: string, _options: RedactOptions): string {
  throw new NotImplementedError('redactText');
}

/** Deep-redact every string in a JSON-like value. */
export function redactValue<T>(_value: T, _options: RedactOptions): T {
  throw new NotImplementedError('redactValue');
}
