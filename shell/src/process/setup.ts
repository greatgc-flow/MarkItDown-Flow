/**
 * Diagnostics-only setup data (20_SHELL.md REQ-SHL-10; 25_PACKAGING.md
 * section 2). Probes are version probes only; instructions are rendered text
 * for the user's own terminal. Nothing is installed, downloaded or executed as
 * a fallback interpreter.
 */
import type { Env, Presence } from '../pure/env';
import { NotImplementedError } from '../pure/errors';
import type { Clock, HostPlatform, Spawner } from './types';
import type { VersionGate, VersionPolicy } from './version-gate';

/** Optional bootstrap probes when `enginePython` is unset; they only prefill instructions. */
export const BOOTSTRAP_PROBE_CANDIDATES: readonly { command: string; args: readonly string[] }[] = [
  { command: 'python3', args: ['--version'] },
  { command: 'python', args: ['--version'] },
  { command: 'py', args: ['-3', '--version'] },
];

export interface BootstrapProbe {
  command: string;
  args: string[];
  result: 'ok' | 'failed' | 'timeout';
  /** Parsed `Python X.Y.Z` or null. */
  version: string | null;
}

export interface BootstrapPaths {
  /** Extracted `engine.zip` root, as the user will type it. */
  engineRoot: string;
  /** Target venv directory. */
  venvDir: string;
  /** Bootstrap interpreter command (`py -3.14`, `python3.14`, or the migrated hint). */
  bootstrapPython: string;
}

export interface SetupDiagnostics {
  enginePython: string | null;
  /** Null when unconfigured. */
  gate: VersionGate | null;
  bootstrapProbes: BootstrapProbe[];
  instructions: { windows: string; posix: string };
  apiKey: Presence;
  jobsEnabled: boolean;
  /** Redacted, code-only summary for the diagnostics copy button. */
  summary: string;
}

export interface SetupDeps {
  spawner: Spawner;
  clock: Clock;
  hostEnv: Env;
  platform: HostPlatform;
  cwd: string;
  enginePython: string | null;
  bootstrapPythonHint?: string;
  paths?: Partial<BootstrapPaths>;
  policy?: VersionPolicy;
  /** Redaction inputs: home prefix and vault root. */
  home?: string;
  vault?: string;
}

/** Render the 25_PACKAGING section 2 command blocks with the given paths substituted. */
export function renderBootstrapInstructions(_paths: BootstrapPaths): { windows: string; posix: string } {
  throw new NotImplementedError('renderBootstrapInstructions');
}

/** Collect diagnostics: version probe of `enginePython` first; bootstrap probes only when unconfigured. */
export async function collectSetupDiagnostics(_deps: SetupDeps): Promise<SetupDiagnostics> {
  throw new NotImplementedError('collectSetupDiagnostics');
}
