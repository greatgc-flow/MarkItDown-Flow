/** Schema-2 settings builder for process/UI tests. */
import type { SettingsV2 } from '../../src/pure/settings';

export const ENGINE_PYTHON = process.platform === 'win32' ? 'C:\\mdflow-venvs\\2.0.0\\Scripts\\python.exe' : '/home/alice/mdflow-venvs/2.0.0/bin/python';
export const VAULT_ROOT = process.platform === 'win32' ? 'C:\\Users\\alice\\Vault' : '/home/alice/Vault';
export const PLUGIN_DIR = `${VAULT_ROOT}${process.platform === 'win32' ? '\\' : '/'}.obsidian${process.platform === 'win32' ? '\\' : '/'}plugins${process.platform === 'win32' ? '\\' : '/'}markitdown-flow`;
export const HOME = process.platform === 'win32' ? 'C:\\Users\\alice' : '/home/alice';

export function settingsV2(overrides: Partial<SettingsV2> = {}): SettingsV2 {
  return {
    schemaVersion: 2,
    enginePython: ENGINE_PYTHON,
    outputPath: 'markitdown-output',
    enableBatchProgress: true,
    enableContextMenu: true,
    enableRecursiveConversion: true,
    enableDragDrop: false,
    conversionHistory: [],
    locale: 'en',
    provider: { name: 'none', model: '', baseUrl: 'https://api.openai.com/v1' },
    runOptions: { dpi: 200, minPriority: 'low', maxUnits: 200, approveThreshold: 20, sensitive: [] },
    ...overrides,
  };
}

export const OPENAI_PROVIDER = { name: 'openai-compatible', model: 'gpt-4.1-mini', baseUrl: 'https://api.openai.com/v1' } as const;

export const KEY_VALUE = 'sk-live-SENTINEL-ENV-KEY-3c9f1e';

export const HOST_ENV: Readonly<Record<string, string>> = {
  PATH: process.platform === 'win32' ? 'C:\\Windows;C:\\Python' : '/usr/bin:/bin',
  HOME,
  USERPROFILE: HOME,
  SYSTEMROOT: 'C:\\Windows',
  TEMP: process.platform === 'win32' ? 'C:\\Temp' : '/tmp',
  LANG: 'ko_KR.UTF-8',
  MDFLOW_API_KEY: KEY_VALUE,
  PYTHONPATH: '/evil/src',
  OPENAI_API_KEY: 'SENTINEL-OTHER-SECRET-77aa',
};

/** Join with the host separator so absolute inputs look native. */
export function abs(...parts: string[]): string {
  return parts.join(process.platform === 'win32' ? '\\' : '/');
}
