/**
 * Decoding of `plan` stdout and the run report (20_SHELL.md REQ-SHL-13;
 * SPEC 7.1/7.4/7.5 incorporated by reference, R5-N08 separate Core vocabulary).
 */
import { NotImplementedError } from './errors';

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

/** Parse the concatenated pretty-printed Plans that `mdflow plan` writes to stdout. */
export function parsePlanOutput(_stdout: string): Decoded<Plan[]> {
  throw new NotImplementedError('parsePlanOutput');
}

/** Validate a run report; mdflow codes checked against SPEC 7.5 only in mdflow-owned fields. */
export function decodeReport(_stdout: string): Decoded<RunReport> {
  throw new NotImplementedError('decodeReport');
}

/** Hashes eligible for `--yes` from fully decoded Plans only (never from events). */
export function approvableHashes(_plans: readonly Plan[]): string[] {
  throw new NotImplementedError('approvableHashes');
}
