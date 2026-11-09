/**
 * JT-06 / REQ-SHL-06: key presence only, absent key keeps `none` usable,
 * engine environment scrub, diagnostics without values, nothing secret is
 * persisted, redaction of notices/logs. FX-70 sentinels.
 */
import { req } from './req';
import { API_KEY_VAR, environmentDiagnostics, keyPresence, PROVIDER_ENV_VARS, providerAvailability, scrubEngineEnv } from '../src/pure/env';
import { migrateSettings, type SettingsV2 } from '../src/pure/settings';
import { redactText, redactValue, REDACTED } from '../src/pure/redact';
import { dictionary } from '../src/pure/i18n';
import { ALL_SENTINELS, SENTINELS } from './fixtures/fx70';

const R = req('REQ-SHL-06');

const KEY_VALUE = 'sk-live-SENTINEL-ENV-KEY-3c9f1e';
const OTHER_SECRET = 'SENTINEL-OTHER-SECRET-77aa';

/** SPEC 8.2 allowlist (engine baseline) + UTF-8 settings. */
const BASELINE = ['PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'COMSPEC', 'HOME', 'USERPROFILE', 'TEMP', 'TMP', 'LANG', 'LC_ALL'];
const UTF8_VARS = ['PYTHONUTF8', 'PYTHONIOENCODING'];

const hostEnv = {
  PATH: 'C:\\Windows;C:\\Python',
  HOME: '/home/alice',
  USERPROFILE: 'C:\\Users\\alice',
  SYSTEMROOT: 'C:\\Windows',
  TEMP: 'C:\\Temp',
  LANG: 'ko_KR.UTF-8',
  PYTHONPATH: '/home/alice/evil-src-tree',
  PYTHONHOME: '/usr',
  OPENAI_API_KEY: OTHER_SECRET,
  AWS_SECRET_ACCESS_KEY: OTHER_SECRET,
  MDFLOW_API_KEY: KEY_VALUE,
  MDFLOW_BASE_URL: 'https://api.openai.com/v1',
  MDFLOW_TIMEOUT_S: '60',
  MDFLOW_COMMAND_TOKEN: OTHER_SECRET,
  SOME_RANDOM_VAR: 'noise',
};

function baseSettings(provider: SettingsV2['provider']): SettingsV2 {
  return {
    schemaVersion: 2,
    enginePython: '/venv/bin/python',
    outputPath: 'markitdown-output',
    enableBatchProgress: true,
    enableContextMenu: true,
    enableRecursiveConversion: true,
    enableDragDrop: false,
    enableLegacyPreconvert: false,
    conversionHistory: [],
    locale: 'auto',
    provider,
    runOptions: { dpi: 200, minPriority: 'low', maxUnits: 200, approveThreshold: 20, sensitive: [] },
  };
}

const NONE = { name: 'none', model: '', baseUrl: 'https://api.openai.com/v1' } as const;
const OPENAI = { name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1' } as const;

it(R('JT-06 keyPresence reports present/absent only; empty value counts as absent'), () => {
  expect(API_KEY_VAR).toBe('MDFLOW_API_KEY');
  expect(keyPresence({ MDFLOW_API_KEY: KEY_VALUE })).toBe('present');
  expect(keyPresence({})).toBe('absent');
  expect(keyPresence({ MDFLOW_API_KEY: '' })).toBe('absent');
  expect(keyPresence({ MDFLOW_API_KEY: undefined })).toBe('absent');
});

it(R('JT-06 environment diagnostics never contain a variable value'), () => {
  const diag = environmentDiagnostics(hostEnv);
  expect(diag.MDFLOW_API_KEY).toBe('present');
  const text = JSON.stringify(diag);
  expect(text).not.toContain(KEY_VALUE);
  expect(text).not.toContain(OTHER_SECRET);
  expect(text).not.toContain('/home/alice');
  for (const value of Object.values(diag)) expect(['present', 'absent']).toContain(value);
});

it(R('JT-06 absent key keeps provider none usable with no guidance'), () => {
  const availability = providerAvailability(baseSettings({ ...NONE }), {});
  expect(availability.effectiveProvider).toBe('none');
  expect(availability.remoteBlocked).toBe(false);
  expect(availability.guidanceKey).toBeNull();
});

it(R('JT-06 absent key blocks remote execution for openai-compatible with localized guidance'), () => {
  const availability = providerAvailability(baseSettings({ ...OPENAI }), { PATH: '/bin' });
  expect(availability.remoteBlocked).toBe(true);
  expect(typeof availability.guidanceKey).toBe('string');
  expect(availability.guidanceKey).toMatch(/^shell\./);
  const key = availability.guidanceKey as string;
  expect(dictionary('en')[key]?.trim().length).toBeGreaterThan(0);
  expect(dictionary('ko')[key]?.trim().length).toBeGreaterThan(0);
  const present = providerAvailability(baseSettings({ ...OPENAI }), { MDFLOW_API_KEY: KEY_VALUE });
  expect(present.remoteBlocked).toBe(false);
  expect(present.effectiveProvider).toBe('openai-compatible');
});

it(R('JT-06 engine env for provider none is the baseline plus UTF-8 settings, with no secrets or Python path overrides'), () => {
  const env = scrubEngineEnv(hostEnv, 'none');
  for (const name of Object.keys(env)) {
    expect([...BASELINE, ...UTF8_VARS]).toContain(name);
  }
  expect(env.PATH).toBe(hostEnv.PATH);
  expect(env.SYSTEMROOT).toBe(hostEnv.SYSTEMROOT);
  expect(env.PYTHONUTF8).toBe('1');
  expect(env.PYTHONIOENCODING?.toLowerCase().replace('-', '')).toBe('utf8');
  for (const forbidden of ['MDFLOW_API_KEY', 'MDFLOW_BASE_URL', 'PYTHONPATH', 'PYTHONHOME', 'OPENAI_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'MDFLOW_COMMAND_TOKEN', 'SOME_RANDOM_VAR']) {
    expect(env).not.toHaveProperty(forbidden);
  }
  expect(JSON.stringify(env)).not.toContain(KEY_VALUE);
  expect(JSON.stringify(env)).not.toContain(OTHER_SECRET);
});

it(R('JT-06 engine env for openai-compatible forwards only the SPEC provider variables in addition'), () => {
  const env = scrubEngineEnv(hostEnv, 'openai-compatible');
  for (const name of Object.keys(env)) {
    expect([...BASELINE, ...UTF8_VARS, ...PROVIDER_ENV_VARS]).toContain(name);
  }
  expect(env.MDFLOW_API_KEY).toBe(KEY_VALUE);
  expect(env.MDFLOW_BASE_URL).toBe(hostEnv.MDFLOW_BASE_URL);
  expect(env.MDFLOW_TIMEOUT_S).toBe('60');
  expect(env).not.toHaveProperty('MDFLOW_PROXY');
  for (const forbidden of ['PYTHONPATH', 'OPENAI_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'MDFLOW_COMMAND_TOKEN']) {
    expect(env).not.toHaveProperty(forbidden);
  }
  expect(PROVIDER_ENV_VARS).toEqual(['MDFLOW_API_KEY', 'MDFLOW_BASE_URL', 'MDFLOW_TIMEOUT_S', 'MDFLOW_PROXY']);
});

it(R('JT-06 no secret, approval hash or consent is ever part of the persisted candidate'), () => {
  const result = migrateSettings({
    schemaVersion: 2,
    provider: { name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1', apiKey: KEY_VALUE },
    approvedHashes: ['f'.repeat(64)],
    consentCompleted: true,
    MDFLOW_API_KEY: KEY_VALUE,
  });
  const text = JSON.stringify(result);
  expect(text).not.toContain(KEY_VALUE);
  expect(text).not.toContain('f'.repeat(64));
  expect(text).not.toContain('consentCompleted');
  expect(Object.keys(result.settings?.provider ?? {}).sort()).toEqual(['baseUrl', 'model', 'name']);
});

it(R('JT-06 redaction removes known credential values and home prefixes from notices and logs'), () => {
  const text = `Spawn failed for /home/alice/venv/bin/python with key ${KEY_VALUE} and token ${SENTINELS.llmApiKey}`;
  const out = redactText(text, { secrets: [KEY_VALUE, ...ALL_SENTINELS], home: '/home/alice' });
  expect(out).not.toContain(KEY_VALUE);
  expect(out).not.toContain(SENTINELS.llmApiKey);
  expect(out).not.toContain('/home/alice');
  expect(out).toContain(REDACTED);
  expect(out).toContain('~/venv/bin/python');
  const deep = redactValue(
    { a: [{ b: `Authorization: Bearer ${KEY_VALUE}` }], c: 'C:\\Users\\alice\\x' },
    { secrets: [KEY_VALUE], home: 'C:\\Users\\alice' },
  );
  const deepText = JSON.stringify(deep);
  expect(deepText).not.toContain(KEY_VALUE);
  expect(deepText).not.toContain('C:\\\\Users\\\\alice');
  expect(deep.a[0].b).toContain(REDACTED);
});
