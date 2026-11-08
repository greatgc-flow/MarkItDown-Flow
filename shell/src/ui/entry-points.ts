/**
 * Ribbon, optional context-menu actions and optional local-file drop
 * (20_SHELL.md REQ-SHL-08). All route through the shared coordinator.
 */
import type { EventRef, Plugin } from 'obsidian';
import { NotImplementedError } from '../pure/errors';
import type { SettingsV2 } from '../pure/settings';
import type { Selection, ShellCoordinator } from './coordinator';

export const RIBBON_ICON = 'file-text';

export interface FilePicker {
  pickFiles(): Promise<string[] | null>;
  pickFolder(): Promise<string | null>;
  /** Selection confirmation shown before any work for drops. */
  confirmSelection(selection: Selection): Promise<boolean>;
}

export interface EntryPointRegistration {
  ribbonEl: HTMLElement;
  contextMenuRefs: EventRef[];
  dropRegistered: boolean;
}

/** Register once per load; disabled preferences register no corresponding action. */
export function registerEntryPoints(
  _plugin: Plugin,
  _coordinator: ShellCoordinator,
  _settings: SettingsV2,
  _picker: FilePicker,
): EntryPointRegistration {
  throw new NotImplementedError('registerEntryPoints');
}

/** Local files only: returns null for text/URL drops so they are never intercepted. */
export function selectionFromDrop(_event: DragEvent): Selection | null {
  throw new NotImplementedError('selectionFromDrop');
}
