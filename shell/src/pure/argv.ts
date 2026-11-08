/**
 * Pure argv construction for the engine module entry point
 * (20_SHELL.md REQ-SHL-04 oracle: no removed-setting flags; SPEC 10.2 options only).
 * Process spawning itself is step 9 (REQ-SHL-12).
 */
import type { SettingsV2 } from './settings';

export interface RunRequest {
  command: 'run' | 'plan';
  /** Ordered absolute input arguments, snapshotted once. */
  inputs: string[];
  outDir: string;
  cacheDir: string;
  /** Approved file plan hashes for `run` after consent. */
  yes?: string[];
  approvedBy?: string;
}

/** Arguments after the interpreter: `-m mdflow <command> ...`. */
export function engineArgv(settings: SettingsV2, request: RunRequest): string[] {
  const { provider, runOptions } = settings;
  const argv: string[] = ['-m', 'mdflow', request.command, ...request.inputs];
  if (request.command === 'run') argv.push('-o', request.outDir);
  argv.push('--cache', request.cacheDir);
  argv.push('--provider', provider.name);
  if (provider.name !== 'none') argv.push('--model', provider.model);
  argv.push('--dpi', String(runOptions.dpi));
  argv.push('--min-priority', runOptions.minPriority);
  argv.push('--max-units', String(runOptions.maxUnits));
  argv.push('--approve-threshold', String(runOptions.approveThreshold));
  for (const glob of runOptions.sensitive) argv.push('--sensitive', glob);
  argv.push('--progress', 'jsonl');
  for (const hash of request.yes ?? []) argv.push('--yes', hash);
  if (request.approvedBy) argv.push('--approved-by', request.approvedBy);
  return argv;
}
