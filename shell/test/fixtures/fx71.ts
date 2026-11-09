/**
 * FX-71 protocol streams recorded from the real engine by the orchestrator
 * (`tools/record_protocol.py`; manifest at fixtures/fx71/manifest.json).
 * This loader reads bytes only; it never alters or hand-writes a stream.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';

export const FX71_DIR = path.join(__dirname, 'fx71');

export interface Fx71Entry {
  kind: 'recorded' | 'derived';
  stream?: 'stdout' | 'stderr' | 'input-file';
  argv?: string[] | null;
  exit?: number | null;
  env_names?: string[];
  bytes: number;
  sha256: string;
  eol?: 'crlf' | 'lf';
  derived_from?: string;
  transform?: string;
  note?: string;
}

export interface Fx71Manifest {
  v: 1;
  fixture: 'FX-71';
  engine: {
    mdflow: string;
    'markitdown-gc': string;
    pypdfium2: string;
    pillow: string;
    python: string;
    platform: string;
    protocol: number;
    triage_schema: number;
  };
  files: Record<string, Fx71Entry>;
}

let manifest: Fx71Manifest | null = null;

export function fx71Manifest(): Fx71Manifest {
  manifest ??= JSON.parse(fs.readFileSync(path.join(FX71_DIR, 'manifest.json'), 'utf8')) as Fx71Manifest;
  return manifest;
}

export function fx71Bytes(name: string): Uint8Array {
  return new Uint8Array(fs.readFileSync(path.join(FX71_DIR, name)));
}

export function fx71Text(name: string): string {
  return fs.readFileSync(path.join(FX71_DIR, name), 'utf8');
}

export function fx71Json<T = unknown>(name: string): T {
  return JSON.parse(fx71Text(name)) as T;
}

/** Recorded argv of a stream (after `python -I -m mdflow`; the recorder runs the isolated interpreter, T-GEN-92/97). */
export function fx71Args(name: string): string[] {
  const entry = fx71Manifest().files[name];
  if (!entry?.argv) throw new Error(`FX-71 ${name}: no recorded argv`);
  const argv = entry.argv;
  if (argv[0] !== 'python' || argv[1] !== '-I' || argv[2] !== '-m' || argv[3] !== 'mdflow') throw new Error(`FX-71 ${name}: unexpected argv prefix`);
  return argv.slice(4);
}

export function fx71Exit(name: string): number {
  const exit = fx71Manifest().files[name]?.exit;
  if (typeof exit !== 'number') throw new Error(`FX-71 ${name}: no recorded exit`);
  return exit;
}

/** Chunks of a `*.split.json` derived stream (base64), concatenating to the parent bytes. */
export function fx71Chunks(name: string): Uint8Array[] {
  const split = fx71Json<{ chunks_b64: string[] }>(name);
  return split.chunks_b64.map((b64) => new Uint8Array(Buffer.from(b64, 'base64')));
}

export function concat(chunks: readonly Uint8Array[]): Uint8Array {
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const out = new Uint8Array(total);
  let pos = 0;
  for (const c of chunks) {
    out.set(c, pos);
    pos += c.length;
  }
  return out;
}

/** Lines of a JSONL stream (both line endings), parsed. */
export function fx71Lines(name: string): unknown[] {
  return fx71Text(name)
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line) as unknown);
}

/** Top-level JSON values of a pretty-printed concatenated `plan` stdout. */
export function fx71PlanObjects(name: string): unknown[] {
  const text = fx71Text(name);
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
    if (ch === '"') inString = true;
    else if (ch === '{') {
      if (depth === 0) start = i;
      depth++;
    } else if (ch === '}') {
      depth--;
      if (depth === 0) values.push(JSON.parse(text.slice(start, i + 1)));
    }
  }
  return values;
}

/** Hashes listed in a recorded `--yes-file` (blank lines and `#` comments ignored, SPEC 10.2). */
export function fx71YesFile(name: string): string[] {
  return fx71Text(name)
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !l.startsWith('#'));
}

/** Recorded logical input layout used by the recorder (tools/record_protocol.py build_inputs). */
export const FX71_ROOTS = {
  inputs: ['sub/a.pdf', '보고서/3분기 결산.pdf', 'b c.docx', 'memo.txt', '.DS_Store'],
  bad: ['broken.pdf', 'empty.pdf', 'garbled.docx'],
  large: ['긴 문서.pdf'],
} as const;
