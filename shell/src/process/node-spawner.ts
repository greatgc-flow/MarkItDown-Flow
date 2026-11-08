/**
 * `node:child_process` adapter (20_SHELL.md REQ-SHL-12/16): executable plus
 * argument array, `shell: false`, `windowsHide: true`; cooperative stop is
 * SIGTERM on POSIX and unavailable on Windows (reported honestly, R5-N07).
 */
import { NotImplementedError } from '../pure/errors';
import type { ChildHandle, Spawner, SpawnRequest } from './types';

export class NodeSpawner implements Spawner {
  spawn(_request: SpawnRequest): ChildHandle {
    throw new NotImplementedError('NodeSpawner.spawn');
  }
}

/** Real timers. */
export const systemClock = {
  now(): number {
    throw new NotImplementedError('systemClock.now');
  },
  setTimeout(_callback: () => void, _ms: number): () => void {
    throw new NotImplementedError('systemClock.setTimeout');
  },
};
