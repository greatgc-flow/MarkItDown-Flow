/**
 * Code-keyed message table and independently authored en/ko dictionaries
 * (20_SHELL.md REQ-SHL-19). Engine rows are generated from SPEC 7.5's active
 * Code-column cells; JT-SHL-19-01 asserts set equality.
 */
import type { Locale } from './settings';
import { NotImplementedError } from './errors';

export type UiLocale = 'en' | 'ko';

/** Shell diagnostic keys fixed by 20_SHELL.md section 6. */
export type ShellDiagnosticKey =
  | 'shell.SETTINGS'
  | 'shell.RUNTIME'
  | 'shell.PROTOCOL'
  | 'shell.DESTINATION'
  | 'shell.BUSY'
  | 'shell.CANCELLED'
  | 'shell.LEGACY_URL';

export const ENGINE_UNKNOWN_KEY = 'engine.UNKNOWN';

export interface MessageRef {
  key: string;
  /** Fixed, already-redacted parameters; never a raw engine `message`. */
  params: Record<string, string>;
}

/** Active engine codes of the message table (E_/W_), excluding the UNKNOWN fallback. */
export function engineCodeKeys(): readonly string[] {
  throw new NotImplementedError('engineCodeKeys');
}

export function dictionary(_locale: UiLocale): Readonly<Record<string, string>> {
  throw new NotImplementedError('dictionary');
}

/** `auto`: `ko*` -> ko, otherwise en; explicit values override the host language. */
export function resolveLocale(_setting: Locale, _hostLanguage: string | undefined): UiLocale {
  throw new NotImplementedError('resolveLocale');
}

export function isEngineCode(_code: string): boolean {
  throw new NotImplementedError('isEngineCode');
}

/** Known code -> `engine.<CODE>`; unknown -> `engine.UNKNOWN` with a redacted literal code. */
export function messageForCode(_code: string, _rawMessage?: string): MessageRef {
  throw new NotImplementedError('messageForCode');
}

/** Interpolate `{name}` placeholders once; parameter values are inserted literally. */
export function formatMessage(_locale: UiLocale, _key: string, _params?: Record<string, string>): string {
  throw new NotImplementedError('formatMessage');
}
