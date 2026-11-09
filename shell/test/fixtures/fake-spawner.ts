/**
 * Scripted child processes replaying FX-71 streams (no OS process). Each spawn
 * is recorded so tests can snapshot every invocation the shell makes.
 */
import { engineSubcommand } from '../../src/process/launcher';
import type { ChildHandle, ExitStatus, Spawner, SpawnRequest } from '../../src/process/types';

/** SPEC 10.1 subcommand of a spawned request (the token after the fixed `-I -X utf8 -m mdflow` prefix). */
export function subcommandOf(request: SpawnRequest): string | undefined {
  return engineSubcommand(request.args);
}

export interface ScriptedChild {
  /** stderr chunks delivered in order (progress JSON lines). */
  stderr?: Uint8Array[];
  /** stdout chunks (report / Plans). */
  stdout?: Uint8Array[];
  exit: ExitStatus;
  /** Behaviour on a cooperative stop request. */
  cooperative?: 'exit130' | 'ignore' | 'unsupported';
  /** When set, the child never exits on its own (blocked provider request); only cancel ends it. */
  blocked?: boolean;
  /** Emitted on spawn failure instead of running. */
  spawnError?: Error;
  /** Report bytes printed on cooperative exit 130. */
  cooperativeStdout?: Uint8Array;
}

export class FakeChild implements ChildHandle {
  readonly pid: number;
  private stdoutListeners: ((c: Uint8Array) => void)[] = [];
  private stderrListeners: ((c: Uint8Array) => void)[] = [];
  private exitListeners: ((s: ExitStatus) => void)[] = [];
  private errorListeners: ((e: Error) => void)[] = [];
  private exited = false;
  cooperativeRequests = 0;
  terminated = false;

  constructor(private readonly script: ScriptedChild, pid: number) {
    this.pid = pid;
    queueMicrotask(() => this.run());
  }

  private async run(): Promise<void> {
    if (this.script.spawnError) {
      for (const l of this.errorListeners) l(this.script.spawnError);
      this.finish({ code: null, signal: null });
      return;
    }
    for (const chunk of this.script.stderr ?? []) {
      await Promise.resolve();
      if (this.exited) return;
      for (const l of this.stderrListeners) l(chunk);
    }
    for (const chunk of this.script.stdout ?? []) {
      await Promise.resolve();
      if (this.exited) return;
      for (const l of this.stdoutListeners) l(chunk);
    }
    if (this.script.blocked) return;
    await Promise.resolve();
    this.finish(this.script.exit);
  }

  private finish(status: ExitStatus): void {
    if (this.exited) return;
    this.exited = true;
    for (const l of this.exitListeners) l(status);
  }

  onStdout(listener: (chunk: Uint8Array) => void): void {
    this.stdoutListeners.push(listener);
  }

  onStderr(listener: (chunk: Uint8Array) => void): void {
    this.stderrListeners.push(listener);
  }

  onExit(listener: (status: ExitStatus) => void): void {
    this.exitListeners.push(listener);
    if (this.exited) listener(this.script.exit);
  }

  onError(listener: (error: Error) => void): void {
    this.errorListeners.push(listener);
  }

  requestCooperativeStop(): boolean {
    this.cooperativeRequests += 1;
    const mode = this.script.cooperative ?? 'exit130';
    if (mode === 'unsupported') return false;
    if (mode === 'exit130') {
      queueMicrotask(() => {
        if (this.exited) return;
        if (this.script.cooperativeStdout) for (const l of this.stdoutListeners) l(this.script.cooperativeStdout);
        this.finish({ code: 130, signal: null });
      });
    }
    return true;
  }

  terminate(): void {
    this.terminated = true;
    queueMicrotask(() => this.finish({ code: null, signal: 'SIGKILL' }));
  }

  get alive(): boolean {
    return !this.exited;
  }
}

export type Script = (request: SpawnRequest, index: number) => ScriptedChild;

export class FakeSpawner implements Spawner {
  readonly requests: SpawnRequest[] = [];
  readonly children: FakeChild[] = [];
  private nextPid = 4000;

  constructor(private readonly script: Script) {}

  spawn(request: SpawnRequest): ChildHandle {
    // Snapshot the request so later mutation by the caller cannot hide what was spawned.
    const copy: SpawnRequest = { ...request, args: [...request.args], env: { ...request.env } };
    this.requests.push(copy);
    const child = new FakeChild(this.script(copy, this.requests.length - 1), this.nextPid++);
    this.children.push(child);
    return child;
  }

  /** Subcommand of each spawn (the token after the fixed `-I -X utf8 -m mdflow` prefix). */
  get commands(): string[] {
    return this.requests.map((r) => subcommandOf(r) ?? '<none>');
  }
}

export function chunksOf(bytes: Uint8Array, size: number): Uint8Array[] {
  const out: Uint8Array[] = [];
  for (let i = 0; i < bytes.length; i += size) out.push(bytes.slice(i, i + size));
  return out.length ? out : [new Uint8Array(0)];
}
