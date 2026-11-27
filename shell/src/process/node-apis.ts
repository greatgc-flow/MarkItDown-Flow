/**
 * Lazy Node/Electron API access (20_SHELL.md REQ-SHL-02): nothing here is
 * loaded before the single `Platform.isDesktop` guard in main.ts passes.
 * Tests mock this module to prove the mobile path loads no Node API.
 *
 * File selection uses the public DOM file input (dom-picker.ts) rather than
 * the removed `electron.remote` dialog; absolute paths come from Electron's
 * `webUtils.getPathForFile` with the legacy `File.path` as fallback.
 */
import { type PickOutcome, pickWithDomInput, type PickerDocument, type PickerInput } from './dom-picker';
import type { FileRow, Mode, StrictResult } from './strict';
import { NodeSpawner } from './node-spawner';
import type { FileSystemOps, Spawner } from './types';

/** Create a private, short-lived UTF-8 manifest for selections that exceed the OS argv budget. */
export async function withInputList<T>(inputs: readonly string[], run: (args: string[]) => Promise<T>): Promise<T> {
  const fs = require('node:fs/promises') as typeof import('node:fs/promises');
  const path = require('node:path') as typeof import('node:path');
  const os = require('node:os') as typeof import('node:os');
  const folder = await fs.mkdtemp(path.join(os.tmpdir(), 'mdflow-inputs-'));
  try {
    const list = path.join(folder, 'selection.json');
    await fs.writeFile(list, JSON.stringify(inputs), {mode:0o600, flag:'wx'});
    return await run(['--input-list', list]);
  } finally { await fs.rm(folder, {recursive:true,force:true}); }
}

export interface SavedJob {
  result: StrictResult;
  inputs: string[];
  mode: Mode;
  outDir: string;
}
export interface JobJournal {
  append(row: FileRow): void;
  close(result?: StrictResult): void;
}

function jobDirectory(home: string, vault: string): string {
  const {createHash} = require('node:crypto') as typeof import('node:crypto');
  const path = require('node:path') as typeof import('node:path');
  return path.join(home, '.mdflow', 'jobs', createHash('sha256').update(vault).digest('hex'));
}

function beginJournal(home: string, vault: string, inputs: readonly string[], mode: Mode, outDir: string): JobJournal {
  const fs = require('node:fs') as typeof import('node:fs');
  const path = require('node:path') as typeof import('node:path');
  const {randomUUID} = require('node:crypto') as typeof import('node:crypto');
  const folder = jobDirectory(home, vault);
  fs.mkdirSync(folder, {recursive:true, mode:0o700});
  const file = path.join(folder, Date.now() + '-' + randomUUID() + '.jsonl');
  const fd = fs.openSync(file, 'wx', 0o600);
  const append = (value: unknown) => fs.writeFileSync(fd, JSON.stringify(value) + '\n');
  try { append({kind:'job', version:1, inputs, mode, outDir}); }
  catch(e) { fs.closeSync(fd); throw e; }
  let stopped = false;
  return {
    append: row => { if (!stopped) append(row); },
    close: result => {
      if (stopped) return;
      stopped = true;
      try {
        if (result) append({kind:'end', status:result.status, skipped:result.skipped, count:result.rows.length});
        fs.fsyncSync(fd);
      } finally { fs.closeSync(fd); }
    },
  };
}

async function lastJob(home: string, vault: string): Promise<SavedJob | null> {
  const fs = require('node:fs/promises') as typeof import('node:fs/promises');
  const path = require('node:path') as typeof import('node:path');
  const folder = jobDirectory(home,vault);
  let names;
  try { names = await fs.readdir(folder); }
  catch (e) { if ((e as NodeJS.ErrnoException).code === 'ENOENT') return null; throw e; }
  const name = names.filter(n => /^\d+-[0-9a-f-]{36}\.jsonl$/.test(n)).sort().pop();
  if (!name) return null;
  const file = path.join(folder, name);
  const info = await fs.lstat(file);
  if (!info.isFile() || info.size > 128 * 1024 * 1024) throw Error('Job exceeds the view limit');
  const lines = (await fs.readFile(file,'utf8')).split('\n');
  lines.pop(); // Ignore an incomplete trailing record after interruption.
  if (!lines.length) return null;
  const header = JSON.parse(lines.shift()!);
  if (header.kind !== 'job' || header.version !== 1 || !['run','extract-text'].includes(header.mode) ||
      !Array.isArray(header.inputs) || !header.inputs.every((v: unknown) => typeof v === 'string' && path.isAbsolute(v)) ||
      typeof header.outDir !== 'string') throw Error('Invalid saved job');
  const result: StrictResult = {rows:[], status:'interrupted', skipped:0};
  for (const line of lines) {
    const row = JSON.parse(line);
    if (row.kind === 'file' && typeof row.source?.relativePath === 'string' && typeof row.source?.path === 'string') result.rows.push(row);
    else if (row.kind === 'end' && row.count === result.rows.length && ['complete','interrupted','failed'].includes(row.status)) {
      result.status = row.status; result.skipped = row.skipped;
    } else throw Error('Invalid saved record');
  }
  return {result, inputs:header.inputs, mode:header.mode, outDir:header.outDir};
}

export interface NodeApis {
  beginJournal?(vault: string, inputs: readonly string[], mode: Mode, out: string): JobJournal;
  lastJob?(vault: string): Promise<SavedJob | null>;
  spawner: Spawner;
  fs: FileSystemOps;
  /** Reveal a folder in the OS file manager (Electron shell); never executes files. */
  revealFile?(path: string): Promise<void>;
  openFolder(path: string): Promise<void>;
  /** Clipboard text write for SetupModal copy buttons. */
  writeClipboard(text: string): Promise<void>;
  /** False when the host offers no file input at all; callers must notify instead of silently doing nothing. */
  pickerAvailable: boolean;
  /** Native-looking open dialogs through the DOM file input; every outcome is distinguishable (cancelled, empty, blocked). */
  pickFiles(): Promise<PickOutcome>;
  /** Folder mode: `selected.paths` holds the one chosen folder root. */
  pickFolder(): Promise<PickOutcome>;
  /** Absolute path of a `File` (drops/pickers); null when the host cannot provide one. */
  filePath(file: unknown): string | null;
  homeDir(): string;
  platform: 'win32' | 'posix';
}

type FsPromises = typeof import('node:fs/promises');
type OsModule = typeof import('node:os');

interface ElectronLike {
  shell?: { showItemInFolder?(path: string): void; openPath(path: string): Promise<string> };
  clipboard?: { writeText(text: string): void };
  webUtils?: { getPathForFile(file: unknown): string };
}

function optionalRequire<T>(name: string): T | null {
  try {
    return require(name) as T;
  } catch {
    return null;
  }
}

class NodeFs implements FileSystemOps {
  constructor(private readonly fsp: FsPromises) {}

  async readFile(path: string): Promise<Uint8Array | null> {
    try {
      const data = await this.fsp.readFile(path);
      return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    } catch {
      return null;
    }
  }

  /** Bounded positional read: `length` bytes at `offset`, fewer at the tail, empty at EOF; rejects for a missing file. */
  async readRange(path: string, offset: number, length: number): Promise<Uint8Array> {
    const handle = await this.fsp.open(path, 'r');
    try {
      const buffer = new Uint8Array(length);
      const { bytesRead } = await handle.read(buffer, 0, length, offset);
      return buffer.subarray(0, bytesRead);
    } finally {
      await handle.close();
    }
  }

  async writeFile(path: string, data: Uint8Array): Promise<void> {
    await this.fsp.writeFile(path, data, { mode: 0o600 });
  }

  async appendFile(path: string, data: Uint8Array): Promise<void> {
    await this.fsp.appendFile(path, data, { mode: 0o600 });
  }

  async remove(path: string): Promise<void> {
    await this.fsp.rm(path, { force: true });
  }

  async rename(from: string, to: string): Promise<void> {
    await this.fsp.rename(from, to);
  }

  async list(dir: string): Promise<string[]> {
    try {
      return (await this.fsp.readdir(dir)).sort();
    } catch {
      return [];
    }
  }

  async size(path: string): Promise<number | null> {
    try {
      return (await this.fsp.stat(path)).size;
    } catch {
      return null;
    }
  }

  async mkdir(dir: string): Promise<void> {
    await this.fsp.mkdir(dir, { recursive: true, mode: 0o700 });
  }

  async realpath(path: string): Promise<string | null> {
    try {
      return await this.fsp.realpath(path);
    } catch {
      return null;
    }
  }

  async isDirectory(path: string): Promise<boolean> {
    try {
      return (await this.fsp.stat(path)).isDirectory();
    } catch {
      return false;
    }
  }

  async isSymlink(path: string): Promise<boolean> {
    try {
      return (await this.fsp.lstat(path)).isSymbolicLink();
    } catch {
      return false;
    }
  }
}

let cached: NodeApis | null = null;

/** Loads `node:child_process`, `node:fs`, `node:os` and the Electron renderer module on first call. */
export function loadNodeApis(): NodeApis {
  if (cached) return cached;
  const fsp = require('node:fs/promises') as FsPromises;
  const os = require('node:os') as OsModule;
  const electron = optionalRequire<ElectronLike>('electron');
  const filePath = (file: unknown): string | null => {
    try {
      const resolved = electron?.webUtils?.getPathForFile(file);
      if (typeof resolved === 'string' && resolved.length > 0) return resolved;
    } catch {
      // Fall through to the legacy field.
    }
    const legacy = (file as { path?: unknown }).path;
    return typeof legacy === 'string' && legacy.length > 0 ? legacy : null;
  };
  const doc: PickerDocument | null = typeof document !== 'undefined'
    ? {
        createElement: (tag) => document.createElement(tag) as unknown as PickerInput,
        // Chromium ignores `input.click()` without transient user activation; report it instead of hanging (M3 N-06).
        hasUserActivation: () => {
          const activation = typeof navigator !== 'undefined' ? (navigator as { userActivation?: { isActive?: boolean } }).userActivation : undefined;
          return activation?.isActive ?? true;
        },
      }
    : null;
  cached = {
    spawner: new NodeSpawner(),
    beginJournal: (vault,inputs,mode,out) => beginJournal(os.homedir(),vault,inputs,mode,out),
    lastJob: vault => lastJob(os.homedir(),vault),
    fs: new NodeFs(fsp),
    async revealFile(path: string): Promise<void> {
      if (!electron?.shell?.showItemInFolder) throw Error('File manager unavailable');
      electron.shell.showItemInFolder(path);
    },
    async openFolder(path: string): Promise<void> {
      if (electron?.shell) await electron.shell.openPath(path);
    },
    async writeClipboard(text: string): Promise<void> {
      if (electron?.clipboard) electron.clipboard.writeText(text);
      else if (typeof navigator !== 'undefined' && navigator.clipboard) await navigator.clipboard.writeText(text);
    },
    pickerAvailable: doc !== null,
    pickFiles: () => (doc ? pickWithDomInput(doc, 'files', filePath) : Promise.resolve({ kind: 'blocked' })),
    pickFolder: () => (doc ? pickWithDomInput(doc, 'folder', filePath) : Promise.resolve({ kind: 'blocked' })),
    filePath,
    homeDir: () => os.homedir(),
    platform: process.platform === 'win32' ? 'win32' : 'posix',
  };
  return cached;
}
