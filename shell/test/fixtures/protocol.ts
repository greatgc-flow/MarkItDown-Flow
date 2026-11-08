/**
 * Synthetic protocol material shaped exactly after SPEC 7.1/7.3/7.4 examples.
 *
 * FX-71 (streams recorded from the real DRAFT-3 engine) does not exist yet
 * (R7 F-04); step 8 framing tests use these builders and must be re-run
 * against FX-71 in step 9. No golden is hand-written here: these are inputs.
 */
import type { Plan, PlanUnit, RunReport } from '../../src/pure/protocol';

export const HEX64_A = 'a'.repeat(64);
export const HEX64_B = 'b'.repeat(64);
export const HEX64_C = 'c'.repeat(64);
export const TS = '2026-11-09T00:00:00+00:00';

export const KOREAN_FILE = '보고서/3분기 결산.pdf';

export function jsonLine(value: unknown): string {
  return JSON.stringify(value);
}

export const encoder = new TextEncoder();

export function bytes(text: string): Uint8Array {
  return encoder.encode(text);
}

/** Split a byte array at the given absolute offsets. */
export function splitAt(buf: Uint8Array, offsets: number[]): Uint8Array[] {
  const out: Uint8Array[] = [];
  let prev = 0;
  for (const off of [...offsets, buf.length]) {
    out.push(buf.slice(prev, off));
    prev = off;
  }
  return out;
}

export const events = {
  runStart: () => ({ v: 1, ev: 'run_start', ts: TS, files: 2, provider: 'none' }),
  fileStart: (file = KOREAN_FILE) => ({ v: 1, ev: 'file_start', ts: TS, file, index: 1, total: 2 }),
  stage: (file = KOREAN_FILE) => ({ v: 1, ev: 'stage', ts: TS, file, stage: 'triage', state: 'end', ms: 412 }),
  classified: (file = KOREAN_FILE) => ({
    v: 1, ev: 'classified', ts: TS, file, route: 'NATIVE', need: 'PARTIAL', label: 'M', action: 'convert_and_ocr',
  }),
  approveRequired: (file = KOREAN_FILE) => ({
    v: 1,
    ev: 'approve_required',
    ts: TS,
    file,
    plan_hash: HEX64_A,
    destination: 'https://api.openai.com/v1/chat/completions',
    model: 'gpt-4.1-mini',
    keys_unique: 2,
    requests_to_send: 1,
    max_requests: 6,
    est_max_cost: '0.024000',
    cost_known: true,
    threshold_exceeded: false,
    sensitive_hits: [],
  }),
  unit: (file = KOREAN_FILE) => ({ v: 1, ev: 'unit', ts: TS, file, unit: 'p3', state: 'ok', code: null }),
  warning: (code = 'W_MEDIA_UNMAPPED', file = KOREAN_FILE) => ({ v: 1, ev: 'warning', ts: TS, file, code, message: 'redacted' }),
  error: (code = 'E_CONVERT_FAIL', file = KOREAN_FILE) => ({ v: 1, ev: 'error', ts: TS, file, code, message: '<redacted>' }),
  fileEnd: (file = KOREAN_FILE) => ({
    v: 1, ev: 'file_end', ts: TS, file, outputs: [`${file}.md`], units: { total: 5, done: 4, pending: 1, failed: 0 },
  }),
  runEnd: () => ({ v: 1, ev: 'run_end', ts: TS, exit: 0, files_ok: 2, files_failed: 0, provider_calls: 0 }),
};

export function planUnit(i: number): PlanUnit {
  return {
    kind: 'page',
    source_id: `p${i}`,
    page: i,
    status: 'eligible',
    raster_sha256: (i % 16).toString(16).repeat(64),
    dpi: 200,
    mime: 'image/png',
    bytes: 100000 + i,
    priority: 'normal',
    priority_core: 'high',
  };
}

export function plan(path: string, planHash: string, unitCount: number): Plan {
  const units = Array.from({ length: unitCount }, (_, i) => planUnit(i + 1));
  const keysUnique = new Set(units.map((u) => u.raster_sha256)).size;
  return {
    v: 1,
    approved: {
      file: { path, sha256: HEX64_C, bytes: 1048576, format: 'pdf' },
      classification: {
        route: 'NATIVE', need: 'PARTIAL', label: 'M', action: 'convert_and_ocr',
        decision: 'ocr_recommended', coverage_state: 'complete',
      },
      provider: {
        name: 'openai-compatible', model: 'gpt-4.1-mini', egress: true, cost_hint: '0.004000', max_batch: 1,
        retries: 2, destination: 'https://api.openai.com/v1/chat/completions', proxy: null, command_env_names: [],
      },
      provider_fingerprint: HEX64_B,
      prompt_version: 'p1',
      dpi: 200,
      units,
      units_total: units.length,
      keys_unique: keysUnique,
      max_requests: keysUnique * 3,
      est_max_cost: (0.004 * keysUnique * 3).toFixed(6),
      cost_known: true,
      approve_threshold: 20,
      threshold_exceeded: keysUnique > 20,
      sensitive_hits: [],
      oversize: false,
    },
    status: {
      units: { eligible: units.length, cached: 0, skipped_low_priority: 0, oversize: 0, render_failed: 0, unsupported_media_format: 0 },
      requests_to_send: keysUnique,
      uninspected_pages: 0,
      frames_total: null,
    },
    plan_hash: planHash,
  };
}

/** `mdflow plan` stdout: one pretty Plan per file, concatenated. */
export function planStdout(plans: Plan[]): string {
  return plans.map((p) => JSON.stringify(p, null, 2)).join('\n') + '\n';
}

export const CORE_TRIAGE_CORRUPT = {
  schema_version: 1,
  rules_version: '1',
  decision: 'corrupt',
  state: 'corrupt',
  issues: [{ code: 'suspect_text_layer', message: 'Core wording' }, { code: 'corrupt', message: 'unparseable' }],
  vendor_extra: { kept: 'verbatim' },
};

export function report(overrides: Partial<RunReport> = {}): RunReport {
  return {
    v: 1,
    mdflow: '2.0.0',
    started: TS,
    finished: TS,
    options: {
      provider: 'none', model: null, dpi: 200, min_priority: 'low', max_units: 200,
      approve_threshold: 20, force: false, cache: '~/.mdflow/cache', out: '~/vault/out',
    },
    files: [
      {
        path: KOREAN_FILE,
        root: 0,
        sha256: HEX64_C,
        bytes: 1048576,
        format: 'pdf',
        route: 'NATIVE',
        need: 'UNKNOWN',
        label: 'X',
        action: 'report_only',
        decision: 'corrupt',
        coverage_state: 'none',
        units: { total: 0, eligible: 0, cached: 0, transcribed: 0, pending: 0, failed: 0 },
        requests: { to_send: 0, sent: 0, ok: 0, failed: 0 },
        placements: 0,
        issues: [{ code: 'E_CORRUPT', message: 'Source could not be parsed.' }],
        outputs: [],
        plan_hash: null,
        consent: null,
        triage: CORE_TRIAGE_CORRUPT,
      },
    ],
    skipped: [{ path: '.DS_Store', code: 'W_SKIPPED_HIDDEN' }],
    exit: 2,
    ...overrides,
  };
}
