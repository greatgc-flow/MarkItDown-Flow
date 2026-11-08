/**
 * Credential presence, provider availability and engine environment scrubbing
 * (20_SHELL.md REQ-SHL-06; SPEC 8.2/9 R8).
 */
import type { ProviderName, SettingsV2 } from './settings';
import { NotImplementedError } from './errors';

export type Env = Readonly<Record<string, string | undefined>>;

export const API_KEY_VAR = 'MDFLOW_API_KEY';

/** Provider variables the engine reads (SPEC 10.2 Env). Forwarded only for `openai-compatible`. */
export const PROVIDER_ENV_VARS: readonly string[] = [
  'MDFLOW_API_KEY',
  'MDFLOW_BASE_URL',
  'MDFLOW_TIMEOUT_S',
  'MDFLOW_PROXY',
];

export type Presence = 'present' | 'absent';

export interface ProviderAvailability {
  effectiveProvider: ProviderName;
  /** True when remote execution must be blocked (openai-compatible without key). */
  remoteBlocked: boolean;
  /** Localized guidance key, e.g. `shell.setup.apiKeyMissing`, or null. */
  guidanceKey: string | null;
}

/** Whether MDFLOW_API_KEY is set; never its value. */
export function keyPresence(_env: Env): Presence {
  throw new NotImplementedError('keyPresence');
}

export function providerAvailability(_settings: SettingsV2, _env: Env): ProviderAvailability {
  throw new NotImplementedError('providerAvailability');
}

/** SPEC baseline allowlist + UTF-8 settings + provider variables for the selected provider. */
export function scrubEngineEnv(_env: Env, _provider: ProviderName): Record<string, string> {
  throw new NotImplementedError('scrubEngineEnv');
}

/** Presence map for diagnostics/SetupModal; contains no variable values. */
export function environmentDiagnostics(_env: Env): Record<string, Presence> {
  throw new NotImplementedError('environmentDiagnostics');
}
