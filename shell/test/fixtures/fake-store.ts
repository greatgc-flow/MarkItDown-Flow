/**
 * In-memory SettingsStore with fault injection (FX-70 "write-denied file";
 * FX-65-style interrupted write). Writes are atomic by construction: a failing
 * write never mutates the stored text.
 */
import type { SettingsStore, StoreFile } from '../../src/pure/persist';

export interface FaultPlan {
  /** Reject the Nth write call (1-based) with EACCES-like error. */
  denyWriteNumber?: number;
  /** Reject every write to this file. */
  denyFile?: StoreFile;
}

export class FakeStore implements SettingsStore {
  readonly files = new Map<string, string>();
  readonly writeLog: { name: StoreFile; text: string }[] = [];
  private writeCalls = 0;

  constructor(initial: Partial<Record<StoreFile, string>> = {}, private readonly faults: FaultPlan = {}) {
    for (const [name, text] of Object.entries(initial)) {
      if (text !== undefined) this.files.set(name, text);
    }
  }

  async read(name: StoreFile): Promise<string | null> {
    return this.files.has(name) ? (this.files.get(name) as string) : null;
  }

  async write(name: StoreFile, text: string): Promise<void> {
    this.writeCalls += 1;
    if (this.faults.denyFile === name || this.faults.denyWriteNumber === this.writeCalls) {
      const err = new Error(`EACCES: permission denied, open '${name}'`) as NodeJS.ErrnoException;
      err.code = 'EACCES';
      throw err;
    }
    this.files.set(name, text);
    this.writeLog.push({ name, text });
  }

  async list(): Promise<string[]> {
    return [...this.files.keys()].sort();
  }

  text(name: StoreFile): string | undefined {
    return this.files.get(name);
  }
}

/** Parse or fail loudly: every stored file must remain valid JSON. */
export function parseJson(text: string | undefined): unknown {
  if (text === undefined) throw new Error('file missing');
  return JSON.parse(text);
}
