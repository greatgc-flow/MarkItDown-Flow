/**
 * Complete `version` response gate (20_SHELL.md REQ-SHL-17; 25_PACKAGING.md
 * REQ-PKG-06; SPEC 10.1 by reference). Missing/malformed required fields,
 * timeout or mismatch block jobs; additional optional fields are ignored.
 */
import type { Env } from '../pure/env';
import { NotImplementedError } from '../pure/errors';
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
  /** Inclusive minor range on the release segment (REQ-GEN-03: 3.10-3.14; 3.15 experimental). */
  pythonMin: Semver;
  pythonMaxExclusive: Semver;
  /** Engine `>=2.0.0,<2.1.0` on the release segment (pre-release suffixes ignored). */
  engineMin: Semver;
  engineMaxExclusive: Semver;
  /** Core `>=0.3.5,<0.4`. */
  coreMin: Semver;
  coreMaxExclusive: Semver;
  /** Exact release-tested renderer/Pillow versions (lock entries, not SPEC examples). */
  pypdfium2: string;
  pillow: string;
  protocol: 1;
  triageSchema: 1;
}

/** Release lock for 2.0.0; values must equal the packaged engine's actual `version` output. */
export const RELEASE_LOCK: VersionPolicy = {
  pythonMin: [3, 10, 0],
  pythonMaxExclusive: [3, 15, 0],
  engineMin: [2, 0, 0],
  engineMaxExclusive: [2, 1, 0],
  coreMin: [0, 3, 5],
  coreMaxExclusive: [0, 4, 0],
  pypdfium2: '5.15.1',
  pillow: '13.0.0',
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

/** Pure: evaluate one stdout text against the policy. */
export function evaluateVersionResponse(_stdout: string, _policy: VersionPolicy = RELEASE_LOCK): VersionGate {
  throw new NotImplementedError('evaluateVersionResponse');
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

/** Spawn `<enginePython> -m mdflow version`, enforce the timeout, evaluate. Never spawns anything else. */
export async function probeVersion(_enginePython: string, _deps: VersionProbeDeps): Promise<VersionGate> {
  throw new NotImplementedError('probeVersion');
}
