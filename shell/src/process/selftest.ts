/**
 * `run-image-pipeline-selftest` (20_SHELL.md REQ-SHL-20): version check, then
 * SPEC 10.1 `selftest`; no shell-authored fixture or parallel health mode.
 */
import type { Env } from '../pure/env';
import { buildUtilityRequest } from './launcher';
import type { Clock, Spawner } from './types';
import { captureProbe, probeVersion, RELEASE_LOCK, type VersionGate, type VersionPolicy } from './version-gate';

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

/** Upper bound for the bundled selftest (classifies one PDF and one PNG). */
export const SELFTEST_TIMEOUT_MS = 120000;

/** Spawns exactly `version` then `selftest` (or only `version` when blocked). */
export async function runSelftest(deps: SelftestDeps): Promise<SelftestOutcome> {
  if (!deps.enginePython) return { gate: null, selftestExit: null, ok: false, diagnostics: ['shell.RUNTIME'] };
  const gate = await probeVersion(deps.enginePython, { spawner: deps.spawner, clock: deps.clock, hostEnv: deps.hostEnv, cwd: deps.cwd, policy: deps.policy ?? RELEASE_LOCK });
  if (!gate.enabled) return { gate, selftestExit: null, ok: false, diagnostics: ['shell.RUNTIME'] };
  const request = buildUtilityRequest(deps.enginePython, 'selftest', deps.hostEnv, deps.cwd);
  const capture = await captureProbe(deps.spawner, request, deps.clock, SELFTEST_TIMEOUT_MS);
  if (capture.error || capture.timedOut || capture.status === null) return { gate, selftestExit: null, ok: false, diagnostics: ['shell.RUNTIME'] };
  const exit = capture.status.code;
  if (exit === 0) return { gate, selftestExit: 0, ok: true, diagnostics: [] };
  return { gate, selftestExit: exit, ok: false, diagnostics: ['shell.RUNTIME'] };
}
