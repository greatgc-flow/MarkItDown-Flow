/**
 * `run-image-pipeline-selftest` (20_SHELL.md REQ-SHL-20): version check, then
 * SPEC 10.1 `selftest`; no shell-authored fixture or parallel health mode.
 */
import type { Env } from '../pure/env';
import { NotImplementedError } from '../pure/errors';
import type { Clock, Spawner } from './types';
import type { VersionGate, VersionPolicy } from './version-gate';

export interface SelftestDeps {
  spawner: Spawner;
  clock: Clock;
  hostEnv: Env;
  cwd: string;
  enginePython: string | null;
  policy?: VersionPolicy;
}

export interface SelftestOutcome {
  gate: VersionGate | null;
  /** Null when the version gate blocked or no interpreter is configured. */
  selftestExit: number | null;
  ok: boolean;
  /** Localized message keys for the coordinator (`shell.RUNTIME`, `shell.PROTOCOL`, ...). */
  diagnostics: string[];
}

/** Spawns exactly `version` then `selftest` (or only `version` when blocked). */
export async function runSelftest(_deps: SelftestDeps): Promise<SelftestOutcome> {
  throw new NotImplementedError('runSelftest');
}
