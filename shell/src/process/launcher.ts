/**
 * Job snapshot and spawn-request construction (20_SHELL.md REQ-SHL-06/11/12/15;
 * SPEC 8.2/8.4/10 by reference). The snapshot of ordered absolute inputs, cwd,
 * output and cache roots and nonsecret options is taken once and reused
 * verbatim for `plan` and the authorized `run` replay.
 */
import { type Env, scrubEngineEnv } from '../pure/env';
import { parentPath } from '../pure/paths';
import type { ProviderSettings, RunOptions, SettingsV2 } from '../pure/settings';
import type { HostPlatform, SpawnRequest } from './types';

export type EngineCommand = 'plan' | 'run' | 'version' | 'selftest';

export const APPROVED_BY_MODAL = 'plugin:modal';

/**
 * Fixed interpreter prefix of every engine spawn (REQ-SHL-12; M3 N-02):
 * `-I` isolated mode (the working directory is not `sys.path[0]`, `PYTHON*`
 * variables and the user site are ignored, so vault or plugin-folder content
 * can never supply `mdflow`, `PIL` or a stdlib shadow); `-X utf8` because `-I`
 * implies `-E` and therefore drops `PYTHONUTF8`/`PYTHONIOENCODING`; then the
 * SPEC 10 module entry point. `-P` alone is not used (absent before 3.11).
 */
export const ENGINE_ARGV_PREFIX: readonly string[] = Object.freeze(['-I', '-X', 'utf8', '-m', 'mdflow']);

/** Index of the SPEC 10.1 subcommand in every engine argv. */
export const SUBCOMMAND_INDEX = ENGINE_ARGV_PREFIX.length;

/** The SPEC 10.1 subcommand of an engine argv built by this module, or undefined when the prefix is absent. */
export function engineSubcommand(args: readonly string[]): string | undefined {
  for (const [i, token] of ENGINE_ARGV_PREFIX.entries()) if (args[i] !== token) return undefined;
  return args[SUBCOMMAND_INDEX];
}

/**
 * Fixed working directory for every engine spawn: the venv root of the selected
 * interpreter (`<venv>/bin/python` or `<venv>\Scripts\python.exe` -> `<venv>`).
 * It exists, is user-owned and is not vault content, so even an interpreter
 * launched without `-I` would not see the vault on `sys.path` (M3 N-02).
 */
export function engineWorkingDirectory(platform: HostPlatform, enginePython: string): string {
  return parentPath(platform, parentPath(platform, enginePython));
}

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
 * Consent for the displayed file scopes (SPEC 8.4): the plugin-owned
 * `--yes-file` of accepted `plan_hash` lines (REQ-SHL-15). The shell never
 * emits bare or repeated `--yes`.
 */
export interface Authorization {
  yesFile: string;
  approvedBy: typeof APPROVED_BY_MODAL;
}

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
 * The scrubbed child environment. For `openai-compatible` the persisted Base URL
 * setting is the endpoint (SPEC REQ-SEC-01 allows a persisted `base_url`; REQ-SHL-06):
 * it is passed as `MDFLOW_BASE_URL` and wins over any host value, never on argv.
 */
export function engineEnvFor(snapshot: Pick<JobSnapshot, 'provider'>, hostEnv: Env): Record<string, string> {
  const env = scrubEngineEnv(hostEnv, snapshot.provider.name);
  if (snapshot.provider.name === 'openai-compatible') env.MDFLOW_BASE_URL = snapshot.provider.baseUrl;
  return env;
}

/**
 * `<enginePython> -I -X utf8 -m mdflow <command> <inputs...> [-o OUT] --cache CACHE ...`
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
  const args: string[] = [...ENGINE_ARGV_PREFIX, command, ...snapshot.inputs];
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
    args.push('--yes-file', authorization.yesFile);
    args.push('--approved-by', authorization.approvedBy);
  }
  return {
    command: snapshot.enginePython,
    args,
    cwd: snapshot.cwd,
    env: engineEnvFor(snapshot, hostEnv),
    shell: false,
    windowsHide: true,
  };
}

/** `<python> -I -X utf8 -m mdflow version` / `selftest` with the baseline environment and a fixed cwd outside the vault. */
export function buildUtilityRequest(enginePython: string, command: 'version' | 'selftest', hostEnv: Env, cwd: string): SpawnRequest {
  return {
    command: enginePython,
    args: [...ENGINE_ARGV_PREFIX, command],
    cwd,
    env: scrubEngineEnv(hostEnv, 'none'),
    shell: false,
    windowsHide: true,
  };
}

/** Render the yes-file the shell writes for one approved run (SPEC 10.2: one hash per line, `#` comments). */
export function renderYesFile(hashes: readonly string[]): string {
  return `# MarkItDown Flow approved plan hashes (REQ-SHL-15)\n${hashes.join('\n')}\n`;
}
