/**
 * Credential presence, provider availability and engine environment scrubbing
 * (20_SHELL.md REQ-SHL-06; SPEC 8.2/9 R8).
 */
import type { ProviderName, SettingsV2 } from './settings';

export type Env = Readonly<Record<string, string | undefined>>;

export const API_KEY_VAR = 'MDFLOW_API_KEY';

/** Provider variables the engine reads (SPEC 10.2 Env). Forwarded only for `openai-compatible`. */
export const PROVIDER_ENV_VARS: readonly string[] = [
  'MDFLOW_API_KEY',
  'MDFLOW_BASE_URL',
  'MDFLOW_TIMEOUT_S',
  'MDFLOW_PROXY',
];

/** SPEC 8.2 allowlist; the engine child receives nothing else from the host. */
export const BASELINE_ENV_VARS: readonly string[] = [
  'PATH',
  'SYSTEMROOT',
  'SYSTEMDRIVE',
  'COMSPEC',
  'HOME',
  'USERPROFILE',
  'TEMP',
  'TMP',
  'LANG',
  'LC_ALL',
];

/**
 * Optional tool locations the engine detects (R31 `EXIFTOOL_PATH`, R33 `SOFFICE_PATH`): nonsecret
 * executable paths, forwarded for every provider so a tool installed outside PATH is found from
 * the plugin exactly as from a terminal. Displayed by presence only.
 */
export const TOOL_PATH_ENV_VARS: readonly string[] = ['EXIFTOOL_PATH', 'SOFFICE_PATH'];

export const API_KEY_MISSING_KEY = 'shell.setup.apiKeyMissing';

export type Presence = 'present' | 'absent';

export interface ProviderAvailability {
  effectiveProvider: ProviderName;
  /** True when remote execution must be blocked (openai-compatible without key). */
  remoteBlocked: boolean;
  /** Localized guidance key, e.g. `shell.setup.apiKeyMissing`, or null. */
  guidanceKey: string | null;
}

function present(env: Env, name: string): boolean {
  const value = env[name];
  return typeof value === 'string' && value.length > 0;
}

/** Whether MDFLOW_API_KEY is set; never its value. */
export function keyPresence(env: Env): Presence {
  return present(env, API_KEY_VAR) ? 'present' : 'absent';
}

export function providerAvailability(settings: SettingsV2, env: Env): ProviderAvailability {
  if (settings.provider.name === 'none') {
    return { effectiveProvider: 'none', remoteBlocked: false, guidanceKey: null };
  }
  if (keyPresence(env) === 'present') {
    return { effectiveProvider: 'openai-compatible', remoteBlocked: false, guidanceKey: null };
  }
  // Keep local conversion usable; remote work is blocked until the key is inherited at launch.
  return { effectiveProvider: 'none', remoteBlocked: true, guidanceKey: API_KEY_MISSING_KEY };
}

/** SPEC baseline allowlist + tool locations + UTF-8 settings + provider variables for the selected provider. */
export function scrubEngineEnv(env: Env, provider: ProviderName): Record<string, string> {
  const out: Record<string, string> = {};
  const copy = (name: string): void => {
    const value = env[name];
    if (typeof value === 'string') out[name] = value;
  };
  for (const name of BASELINE_ENV_VARS) copy(name);
  for (const name of TOOL_PATH_ENV_VARS) copy(name);
  out.PYTHONUTF8 = '1';
  out.PYTHONIOENCODING = 'utf-8';
  if (provider === 'openai-compatible') {
    for (const name of PROVIDER_ENV_VARS) copy(name);
  }
  return out;
}

/** Presence map for diagnostics/SetupModal; contains no variable values. */
export function environmentDiagnostics(env: Env): Record<string, Presence> {
  const out: Record<string, Presence> = {};
  for (const name of PROVIDER_ENV_VARS) out[name] = present(env, name) ? 'present' : 'absent';
  return out;
}

/** Presence (never the path) of the optional tool location variables. */
export function toolEnvironmentDiagnostics(env: Env): Record<string, Presence> {
  const out: Record<string, Presence> = {};
  for (const name of TOOL_PATH_ENV_VARS) out[name] = present(env, name) ? 'present' : 'absent';
  return out;
}
