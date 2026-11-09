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
import { NodeSpawner } from './node-spawner';
import type { FileSystemOps, Spawner } from './types';

export interface NodeApis {
  spawner: Spawner;
  fs: FileSystemOps;
  /** Reveal a folder in the OS file manager (Electron shell); never executes files. */
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
  shell?: { openPath(path: string): Promise<string> };
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
    fs: new NodeFs(fsp),
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
