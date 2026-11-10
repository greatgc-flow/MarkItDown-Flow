/**
 * One consent modal for the complete original selection (20_SHELL.md
 * REQ-SHL-14; SPEC 7.1/8.4 by reference). Fields are rendered as literal text;
 * the default is Keep pending (no authorization; the no-OCR part still runs, R37);
 * Escape/close grants nothing and runs nothing.
 *
 * Layout (R32): a compact per-file summary table (file, class, units,
 * destination, est. max cost, status) followed by collapsible full Plan details
 * per file, then Keep pending (primary) / Approve this selection (secondary).
 * There is no run-level cost total or hash: every number is a per-file bound
 * supplied by the engine.
 */
import { type App, Modal } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import type { Plan } from '../pure/protocol';

/** Per-file display model; every value is copied from the engine Plan. */
export interface ConsentFileView {
  path: string;
  /** SPEC 3.2 classification label (`T`/`S`/`M`/`U`/`C`/`L`/`P`/`X`). */
  label: string;
  sha256: string;
  planHash: string;
  provider: string;
  model: string;
  destination: string | null;
  /** `approved.provider.proxy` (`MDFLOW_PROXY`; hashed into the Plan): the hop requests pass through, or null. */
  proxy: string | null;
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
  /** Files in the selection. */
  fileCount: number;
  /** Files whose Plan needs approval (`needsConsent`). */
  consentCount: number;
  /** Fixed REQ-SHL-14 disclosure: interrupted/failed requests may be billed; retry can duplicate cost. */
  billingNoticeKey: 'shell.consent.billing';
  /** True when any file has threshold/sensitive/unknown-cost notices to acknowledge. */
  requiresAcknowledgement: boolean;
}

/**
 * `approved: false` grants nothing. `keepPending: true` (the explicit default button, owner decision R37) still asks
 * for the original invocation to run without any authorization, so every no-OCR part is converted now and OCR units
 * stay pending (SPEC REQ-APR-03: no egress); a dismissal (Escape/close, no flag) launches nothing.
 */
export type ConsentDecision = { approved: false; keepPending?: true } | { approved: true; hashes: string[] };

/** SPEC 3.2 labels with a legend string (`shell.label.<L>`); anything else is shown as its literal letter(s). */
const KNOWN_LABELS: ReadonlySet<string> = new Set(['T', 'S', 'M', 'U', 'C', 'L', 'P', 'X']);

/** Legend key for a classification label, or null for an unknown label. */
export function labelLegendKey(label: string): string | null {
  return KNOWN_LABELS.has(label) ? `shell.label.${label}` : null;
}

/** Pure projection of decoded Plans into the display model. */
export function buildConsentView(plans: readonly Plan[], destinationDir: string): ConsentViewModel {
  const files: ConsentFileView[] = plans.map((plan) => {
    const { approved, status } = plan;
    const unknownCost = approved.est_max_cost === null || !approved.cost_known;
    return {
      path: approved.file.path,
      label: approved.classification.label,
      sha256: approved.file.sha256,
      planHash: plan.plan_hash,
      provider: approved.provider.name,
      model: approved.provider.model,
      destination: approved.provider.destination,
      proxy: approved.provider.proxy,
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
    fileCount: files.length,
    consentCount: files.filter((f) => f.needsConsent).length,
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

  /** Resolves once: approve -> displayed hashes; keep pending -> no authorization, no-OCR run (R37); close / Escape -> no authorization, no run. */
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

  /** Default action: convert everything that needs no OCR now and leave the OCR units pending (R37). */
  keepPending(): void {
    this.settle({ approved: false, keepPending: true });
    this.close();
  }

  private t(key: string, params?: Record<string, string>): string {
    return formatMessage(this.locale, key, params);
  }

  private costText(file: ConsentFileView): string {
    return file.unknownCost ? this.t('shell.consent.unknownCost') : file.estMaxCost;
  }

  /** Destination plus the proxy every request passes through, when one is configured (P3). */
  private destinationText(file: ConsentFileView): string {
    const destination = file.destination ?? '-';
    return file.proxy ? `${destination} (${this.t('shell.consent.proxy')}: ${file.proxy})` : destination;
  }

  private renderSummary(parent: HTMLElement): void {
    const table = parent.createEl('table', { cls: 'mdflow-table mdflow-consent-summary' });
    const head = table.createEl('thead').createEl('tr');
    for (const column of ['file', 'label', 'units', 'destination', 'cost', 'status']) {
      head.createEl('th', { text: this.t(`shell.consent.col.${column}`), attr: { scope: 'col' } });
    }
    const body = table.createEl('tbody');
    for (const file of this.view.files) {
      const row = body.createEl('tr', { cls: file.needsConsent ? 'mdflow-consent-needed' : 'mdflow-consent-info' });
      row.createEl('td', { cls: 'mdflow-cell-path', text: file.path });
      const legend = labelLegendKey(file.label);
      const labelCell = row.createEl('td', { cls: 'mdflow-cell-label', text: file.label });
      if (legend) labelCell.setAttr('title', this.t(legend));
      row.createEl('td', { cls: 'mdflow-cell-number', text: String(file.selectedUnits) });
      row.createEl('td', { cls: 'mdflow-cell-path', text: this.destinationText(file) });
      row.createEl('td', { cls: 'mdflow-cell-number', text: this.costText(file) });
      row.createEl('td', {
        cls: `mdflow-badge ${file.needsConsent ? 'mdflow-badge-attention' : 'mdflow-badge-muted'}`,
        text: this.t(file.needsConsent ? 'shell.consent.status.needsConsent' : 'shell.consent.status.informational'),
      });
    }
  }

  private renderLegend(parent: HTMLElement): void {
    const keys = [...new Set(this.view.files.map((f) => labelLegendKey(f.label)))].filter((k): k is string => k !== null);
    if (keys.length === 0) return;
    const legend = parent.createDiv({ cls: 'mdflow-legend' });
    legend.createSpan({ cls: 'mdflow-legend-title', text: `${this.t('shell.consent.legend')}: ` });
    legend.createSpan({ text: keys.map((k) => this.t(k)).join(' · ') });
  }

  private renderDetails(parent: HTMLElement): void {
    const list = parent.createDiv({ cls: 'mdflow-consent-files' });
    for (const file of this.view.files) {
      const section = list.createEl('details', { cls: 'mdflow-consent-file' });
      const summary = section.createEl('summary');
      summary.createSpan({ cls: 'mdflow-cell-label', text: file.label });
      summary.createSpan({ text: ` ${file.path}` });
      summary.createSpan({ cls: 'mdflow-consent-details-hint', text: ` – ${this.t('shell.consent.details')}` });
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
      if (file.proxy) row(this.t('shell.consent.proxy'), file.proxy);
      row(this.t('shell.consent.selectedUnits'), String(file.selectedUnits));
      row(this.t('shell.consent.dpi'), String(file.dpi));
      row(this.t('shell.consent.pendingLowPriority'), String(file.pendingLowPriority));
      section.createDiv({ cls: 'mdflow-consent-row', text: this.t('shell.consent.cacheStatus', { cached: String(file.cached), toSend: String(file.requestsToSend) }) });
      row(this.t('shell.consent.budget'), String(file.approvedBudget));
      row(this.t('shell.consent.estMaxCost'), this.costText(file));
      if (file.thresholdExceeded) section.createDiv({ cls: 'mdflow-consent-warning', text: this.t('shell.consent.thresholdExceeded') });
      if (file.sensitiveHits.length > 0) {
        section.createDiv({ cls: 'mdflow-consent-warning', text: this.t('shell.consent.sensitiveHits', { hits: file.sensitiveHits.join(', ') }) });
      }
    }
  }

  override onOpen(): void {
    const { contentEl, titleEl } = this;
    titleEl.setText(this.t('shell.consent.title'));
    contentEl.empty();
    contentEl.addClass('mdflow-consent');
    contentEl.createEl('p', {
      cls: 'mdflow-consent-scope',
      text: this.t('shell.consent.scope', { consent: String(this.view.consentCount), count: String(this.view.fileCount) }),
    });
    contentEl.createEl('p', { cls: 'mdflow-muted', text: this.t('shell.consent.destinationDir', { dir: this.view.destinationDir }) });
    this.renderSummary(contentEl);
    this.renderLegend(contentEl);
    contentEl.createEl('p', { cls: 'mdflow-consent-billing', text: this.t(this.view.billingNoticeKey) });
    if (this.view.requiresAcknowledgement) contentEl.createEl('p', { cls: 'mdflow-consent-ack', text: this.t('shell.consent.acknowledge') });
    this.renderDetails(contentEl);
    contentEl.createEl('p', { cls: 'mdflow-muted mdflow-consent-keep-hint', text: this.t('shell.consent.keepPendingHint') });
    const buttons = contentEl.createDiv({ cls: 'mdflow-buttons mdflow-consent-buttons' });
    const approve = buttons.createEl('button', { text: this.t('shell.consent.approve'), cls: 'mdflow-consent-approve', attr: { type: 'button' } });
    approve.addEventListener('click', () => this.approve());
    const keep = buttons.createEl('button', { text: this.t('shell.consent.keepPending'), cls: 'mod-cta mdflow-consent-keep', attr: { type: 'button' } });
    keep.addEventListener('click', () => this.keepPending());
    keep.focus();
  }

  override onClose(): void {
    // Escape/close without a choice: no authorization.
    this.settle({ approved: false });
    this.contentEl.empty();
  }
}
