/**
 * Private spool for structured engine stdout (20_SHELL.md REQ-SHL-13).
 * Transport storage only, never publication staging. Filesystem is injected.
 */
import { decodeReport, type Decoded, type RunReport } from './protocol';

/** Bounded read size used when draining a spool file. */
export const SPOOL_READ_BUFFER_BYTES = 65536;

/** Owned spool file name: `mdflow-spool-<nonce>.json` inside the owned directory. */
export const SPOOL_NAME_PATTERN = /^mdflow-spool-[0-9a-f]{16}\.json$/;

const NONCE_PATTERN = /^[0-9a-f]{16}$/;

export interface SpoolFs {
  append(name: string, chunk: Uint8Array): Promise<void>;
  /** Read at most `max` bytes starting at `offset`; empty array at EOF. */
  read(name: string, offset: number, max: number): Promise<Uint8Array>;
  remove(name: string): Promise<void>;
  list(): Promise<string[]>;
}

export class Spool {
  private readonly fileName: string;
  private written = false;

  constructor(private readonly fs: SpoolFs, nonce: string) {
    if (!NONCE_PATTERN.test(nonce)) throw new Error('spool nonce must be 16 lowercase hex characters');
    this.fileName = `mdflow-spool-${nonce}.json`;
  }

  get name(): string {
    return this.fileName;
  }

  async write(chunk: Uint8Array): Promise<void> {
    this.written = true;
    await this.fs.append(this.fileName, chunk);
  }

  /** Drain with bounded reads, decode the 7.4 report, then remove the file whether or not decoding succeeded. */
  async finish(): Promise<Decoded<RunReport>> {
    return this.finishWith(decodeReport);
  }

  /** Same as `finish` with an injected decoder (7.1 Plans for `plan` stdout). */
  async finishWith<T>(decode: (text: string) => Decoded<T>): Promise<Decoded<T>> {
    try {
      if (!this.written) return { ok: false, diagnostic: 'shell.PROTOCOL', reason: 'report missing' };
      const parts: Uint8Array[] = [];
      let offset = 0;
      for (;;) {
        const chunk = await this.fs.read(this.fileName, offset, SPOOL_READ_BUFFER_BYTES);
        if (chunk.length === 0) break;
        parts.push(chunk);
        offset += chunk.length;
      }
      const whole = new Uint8Array(offset);
      let position = 0;
      for (const part of parts) {
        whole.set(part, position);
        position += part.length;
      }
      let text: string;
      try {
        text = new TextDecoder('utf-8', { fatal: true }).decode(whole);
      } catch {
        return { ok: false, diagnostic: 'shell.PROTOCOL', reason: 'report is not UTF-8' };
      }
      return decode(text);
    } catch {
      return { ok: false, diagnostic: 'shell.PROTOCOL', reason: 'spool unreadable' };
    } finally {
      await this.discard();
    }
  }

  /** Cancel/handled failure: remove without decoding. */
  async discard(): Promise<void> {
    try {
      await this.fs.remove(this.fileName);
    } catch {
      // Already gone or not removable: nothing owned remains to recover from this handle.
    }
  }
}

/** Names in the owned directory that are verified owned stale spools; others are left alone. */
export function recoverableSpools(names: readonly string[]): string[] {
  return names.filter((name) => SPOOL_NAME_PATTERN.test(name));
}
