/**
 * JT-SHL-19-01 / REQ-SHL-19: engine-code key parity between SPEC 7.5 active
 * Code-column cells, the shell message table, the 20_SHELL.md section 6
 * snapshot, and the en/ko dictionaries (excluding `engine.UNKNOWN`);
 * nonempty, interpolation-safe values; locale resolution; unknown-code fallback.
 */
import { req } from './req';
import { dictionary, ENGINE_UNKNOWN_KEY, engineCodeKeys, formatMessage, isEngineCode, messageForCode, resolveLocale } from '../src/pure/i18n';
import { DELETED_CODES, shellDocDiagnosticKeys, shellDocEngineCodes, specActiveCodes } from './fixtures/spec-docs';

const R = req('REQ-SHL-19');

const PLACEHOLDER = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g;

function engineSuffixes(locale: 'en' | 'ko'): Set<string> {
  return new Set(
    Object.keys(dictionary(locale))
      .filter((k) => k.startsWith('engine.') && k !== ENGINE_UNKNOWN_KEY)
      .map((k) => k.slice('engine.'.length)),
  );
}

function sorted(set: Iterable<string>): string[] {
  return [...set].sort();
}

it(R('JT-SHL-19-01 SPEC 7.5 active Code-column cells form a nonempty set without deleted codes'), () => {
  const spec = specActiveCodes();
  expect(spec.rows).toBeGreaterThan(0);
  expect(spec.codes.size).toBeGreaterThan(0);
  for (const code of spec.codes) expect(code).toMatch(/^[EW]_[A-Z0-9_]+$/);
  for (const deleted of DELETED_CODES) expect(spec.codes.has(deleted)).toBe(false);
  // E_PROVIDER_CONFIG legitimately appears in two SPEC rows (startup/runtime); the union is still one key.
  expect(spec.codes.has('E_PROVIDER_CONFIG')).toBe(true);
  expect(engineCodeKeys()).toContain('E_PROVIDER_CONFIG');
});

it(R('JT-SHL-19-01 shell message table engine rows equal the SPEC set with no duplicate rows'), () => {
  const spec = specActiveCodes();
  const table = engineCodeKeys();
  expect(new Set(table).size).toBe(table.length);
  expect(sorted(table)).toEqual(sorted(spec.codes));
  expect(table).not.toContain('UNKNOWN');
});

it(R('JT-SHL-19-01 the 20_SHELL.md section 6 snapshot equals the SPEC set and has no duplicate rows'), () => {
  const spec = specActiveCodes();
  const doc = shellDocEngineCodes();
  expect(doc.literals.length).toBe(doc.codes.size);
  expect(sorted(doc.codes)).toEqual(sorted(spec.codes));
  expect(sorted(doc.codes)).toEqual(sorted(engineCodeKeys()));
});

it(R('JT-SHL-19-01 en and ko engine-code suffixes both equal the SPEC set, excluding UNKNOWN'), () => {
  const spec = specActiveCodes();
  expect(sorted(engineSuffixes('en'))).toEqual(sorted(spec.codes));
  expect(sorted(engineSuffixes('ko'))).toEqual(sorted(spec.codes));
  // Array path: the key itself contains a dot.
  expect(dictionary('en')).toHaveProperty([ENGINE_UNKNOWN_KEY]);
  expect(dictionary('ko')).toHaveProperty([ENGINE_UNKNOWN_KEY]);
});

it(R('JT-SHL-19-01 en and ko have identical key sets including every shell diagnostic key of section 6'), () => {
  const en = Object.keys(dictionary('en'));
  const ko = Object.keys(dictionary('ko'));
  expect(sorted(en)).toEqual(sorted(ko));
  for (const key of shellDocDiagnosticKeys()) {
    expect(en).toContain(key);
  }
  expect(shellDocDiagnosticKeys()).toEqual([
    'shell.SETTINGS', 'shell.RUNTIME', 'shell.PROTOCOL', 'shell.DESTINATION', 'shell.BUSY', 'shell.CANCELLED', 'shell.LEGACY_URL', 'engine.UNKNOWN',
  ]);
});

it(R('JT-SHL-19-01 every value is nonempty and placeholders match between languages'), () => {
  const en = dictionary('en');
  const ko = dictionary('ko');
  for (const key of Object.keys(en)) {
    expect(en[key].trim().length).toBeGreaterThan(0);
    expect(ko[key].trim().length).toBeGreaterThan(0);
    const enParams = sorted([...en[key].matchAll(PLACEHOLDER)].map((m) => m[1]));
    const koParams = sorted([...ko[key].matchAll(PLACEHOLDER)].map((m) => m[1]));
    expect(koParams).toEqual(enParams);
    expect(en[key]).not.toMatch(/\{\s*\}|\{[^}]*$/);
    expect(ko[key]).not.toMatch(/\{\s*\}|\{[^}]*$/);
  }
  // Independently authored: no engine message is byte-identical across the two languages.
  const identical = Object.keys(en).filter((k) => k.startsWith('engine.') && en[k] === ko[k]);
  expect(identical).toEqual([]);
});

it(R('JT-SHL-19-01 interpolation inserts parameters literally exactly once and never leaves undefined'), () => {
  const hostile = 'E_{code}<img src=x onerror=alert(1)>$1 ${x} %s';
  const out = formatMessage('en', ENGINE_UNKNOWN_KEY, { code: hostile });
  expect(out).toContain(hostile);
  expect(out.split(hostile)).toHaveLength(2);
  expect(out).not.toContain('undefined');
  const ko = formatMessage('ko', ENGINE_UNKNOWN_KEY, { code: 'E_FUTURE' });
  expect(ko).toContain('E_FUTURE');
  expect(formatMessage('en', 'shell.BUSY')).toBe(dictionary('en')['shell.BUSY']);
  // Missing parameter: template placeholder is not replaced by the string "undefined".
  expect(formatMessage('en', ENGINE_UNKNOWN_KEY, {})).not.toContain('undefined');
});

it(R('JT-SHL-19-01 locale auto follows the host language (ko* -> ko, otherwise en) and explicit values override'), () => {
  expect(resolveLocale('auto', 'ko')).toBe('ko');
  expect(resolveLocale('auto', 'ko-KR')).toBe('ko');
  expect(resolveLocale('auto', 'KO_kr')).toBe('ko');
  expect(resolveLocale('auto', 'en-US')).toBe('en');
  expect(resolveLocale('auto', 'ja')).toBe('en');
  expect(resolveLocale('auto', 'kok')).toBe('en');
  expect(resolveLocale('auto', undefined)).toBe('en');
  expect(resolveLocale('auto', '')).toBe('en');
  expect(resolveLocale('ko', 'en-US')).toBe('ko');
  expect(resolveLocale('en', 'ko-KR')).toBe('en');
});

it(R('JT-SHL-19-01 known codes select engine.<CODE>; unknown codes select engine.UNKNOWN with a redacted literal and never the raw message'), () => {
  const spec = specActiveCodes();
  for (const code of spec.codes) {
    expect(isEngineCode(code)).toBe(true);
    expect(messageForCode(code, 'raw engine text')).toEqual({ key: `engine.${code}`, params: {} });
  }
  for (const outside of ['suspect_text_layer', 'corrupt', 'E_BOGUS', ...DELETED_CODES, '', 'UNKNOWN']) {
    expect(isEngineCode(outside)).toBe(false);
    const ref = messageForCode(outside, 'raw engine text /home/alice sk-SECRET');
    expect(ref.key).toBe(ENGINE_UNKNOWN_KEY);
    expect(ref.params).not.toHaveProperty('message');
    expect(JSON.stringify(ref)).not.toContain('raw engine text');
  }
  const futureRef = messageForCode('E_FUTURE_THING');
  expect(futureRef.params.code).toBe('E_FUTURE_THING');
  const hostileRef = messageForCode('E_<b>x</b>\n' + 'z'.repeat(500));
  expect(hostileRef.params.code).not.toMatch(/[<>\n]/);
  expect(hostileRef.params.code.length).toBeLessThanOrEqual(64);
});
