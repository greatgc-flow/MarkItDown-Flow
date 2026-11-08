/**
 * The single conversion coordinator every entry point shares (20_SHELL.md
 * REQ-SHL-08/09/14/15/16). One owned conversion per plugin instance; output
 * validation, diagnostics, consent, replay and cancellation live here.
 */
import type { Env } from '../pure/env';
import { NotImplementedError } from '../pure/errors';
import type { HistoryEntry } from '../pure/history';
import type { UiLocale } from '../pure/i18n';
import type { SettingsV2 } from '../pure/settings';
import type { SpoolFs } from '../pure/spool';
import type { EngineResult } from '../process/engine-process';
import type { JobSnapshot } from '../process/launcher';
import type { RotatingLog } from '../process/log';
import type { Clock, FileSystemOps, HostPlatform, Spawner } from '../process/types';
import type { VersionGate } from '../process/version-gate';
import type { ConsentDecision, ConsentViewModel } from './consent-modal';
import type { Plan, RunReport } from '../pure/protocol';

export type EntryPoint = 'command' | 'ribbon' | 'context-menu' | 'drop';

export interface Selection {
  kind: 'files' | 'folder';
  /** Absolute paths exactly as selected, in selection order. */
  paths: readonly string[];
}

/** The request every entry point produces; identical selections give identical requests. */
export interface CoordinatorRequest {
  inputs: string[];
  cwd: string;
  outDir: string;
  cacheDir: string;
  recursive: boolean;
}

export type SubmitResult =
  | { accepted: true; snapshot: JobSnapshot }
  | { accepted: false; diagnostic: 'shell.BUSY' | 'shell.DESTINATION' | 'shell.RUNTIME' | 'shell.SETTINGS' };

export interface CoordinatorDeps {
  spawner: Spawner;
  fs: FileSystemOps;
  spoolFs: SpoolFs;
  clock: Clock;
  hostEnv: Env;
  platform: HostPlatform;
  vaultRoot: string;
  pluginDir: string;
  locale: UiLocale;
  settings: () => SettingsV2;
  /** Result of the version gate taken before jobs; null blocks with `shell.RUNTIME`. */
  gate: () => VersionGate | null;
  /** Presents the single consent modal; tests inject a decision. */
  consent: (view: ConsentViewModel) => Promise<ConsentDecision>;
  notify: (key: string, params?: Record<string, string>) => void;
  /** Persist a history entry (settings owner). */
  recordHistory: (entry: HistoryEntry) => Promise<void>;
  log: RotatingLog | null;
  /** Random 16-hex nonce source for spool names. */
  nonce: () => string;
}

export interface JobReport {
  snapshot: JobSnapshot;
  plan: EngineResult<Plan[]> | null;
  run: EngineResult<RunReport> | null;
  decision: ConsentDecision | null;
  /** True when a pending/denied engine state was displayed for fresh review (never auto-approved). */
  pendingShown: boolean;
}

export class ShellCoordinator {
  constructor(_deps: CoordinatorDeps) {}

  /** Pure projection used by every entry point before any work. */
  buildRequest(_selection: Selection): CoordinatorRequest {
    throw new NotImplementedError('ShellCoordinator.buildRequest');
  }

  /** Busy check, destination validation, snapshot; then starts the job (not awaited). */
  async submit(_selection: Selection, _entry: EntryPoint): Promise<SubmitResult> {
    throw new NotImplementedError('ShellCoordinator.submit');
  }

  /** Resolves when the current job (if any) has finished, with its report. */
  get current(): Promise<JobReport> | null {
    throw new NotImplementedError('ShellCoordinator.current');
  }

  get active(): boolean {
    throw new NotImplementedError('ShellCoordinator.active');
  }

  /** Cancel: dismiss consent, prevent launches, cooperative-then-forced stop of the owned engine. */
  cancel(): void {
    throw new NotImplementedError('ShellCoordinator.cancel');
  }

  /** Unload: same as cancel plus disposal of listeners. */
  dispose(): void {
    throw new NotImplementedError('ShellCoordinator.dispose');
  }

  /** `convert-url` compatibility notice: zero engine or network work. */
  legacyUrlNotice(): void {
    throw new NotImplementedError('ShellCoordinator.legacyUrlNotice');
  }
}
