/**
 * Doc parsers used by JT-SHL-19-01 (REQ-SHL-19): active Code-column cells of
 * SPEC section 7.5 and the engine-code rows of 20_SHELL.md section 6.
 * Only table rows are scanned; prose (including the "Deleted:" line) is ignored.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { REPO_ROOT } from '../req';

const CODE = /^[EW]_[A-Z0-9_]+$/;

function docText(name: string): string {
  return fs.readFileSync(path.join(REPO_ROOT, 'docs', 'renewal', name), 'utf8');
}

/** Lines of the first markdown table that follows `heading` (header + separator skipped). */
function tableRowsAfter(text: string, heading: RegExp): string[] {
  const lines = text.split(/\r?\n/);
  const start = lines.findIndex((l) => heading.test(l));
  if (start < 0) throw new Error(`heading not found: ${heading}`);
  const rows: string[] = [];
  let inTable = false;
  for (let i = start + 1; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('|')) {
      inTable = true;
      rows.push(line);
    } else if (inTable) {
      break;
    } else if (/^#{1,6}\s/.test(line)) {
      throw new Error(`no table before next heading after ${heading}`);
    }
  }
  if (rows.length < 3) throw new Error(`table after ${heading} is too short`);
  return rows.slice(2); // drop header and separator
}

function firstCell(row: string): string {
  return row.split('|')[1]?.trim() ?? '';
}

/** Backticked code literals in a cell, e.g. "`E_USAGE E_CORE_VERSION`(startup)" -> both. */
function codesInCell(cell: string): string[] {
  const out: string[] = [];
  for (const m of cell.matchAll(/`([^`]+)`/g)) {
    for (const token of m[1].split(/\s+/)) {
      if (CODE.test(token)) out.push(token);
    }
  }
  return out;
}

export interface CodeScan {
  /** Deduplicated set. */
  codes: Set<string>;
  /** Every literal in row order, duplicates included. */
  literals: string[];
  rows: number;
}

/** SPEC 7.5: union of E_/W_ literals in the first (Code) cell of each active row. */
export function specActiveCodes(): CodeScan {
  const rows = tableRowsAfter(docText('10_SPEC.md'), /^### 7\.5 /);
  const literals = rows.flatMap((r) => codesInCell(firstCell(r)));
  return { codes: new Set(literals), literals, rows: rows.length };
}

/** 20_SHELL.md section 6: engine error table + engine warning table first cells. */
export function shellDocEngineCodes(): CodeScan {
  const text = docText('20_SHELL.md');
  const errorRows = tableRowsAfterHeaderRow(text, /^\| Engine error code \|/);
  const warningRows = tableRowsAfterHeaderRow(text, /^\| Engine warning code \|/);
  const literals = [...errorRows, ...warningRows].flatMap((r) => codesInCell(firstCell(r)));
  return { codes: new Set(literals), literals, rows: errorRows.length + warningRows.length };
}

/** Rows of the table whose header row matches `headerRow` (header + separator skipped). */
function tableRowsAfterHeaderRow(text: string, headerRow: RegExp): string[] {
  const lines = text.split(/\r?\n/);
  const start = lines.findIndex((l) => headerRow.test(l));
  if (start < 0) throw new Error(`table header not found: ${headerRow}`);
  const rows: string[] = [];
  for (let i = start + 2; i < lines.length; i++) {
    if (!lines[i].startsWith('|')) break;
    rows.push(lines[i]);
  }
  return rows;
}

/** 20_SHELL.md section 6: shell diagnostic keys (`shell.*`, `engine.UNKNOWN`). */
export function shellDocDiagnosticKeys(): string[] {
  const rows = tableRowsAfterHeaderRow(docText('20_SHELL.md'), /^\| Shell diagnostic key \|/);
  return rows.map((r) => firstCell(r).replace(/`/g, ''));
}

/** Codes named as deleted in SPEC 7.5 prose; must not be in the active set. */
export const DELETED_CODES = ['W_TRIAGE_COVERAGE', 'E_PROVIDER_INTERRUPTED', 'W_STALE_TEMP'] as const;
