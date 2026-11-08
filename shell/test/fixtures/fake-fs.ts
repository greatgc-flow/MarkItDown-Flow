/**
 * In-memory FileSystemOps / SpoolFs with path semantics configurable per test
 * (symlink and realpath maps). Records every mutation for "nothing written"
 * assertions.
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
  readonly platform: HostPlatform;

  constructor(options: FakeFsOptions = {}) {
    this.platform = options.platform ?? (process.platform === 'win32' ? 'win32' : 'posix');
    for (const d of options.directories ?? []) this.directories.add(this.norm(d));
    for (const [k, v] of Object.entries(options.links ?? {})) this.links.set(this.norm(k), this.norm(v));
  }

  norm(p: string): string {
    const slashed = p.replace(/\\/g, '/').replace(/\/+$/, '');
    return this.platform === 'win32' ? slashed.toLowerCase() : slashed;
  }

  async readFile(path: string): Promise<Uint8Array | null> {
    return this.files.get(this.norm(path)) ?? null;
  }

  async writeFile(path: string, data: Uint8Array): Promise<void> {
    this.mutations.push(`write:${path}`);
    this.files.set(this.norm(path), data.slice());
  }

  async appendFile(path: string, data: Uint8Array): Promise<void> {
    this.mutations.push(`append:${path}`);
    const prev = this.files.get(this.norm(path)) ?? new Uint8Array(0);
    const next = new Uint8Array(prev.length + data.length);
    next.set(prev, 0);
    next.set(data, prev.length);
    this.files.set(this.norm(path), next);
  }

  async remove(path: string): Promise<void> {
    this.mutations.push(`remove:${path}`);
    this.files.delete(this.norm(path));
  }

  async rename(from: string, to: string): Promise<void> {
    this.mutations.push(`rename:${from}->${to}`);
    const data = this.files.get(this.norm(from));
    if (!data) throw new Error(`ENOENT: ${from}`);
    this.files.delete(this.norm(from));
    this.files.set(this.norm(to), data);
  }

  async list(dir: string): Promise<string[]> {
    const prefix = this.norm(dir) + '/';
    const names = new Set<string>();
    for (const key of [...this.files.keys(), ...this.directories]) {
      if (key.startsWith(prefix)) {
        const rest = key.slice(prefix.length);
        if (rest && !rest.includes('/')) names.add(rest);
      }
    }
    return [...names].sort();
  }

  async size(path: string): Promise<number | null> {
    return this.files.get(this.norm(path))?.length ?? null;
  }

  async mkdir(dir: string): Promise<void> {
    this.mutations.push(`mkdir:${dir}`);
    this.directories.add(this.norm(dir));
  }

  async realpath(path: string): Promise<string | null> {
    const n = this.norm(path);
    const resolved = this.links.get(n) ?? n;
    if (this.files.has(resolved) || this.directories.has(resolved)) return resolved;
    return null;
  }

  async isDirectory(path: string): Promise<boolean> {
    const real = await this.realpath(path);
    return real !== null && this.directories.has(real);
  }

  async isSymlink(path: string): Promise<boolean> {
    return this.links.has(this.norm(path));
  }

  text(path: string): string | undefined {
    const data = this.files.get(this.norm(path));
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
