/**
 * Lazy Node/Electron API access (20_SHELL.md REQ-SHL-02): nothing here is
 * loaded before the single `Platform.isDesktop` guard in main.ts passes.
 * Tests mock this module to prove the mobile path loads no Node API.
 */
import { NodeSpawner } from './node-spawner';
import type { FileSystemOps, Spawner } from './types';

export interface NodeApis {
  spawner: Spawner;
  fs: FileSystemOps;
  /** Reveal a folder in the OS file manager (Electron shell); never executes files. */
  openFolder(path: string): Promise<void>;
  /** Clipboard text write for SetupModal copy buttons. */
  writeClipboard(text: string): Promise<void>;
  /** Native open dialogs (Electron); null when the user cancels. */
  pickFiles(): Promise<string[] | null>;
  pickFolder(): Promise<string | null>;
  homeDir(): string;
  platform: 'win32' | 'posix';
}

type FsPromises = typeof import('node:fs/promises');
type OsModule = typeof import('node:os');

interface ElectronLike {
  shell?: { openPath(path: string): Promise<string> };
  clipboard?: { writeText(text: string): void };
  remote?: { dialog?: ElectronDialog };
  dialog?: ElectronDialog;
}

interface ElectronDialog {
  showOpenDialog(options: { properties: string[] }): Promise<{ canceled: boolean; filePaths: string[] }>;
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

/** Loads `node:child_process`, `node:fs`, `node:os` and the Electron shell on first call. */
export function loadNodeApis(): NodeApis {
  if (cached) return cached;
  const fsp = require('node:fs/promises') as FsPromises;
  const os = require('node:os') as OsModule;
  const electron = optionalRequire<ElectronLike>('electron');
  const remote = electron?.remote ?? optionalRequire<{ dialog?: ElectronDialog }>('@electron/remote');
  const dialog = remote?.dialog ?? electron?.dialog ?? null;
  const pick = async (properties: string[]): Promise<string[] | null> => {
    if (!dialog) return null;
    const result = await dialog.showOpenDialog({ properties });
    return result.canceled || result.filePaths.length === 0 ? null : result.filePaths;
  };
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
    pickFiles: () => pick(['openFile', 'multiSelections']),
    pickFolder: async () => (await pick(['openDirectory']))?.[0] ?? null,
    homeDir: () => os.homedir(),
    platform: process.platform === 'win32' ? 'win32' : 'posix',
  };
  return cached;
}
