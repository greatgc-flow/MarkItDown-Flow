/**
 * Job snapshot and spawn-request construction (20_SHELL.md REQ-SHL-11/12/15;
 * SPEC 8.4/10 by reference). The snapshot of ordered absolute inputs, cwd,
 * output and cache roots and nonsecret options is taken once and reused
 * verbatim for `plan` and the authorized `run` replay.
 */
import type { Env } from '../pure/env';
import { NotImplementedError } from '../pure/errors';
import type { ProviderSettings, RunOptions, SettingsV2 } from '../pure/settings';
import type { SpawnRequest } from './types';

export type EngineCommand = 'plan' | 'run' | 'version' | 'selftest';

/** SPEC 10.1 subcommands the shell may ever invoke. */
export const SPEC_COMMANDS: readonly EngineCommand[] = ['plan', 'run', 'version', 'selftest'];

/** SPEC 10.2 option tokens; anything else is an invented option and fails REQ-SHL-11. */
export const SPEC_OPTIONS: readonly string[] = [
  '-o', '--out', '--provider', '--model', '--dpi', '--prompt-version', '--yes', '--yes-file', '--approved-by',
  '--approve-threshold', '--sensitive', '--min-priority', '--max-units', '--max-bytes', '--max-pixels',
  '--zip-depth', '--zip-entries', '--zip-total-bytes', '--force', '--cache', '--progress', '--report',
  '--command', '--command-egress', '--command-env', '--trust-command', '--cost-hint',
];

export const APPROVED_BY_MODAL = 'plugin:modal';

export interface JobSnapshot {
  /** Absolute venv interpreter. */
  enginePython: string;
  /** Ordered absolute input arguments exactly as selected (files and/or directories). */
  inputs: readonly string[];
  cwd: string;
  /** Validated vault destination, passed directly as `-o`. */
  outDir: string;
  /** `<plugin-dir>/cache`. */
  cacheDir: string;
  provider: Readonly<ProviderSettings>;
  runOptions: Readonly<RunOptions>;
}

export interface SnapshotParams {
  settings: SettingsV2;
  inputs: readonly string[];
  cwd: string;
  outDir: string;
  cacheDir: string;
}

/** Per-file hashes approved in the modal for the displayed file scopes (SPEC 8.4). */
export interface Authorization {
  yes: readonly string[];
  approvedBy: typeof APPROVED_BY_MODAL;
}

/** Deep-frozen snapshot; throws when `enginePython` is unset or an input is not absolute. */
export function snapshotJob(_params: SnapshotParams): JobSnapshot {
  throw new NotImplementedError('snapshotJob');
}

/**
 * `<enginePython> -m mdflow <command> <inputs...> [-o OUT] --cache CACHE ...`
 * with the SPEC-baseline scrubbed environment. `plan` and `run` differ only in
 * the subcommand, `-o`, and the authorization arguments.
 */
export function buildSpawnRequest(
  _snapshot: JobSnapshot,
  _command: 'plan' | 'run',
  _hostEnv: Env,
  _authorization?: Authorization | null,
): SpawnRequest {
  throw new NotImplementedError('buildSpawnRequest');
}

/** `<python> -m mdflow version` / `selftest` with the baseline environment and a fixed cwd. */
export function buildUtilityRequest(_enginePython: string, _command: 'version' | 'selftest', _hostEnv: Env, _cwd: string): SpawnRequest {
  throw new NotImplementedError('buildUtilityRequest');
}

export interface InvocationViolation {
  kind: 'module' | 'command' | 'option' | 'shell' | 'secret';
  token: string;
}

/**
 * REQ-SHL-11 oracle: every shell invocation is `-m mdflow <SPEC command>` with
 * SPEC 10.2 options only. Returns the violations (empty when conformant).
 */
export function invocationViolations(_request: SpawnRequest): InvocationViolation[] {
  throw new NotImplementedError('invocationViolations');
}

/** Arguments after `-m mdflow <command>` minus `-o X`, `--yes X`, `--yes-file X`, `--approved-by X`. */
export function replayInvariantArgs(_args: readonly string[]): string[] {
  throw new NotImplementedError('replayInvariantArgs');
}

/** The `--yes` hash list of an invocation, in order. */
export function approvedHashesIn(_args: readonly string[]): string[] {
  throw new NotImplementedError('approvedHashesIn');
}
