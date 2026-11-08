/**
 * Pure argv construction for the engine module entry point
 * (20_SHELL.md REQ-SHL-04 oracle: no removed-setting flags; SPEC 10.2 options only).
 * Process spawning itself is step 9 (REQ-SHL-12).
 */
import type { SettingsV2 } from './settings';
import { NotImplementedError } from './errors';

export interface RunRequest {
  command: 'run' | 'plan';
  /** Ordered absolute input arguments, snapshotted once. */
  inputs: string[];
  outDir: string;
  cacheDir: string;
  /** Approved file plan hashes for `run` after consent. */
  yes?: string[];
  approvedBy?: string;
}

/** Arguments after the interpreter: `-m mdflow <command> ...`. */
export function engineArgv(_settings: SettingsV2, _request: RunRequest): string[] {
  throw new NotImplementedError('engineArgv');
}
