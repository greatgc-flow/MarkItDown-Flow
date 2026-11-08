/**
 * Active mdflow engine codes: the shell's engine message-table rows, generated
 * from the Code column of SPEC section 7.5 (20_SHELL.md section 6). JT-SHL-19-01
 * asserts set equality with the SPEC table and both dictionaries; keep this the
 * only code list in the shell.
 */

export const ENGINE_ERROR_CODES = [
  'E_USAGE',
  'E_CORE_VERSION',
  'E_PROVIDER_CONFIG',
  'E_SNIFF_IO',
  'E_TOO_LARGE',
  'E_ENCRYPTED',
  'E_CORRUPT',
  'E_UNSUPPORTED',
  'E_MEDIA_OUT_OF_SCOPE',
  'E_LEGACY',
  'E_ZIP_PATH',
  'E_ZIP_DEPTH',
  'E_ZIP_ENTRIES',
  'E_ZIP_TOTAL',
  'E_ZIP_BOMB',
  'E_TRIAGE_FAIL',
  'E_TRIAGE_SCHEMA',
  'E_CONVERT_FAIL',
  'E_RENDER_FAIL',
  'E_PLAN_OVERSIZE',
  'E_OUTPUT_IO',
  'E_OUTPUT_COLLISION',
  'E_CACHE_IO',
  'E_APPROVAL_REQUIRED',
  'E_APPROVAL_DENIED',
  'E_PROVIDER_HTTP',
  'E_PROVIDER_TIMEOUT',
  'E_PROVIDER_OUTPUT',
] as const;

export const ENGINE_WARNING_CODES = [
  'W_SKIPPED_HIDDEN',
  'W_SKIPPED_SYMLINK',
  'W_DUPLICATE_INPUT',
  'W_EXT_MISMATCH',
  'W_MEDIA_NOT_INSPECTED',
  'W_TRIAGE_UNSUPPORTED',
  'W_TRIAGE_UNKNOWN',
  'W_TRIAGE_INCONSISTENT',
  'W_TRIAGE_UNKNOWN_VALUE',
  'W_TRIAGE_PARTIAL',
  'W_CORE_DEPENDENCY',
  'W_EXTERNAL_MEDIA',
  'W_UNRESOLVED_EMBED',
  'W_IMAGE_PROBE',
  'W_REVIEW_PRIORITY',
  'W_MEDIA_UNMAPPED',
  'W_MEDIA_FORMAT',
  'W_MEDIA_MULTIFRAME',
  'W_CACHE_CORRUPT',
  'W_OUTPUT_TRUNCATED',
  'W_OUTPUT_EDITED',
  'W_APPROVAL_UNUSED',
] as const;

export type EngineCode = (typeof ENGINE_ERROR_CODES)[number] | (typeof ENGINE_WARNING_CODES)[number];

export const ENGINE_CODES: readonly EngineCode[] = [...ENGINE_ERROR_CODES, ...ENGINE_WARNING_CODES];

const CODE_SET: ReadonlySet<string> = new Set<string>(ENGINE_CODES);

export function isKnownEngineCode(code: unknown): code is EngineCode {
  return typeof code === 'string' && CODE_SET.has(code);
}
