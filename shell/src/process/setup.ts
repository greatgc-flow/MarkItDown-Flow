/**
 * Diagnostics-only setup data (20_SHELL.md REQ-SHL-10; 25_PACKAGING.md
 * section 2). Probes are version probes only; instructions are rendered text
 * for the user's own terminal. Nothing is installed, downloaded or executed as
 * a fallback interpreter.
 */
import { type Env, environmentDiagnostics, keyPresence, type Presence, scrubEngineEnv, toolEnvironmentDiagnostics } from '../pure/env';
import { diagnosticsCopy } from './log';
import type { Clock, HostPlatform, Spawner, SpawnRequest } from './types';
import { captureProbe, probeVersion, RELEASE_LOCK, VERSION_PROBE_TIMEOUT_MS, type VersionGate, type VersionPolicy } from './version-gate';

/** Optional bootstrap probes when `enginePython` is unset; they only prefill instructions. Isolated like every spawn (M3 N-02). */
export const BOOTSTRAP_PROBE_CANDIDATES: readonly { command: string; args: readonly string[] }[] = [
  { command: 'python3', args: ['-I', '--version'] },
  { command: 'python', args: ['-I', '--version'] },
  { command: 'py', args: ['-3', '-I', '--version'] },
];

export interface BootstrapProbe {
  command: string;
  args: string[];
  result: 'ok' | 'failed' | 'timeout';
  /** Parsed `Python X.Y.Z` or null. */
  version: string | null;
}

export interface BootstrapPaths {
  /** Directory holding the verified release wheel, as the user will type it. */
  downloadDir: string;
  /** Target venv directory. */
  venvDir: string;
  /** Bootstrap interpreter command (`py -3.14`, `python3.14`, or the migrated hint). */
  bootstrapPython: string;
}

/** Release wheel attached to the GitHub release (R27). */
export const ENGINE_WHEEL = 'mdflow-2.0.0-py3-none-any.whl';
/** Declared Core policy, visible in the example even though the wheel metadata already declares it. */
export const CORE_REQUIREMENT = 'markitdown-gc>=0.3.7,<0.4';

export interface SetupDiagnostics {
  enginePython: string | null;
  /** Null when unconfigured. */
  gate: VersionGate | null;
  bootstrapProbes: BootstrapProbe[];
  instructions: { windows: string; posix: string };
  apiKey: Presence;
  /** Presence (never values) of every SPEC 10.2 provider variable in the Obsidian process. */
  providerEnv: Record<string, Presence>;
  /** Presence (never the path) of the optional tool location variables `EXIFTOOL_PATH`/`SOFFICE_PATH` (R31/R33). */
  toolEnv: Record<string, Presence>;
  jobsEnabled: boolean;
  /**
   * R33c: the terminal command that removes a co-installed upstream `markitdown` from the selected
   * interpreter's venv, when the gate is blocked by `core_conflict`; null otherwise. Rendered text only.
   */
  conflictFix: string | null;
  /** Redacted, code-only summary for the diagnostics copy button. */
  summary: string;
}

export interface SetupDeps {
  spawner: Spawner;
  clock: Clock;
  hostEnv: Env;
  platform: HostPlatform;
  /** Probe working directory: an existing user-owned directory (the engine venv root, or home when unconfigured; M3 N-02). */
  cwd: string;
  enginePython: string | null;
  bootstrapPythonHint?: string;
  paths?: Partial<BootstrapPaths>;
  policy?: VersionPolicy;
  /** Redaction inputs: home prefix and vault root. */
  home?: string;
  vault?: string;
}

const DEFAULT_PATHS: Record<HostPlatform, BootstrapPaths> = {
  win32: { downloadDir: 'C:\\Downloads\\mdflow-2.0.0', venvDir: 'C:\\mdflow-venvs\\2.0.0', bootstrapPython: 'py -3.14' },
  posix: { downloadDir: '/path/to/mdflow-2.0.0', venvDir: '/path/to/mdflow-venvs/2.0.0', bootstrapPython: 'python3.14' },
};

/**
 * PowerShell single-quoted literal: every single-quote character is doubled. PowerShell treats the typographic
 * U+2018, U+2019, U+201A and U+201B as quotes too (about_Quoting_Rules), so a name typed in a word processor
 * must not close the literal (M7-01).
 */
function quote(value: string): string {
  return `'${value.replace(/['‘’‚‛]/g, (c) => c + c)}'`;
}

/** POSIX `sh` single-quoted literal: a single quote closes, escapes and reopens the quote (M6-03). */
function shQuote(value: string): string {
  return `'${value.replace(/'/g, "'\\''")}'`;
}

/** A bare command with optional plain flags (`python3.14`, `py -3.14`): rendered as typed. Anything else is a path. */
const PLAIN_COMMAND = /^[A-Za-z][A-Za-z0-9._+-]*(?: -[A-Za-z0-9.]+)*$/;

/**
 * The bootstrap interpreter as terminal text (M6-02): probe candidates and the defaults are commands plus flags and
 * stay unquoted; a migrated `pythonPath` hint (any printable text, often a path with spaces) is rendered as a quoted
 * executable so it never splits or runs as shell text. PowerShell needs the call operator for a quoted path.
 */
function bootstrapCommand(hint: string, platform: HostPlatform): string {
  if (PLAIN_COMMAND.test(hint)) return hint;
  return platform === 'win32' ? `& ${quote(hint)}` : shQuote(hint);
}

/**
 * Render the R27 user-terminal recipe (25_PACKAGING section 2): verify the release wheel,
 * create a venv, wheel-only install from the download directory (Core from PyPI), check, probe.
 * The Windows block is PowerShell text and the POSIX block `sh` text; each uses its own quoting.
 */
export function renderBootstrapInstructions(paths: BootstrapPaths): { windows: string; posix: string } {
  const venv = paths.venvDir.replace(/[\\/]+$/, '');
  const winPython = `& ${quote(`${venv}\\Scripts\\python.exe`)}`;
  const windows = [
    `Set-Location -LiteralPath ${quote(paths.downloadDir)}`,
    `${bootstrapCommand(paths.bootstrapPython, 'win32')} -m venv ${quote(paths.venvDir)}`,
    `${winPython} -m pip install --only-binary=:all: ${quote(`.\\${ENGINE_WHEEL}`)} ${quote(CORE_REQUIREMENT)}`,
    `${winPython} -m pip check`,
    `${winPython} -I -m mdflow version`,
    `${winPython} -I -m mdflow selftest`,
  ].join('\n');
  const posixPython = shQuote(`${venv}/bin/python`);
  const posix = [
    `cd ${shQuote(paths.downloadDir)}`,
    `${bootstrapCommand(paths.bootstrapPython, 'posix')} -m venv ${shQuote(paths.venvDir)}`,
    `${posixPython} -m pip install --only-binary=:all: ${shQuote(`./${ENGINE_WHEEL}`)} ${shQuote(CORE_REQUIREMENT)}`,
    `${posixPython} -m pip check`,
    `${posixPython} -I -m mdflow version`,
    `${posixPython} -I -m mdflow selftest`,
  ].join('\n');
  return { windows, posix };
}

/**
 * R33c fix command for the co-install guard: uninstall the upstream `markitdown` distribution from the
 * selected interpreter's venv (`markitdown-gc` stays). Rendered for the user's own terminal, never executed.
 */
export function renderUpstreamUninstall(enginePython: string, platform: HostPlatform): string {
  const python = platform === 'win32' ? `& ${quote(enginePython)}` : shQuote(enginePython);
  return `${python} -m pip uninstall -y markitdown`;
}

function parsePythonVersion(text: string): string | null {
  const match = /Python\s+(\d+\.\d+(?:\.\d+)?)/.exec(text);
  return match ? match[1] : null;
}

async function bootstrapProbes(deps: SetupDeps): Promise<BootstrapProbe[]> {
  const probes: BootstrapProbe[] = [];
  for (const candidate of BOOTSTRAP_PROBE_CANDIDATES) {
    const request: SpawnRequest = {
      command: candidate.command,
      args: [...candidate.args],
      cwd: deps.cwd,
      env: scrubEngineEnv(deps.hostEnv, 'none'),
      shell: false,
      windowsHide: true,
    };
    const capture = await captureProbe(deps.spawner, request, deps.clock, VERSION_PROBE_TIMEOUT_MS);
    let result: BootstrapProbe['result'] = 'failed';
    if (capture.timedOut) result = 'timeout';
    else if (!capture.error && capture.status?.code === 0) result = 'ok';
    probes.push({
      command: candidate.command,
      args: [...candidate.args],
      result,
      version: result === 'ok' ? parsePythonVersion(capture.stdout + capture.stderr) : null,
    });
  }
  return probes;
}

/** Collect diagnostics: version probe of `enginePython` first; bootstrap probes only when unconfigured. */
export async function collectSetupDiagnostics(deps: SetupDeps): Promise<SetupDiagnostics> {
  const policy = deps.policy ?? RELEASE_LOCK;
  let gate: VersionGate | null = null;
  let probes: BootstrapProbe[] = [];
  if (deps.enginePython) {
    gate = await probeVersion(deps.enginePython, { spawner: deps.spawner, clock: deps.clock, hostEnv: deps.hostEnv, cwd: deps.cwd, policy });
  } else {
    probes = await bootstrapProbes(deps);
  }
  const defaults = DEFAULT_PATHS[deps.platform];
  const detected = probes.find((p) => p.result === 'ok');
  const bootstrapPython = deps.paths?.bootstrapPython ?? (detected ? [detected.command, ...detected.args.filter((a) => a !== '--version' && a !== '-I')].join(' ') : deps.bootstrapPythonHint ?? defaults.bootstrapPython);
  const paths: BootstrapPaths = {
    downloadDir: deps.paths?.downloadDir ?? defaults.downloadDir,
    venvDir: deps.paths?.venvDir ?? defaults.venvDir,
    bootstrapPython,
  };
  const instructions = renderBootstrapInstructions(paths);
  const redact = { home: deps.home, vault: deps.vault };
  const summary = diagnosticsCopy(
    { version: gate, probes, codes: [], paths: deps.enginePython ? [deps.enginePython] : [] },
    redact,
  );
  const conflict = gate !== null && !gate.enabled && gate.reason === 'core_conflict' && deps.enginePython;
  return {
    enginePython: deps.enginePython,
    gate,
    bootstrapProbes: probes,
    instructions,
    apiKey: keyPresence(deps.hostEnv),
    providerEnv: environmentDiagnostics(deps.hostEnv),
    toolEnv: toolEnvironmentDiagnostics(deps.hostEnv),
    jobsEnabled: gate?.enabled === true,
    conflictFix: conflict ? renderUpstreamUninstall(deps.enginePython as string, deps.platform) : null,
    summary,
  };
}
