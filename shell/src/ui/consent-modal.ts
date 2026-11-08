/**
 * One consent modal for the complete original selection (20_SHELL.md
 * REQ-SHL-14; SPEC 7.1/8.4 by reference). Fields are rendered as literal text;
 * the default is Keep pending; Escape/close grants nothing.
 */
import { type App, Modal } from 'obsidian';
import { NotImplementedError } from '../pure/errors';
import type { UiLocale } from '../pure/i18n';
import type { Plan } from '../pure/protocol';

/** Per-file display model; every value is copied from the engine Plan. */
export interface ConsentFileView {
  path: string;
  sha256: string;
  planHash: string;
  provider: string;
  model: string;
  destination: string | null;
  /** `approved.units` with status `eligible`. */
  selectedUnits: number;
  dpi: number;
  pendingLowPriority: number;
  /** Informational, not an authorization field. */
  cached: number;
  requestsToSend: number;
  /** `approved.max_requests`. */
  approvedBudget: number;
  /** `approved.est_max_cost` in USD or the literal `unknown`. */
  estMaxCost: string;
  thresholdExceeded: boolean;
  sensitiveHits: string[];
  unknownCost: boolean;
}

export interface ConsentViewModel {
  destinationDir: string;
  files: ConsentFileView[];
  /** Fixed REQ-SHL-14 disclosure: interrupted/failed requests may be billed; retry can duplicate cost. */
  billingNoticeKey: 'shell.consent.billing';
  /** True when any file has threshold/sensitive/unknown-cost notices to acknowledge. */
  requiresAcknowledgement: boolean;
}

export type ConsentDecision = { approved: false } | { approved: true; hashes: string[] };

/** Pure projection of decoded Plans into the display model. */
export function buildConsentView(_plans: readonly Plan[], _destinationDir: string): ConsentViewModel {
  throw new NotImplementedError('buildConsentView');
}

export class ConsentModal extends Modal {
  constructor(app: App, _view: ConsentViewModel, _locale: UiLocale) {
    super(app);
  }

  /** Resolves once: approve -> displayed hashes; keep pending / close / Escape -> no authorization. */
  get decision(): Promise<ConsentDecision> {
    throw new NotImplementedError('ConsentModal.decision');
  }

  /** "Approve this selection": acknowledges the displayed notices once for the displayed file scopes. */
  approve(): void {
    throw new NotImplementedError('ConsentModal.approve');
  }

  /** Default action. */
  keepPending(): void {
    throw new NotImplementedError('ConsentModal.keepPending');
  }

  override onOpen(): void {
    throw new NotImplementedError('ConsentModal.onOpen');
  }

  override onClose(): void {
    throw new NotImplementedError('ConsentModal.onClose');
  }
}
