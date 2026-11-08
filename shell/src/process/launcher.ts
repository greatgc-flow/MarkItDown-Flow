/**
 * Job snapshot and spawn-request construction (20_SHELL.md REQ-SHL-11/12/15;
 * SPEC 8.4/10 by reference). The snapshot of ordered absolute inputs, cwd,
 * output and cache roots and nonsecret options is taken once and reused
 * verbatim for `plan` and the authorized `run` replay.
 */
import { type Env, scrubEngineEnv } from '../pure/env';
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

/** SPEC 10.2 options that take no value. */
const FLAG_OPTIONS: ReadonlySet<string> = new Set(['--force', '--trust-command']);

/** Options removed when comparing the `plan` invocation with its `run` replay. */
const REPLAY_VARIANT_OPTIONS: ReadonlySet<string> = new Set(['-o', '--out', '--yes', '--yes-file', '--approved-by']);

export const APPROVED_BY_MODAL = 'plugin:modal';

const HEX64 = /^[0-9a-f]{64}$/;

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

/**
 * Consent for the displayed file scopes (SPEC 8.4). Either repeated
 * `--yes <hash>` tokens or a plugin-owned `--yes-file` (REQ-SHL-15).
 */
export type Authorization =
  | { yes: readonly string[]; approvedBy: typeof APPROVED_BY_MODAL }
  | { yesFile: string; approvedBy: typeof APPROVED_BY_MODAL };

/** Absolute on either platform: POSIX root, drive letter or UNC. */
export function isAbsolutePath(value: string): boolean {
  return /^(?:\/|\\\\|[A-Za-z]:[\\/])/.test(value);
}

function freezeDeep<T>(value: T): T {
  if (value !== null && typeof value === 'object') {
    for (const inner of Object.values(value as Record<string, unknown>)) freezeDeep(inner);
    Object.freeze(value);
  }
  return value;
}

/** Deep-frozen snapshot; throws when `enginePython` is unset or an input is not absolute. */
export function snapshotJob(params: SnapshotParams): JobSnapshot {
  const { settings } = params;
  if (!settings.enginePython || !isAbsolutePath(settings.enginePython)) {
    throw new Error('snapshotJob: enginePython must be an absolute interpreter path');
  }
  if (params.inputs.length === 0) throw new Error('snapshotJob: at least one input is required');
  for (const input of params.inputs) {
    if (!isAbsolutePath(input)) throw new Error(`snapshotJob: input is not absolute: ${JSON.stringify(input)}`);
  }
  for (const [name, value] of [['cwd', params.cwd], ['outDir', params.outDir], ['cacheDir', params.cacheDir]] as const) {
    if (!isAbsolutePath(value)) throw new Error(`snapshotJob: ${name} is not absolute`);
  }
  const snapshot: JobSnapshot = {
    enginePython: settings.enginePython,
    inputs: [...params.inputs],
    cwd: params.cwd,
    outDir: params.outDir,
    cacheDir: params.cacheDir,
    provider: { name: settings.provider.name, model: settings.provider.model, baseUrl: settings.provider.baseUrl },
    runOptions: { ...settings.runOptions, sensitive: [...settings.runOptions.sensitive] },
  };
  return freezeDeep(snapshot);
}

/**
 * `<enginePython> -m mdflow <command> <inputs...> [-o OUT] --cache CACHE ...`
 * with the SPEC-baseline scrubbed environment. `plan` and `run` differ only in
 * the subcommand, `-o`, and the authorization arguments.
 */
export function buildSpawnRequest(
  snapshot: JobSnapshot,
  command: 'plan' | 'run',
  hostEnv: Env,
  authorization?: Authorization | null,
): SpawnRequest {
  const { provider, runOptions } = snapshot;
  const args: string[] = ['-m', 'mdflow', command, ...snapshot.inputs];
  if (command === 'run') args.push('-o', snapshot.outDir);
  args.push('--cache', snapshot.cacheDir);
  args.push('--provider', provider.name);
  if (provider.name !== 'none') args.push('--model', provider.model);
  args.push('--dpi', String(runOptions.dpi));
  args.push('--min-priority', runOptions.minPriority);
  args.push('--max-units', String(runOptions.maxUnits));
  args.push('--approve-threshold', String(runOptions.approveThreshold));
  for (const glob of runOptions.sensitive) args.push('--sensitive', glob);
  args.push('--progress', 'jsonl');
  if (authorization && command === 'run') {
    if ('yesFile' in authorization) {
      args.push('--yes-file', authorization.yesFile);
    } else {
      for (const hash of authorization.yes) args.push('--yes', hash);
    }
    args.push('--approved-by', authorization.approvedBy);
  }
  return {
    command: snapshot.enginePython,
    args,
    cwd: snapshot.cwd,
    env: scrubEngineEnv(hostEnv, provider.name),
    shell: false,
    windowsHide: true,
  };
}

/** `<python> -m mdflow version` / `selftest` with the baseline environment and a fixed cwd. */
export function buildUtilityRequest(enginePython: string, command: 'version' | 'selftest', hostEnv: Env, cwd: string): SpawnRequest {
  return {
    command: enginePython,
    args: ['-m', 'mdflow', command],
    cwd,
    env: scrubEngineEnv(hostEnv, 'none'),
    shell: false,
    windowsHide: true,
  };
}

export interface InvocationViolation {
  kind: 'module' | 'command' | 'option' | 'shell' | 'secret';
  token: string;
}

/**
 * REQ-SHL-11 oracle: every shell invocation is `-m mdflow <SPEC command>` with
 * SPEC 10.2 options only. Returns the violations (empty when conformant).
 */
export function invocationViolations(request: SpawnRequest): InvocationViolation[] {
  const violations: InvocationViolation[] = [];
  const { args } = request;
  if ((request.shell as boolean) !== false) violations.push({ kind: 'shell', token: String(request.shell) });
  if (args[0] !== '-m') violations.push({ kind: 'module', token: args[0] ?? '<missing -m>' });
  if (args[1] !== 'mdflow') violations.push({ kind: 'module', token: args[1] ?? '<missing module>' });
  const command = args[2];
  if (!(SPEC_COMMANDS as readonly string[]).includes(command)) violations.push({ kind: 'command', token: command ?? '<missing command>' });
  for (let i = 3; i < args.length; i++) {
    const token = args[i];
    if (!token.startsWith('-')) continue;
    if (!SPEC_OPTIONS.includes(token)) {
      violations.push({ kind: 'option', token });
      continue;
    }
    if (!FLAG_OPTIONS.has(token) && i + 1 < args.length && !args[i + 1].startsWith('-')) i += 1;
  }
  return violations;
}

/** Arguments after `-m mdflow <command>` minus `-o X`, `--yes X`, `--yes-file X`, `--approved-by X`. */
export function replayInvariantArgs(args: readonly string[]): string[] {
  const out: string[] = [];
  for (let i = 3; i < args.length; i++) {
    const token = args[i];
    if (REPLAY_VARIANT_OPTIONS.has(token)) {
      if (i + 1 < args.length && !args[i + 1].startsWith('-')) i += 1;
      continue;
    }
    out.push(token);
  }
  return out;
}

/** SPEC 10.2 `--yes-file`: one `plan_hash` per line; blank lines and `#` comments ignored. */
export function parseYesFile(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith('#'));
}

/** The approved hash list of an invocation: `--yes` values plus the `--yes-file` content when a reader is given. */
export function approvedHashesIn(args: readonly string[], readFile?: (path: string) => string | null): string[] {
  const hashes: string[] = [];
  for (let i = 3; i < args.length; i++) {
    const token = args[i];
    const value = args[i + 1];
    if (token === '--yes' && value !== undefined && HEX64.test(value)) {
      hashes.push(value);
      i += 1;
    } else if (token === '--yes-file' && value !== undefined) {
      const text = readFile?.(value) ?? null;
      if (text !== null) hashes.push(...parseYesFile(text));
      i += 1;
    }
  }
  return hashes;
}

/** Render the yes-file the shell writes for one approved run. */
export function renderYesFile(hashes: readonly string[]): string {
  return `# MarkItDown Flow approved plan hashes (REQ-SHL-15)\n${hashes.join('\n')}\n`;
}
