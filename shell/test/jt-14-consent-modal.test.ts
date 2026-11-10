/**
 * JT-14 / REQ-SHL-14: one modal for the complete selection; per-file fields
 * equal the engine Plans (FX-71); no invented run/token/interruption fields;
 * Keep pending is the default and Escape/close grants nothing; HTML stays
 * literal; the fixed billing disclosure is present in both languages.
 */
import { req } from './req';
import { asFake, createApp, mockState } from './__mocks__/obsidian';
import { dictionary } from '../src/pure/i18n';
import { MAX_LINE_BYTES } from '../src/pure/framing';
import { parsePlanOutput, type Plan } from '../src/pure/protocol';
import { buildConsentView, ConsentModal, type ConsentViewModel } from '../src/ui/consent-modal';
import { fx71Text } from './fixtures/fx71';
import { HEX64_A, plan as syntheticPlan } from './fixtures/protocol';

const R = req('REQ-SHL-14');
const DEST = '/home/alice/Vault/markitdown-output';

function plans(name: string): Plan[] {
  const decoded = parsePlanOutput(fx71Text(name));
  if (!decoded.ok) throw new Error(decoded.reason);
  return decoded.value;
}

function text(modal: ConsentModal): string {
  return asFake(modal.contentEl).textContent + asFake(modal.titleEl).textContent;
}

beforeEach(() => mockState.reset());

it(R('JT-14 per-file fields are copied from the engine Plans: hash, provider, model, destination, units, dpi, cache status, budget, cost, threshold, sensitive hits'), () => {
  const view = buildConsentView(plans('plan-mixed.stdout.json'), DEST);
  expect(view.destinationDir).toBe(DEST);
  expect(view.files.map((f) => f.path)).toEqual(['b c.docx', 'memo.txt', 'sub/a.pdf', '보고서/3분기 결산.pdf']);
  const docx = view.files[0];
  expect(docx).toEqual({
    path: 'b c.docx',
    label: 'M',
    sha256: '4e4cbb1dc698162a53fd655903e4199a6b0aeb81d2896105b6f92e8ff6ffbabc',
    planHash: 'e81c750520319e685f3483f10caaca33856e78dd8afb348a9e447a4b2f89695f',
    provider: 'openai-compatible',
    model: 'gpt-4.1-mini',
    destination: 'https://api.openai.com/v1/chat/completions',
    proxy: null,
    selectedUnits: 2,
    dpi: 200,
    pendingLowPriority: 0,
    cached: 0,
    requestsToSend: 2,
    approvedBudget: 6,
    estMaxCost: 'unknown',
    thresholdExceeded: false,
    sensitiveHits: [],
    unknownCost: true,
    needsConsent: true,
  });
  const korean = view.files[3];
  expect(korean.selectedUnits).toBe(3);
  expect(korean.requestsToSend).toBe(1);
  expect(korean.approvedBudget).toBe(3);
  expect(view.requiresAcknowledgement).toBe(true);
  expect(view.billingNoticeKey).toBe('shell.consent.billing');
  // memo.txt has nothing to send: listed for completeness, informational only (SPEC 8.4 / approve.py requests_to_send > 0).
  expect(view.files[1].path).toBe('memo.txt');
  expect(view.files[1].needsConsent).toBe(false);
  const warm = buildConsentView(plans('consent-4-plan-warm.stdout.json'), DEST);
  expect(warm.files.map((f) => [f.path, f.needsConsent])).toEqual([['b c.docx', false], ['memo.txt', false], ['sub/a.pdf', true], ['보고서/3분기 결산.pdf', true]]);
  const modal = new ConsentModal(createApp(), warm, 'en');
  modal.open();
  const sections = asFake(modal.contentEl).findAll((el) => el.hasClass('mdflow-consent-file'));
  expect(sections).toHaveLength(4);
  expect(sections[0].textContent).toContain(dictionary('en')['shell.consent.informational']);
  expect(sections[2].textContent).not.toContain(dictionary('en')['shell.consent.informational']);
  modal.close();
});

it(R('JT-14 known cost is shown in USD from approved.est_max_cost, cached units are informational and never an authorization field'), () => {
  const known = syntheticPlan('reports/q3.pdf', HEX64_A, 2);
  const view = buildConsentView([known], DEST);
  expect(view.files[0].estMaxCost).toBe(known.approved.est_max_cost);
  expect(view.files[0].unknownCost).toBe(false);
  expect(view.requiresAcknowledgement).toBe(false);
  // Warm plan: cache filled, same approved hash; display differs only in informational status.
  const cold = plans('consent-1-plan.stdout.json');
  const warm = plans('consent-4-plan-warm.stdout.json');
  const coldView = buildConsentView(cold, DEST);
  const warmView = buildConsentView(warm, DEST);
  expect(warmView.files.map((f) => f.planHash)).toEqual(coldView.files.map((f) => f.planHash));
  expect(warmView.files[0].cached).toBe(2);
  expect(coldView.files[0].cached).toBe(0);
  expect(warmView.files[0].requestsToSend).toBe(0);
  // `needsConsent` follows requests_to_send, so it is informational cache state too (SPEC 8.4), never part of the hash.
  const strip = (f: ConsentViewModel['files'][number]): Omit<typeof f, 'cached' | 'requestsToSend' | 'needsConsent'> => {
    const { cached: _c, requestsToSend: _r, needsConsent: _n, ...rest } = f;
    void _c;
    void _r;
    void _n;
    return rest;
  };
  expect(warmView.files.map(strip)).toEqual(coldView.files.map(strip));
});

it(R('JT-14 the view carries no run-level hash, token estimate, run totals or interruption counters'), () => {
  const view = buildConsentView(plans('plan-mixed.stdout.json'), DEST);
  const keys = new Set<string>();
  const walk = (v: unknown): void => {
    if (Array.isArray(v)) v.forEach(walk);
    else if (v && typeof v === 'object') for (const [k, inner] of Object.entries(v)) {
      keys.add(k);
      walk(inner);
    }
  };
  walk(view);
  // `selectedUnits` is a per-file count from the Plan; a raw `units` list is the invented field.
  for (const key of keys) expect(key).not.toMatch(/token|run_hash|runHash|interrupt|total_cost|totalCost|runTotal|^units$/i);
  expect(JSON.stringify(view)).not.toContain('"units":[');
});

it(R('JT-14 fifty files produce one modal listing every file; the 200-unit Plan comes from plan stdout while its event stayed bounded'), () => {
  const fifty = Array.from({ length: 50 }, (_, i) => syntheticPlan(`batch/file-${i}.pdf`, i.toString(16).padStart(64, '0'), 3));
  const view = buildConsentView(fifty, DEST);
  const modal = new ConsentModal(createApp(), view, 'en');
  modal.open();
  expect(mockState.openModals).toHaveLength(1);
  const rendered = text(modal);
  for (const p of fifty) {
    expect(rendered).toContain(p.approved.file.path);
    expect(rendered).toContain(p.plan_hash);
  }
  modal.close();
  const large = plans('plan-large.stdout.json');
  const largeView = buildConsentView(large, DEST);
  expect(largeView.files[0].selectedUnits).toBe(200);
  expect(Buffer.byteLength(fx71Text('plan-large.stdout.json'), 'utf8')).toBeGreaterThan(MAX_LINE_BYTES);
  const largeModal = new ConsentModal(createApp(), largeView, 'ko');
  largeModal.open();
  expect(text(largeModal)).toContain('긴 문서.pdf');
  expect(text(largeModal)).toContain('200');
  largeModal.close();
});

it(R('JT-14 Keep pending is the default: closing or Escape yields no authorization; approve returns exactly the displayed hashes'), async () => {
  const view = buildConsentView(plans('plan-mixed.stdout.json'), DEST);
  const closed = new ConsentModal(createApp(), view, 'en');
  closed.open();
  closed.close();
  await expect(closed.decision).resolves.toEqual({ approved: false });
  const kept = new ConsentModal(createApp(), view, 'en');
  kept.open();
  kept.keepPending();
  await expect(kept.decision).resolves.toEqual({ approved: false });
  expect(mockState.openModals).not.toContain(kept);
  const approved = new ConsentModal(createApp(), view, 'en');
  approved.open();
  approved.approve();
  await expect(approved.decision).resolves.toEqual({ approved: true, hashes: view.files.map((f) => f.planHash) });
  // A later close does not change the decision, and approve after close grants nothing new.
  approved.close();
  await expect(approved.decision).resolves.toEqual({ approved: true, hashes: view.files.map((f) => f.planHash) });
  const never = new ConsentModal(createApp(), view, 'en');
  never.open();
  never.close();
  never.approve();
  await expect(never.decision).resolves.toEqual({ approved: false });
});

it(R('JT-14 Plan text is rendered literally: markup in a file path never becomes elements; the disclosure exists in en and ko'), () => {
  const hostile = syntheticPlan('<b>bold</b> & "q" <img src=x onerror=alert(1)>.pdf', HEX64_A, 1);
  const view = buildConsentView([hostile], DEST);
  const modal = new ConsentModal(createApp(), view, 'en');
  modal.open();
  const content = asFake(modal.contentEl);
  expect(content.textContent).toContain('<b>bold</b> & "q" <img src=x onerror=alert(1)>.pdf');
  expect(content.findAll((el) => ['b', 'img', 'script'].includes(el.tagName.toLowerCase()))).toEqual([]);
  // Fixed disclosure: interrupted/failed requests may already have been billed; retry can duplicate cost.
  for (const locale of ['en', 'ko'] as const) {
    const disclosure = dictionary(locale)[view.billingNoticeKey];
    expect(disclosure?.trim().length).toBeGreaterThan(0);
    expect(disclosure).not.toContain('{');
  }
  expect(content.textContent).toContain(dictionary('en')[view.billingNoticeKey]);
  modal.close();
});
