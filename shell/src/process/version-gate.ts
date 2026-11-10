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

/** Detection states of the optional external tools (SPEC REQ-CNV-06 for exiftool; R33 LibreOffice alike). */
export const TOOL_STATUSES = ['ok', 'not_found', 'too_old', 'unusable'] as const;
export type ToolStatus = (typeof TOOL_STATUSES)[number];

/** Where the engine found an optional tool: its `*_PATH` variable, `PATH`, or nowhere. */
export type ToolSource = string | null;

export interface VersionInfo {
  mdflow: string;
  'markitdown-gc': string;
  pypdfium2: string;
  pillow: string;
  python: string;
  platform: string;
  protocol: 1;
  triage_schema: 1;
  /**
   * Optional (R31): exiftool version text, or `null` when the engine reports none (its
   * `"unavailable"` spelling or JSON null). Absent when the engine does not report it.
   * Diagnostics only; never gated.
   */
  exiftool?: string | null;
  exiftool_status?: ToolStatus;
  exiftool_source?: ToolSource;
  /**
   * Optional (R33): LibreOffice (`soffice`) as detected through `SOFFICE_PATH`/PATH, same shape as
   * exiftool. Older engines that omit these diagnostics show "not reported".
   */
  libreoffice?: string | null;
  libreoffice_status?: ToolStatus;
  libreoffice_source?: ToolSource;
}

/** Optional `version` keys that describe tools, not the gated engine identity. */
export const TOOL_INFO_KEYS: readonly (keyof VersionInfo)[] = [
  'exiftool', 'exiftool_status', 'exiftool_source', 'libreoffice', 'libreoffice_status', 'libreoffice_source',
];

/** SPEC 7.5 startup code of the R33c co-install guard (REQ-GEN-12): `version` exits 1 with it before any response. */
export const CORE_CONFLICT_CODE = 'E_CORE_CONFLICT';

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
  /** Core `>=0.3.7,<0.4`. */
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
  coreMin: [0, 3, 7],
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
  | 'platform'
  /** R33c: `version` exited 1 with `E_CORE_CONFLICT` (upstream `markitdown` co-installed with markitdown-gc). */
  | 'core_conflict';

export type VersionGate =
  | { enabled: true; info: VersionInfo }
  | { enabled: false; diagnostic: 'shell.RUNTIME'; reason: VersionGateReason; field?: VersionField };

function blocked(reason: VersionGateReason, field?: VersionField): VersionGate {
  return field === undefined ? { enabled: false, diagnostic: 'shell.RUNTIME', reason } : { enabled: false, diagnostic: 'shell.RUNTIME', reason, field };
}

/**
 * Step one of the package gate (`test_pt_release.py`): the whole text is
 * `[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.+-]*)`. Excludes whitespace, `v` prefixes,
 * epochs (`1!`), `_` separators and a bare major.
 */
const PACKAGE_GATE_CHARSET = /^[0-9]+(?:\.[0-9]+)+[A-Za-z0-9.+-]*$/;

/**
 * Step two of the package gate: `packaging.version.Version(text)` must accept the text.
 * This is PEP 440's public grammar as `packaging` spells it (case-insensitive), minus the
 * parts step one already excludes (surrounding whitespace, `v`, epoch, `_` separators):
 * release `N(.N)*`, optional pre `[-.]?(a|b|c|rc|alpha|beta|pre|preview)[-.]?N?`, optional
 * post `-N` or `[-.]?(post|rev|r)[-.]?N?`, optional dev `[-.]?dev[-.]?N?`, optional local
 * `+[a-z0-9]+([-.][a-z0-9]+)*`.
 */
const PEP440_PUBLIC = /^(\d+(?:\.\d+)*)(?:[-.]?(?:a|b|c|rc|alpha|beta|pre|preview)[-.]?\d*)?(?:-\d+|[-.]?(?:post|rev|r)[-.]?\d*)?(?:[-.]?dev[-.]?\d*)?(?:\+[a-z0-9]+(?:[-.][a-z0-9]+)*)?$/i;

/**
 * Release segment `major.minor[.patch]` of a version string that passes BOTH steps of the
 * package gate (`test_pt_release.py` `valid()`: the character regex, then
 * `packaging.version.Version`). PEP 440 suffixes (`rc1`, `.post1`, `-1`, `.dev0`, `+local`)
 * are admitted and ignored on the release segment; `3.14garbage`, `5.15.1abc`, `5.15.1..1`,
 * `5.15.1+`, `5.15.1???`, whitespace or a bare major are null, so the shell and the package
 * gate agree on every spelling (M4 P-02 / M3-V04 / M5 Q-01).
 */
export function releaseSegment(version: string): Semver | null {
  if (!PACKAGE_GATE_CHARSET.test(version)) return null;
  const match = PEP440_PUBLIC.exec(version);
  if (!match) return null;
  // `version_tuple` of the package gate: the leading dotted integers; parts beyond the third are ignored.
  const parts = match[1].split('.').map(Number);
  return [parts[0], parts[1] ?? 0, parts[2] ?? 0];
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
  // Optional tool status (R31 exiftool, R33 LibreOffice): a version string or null (the engine's `"unavailable"`
  // reads as null); status/source only in their closed vocabularies. Any other shape is an ignored optional field.
  for (const tool of ['exiftool', 'libreoffice'] as const) {
    const version = raw[tool];
    if (version === null || version === 'unavailable') info[tool] = null;
    else if (typeof version === 'string') info[tool] = version;
    const status = raw[`${tool}_status`];
    if (typeof status === 'string' && (TOOL_STATUSES as readonly string[]).includes(status)) info[`${tool}_status`] = status as ToolStatus;
    const source = raw[`${tool}_source`];
    if (source === null || typeof source === 'string') info[`${tool}_source`] = source;
  }
  if (!inRange(info.python, policy.pythonMin, policy.pythonMaxExclusive)) return blocked('python', 'python');
  if (!inRange(info.mdflow, policy.engineMin, policy.engineMaxExclusive)) return blocked('engine', 'mdflow');
  if (!inRange(info['markitdown-gc'], policy.coreMin, policy.coreMaxExclusive)) return blocked('core', 'markitdown-gc');
  if (!inRange(info.pypdfium2, policy.pypdfium2Min, policy.pypdfium2MaxExclusive)) return blocked('pypdfium2', 'pypdfium2');
  if (!inRange(info.pillow, policy.pillowMin, policy.pillowMaxExclusive)) return blocked('pillow', 'pillow');
  if (info.platform.trim().length === 0) return blocked('platform', 'platform');
  return { enabled: true, info };
}

/**
 * The SPEC 7.5 code of an exit-1 startup error object (`{"error": {"code": ..., "message": ...}}`,
 * one JSON object on stderr), or null when stderr holds anything else. The message is never read.
 */
export function startupErrorCode(stderr: string): string | null {
  const text = stderr.trim();
  if (text.length === 0 || text.includes('\n')) return null;
  try {
    const parsed: unknown = JSON.parse(text);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return null;
    const error = (parsed as Record<string, unknown>).error;
    if (typeof error !== 'object' || error === null) return null;
    const code = (error as Record<string, unknown>).code;
    return typeof code === 'string' && /^E_[A-Z0-9_]+$/.test(code) ? code : null;
  } catch {
    return null;
  }
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
    // Assigned after the spawn succeeds; a synchronous spawn failure finishes before any timer exists (no TDZ access).
    let cancelTimer: () => void = () => undefined;
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
    cancelTimer = clock.setTimeout(() => {
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

/**
 * M6-01: pause before the single retry of a timed-out probe. The engine's optional exiftool/LibreOffice
 * probes can make a cold first `version` slow (profile creation, antivirus scan); the second attempt runs warm.
 */
export const VERSION_PROBE_BACKOFF_MS = 1000;

/**
 * M6-01: a gate that says nothing about compatibility (the probe did not answer or could not start).
 * It must never be cached as the jobs verdict: the next job probes again.
 */
export function isTransientGate(gate: VersionGate | null): boolean {
  return gate !== null && !gate.enabled && (gate.reason === 'timeout' || gate.reason === 'spawn_failed');
}

/** Spawn `<enginePython> -m mdflow version`, enforce the timeout, evaluate. A timeout is retried once after a backoff. */
export async function probeVersion(enginePython: string, deps: VersionProbeDeps): Promise<VersionGate> {
  const first = await probeVersionOnce(enginePython, deps);
  if (!(!first.enabled && first.reason === 'timeout')) return first;
  await new Promise<void>((resolve) => {
    deps.clock.setTimeout(resolve, VERSION_PROBE_BACKOFF_MS);
  });
  return probeVersionOnce(enginePython, deps);
}

/** One bounded attempt. Never spawns anything but `version`. */
async function probeVersionOnce(enginePython: string, deps: VersionProbeDeps): Promise<VersionGate> {
  const request = buildUtilityRequest(enginePython, 'version', deps.hostEnv, deps.cwd);
  const capture = await captureProbe(deps.spawner, request, deps.clock, deps.timeoutMs ?? VERSION_PROBE_TIMEOUT_MS);
  if (capture.error) return blocked('spawn_failed');
  if (capture.timedOut) return blocked('timeout');
  if (capture.status?.code !== 0) {
    // R33c (SPEC REQ-GEN-12): the co-install guard answers `version` with exit 1 and E_CORE_CONFLICT on stderr
    // before any response; name that state so diagnostics can show the fix. Any other exit is a plain `exit`.
    return blocked(startupErrorCode(capture.stderr) === CORE_CONFLICT_CODE ? 'core_conflict' : 'exit');
  }
  return evaluateVersionResponse(capture.stdout, deps.policy ?? RELEASE_LOCK);
}
