/**
 * Process-layer seams (20_SHELL.md REQ-SHL-12/16). Everything that touches the
 * OS is injected so the lifecycle logic is testable with scripted children and
 * verifiable with real children (JT-16).
 */

export interface SpawnRequest {
  /** Absolute interpreter path (`enginePython`) or a bootstrap probe command name. */
  command: string;
  /** Argument array; never joined into a shell string. */
  args: string[];
  /** Fixed for the whole job and its replay. */
  cwd: string;
  /** Scrubbed environment (pure/env.ts); never the host environment. */
  env: Record<string, string>;
  shell: false;
  /** Hidden subprocess window on Windows. */
  windowsHide: true;
}

export interface ExitStatus {
  /** Native exit code, or null when the child died from a signal / TerminateProcess. */
  code: number | null;
  signal: string | null;
}

export interface ChildHandle {
  readonly pid: number | null;
  onStdout(listener: (chunk: Uint8Array) => void): void;
  onStderr(listener: (chunk: Uint8Array) => void): void;
  onExit(listener: (status: ExitStatus) => void): void;
  onError(listener: (error: Error) => void): void;
  /**
   * R19 cooperative cancellation (SIGTERM on POSIX). Returns false when the
   * platform cannot deliver a cooperative signal (Windows without a console
   * control event); the supervisor then proceeds to forced termination and
   * reports the run as interrupted, never as exit 130.
   */
  requestCooperativeStop(): boolean;
  /** Forced termination: SIGKILL / TerminateProcess. */
  terminate(): void;
}

export interface Spawner {
  spawn(request: SpawnRequest): ChildHandle;
}

/** Injected timers so supervision is deterministic in tests. */
export interface Clock {
  now(): number;
  /** Returns a cancel function. */
  setTimeout(callback: () => void, ms: number): () => void;
}

export interface FileSystemOps {
  readFile(path: string): Promise<Uint8Array | null>;
  writeFile(path: string, data: Uint8Array): Promise<void>;
  appendFile(path: string, data: Uint8Array): Promise<void>;
  remove(path: string): Promise<void>;
  rename(from: string, to: string): Promise<void>;
  list(dir: string): Promise<string[]>;
  size(path: string): Promise<number | null>;
  mkdir(dir: string): Promise<void>;
  /** Resolved real path or null when the path does not exist. */
  realpath(path: string): Promise<string | null>;
  isDirectory(path: string): Promise<boolean>;
  isSymlink(path: string): Promise<boolean>;
}

export type HostPlatform = 'win32' | 'posix';
