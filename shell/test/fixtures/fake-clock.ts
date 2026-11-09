/** Deterministic Clock: timers fire only when the test advances time. */
import type { Clock } from '../../src/process/types';

interface Pending {
  at: number;
  callback: () => void;
  cancelled: boolean;
}

export class FakeClock implements Clock {
  private time: number;
  private readonly timers: Pending[] = [];

  constructor(start = 1_700_000_000_000) {
    this.time = start;
  }

  now(): number {
    return this.time;
  }

  setTimeout(callback: () => void, ms: number): () => void {
    const pending: Pending = { at: this.time + ms, callback, cancelled: false };
    this.timers.push(pending);
    return () => {
      pending.cancelled = true;
    };
  }

  /** Advance time, firing due timers in order; yields to microtasks between them. */
  async advance(ms: number): Promise<void> {
    const target = this.time + ms;
    for (;;) {
      const due = this.timers.filter((t) => !t.cancelled && t.at <= target).sort((a, b) => a.at - b.at)[0];
      if (!due) break;
      this.time = due.at;
      due.cancelled = true;
      due.callback();
      await flush();
    }
    this.time = target;
    await flush();
  }

  get pendingCount(): number {
    return this.timers.filter((t) => !t.cancelled).length;
  }
}

/** Drain microtasks and one macrotask turn. */
export async function flush(turns = 3): Promise<void> {
  for (let i = 0; i < turns; i++) {
    await new Promise<void>((resolve) => setImmediate(resolve));
  }
}
