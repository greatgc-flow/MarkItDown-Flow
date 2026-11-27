import { scrubEngineEnv, type Env } from '../pure/env';
import { ENGINE_ARGV_PREFIX, type JobSnapshot } from './launcher';
import { withInputList } from './node-apis';
import type { Spawner } from './types';

export type Mode = 'run' | 'preview' | 'extract-text';
export interface FileRow {
  kind: 'file';
  outcome: string;
  reason: string;
  source: { path: string; relativePath: string; originalRelative?: string; format?: string; sha256: string; originalSha256?: string; member?: string | null };
  inspection?: { area_percent?: Record<string, number> | null; inspected_pages?: number; total_pages?: number; measured_pages?: number; pages?: { number: number; role: string }[] };
  action?: string;
  output?: string;
}
export interface StrictResult {
  rows: FileRow[];
  status: 'complete' | 'failed' | 'interrupted';
  skipped: number;
}
export interface SourceAction {
  mode: Mode;
  sha?: string;
  member?: string;
}

export class StrictStream {
  readonly rows: FileRow[] = [];
  private counts: Record<string, number> = {};
  private id: string | null = null;
  private exit: number | null = null;
  skipped = 0;
  constructor(private readonly mode: Mode, private readonly onFile?: (r: FileRow) => void) {}

  accept(line: string): void {
    const row = JSON.parse(line);
    if (!row || typeof row !== 'object' || this.exit !== null) throw Error('Unexpected record');
    if (this.id === null) {
      if (row.kind !== 'header' || row.schema !== 2 || row.policy !== 'strict-v1' || row.mode !== this.mode ||
        typeof row.run_id !== 'string' || !row.run_id) throw Error('Invalid strict header');
      this.id = row.run_id;
      return;
    }
    if (row.kind === 'skip') { this.skipped++; return; }
    if (row.kind === 'container') return;
    if (row.kind === 'file') {
      if (!['complete', 'eligible', 'excluded', 'failed'].includes(row.outcome) || typeof row.reason !== 'string' ||
        typeof row.source?.path !== 'string' || typeof row.source?.relativePath !== 'string' || typeof row.source?.sha256 !== 'string') throw Error('Invalid file record');
      this.counts[row.outcome] = (this.counts[row.outcome] ?? 0) + 1;
      this.rows.push(row);
      this.onFile?.(row);
      return;
    }
    if (row.kind !== 'footer' || row.run_id !== this.id || row.mode !== this.mode || row.schema !== 2 || row.policy !== 'strict-v1' ||
      row.files !== this.rows.length || ![0, 2].includes(row.exit) || !row.counts || typeof row.counts !== 'object' ||
      Object.keys({...this.counts, ...row.counts}).some(k => (this.counts[k] ?? 0) !== row.counts[k])) throw Error('Invalid strict footer');
    this.exit = row.exit;
  }

  finish(code: number | null): StrictResult {
    return {rows: this.rows, skipped: this.skipped, status: code === null || code !== this.exit ? 'interrupted' : code === 0 ? 'complete' : 'failed'};
  }
}

/** Decode incrementally. A truncated UTF-8 sequence or JSON line cannot produce a successful run. */
export function launchLines(spawner: Spawner, snapshot: JobSnapshot, host: Env, args: string[],
  signal: AbortSignal, accept: (line: string) => void): Promise<number | null> {
  if (signal.aborted) return Promise.resolve(null);
  return new Promise((resolve, reject) => {
    const child = spawner.spawn({command: snapshot.enginePython, args: [...ENGINE_ARGV_PREFIX, ...args],
      cwd: snapshot.cwd, env: scrubEngineEnv(host, 'none'), shell: false, windowsHide: true});
    const decoder = new TextDecoder('utf-8', {fatal: true});
    let remainder = '';
    let bad = false;
    const stop = () => child.terminate();
    signal.addEventListener('abort', stop, {once: true});
    child.onStdout(chunk => {
      if (bad || signal.aborted) return;
      try {
        const lines = (remainder + decoder.decode(chunk, {stream:true})).split('\n');
        remainder = lines.pop() ?? '';
        if (remainder.length > 1024 * 1024) throw Error('Oversized record');
        for (const line of lines) {
          if (line.length > 1024 * 1024) throw Error('Oversized record');
          accept(line);
        }
      } catch { bad = true; stop(); }
    });
    child.onStderr(() => {});
    child.onError(e => { signal.removeEventListener('abort', stop); reject(e); });
    child.onExit(status => {
      signal.removeEventListener('abort', stop);
      try { remainder += decoder.decode(); } catch { bad = true; }
      resolve(bad || signal.aborted || remainder ? null : status.code);
    });
  });
}

export async function runStrict(spawner: Spawner, snapshot: JobSnapshot, host: Env, action: SourceAction,
  signal: AbortSignal, onFile?: (row: FileRow) => void): Promise<StrictResult> {
  const stream = new StrictStream(action.mode, onFile);
  const args = [action.mode === 'preview' ? 'run' : action.mode, '--policy', 'strict-v1', '--exclude', snapshot.outDir,
    '--exclude', snapshot.cacheDir];
  if (action.mode === 'preview') args.push('--dry-run');
  else args.push('-o', snapshot.outDir);
  if (action.sha) args.push('--expected-sha256', action.sha);
  if (action.member) args.push('--member', action.member);
  const start = (inputs: readonly string[]) =>
    launchLines(spawner, snapshot, host, [...args, ...inputs], signal, line => stream.accept(line));
  const code = snapshot.inputs.reduce((n,p) => n+p.length+3, 0) <= 12000
    ? await start(['--', ...snapshot.inputs]) : await withInputList(snapshot.inputs, start);
  return stream.finish(code);
}
