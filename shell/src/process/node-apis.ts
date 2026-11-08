/**
 * Lazy Node/Electron API access (20_SHELL.md REQ-SHL-02): nothing here is
 * loaded before the single `Platform.isDesktop` guard in main.ts passes.
 * Tests mock this module to prove the mobile path loads no Node API.
 */
import { NotImplementedError } from '../pure/errors';
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

/** Loads `node:child_process`, `node:fs`, `node:os` and the Electron shell on first call. */
export function loadNodeApis(): NodeApis {
  throw new NotImplementedError('loadNodeApis');
}
