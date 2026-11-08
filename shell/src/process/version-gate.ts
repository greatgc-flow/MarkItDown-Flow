/**
 * Complete `version` response gate (20_SHELL.md REQ-SHL-17; 25_PACKAGING.md
 * REQ-PKG-06; SPEC 10.1 by reference). Missing/malformed required fields,
 * timeout or mismatch block jobs; additional optional fields are ignored.
 */
import type { Env } from '../pure/env';
import { buildUtilityRequest } from './launcher';
import type { Clock, Spawner } from './types';

/** SPEC 10.1 `version` keys; all required. */
export const VERSION_REQUIRED_FIELDS = [
  'mdflow', 'markitdown-gc', 'pypdfium2', 'pillow', 'python', 'platform', 'protocol', 'triage_schema',
] as const;

export type VersionField = (typeof VERSION_REQUIRED_FIELDS)[number];

export interface VersionInfo {
  mdflow: string;
  'markitdown-gc': string;
  pypdfium2: string;
  pillow: string;
  python: string;
  platform: string;
  protocol: 1;
  triage_schema: 1;
}

export type Semver = readonly [number, number, number];

export interface VersionPolicy {
  /**
   * Tested interpreter range on the release segment. 25_PACKAGING.md REQ-PKG-05:
   * "Use a tested Python 3.10-3.14 interpreter; 3.15 is experimental" and
   * REQ-PKG-06: a Python policy mismatch blocks conversions. SPEC REQ-GEN-03's
   * "3.15 allowed-failure" is a CI-matrix rule (REQ-PKG-07), not a runtime
   * admission; an untested interpreter is blocked like any other mismatch.
   */
  pythonMin: Semver;
  pythonMaxExclusive: Semver;
  /** Engine `>=2.0.0,<2.1.0` on the release segment (pre-release suffixes ignored). */
  engineMin: Semver;
  engineMaxExclusive: Semver;
  /** Core `>=0.3.5,<0.4`. */
  coreMin: Semver;
  coreMaxExclusive: Semver;
  /**
   * Renderer/Pillow compatibility ranges (R27: range-resolved user installs are
   * admitted; exact installed versions are recorded in `VersionInfo` for
   * diagnosis/determinism, not gated).
   */
  pypdfium2Min: Semver;
  pypdfium2MaxExclusive: Semver;
  pillowMin: Semver;
  pillowMaxExclusive: Semver;
  protocol: 1;
  triageSchema: 1;
}

/** Compatibility policy for 2.0.0; the CI reference environment (pypdfium2 5.15.1, Pillow 13.0.0) lies inside. */
export const RELEASE_LOCK: VersionPolicy = {
  pythonMin: [3, 10, 0],
  pythonMaxExclusive: [3, 15, 0],
  engineMin: [2, 0, 0],
  engineMaxExclusive: [2, 1, 0],
  coreMin: [0, 3, 5],
  coreMaxExclusive: [0, 4, 0],
  pypdfium2Min: [5, 0, 0],
  pypdfium2MaxExclusive: [6, 0, 0],
  pillowMin: [11, 0, 0],
  pillowMaxExclusive: [14, 0, 0],
  protocol: 1,
  triageSchema: 1,
};

export type VersionGateReason =
  | 'spawn_failed'
  | 'timeout'
  | 'exit'
  | 'not_json'
  | 'missing_field'
  | 'bad_type'
  | 'protocol'
  | 'triage_schema'
  | 'python'
  | 'engine'
  | 'core'
  | 'pypdfium2'
  | 'pillow'
  | 'platform';

export type VersionGate =
  | { enabled: true; info: VersionInfo }
  | { enabled: false; diagnostic: 'shell.RUNTIME'; reason: VersionGateReason; field?: VersionField };

function blocked(reason: VersionGateReason, field?: VersionField): VersionGate {
  return field === undefined ? { enabled: false, diagnostic: 'shell.RUNTIME', reason } : { enabled: false, diagnostic: 'shell.RUNTIME', reason, field };
}

/** Release segment `major.minor[.patch]`; pre-release/dev suffixes are ignored. Null when unparsable. */
export function releaseSegment(version: string): Semver | null {
  const match = /^\s*(\d+)\.(\d+)(?:\.(\d+))?/.exec(version);
  if (!match) return null;
  return [Number(match[1]), Number(match[2]), match[3] === undefined ? 0 : Number(match[3])];
}

function compare(a: Semver, b: Semver): number {
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  }
  return 0;
}

function inRange(version: string, min: Semver, maxExclusive: Semver): boolean {
  const parsed = releaseSegment(version);
  return parsed !== null && compare(parsed, min) >= 0 && compare(parsed, maxExclusive) < 0;
}

const STRING_FIELDS: readonly VersionField[] = ['mdflow', 'markitdown-gc', 'pypdfium2', 'pillow', 'python', 'platform'];

/** Pure: evaluate one stdout text against the policy. */
export function evaluateVersionResponse(stdout: string, policy: VersionPolicy = RELEASE_LOCK): VersionGate {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return blocked('not_json');
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return blocked('not_json');
  const raw = parsed as Record<string, unknown>;
  for (const field of VERSION_REQUIRED_FIELDS) {
    if (!(field in raw) || raw[field] === undefined || raw[field] === null) return blocked('missing_field', field);
  }
  for (const field of STRING_FIELDS) {
    if (typeof raw[field] !== 'string') return blocked('bad_type', field);
  }
  if (typeof raw.protocol !== 'number') return blocked('bad_type', 'protocol');
  if (typeof raw.triage_schema !== 'number') return blocked('bad_type', 'triage_schema');
  if (raw.protocol !== policy.protocol) return blocked('protocol', 'protocol');
  if (raw.triage_schema !== policy.triageSchema) return blocked('triage_schema', 'triage_schema');
  const info: VersionInfo = {
    mdflow: raw.mdflow as string,
    'markitdown-gc': raw['markitdown-gc'] as string,
    pypdfium2: raw.pypdfium2 as string,
    pillow: raw.pillow as string,
    python: raw.python as string,
    platform: raw.platform as string,
    protocol: 1,
    triage_schema: 1,
  };
  if (!inRange(info.python, policy.pythonMin, policy.pythonMaxExclusive)) return blocked('python', 'python');
  if (!inRange(info.mdflow, policy.engineMin, policy.engineMaxExclusive)) return blocked('engine', 'mdflow');
  if (!inRange(info['markitdown-gc'], policy.coreMin, policy.coreMaxExclusive)) return blocked('core', 'markitdown-gc');
  if (!inRange(info.pypdfium2, policy.pypdfium2Min, policy.pypdfium2MaxExclusive)) return blocked('pypdfium2', 'pypdfium2');
  if (!inRange(info.pillow, policy.pillowMin, policy.pillowMaxExclusive)) return blocked('pillow', 'pillow');
  if (info.platform.trim().length === 0) return blocked('platform', 'platform');
  return { enabled: true, info };
}

/** REQ-SHL-10: probe the configured interpreter first with a five-second timeout. */
export const VERSION_PROBE_TIMEOUT_MS = 5000;

export interface VersionProbeDeps {
  spawner: Spawner;
  clock: Clock;
  hostEnv: Env;
  cwd: string;
  policy?: VersionPolicy;
  timeoutMs?: number;
}

export interface ProbeCapture {
  status: { code: number | null; signal: string | null } | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
  error: Error | null;
}

/** Bounded capture of a short-lived child (probes only); never used for conversions. */
export function captureProbe(
  spawner: Spawner,
  request: Parameters<Spawner['spawn']>[0],
  clock: Clock,
  timeoutMs: number,
  maxBytes = 65536,
): Promise<ProbeCapture> {
  return new Promise((resolve) => {
    const capture: ProbeCapture = { status: null, stdout: '', stderr: '', timedOut: false, error: null };
    let settled = false;
    let outBytes = 0;
    let errBytes = 0;
    const decoder = new TextDecoder('utf-8');
    const errDecoder = new TextDecoder('utf-8');
    const finish = (): void => {
      if (settled) return;
      settled = true;
      cancelTimer();
      resolve(capture);
    };
    let child: ReturnType<Spawner['spawn']>;
    try {
      child = spawner.spawn(request);
    } catch (error) {
      capture.error = error instanceof Error ? error : new Error(String(error));
      finish();
      return;
    }
    const cancelTimer = clock.setTimeout(() => {
      capture.timedOut = true;
      child.terminate();
      // Resolve once the child reports its exit; a child that never exits still releases the caller.
      finish();
    }, timeoutMs);
    child.onStdout((chunk) => {
      if (outBytes >= maxBytes) return;
      outBytes += chunk.length;
      capture.stdout += decoder.decode(chunk, { stream: true });
    });
    child.onStderr((chunk) => {
      if (errBytes >= maxBytes) return;
      errBytes += chunk.length;
      capture.stderr += errDecoder.decode(chunk, { stream: true });
    });
    child.onError((error) => {
      capture.error = error;
      finish();
    });
    child.onExit((status) => {
      capture.status = status;
      capture.stdout += decoder.decode();
      capture.stderr += errDecoder.decode();
      finish();
    });
  });
}

/** Spawn `<enginePython> -m mdflow version`, enforce the timeout, evaluate. Never spawns anything else. */
export async function probeVersion(enginePython: string, deps: VersionProbeDeps): Promise<VersionGate> {
  const request = buildUtilityRequest(enginePython, 'version', deps.hostEnv, deps.cwd);
  const capture = await captureProbe(deps.spawner, request, deps.clock, deps.timeoutMs ?? VERSION_PROBE_TIMEOUT_MS);
  if (capture.error) return blocked('spawn_failed');
  if (capture.timedOut) return blocked('timeout');
  if (capture.status?.code !== 0) return blocked('exit');
  return evaluateVersionResponse(capture.stdout, deps.policy ?? RELEASE_LOCK);
}
