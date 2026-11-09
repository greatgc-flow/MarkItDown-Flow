/**
 * One consent modal for the complete original selection (20_SHELL.md
 * REQ-SHL-14; SPEC 7.1/8.4 by reference). Fields are rendered as literal text;
 * the default is Keep pending; Escape/close grants nothing.
 */
import { type App, Modal } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
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
  /** SPEC 8.4: consent is required only when the provider has egress and requests remain to send; otherwise informational. */
  needsConsent: boolean;
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
export function buildConsentView(plans: readonly Plan[], destinationDir: string): ConsentViewModel {
  const files: ConsentFileView[] = plans.map((plan) => {
    const { approved, status } = plan;
    const unknownCost = approved.est_max_cost === null || !approved.cost_known;
    return {
      path: approved.file.path,
      sha256: approved.file.sha256,
      planHash: plan.plan_hash,
      provider: approved.provider.name,
      model: approved.provider.model,
      destination: approved.provider.destination,
      selectedUnits: approved.units.filter((u) => u.status === 'eligible').length,
      dpi: approved.dpi,
      pendingLowPriority: status.units.skipped_low_priority,
      cached: status.units.cached,
      requestsToSend: status.requests_to_send,
      approvedBudget: approved.max_requests,
      estMaxCost: approved.est_max_cost ?? 'unknown',
      thresholdExceeded: approved.threshold_exceeded,
      sensitiveHits: [...approved.sensitive_hits],
      unknownCost,
      needsConsent: approved.provider.egress && status.requests_to_send > 0,
    };
  });
  return {
    destinationDir,
    files,
    billingNoticeKey: 'shell.consent.billing',
    requiresAcknowledgement: files.some((f) => f.needsConsent && (f.thresholdExceeded || f.sensitiveHits.length > 0 || f.unknownCost)),
  };
}

type Resolver = (decision: ConsentDecision) => void;

export class ConsentModal extends Modal {
  private resolveDecision!: Resolver;
  private readonly decisionPromise: Promise<ConsentDecision>;
  private settled = false;

  constructor(
    app: App,
    private readonly view: ConsentViewModel,
    private readonly locale: UiLocale,
  ) {
    super(app);
    this.decisionPromise = new Promise<ConsentDecision>((resolve) => {
      this.resolveDecision = resolve;
    });
  }

  /** Resolves once: approve -> displayed hashes; keep pending / close / Escape -> no authorization. */
  get decision(): Promise<ConsentDecision> {
    return this.decisionPromise;
  }

  private settle(decision: ConsentDecision): void {
    if (this.settled) return;
    this.settled = true;
    this.resolveDecision(decision);
  }

  /** "Approve this selection": acknowledges the displayed notices once for the displayed file scopes. */
  approve(): void {
    if (this.settled) return;
    this.settle({ approved: true, hashes: this.view.files.map((f) => f.planHash) });
    this.close();
  }

  /** Default action. */
  keepPending(): void {
    this.settle({ approved: false });
    this.close();
  }

  private t(key: string, params?: Record<string, string>): string {
    return formatMessage(this.locale, key, params);
  }

  override onOpen(): void {
    const { contentEl, titleEl } = this;
    titleEl.setText(this.t('shell.consent.title'));
    contentEl.empty();
    contentEl.addClass('mdflow-consent');
    contentEl.createEl('p', { text: this.t('shell.consent.destinationDir', { dir: this.view.destinationDir }) });
    contentEl.createEl('p', { cls: 'mdflow-consent-billing', text: this.t(this.view.billingNoticeKey) });
    if (this.view.requiresAcknowledgement) contentEl.createEl('p', { cls: 'mdflow-consent-ack', text: this.t('shell.consent.acknowledge') });
    const list = contentEl.createDiv({ cls: 'mdflow-consent-files' });
    for (const file of this.view.files) {
      const section = list.createDiv({ cls: 'mdflow-consent-file' });
      if (!file.needsConsent) section.createDiv({ cls: 'mdflow-consent-informational', text: this.t('shell.consent.informational') });
      const row = (label: string, value: string): void => {
        const line = section.createDiv({ cls: 'mdflow-consent-row' });
        line.createSpan({ cls: 'mdflow-consent-label', text: `${label}: ` });
        line.createSpan({ cls: 'mdflow-consent-value', text: value });
      };
      row(this.t('shell.consent.file'), file.path);
      row(this.t('shell.consent.sha256'), file.sha256);
      row(this.t('shell.consent.planHash'), file.planHash);
      row(this.t('shell.consent.provider'), `${file.provider} / ${file.model}`);
      row(this.t('shell.consent.destination'), file.destination ?? '-');
      row(this.t('shell.consent.selectedUnits'), String(file.selectedUnits));
      row(this.t('shell.consent.dpi'), String(file.dpi));
      row(this.t('shell.consent.pendingLowPriority'), String(file.pendingLowPriority));
      section.createDiv({ cls: 'mdflow-consent-row', text: this.t('shell.consent.cacheStatus', { cached: String(file.cached), toSend: String(file.requestsToSend) }) });
      row(this.t('shell.consent.budget'), String(file.approvedBudget));
      row(this.t('shell.consent.estMaxCost'), file.unknownCost ? this.t('shell.consent.unknownCost') : file.estMaxCost);
      if (file.thresholdExceeded) section.createDiv({ cls: 'mdflow-consent-warning', text: this.t('shell.consent.thresholdExceeded') });
      if (file.sensitiveHits.length > 0) {
        section.createDiv({ cls: 'mdflow-consent-warning', text: this.t('shell.consent.sensitiveHits', { hits: file.sensitiveHits.join(', ') }) });
      }
    }
    const buttons = contentEl.createDiv({ cls: 'mdflow-consent-buttons' });
    const keep = buttons.createEl('button', { text: this.t('shell.consent.keepPending'), cls: 'mod-cta' });
    keep.addEventListener('click', () => this.keepPending());
    const approve = buttons.createEl('button', { text: this.t('shell.consent.approve') });
    approve.addEventListener('click', () => this.approve());
  }

  override onClose(): void {
    // Escape/close without a choice: no authorization.
    this.settle({ approved: false });
    this.contentEl.empty();
  }
}
