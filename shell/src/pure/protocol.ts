/**
 * Decoding of `plan` stdout and the run report (20_SHELL.md REQ-SHL-13;
 * SPEC 7.1/7.4/7.5 incorporated by reference, R5-N08 separate Core vocabulary).
 */
import { isKnownEngineCode } from './codes';

export interface PlanUnit {
  kind: 'page' | 'media';
  source_id: string;
  page: number | null;
  status: 'eligible' | 'skipped_low_priority' | 'oversize' | 'render_failed' | 'unsupported_media_format';
  raster_sha256: string | null;
  dpi: number;
  mime: string | null;
  bytes: number | null;
  priority: 'normal' | 'low';
  priority_core: 'high' | 'low';
  also?: string[];
  media_file?: string | null;
}

export interface Plan {
  v: 1;
  approved: {
    file: { path: string; sha256: string; bytes: number; format: string };
    classification: {
      route: string; need: string; label: string; action: string; decision: string; coverage_state: string;
    };
    provider: {
      name: string; model: string; egress: boolean; cost_hint: string | null; max_batch: number;
      retries: number; destination: string | null; proxy: string | null; command_env_names: string[];
    };
    provider_fingerprint: string;
    prompt_version: string;
    dpi: number;
    units: PlanUnit[];
    units_total: number;
    keys_unique: number;
    max_requests: number;
    est_max_cost: string | null;
    cost_known: boolean;
    approve_threshold: number;
    threshold_exceeded: boolean;
    sensitive_hits: string[];
    oversize: boolean;
  };
  status: {
    units: {
      eligible: number; cached: number; skipped_low_priority: number; oversize: number;
      render_failed: number; unsupported_media_format: number;
    };
    requests_to_send: number;
    uninspected_pages: number;
    frames_total: number | null;
  };
  plan_hash: string;
}

export interface Issue { code: string; message: string }

export interface ReportFile {
  path: string;
  root: number;
  sha256: string;
  bytes: number;
  format: string;
  route: string;
  need: string;
  label: string;
  action: string;
  decision: string;
  coverage_state: string;
  units: { total: number; eligible: number; cached: number; transcribed: number; pending: number; failed: number };
  requests: { to_send: number; sent: number; ok: number; failed: number };
  placements: number;
  issues: Issue[];
  outputs: string[];
  plan_hash: string | null;
  consent: { plan_hash: string; approved_at: string; by: string } | null;
  /** Verbatim Core report; its vocabulary is NOT validated against SPEC 7.5. */
  triage: unknown;
}

export interface RunReport {
  v: 1;
  mdflow: string;
  started: string;
  finished: string;
  options: Record<string, unknown>;
  files: ReportFile[];
  skipped: { path: string; code: string }[];
  exit: number;
}

export type Decoded<T> =
  | { ok: true; value: T }
  | { ok: false; diagnostic: 'shell.PROTOCOL'; reason: string };

type Raw = Record<string, unknown>;

const HEX64 = /^[0-9a-f]{64}$/;
const UNIT_STATUSES: ReadonlySet<string> = new Set(['eligible', 'skipped_low_priority', 'oversize', 'render_failed', 'unsupported_media_format']);

function isRecord(value: unknown): value is Raw {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
const isString = (v: unknown): v is string => typeof v === 'string';
const isNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isBoolean = (v: unknown): v is boolean => typeof v === 'boolean';
const isStringArray = (v: unknown): v is string[] => Array.isArray(v) && v.every(isString);
const isNullableString = (v: unknown): v is string | null => v === null || isString(v);
const isNullableNumber = (v: unknown): v is number | null => v === null || isNumber(v);

class SchemaError extends Error {}

function fail(reason: string): never {
  throw new SchemaError(reason);
}

function need<T>(ok: boolean, value: unknown, reason: string): T {
  if (!ok) fail(reason);
  return value as T;
}

function numbers<K extends string>(value: unknown, keys: readonly K[], where: string): Record<K, number> {
  const r = need<Raw>(isRecord(value), value, `${where} must be an object`);
  const out = {} as Record<K, number>;
  for (const key of keys) out[key] = need<number>(isNumber(r[key]), r[key], `${where}.${key} must be a number`);
  return out;
}

function decodeUnit(value: unknown, index: number): PlanUnit {
  const where = `units[${index}]`;
  const r = need<Raw>(isRecord(value), value, `${where} must be an object`);
  const unit: PlanUnit = {
    kind: need(r.kind === 'page' || r.kind === 'media', r.kind, `${where}.kind`),
    source_id: need(isString(r.source_id), r.source_id, `${where}.source_id`),
    page: need(isNullableNumber(r.page), r.page, `${where}.page`),
    status: need(isString(r.status) && UNIT_STATUSES.has(r.status), r.status, `${where}.status`),
    raster_sha256: need(r.raster_sha256 === null || (isString(r.raster_sha256) && HEX64.test(r.raster_sha256)), r.raster_sha256, `${where}.raster_sha256`),
    dpi: need(isNumber(r.dpi), r.dpi, `${where}.dpi`),
    mime: need(isNullableString(r.mime), r.mime, `${where}.mime`),
    bytes: need(isNullableNumber(r.bytes), r.bytes, `${where}.bytes`),
    priority: need(r.priority === 'normal' || r.priority === 'low', r.priority, `${where}.priority`),
    priority_core: need(r.priority_core === 'high' || r.priority_core === 'low', r.priority_core, `${where}.priority_core`),
  };
  if (r.also !== undefined) unit.also = need<string[]>(isStringArray(r.also), r.also, `${where}.also`);
  if (r.media_file !== undefined) unit.media_file = need<string | null>(isNullableString(r.media_file), r.media_file, `${where}.media_file`);
  return unit;
}

function decodePlan(value: unknown): Plan {
  const r = need<Raw>(isRecord(value), value, 'plan must be an object');
  if (r.v !== 1) fail('plan.v must be 1');
  const a = need<Raw>(isRecord(r.approved), r.approved, 'plan.approved');
  const file = need<Raw>(isRecord(a.file), a.file, 'approved.file');
  const cls = need<Raw>(isRecord(a.classification), a.classification, 'approved.classification');
  const prov = need<Raw>(isRecord(a.provider), a.provider, 'approved.provider');
  const unitsRaw = need<unknown[]>(Array.isArray(a.units), a.units, 'approved.units must be an array');
  const units = unitsRaw.map(decodeUnit);
  const statusRaw = need<Raw>(isRecord(r.status), r.status, 'plan.status');
  const statusUnits = numbers(statusRaw.units, ['eligible', 'cached', 'skipped_low_priority', 'oversize', 'render_failed', 'unsupported_media_format'] as const, 'status.units');
  const plan: Plan = {
    v: 1,
    approved: {
      file: {
        path: need(isString(file.path), file.path, 'file.path'),
        sha256: need(isString(file.sha256), file.sha256, 'file.sha256'),
        bytes: need(isNumber(file.bytes), file.bytes, 'file.bytes'),
        format: need(isString(file.format), file.format, 'file.format'),
      },
      classification: {
        route: need(isString(cls.route), cls.route, 'classification.route'),
        need: need(isString(cls.need), cls.need, 'classification.need'),
        label: need(isString(cls.label), cls.label, 'classification.label'),
        action: need(isString(cls.action), cls.action, 'classification.action'),
        decision: need(isString(cls.decision), cls.decision, 'classification.decision'),
        coverage_state: need(isString(cls.coverage_state), cls.coverage_state, 'classification.coverage_state'),
      },
      provider: {
        name: need(isString(prov.name), prov.name, 'provider.name'),
        model: need(isString(prov.model), prov.model, 'provider.model'),
        egress: need(isBoolean(prov.egress), prov.egress, 'provider.egress'),
        cost_hint: need(isNullableString(prov.cost_hint), prov.cost_hint, 'provider.cost_hint'),
        max_batch: need(isNumber(prov.max_batch), prov.max_batch, 'provider.max_batch'),
        retries: need(isNumber(prov.retries), prov.retries, 'provider.retries'),
        destination: need(isNullableString(prov.destination), prov.destination, 'provider.destination'),
        proxy: need(isNullableString(prov.proxy), prov.proxy, 'provider.proxy'),
        command_env_names: need(isStringArray(prov.command_env_names), prov.command_env_names, 'provider.command_env_names'),
      },
      provider_fingerprint: need(isString(a.provider_fingerprint), a.provider_fingerprint, 'approved.provider_fingerprint'),
      prompt_version: need(isString(a.prompt_version), a.prompt_version, 'approved.prompt_version'),
      dpi: need(isNumber(a.dpi), a.dpi, 'approved.dpi'),
      units,
      units_total: need(isNumber(a.units_total), a.units_total, 'approved.units_total'),
      keys_unique: need(isNumber(a.keys_unique), a.keys_unique, 'approved.keys_unique'),
      max_requests: need(isNumber(a.max_requests), a.max_requests, 'approved.max_requests'),
      est_max_cost: need(isNullableString(a.est_max_cost), a.est_max_cost, 'approved.est_max_cost'),
      cost_known: need(isBoolean(a.cost_known), a.cost_known, 'approved.cost_known'),
      approve_threshold: need(isNumber(a.approve_threshold), a.approve_threshold, 'approved.approve_threshold'),
      threshold_exceeded: need(isBoolean(a.threshold_exceeded), a.threshold_exceeded, 'approved.threshold_exceeded'),
      sensitive_hits: need(isStringArray(a.sensitive_hits), a.sensitive_hits, 'approved.sensitive_hits'),
      oversize: need(isBoolean(a.oversize), a.oversize, 'approved.oversize'),
    },
    status: {
      units: statusUnits,
      requests_to_send: need(isNumber(statusRaw.requests_to_send), statusRaw.requests_to_send, 'status.requests_to_send'),
      uninspected_pages: need(isNumber(statusRaw.uninspected_pages), statusRaw.uninspected_pages, 'status.uninspected_pages'),
      frames_total: need(isNullableNumber(statusRaw.frames_total), statusRaw.frames_total, 'status.frames_total'),
    },
    plan_hash: need(isString(r.plan_hash) && HEX64.test(r.plan_hash), r.plan_hash, 'plan_hash must be 64 hex'),
  };
  // SPEC 7.1 structural equations the shell can check without the raster bytes.
  if (plan.approved.units_total !== units.length) fail('units_total != len(units)');
  const sum = Object.values(statusUnits).reduce((acc, n) => acc + n, 0);
  if (sum !== plan.approved.units_total) fail('sum(status.units) != units_total');
  if (plan.status.requests_to_send > plan.approved.keys_unique) fail('requests_to_send > keys_unique');
  return plan;
}

/** Split concatenated top-level JSON values (pretty-printed, whitespace separated). */
function splitJsonValues(text: string): unknown[] {
  const values: unknown[] = [];
  let depth = 0;
  let inString = false;
  let escaped = false;
  let start = -1;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inString) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') { inString = true; continue; }
    if (ch === '{' || ch === '[') {
      if (depth === 0) start = i;
      depth += 1;
    } else if (ch === '}' || ch === ']') {
      depth -= 1;
      if (depth < 0) fail('unbalanced JSON');
      if (depth === 0) {
        values.push(JSON.parse(text.slice(start, i + 1)));
        start = -1;
      }
    } else if (depth === 0 && !/\s/.test(ch)) {
      fail('unexpected text between JSON values');
    }
  }
  if (depth !== 0 || inString) fail('truncated JSON');
  return values;
}

/** Parse the concatenated pretty-printed Plans that `mdflow plan` writes to stdout. */
export function parsePlanOutput(stdout: string): Decoded<Plan[]> {
  try {
    const values = splitJsonValues(stdout);
    if (values.length === 0) fail('no Plan in output');
    return { ok: true, value: values.map(decodePlan) };
  } catch (error) {
    return { ok: false, diagnostic: 'shell.PROTOCOL', reason: error instanceof SchemaError ? error.message : 'plan output is not valid JSON' };
  }
}

function decodeIssue(value: unknown, where: string): Issue {
  const r = need<Raw>(isRecord(value), value, `${where} must be an object`);
  const code = need<string>(isString(r.code), r.code, `${where}.code`);
  if (!isKnownEngineCode(code)) fail(`${where}.code is not a SPEC 7.5 code`);
  return { code, message: need(isString(r.message), r.message, `${where}.message`) };
}

function decodeFile(value: unknown, index: number): ReportFile {
  const where = `files[${index}]`;
  const r = need<Raw>(isRecord(value), value, `${where} must be an object`);
  const str = (key: string): string => need(isString(r[key]), r[key], `${where}.${key}`);
  const consentRaw = r.consent;
  let consent: ReportFile['consent'] = null;
  if (consentRaw !== null) {
    const c = need<Raw>(isRecord(consentRaw), consentRaw, `${where}.consent`);
    consent = {
      plan_hash: need(isString(c.plan_hash), c.plan_hash, `${where}.consent.plan_hash`),
      approved_at: need(isString(c.approved_at), c.approved_at, `${where}.consent.approved_at`),
      by: need(isString(c.by), c.by, `${where}.consent.by`),
    };
  }
  const issuesRaw = need<unknown[]>(Array.isArray(r.issues), r.issues, `${where}.issues`);
  return {
    path: str('path'),
    root: need(isNumber(r.root), r.root, `${where}.root`),
    sha256: str('sha256'),
    bytes: need(isNumber(r.bytes), r.bytes, `${where}.bytes`),
    format: str('format'),
    route: str('route'),
    need: str('need'),
    label: str('label'),
    action: str('action'),
    decision: str('decision'),
    coverage_state: str('coverage_state'),
    units: numbers(r.units, ['total', 'eligible', 'cached', 'transcribed', 'pending', 'failed'] as const, `${where}.units`),
    requests: numbers(r.requests, ['to_send', 'sent', 'ok', 'failed'] as const, `${where}.requests`),
    placements: need(isNumber(r.placements), r.placements, `${where}.placements`),
    issues: issuesRaw.map((issue, i) => decodeIssue(issue, `${where}.issues[${i}]`)),
    outputs: need(isStringArray(r.outputs), r.outputs, `${where}.outputs`),
    plan_hash: need(isNullableString(r.plan_hash), r.plan_hash, `${where}.plan_hash`),
    consent,
    // Verbatim Core report (R5-N08): retained as-is, including a `corrupt` decision and Core issue codes.
    triage: r.triage === undefined ? null : r.triage,
  };
}

/** Validate a run report; mdflow codes checked against SPEC 7.5 only in mdflow-owned fields. */
export function decodeReport(stdout: string): Decoded<RunReport> {
  try {
    let parsed: unknown;
    try {
      parsed = JSON.parse(stdout);
    } catch {
      fail(stdout.trim().length === 0 ? 'report missing' : 'report is not valid JSON');
    }
    const r = need<Raw>(isRecord(parsed), parsed, 'report must be an object');
    if (r.v !== 1) fail('report.v must be 1');
    const filesRaw = need<unknown[]>(Array.isArray(r.files), r.files, 'report.files');
    const skippedRaw = need<unknown[]>(Array.isArray(r.skipped), r.skipped, 'report.skipped');
    const skipped = skippedRaw.map((item, i) => {
      const s = need<Raw>(isRecord(item), item, `skipped[${i}]`);
      const code = need<string>(isString(s.code), s.code, `skipped[${i}].code`);
      if (!isKnownEngineCode(code)) fail(`skipped[${i}].code is not a SPEC 7.5 code`);
      return { path: need<string>(isString(s.path), s.path, `skipped[${i}].path`), code };
    });
    const report: RunReport = {
      v: 1,
      mdflow: need(isString(r.mdflow), r.mdflow, 'report.mdflow'),
      started: need(isString(r.started), r.started, 'report.started'),
      finished: need(isString(r.finished), r.finished, 'report.finished'),
      options: need(isRecord(r.options), r.options, 'report.options'),
      files: filesRaw.map(decodeFile),
      skipped,
      exit: need(isNumber(r.exit), r.exit, 'report.exit'),
    };
    return { ok: true, value: report };
  } catch (error) {
    return { ok: false, diagnostic: 'shell.PROTOCOL', reason: error instanceof SchemaError ? error.message : 'report decoding failed' };
  }
}
