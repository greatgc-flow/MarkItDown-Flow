/**
 * Ribbon, optional context-menu actions and optional local-file drop
 * (20_SHELL.md REQ-SHL-08). All route through the shared coordinator; a drop
 * shows its selection for confirmation before any work.
 */
import { type EventRef, FileSystemAdapter, type Menu, Platform, type Plugin, type TAbstractFile, TFolder } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';
import type { SettingsV2 } from '../pure/settings';
import type { Selection, ShellCoordinator } from './coordinator';
import { joinPath } from './output-path';

export const RIBBON_ICON = 'file-text';

/** Absolute path of a dropped/picked `File`; null when the host cannot provide one. */
export type PathResolver = (file: unknown) => string | null;

export interface FilePicker {
  pickFiles(): Promise<string[] | null>;
  pickFolder(): Promise<string | null>;
  /** Selection confirmation shown before any work for drops. */
  confirmSelection(selection: Selection): Promise<boolean>;
  /** Resolver for dropped files (Electron `webUtils.getPathForFile`); defaults to the legacy `File.path`. */
  pathOf?: PathResolver;
}

export interface EntryPointRegistration {
  ribbonEl: HTMLElement;
  contextMenuRefs: EventRef[];
  dropRegistered: boolean;
}

/** Absolute path of a vault file through the desktop adapter's base path. */
export function vaultAbsolutePath(plugin: Plugin, file: TAbstractFile): string | null {
  const adapter = plugin.app.vault.adapter;
  if (!(adapter instanceof FileSystemAdapter)) return null;
  return joinPath(Platform.isWin ? 'win32' : 'posix', adapter.getBasePath(), file.path);
}

function selectionFor(plugin: Plugin, files: TAbstractFile[]): Selection | null {
  const paths: string[] = [];
  let folder = false;
  for (const file of files) {
    const absolute = vaultAbsolutePath(plugin, file);
    if (!absolute) return null;
    if (file instanceof TFolder) folder = true;
    paths.push(absolute);
  }
  if (paths.length === 0) return null;
  if (folder && paths.length === 1) return { kind: 'folder', paths };
  if (folder) return null;
  return { kind: 'files', paths };
}

/** Legacy Electron `File.path` (removed upstream in Electron 32; Obsidian exposes `webUtils` instead). */
export const legacyFilePath: PathResolver = (file) => {
  const path = (file as { path?: unknown }).path;
  return typeof path === 'string' && path.length > 0 ? path : null;
};

/** Local files only: returns null for text/URL drops so they are never intercepted. */
export function selectionFromDrop(event: DragEvent, pathOf: PathResolver = legacyFilePath): Selection | null {
  const transfer = event.dataTransfer;
  if (!transfer) return null;
  const types = Array.from((transfer.types ?? []) as ArrayLike<string>);
  if (!types.includes('Files')) return null;
  const files = Array.from((transfer.files ?? []) as ArrayLike<unknown>);
  if (files.length === 0) return null;
  const paths: string[] = [];
  for (const file of files) {
    const path = pathOf(file);
    if (!path) return null;
    paths.push(path);
  }
  return { kind: 'files', paths };
}

/** Register once per load; disabled preferences register no corresponding action. */
export function registerEntryPoints(
  plugin: Plugin,
  coordinator: ShellCoordinator,
  settings: SettingsV2,
  picker: FilePicker,
  locale: UiLocale = 'en',
): EntryPointRegistration {
  const t = (key: string, params?: Record<string, string>): string => formatMessage(locale, key, params);

  const ribbonEl = plugin.addRibbonIcon(RIBBON_ICON, t('shell.ribbon.title'), () => {
    void (async () => {
      const files = await picker.pickFiles();
      if (files && files.length > 0) await coordinator.submit({ kind: 'files', paths: files }, 'ribbon');
    })();
  });

  const contextMenuRefs: EventRef[] = [];
  if (settings.enableContextMenu) {
    const addAction = (menu: Menu, files: TAbstractFile[]): void => {
      const selection = selectionFor(plugin, files);
      if (!selection) return;
      menu.addItem((item) => {
        item.setTitle(t('shell.menu.convert')).setIcon(RIBBON_ICON).onClick(() => {
          void coordinator.submit(selection, 'context-menu');
        });
      });
    };
    const single = plugin.app.workspace.on('file-menu', (menu, file) => addAction(menu, [file]));
    const multi = plugin.app.workspace.on('files-menu', (menu, files) => addAction(menu, files));
    plugin.registerEvent(single);
    plugin.registerEvent(multi);
    contextMenuRefs.push(single, multi);
  }

  let dropRegistered = false;
  if (settings.enableDragDrop) {
    const container = plugin.app.workspace.containerEl;
    const pathOf = picker.pathOf ?? legacyFilePath;
    plugin.registerDomEvent(container, 'dragover', (event: DragEvent) => {
      const types = Array.from((event.dataTransfer?.types ?? []) as ArrayLike<string>);
      if (types.includes('Files')) event.preventDefault();
    });
    plugin.registerDomEvent(container, 'drop', (event: DragEvent) => {
      const selection = selectionFromDrop(event, pathOf);
      if (!selection) return;
      event.preventDefault();
      event.stopPropagation();
      void (async () => {
        if (await picker.confirmSelection(selection)) await coordinator.submit(selection, 'drop');
      })();
    });
    dropRegistered = true;
  }

  return { ribbonEl, contextMenuRefs, dropRegistered };
}
