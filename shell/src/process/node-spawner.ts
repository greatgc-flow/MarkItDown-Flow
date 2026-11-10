/**
 * `node:child_process` adapter (20_SHELL.md REQ-SHL-12/16): executable plus
 * argument array, `shell: false`, `windowsHide: true`; cooperative stop is
 * SIGTERM on POSIX and unavailable on Windows (reported honestly, R5-N07).
 *
 * Node modules are required lazily so importing this file loads nothing.
 */
import type { ChildHandle, ExitStatus, Spawner, SpawnRequest } from './types';

type ChildProcessModule = typeof import('node:child_process');

let childProcessModule: ChildProcessModule | null = null;

function childProcess(): ChildProcessModule {
  childProcessModule ??= require('node:child_process') as ChildProcessModule;
  return childProcessModule;
}

class NodeChild implements ChildHandle {
  readonly pid: number | null;
  private exitListeners: ((status: ExitStatus) => void)[] = [];
  private errorListeners: ((error: Error) => void)[] = [];
  private status: ExitStatus | null = null;
  private error: Error | null = null;

  constructor(private readonly child: ReturnType<ChildProcessModule['spawn']>) {
    this.pid = child.pid ?? null;
    child.on('error', (error: Error) => {
      this.error = error;
      for (const listener of this.errorListeners) listener(error);
    });
    // `close` fires after stdio has flushed, so stdout is complete when the status is reported.
    child.on('close', (code: number | null, signal: NodeJS.Signals | null) => {
      this.status = { code, signal };
      for (const listener of this.exitListeners) listener(this.status);
    });
  }

  onStdout(listener: (chunk: Uint8Array) => void): void {
    this.child.stdout?.on('data', (data: Buffer) => listener(new Uint8Array(data.buffer, data.byteOffset, data.byteLength)));
  }

  onStderr(listener: (chunk: Uint8Array) => void): void {
    this.child.stderr?.on('data', (data: Buffer) => listener(new Uint8Array(data.buffer, data.byteOffset, data.byteLength)));
  }

  onExit(listener: (status: ExitStatus) => void): void {
    if (this.status) listener(this.status);
    else this.exitListeners.push(listener);
  }

  onError(listener: (error: Error) => void): void {
    if (this.error) listener(this.error);
    else this.errorListeners.push(listener);
  }

  requestCooperativeStop(): boolean {
    if (process.platform === 'win32') return false;
    try {
      return this.child.kill('SIGTERM');
    } catch {
      return false;
    }
  }

  /** Forced stop kills the whole process tree: the engine's own children (soffice, a command template) must not outlive it. */
  terminate(): void {
    const pid = this.pid;
    if (pid !== null) {
      try {
        if (process.platform === 'win32') {
          const result = childProcess().spawnSync('taskkill', ['/PID', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
          if (result.status === 0) return;
        } else {
          process.kill(-pid, 'SIGKILL'); // the child leads its own process group (see spawn)
          return;
        }
      } catch {
        // Fall back to the direct kill below.
      }
    }
    try {
      this.child.kill('SIGKILL');
    } catch {
      // Already gone.
    }
  }
}

export class NodeSpawner implements Spawner {
  spawn(request: SpawnRequest): ChildHandle {
    const child = childProcess().spawn(request.command, [...request.args], {
      cwd: request.cwd,
      env: { ...request.env },
      shell: false,
      windowsHide: true,
      detached: process.platform !== 'win32', // POSIX: own process group, so terminate() can kill the tree
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    return new NodeChild(child);
  }
}

/** Real timers. */
export const systemClock = {
  now(): number {
    return Date.now();
  },
  setTimeout(callback: () => void, ms: number): () => void {
    const handle = setTimeout(callback, ms);
    return () => clearTimeout(handle);
  },
};
