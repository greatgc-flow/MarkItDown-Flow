/**
 * Private spool for structured engine stdout (20_SHELL.md REQ-SHL-13).
 * Transport storage only, never publication staging. Filesystem is injected.
 */
import type { Decoded, RunReport } from './protocol';
import { NotImplementedError } from './errors';

/** Bounded read size used when draining a spool file. */
export const SPOOL_READ_BUFFER_BYTES = 65536;

/** Owned spool file name: `mdflow-spool-<nonce>.json` inside the owned directory. */
export const SPOOL_NAME_PATTERN = /^mdflow-spool-[0-9a-f]{16}\.json$/;

export interface SpoolFs {
  append(name: string, chunk: Uint8Array): Promise<void>;
  /** Read at most `max` bytes starting at `offset`; empty array at EOF. */
  read(name: string, offset: number, max: number): Promise<Uint8Array>;
  remove(name: string): Promise<void>;
  list(): Promise<string[]>;
}

export class Spool {
  constructor(_fs: SpoolFs, _nonce: string) {
    throw new NotImplementedError('Spool');
  }

  get name(): string {
    throw new NotImplementedError('Spool.name');
  }

  write(_chunk: Uint8Array): Promise<void> {
    throw new NotImplementedError('Spool.write');
  }

  /** Drain with bounded reads, decode, then remove the file whether or not decoding succeeded. */
  finish(): Promise<Decoded<RunReport>> {
    throw new NotImplementedError('Spool.finish');
  }

  /** Cancel/handled failure: remove without decoding. */
  discard(): Promise<void> {
    throw new NotImplementedError('Spool.discard');
  }
}

/** Names in the owned directory that are verified owned stale spools; others are left alone. */
export function recoverableSpools(_names: readonly string[]): string[] {
  throw new NotImplementedError('recoverableSpools');
}
