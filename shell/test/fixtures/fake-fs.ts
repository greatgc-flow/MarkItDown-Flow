/**
 * In-memory FileSystemOps / SpoolFs with path semantics configurable per test
 * (symlink and realpath maps). Records every mutation for "nothing written"
 * assertions. Names are stored case-preserved; on win32 lookups are
 * case-insensitive (like NTFS), so listings return the original spelling.
 */
import type { SpoolFs } from '../../src/pure/spool';
import type { FileSystemOps, HostPlatform } from '../../src/process/types';

export interface FakeFsOptions {
  platform?: HostPlatform;
  /** path -> real path (symlinks). */
  links?: Record<string, string>;
  directories?: string[];
}

export class FakeFs implements FileSystemOps {
  readonly files = new Map<string, Uint8Array>();
  readonly directories = new Set<string>();
  readonly links = new Map<string, string>();
  readonly mutations: string[] = [];
  /** Every `readRange` call as `[offset, length]` (bounded-read oracle, JT-13). */
  readonly readRanges: [number, number][] = [];
  /** Every whole-file `readFile` path. */
  readonly wholeFileReads: string[] = [];
  readonly platform: HostPlatform;

  constructor(options: FakeFsOptions = {}) {
    this.platform = options.platform ?? (process.platform === 'win32' ? 'win32' : 'posix');
    for (const d of options.directories ?? []) this.directories.add(this.norm(d));
    for (const [k, v] of Object.entries(options.links ?? {})) this.links.set(this.norm(k), this.norm(v));
  }

  /** Forward slashes, no trailing slash; case is preserved. */
  norm(p: string): string {
    return p.replace(/\\/g, '/').replace(/\/+$/, '');
  }

  private fold(p: string): string {
    return this.platform === 'win32' ? p.toLowerCase() : p;
  }

  /** Existing stored key matching `p` (case-insensitively on win32), or the normalized input. */
  key(p: string): string {
    const n = this.norm(p);
    if (this.files.has(n) || this.directories.has(n) || this.links.has(n)) return n;
    if (this.platform === 'win32') {
      const folded = n.toLowerCase();
      for (const existing of [...this.files.keys(), ...this.directories, ...this.links.keys()]) {
        if (existing.toLowerCase() === folded) return existing;
      }
    }
    return n;
  }

  async readFile(path: string): Promise<Uint8Array | null> {
    this.wholeFileReads.push(path);
    return this.files.get(this.key(path)) ?? null;
  }

  async readRange(path: string, offset: number, length: number): Promise<Uint8Array> {
    this.readRanges.push([offset, length]);
    const data = this.files.get(this.key(path));
    if (!data) throw new Error(`ENOENT: ${path}`);
    return data.slice(offset, offset + length);
  }

  async writeFile(path: string, data: Uint8Array): Promise<void> {
    this.mutations.push(`write:${path}`);
    this.files.set(this.key(path), data.slice());
  }

  async appendFile(path: string, data: Uint8Array): Promise<void> {
    this.mutations.push(`append:${path}`);
    const key = this.key(path);
    const prev = this.files.get(key) ?? new Uint8Array(0);
    const next = new Uint8Array(prev.length + data.length);
    next.set(prev, 0);
    next.set(data, prev.length);
    this.files.set(key, next);
  }

  async remove(path: string): Promise<void> {
    this.mutations.push(`remove:${path}`);
    this.files.delete(this.key(path));
  }

  async rename(from: string, to: string): Promise<void> {
    this.mutations.push(`rename:${from}->${to}`);
    const fromKey = this.key(from);
    const data = this.files.get(fromKey);
    if (!data) throw new Error(`ENOENT: ${from}`);
    this.files.delete(fromKey);
    this.files.set(this.key(to), data);
  }

  async list(dir: string): Promise<string[]> {
    const prefix = this.fold(this.key(dir)) + '/';
    const names = new Set<string>();
    for (const stored of [...this.files.keys(), ...this.directories]) {
      if (this.fold(stored).startsWith(prefix)) {
        const rest = stored.slice(prefix.length);
        if (rest && !rest.includes('/')) names.add(rest);
      }
    }
    return [...names].sort();
  }

  async size(path: string): Promise<number | null> {
    return this.files.get(this.key(path))?.length ?? null;
  }

  async mkdir(dir: string): Promise<void> {
    this.mutations.push(`mkdir:${dir}`);
    this.directories.add(this.key(dir));
  }

  async realpath(path: string): Promise<string | null> {
    const key = this.key(path);
    const resolved = this.links.has(key) ? this.key(this.links.get(key) as string) : key;
    if (this.files.has(resolved) || this.directories.has(resolved)) return resolved;
    return null;
  }

  async isDirectory(path: string): Promise<boolean> {
    const real = await this.realpath(path);
    return real !== null && this.directories.has(real);
  }

  async isSymlink(path: string): Promise<boolean> {
    return this.links.has(this.key(path));
  }

  text(path: string): string | undefined {
    const data = this.files.get(this.key(path));
    return data ? new TextDecoder().decode(data) : undefined;
  }
}

/** SpoolFs over a directory of a FakeFs. */
export class FakeSpoolFs implements SpoolFs {
  readonly reads: number[] = [];

  constructor(readonly fs: FakeFs, readonly dir: string) {}

  private at(name: string): string {
    return `${this.dir}/${name}`;
  }

  async append(name: string, chunk: Uint8Array): Promise<void> {
    await this.fs.appendFile(this.at(name), chunk);
  }

  async read(name: string, offset: number, max: number): Promise<Uint8Array> {
    this.reads.push(max);
    const data = await this.fs.readFile(this.at(name));
    if (!data) throw new Error(`ENOENT: ${name}`);
    return data.slice(offset, offset + max);
  }

  async remove(name: string): Promise<void> {
    await this.fs.remove(this.at(name));
  }

  async list(): Promise<string[]> {
    return this.fs.list(this.dir);
  }
}
