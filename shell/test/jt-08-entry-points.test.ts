/**
 * JT-08 / REQ-SHL-08: one ribbon registration, conditional context actions,
 * conditional drop listener; drops accept local files only, show the selection
 * before work and never intercept text/URL drops; identical selections through
 * every entry point produce identical coordinator requests; reload leaves one
 * listener/icon.
 */
import * as path from 'node:path';
import type { Plugin as ObsidianPlugin } from 'obsidian';
import { req } from './req';
import { App, asFake, Menu, mockState, Plugin as MockPlugin, testManifest, TFile, TFolder } from './__mocks__/obsidian';
import { type CoordinatorDeps, type EntryPoint, type Selection, ShellCoordinator } from '../src/ui/coordinator';
import { type FilePicker, registerEntryPoints, selectionFromDrop } from '../src/ui/entry-points';
import { FakeClock } from './fixtures/fake-clock';
import { FakeFs, FakeSpoolFs } from './fixtures/fake-fs';
import { FakeSpawner } from './fixtures/fake-spawner';
import { abs, HOST_ENV, PLUGIN_DIR, settingsV2, VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-08');

const FILE_A = path.join(VAULT_ROOT, 'inbox', 'a.pdf');
const FOLDER = path.join(VAULT_ROOT, 'inbox');

interface Submitted {
  selection: Selection;
  entry: EntryPoint;
}

interface Harness {
  plugin: MockPlugin;
  app: App;
  submitted: Submitted[];
  coordinator: ShellCoordinator;
  picker: FilePicker & { confirmations: Selection[]; confirmAnswer: boolean; files: string[] | null; folder: string | null };
}

/** Test resolver standing in for Electron `webUtils.getPathForFile` (node-apis.filePath is the single production resolver, S-20). */
const legacyPath = (file: unknown): string | null => {
  const value = (file as { path?: unknown }).path;
  return typeof value === 'string' && value.length > 0 ? value : null;
};

function realCoordinator(): ShellCoordinator {
  const fs = new FakeFs({ directories: [VAULT_ROOT, abs(VAULT_ROOT, 'markitdown-output'), FOLDER, PLUGIN_DIR] });
  const deps: CoordinatorDeps = {
    spawner: new FakeSpawner(() => ({ exit: { code: 0, signal: null } })),
    fs,
    spoolFs: new FakeSpoolFs(fs, abs(PLUGIN_DIR, 'spool')),
    clock: new FakeClock(),
    hostEnv: HOST_ENV,
    platform: process.platform === 'win32' ? 'win32' : 'posix',
    vaultRoot: VAULT_ROOT,
    pluginDir: PLUGIN_DIR,
    settings: () => settingsV2(),
    gate: () => null,
    consent: async () => ({ approved: false }),
    notify: () => undefined,
    recordHistory: async () => undefined,
    log: null,
    nonce: () => '0123456789abcdef',
  };
  return new ShellCoordinator(deps);
}

function harness(settingsOverrides: Parameters<typeof settingsV2>[0] = {}): Harness {
  const app = new App();
  const plugin = new MockPlugin(app, testManifest());
  const submitted: Submitted[] = [];
  const real = realCoordinator();
  // Entry points call `submit`; the request projection is the real coordinator's.
  const coordinator = new Proxy(real, {
    get(target, prop, receiver) {
      if (prop === 'submit') {
        return async (selection: Selection, entry: EntryPoint) => {
          submitted.push({ selection, entry });
          return { accepted: false, diagnostic: 'shell.BUSY' as const };
        };
      }
      return Reflect.get(target, prop, receiver) as unknown;
    },
  });
  const picker: Harness['picker'] = {
    confirmations: [],
    confirmAnswer: true,
    files: [FILE_A],
    folder: FOLDER,
    pickFiles: async () => picker.files,
    pickFolder: async () => picker.folder,
    confirmSelection: async (selection) => {
      picker.confirmations.push(selection);
      return picker.confirmAnswer;
    },
    pathOf: legacyPath,
  };
  const settings = settingsV2(settingsOverrides);
  plugin.load();
  registerEntryPoints(plugin as unknown as ObsidianPlugin, coordinator, settings, picker);
  return { plugin, app, submitted, coordinator, picker };
}

function vaultFile(app: App, rel: string): TFile {
  const file = new TFile(rel);
  file.vault = app.vault;
  mockState.files.set(rel, file);
  return file;
}

function vaultFolder(app: App, rel: string): TFolder {
  const folder = new TFolder(rel);
  folder.vault = app.vault;
  mockState.files.set(rel, folder);
  return folder;
}

const tick = (): Promise<void> => new Promise((resolve) => setImmediate(resolve));

beforeEach(() => {
  mockState.reset();
  mockState.vaultRoot = VAULT_ROOT;
});

it(R('JT-08 one ribbon icon opens file selection and routes the selection through the coordinator; cancelled pickers submit nothing'), async () => {
  const h = harness();
  expect(h.plugin.ribbons).toHaveLength(1);
  expect(h.plugin.ribbons[0].icon.length).toBeGreaterThan(0);
  asFake(h.plugin.ribbons[0].el).click();
  await tick();
  expect(h.submitted).toEqual([{ selection: { kind: 'files', paths: [FILE_A] }, entry: 'ribbon' }]);
  h.picker.files = null;
  asFake(h.plugin.ribbons[0].el).click();
  await tick();
  expect(h.submitted).toHaveLength(1);
});

it(R('JT-08 context-menu actions are registered only when enabled and use the same coordinator for files and folders'), async () => {
  const disabled = harness({ enableContextMenu: false });
  expect(disabled.app.workspace.listenerCount('file-menu')).toBe(0);
  expect(disabled.app.workspace.listenerCount('files-menu')).toBe(0);

  const enabled = harness({ enableContextMenu: true });
  expect(enabled.app.workspace.listenerCount('file-menu')).toBe(1);
  const menu = new Menu();
  enabled.app.workspace.trigger('file-menu', menu, vaultFile(enabled.app, 'inbox/a.pdf'), 'file-explorer');
  expect(menu.items.length).toBeGreaterThanOrEqual(1);
  menu.items[0].click();
  await tick();
  expect(enabled.submitted).toEqual([{ selection: { kind: 'files', paths: [FILE_A] }, entry: 'context-menu' }]);

  const folderMenu = new Menu();
  enabled.app.workspace.trigger('file-menu', folderMenu, vaultFolder(enabled.app, 'inbox'), 'file-explorer');
  folderMenu.items[0].click();
  await tick();
  expect(enabled.submitted[1]).toEqual({ selection: { kind: 'folder', paths: [FOLDER] }, entry: 'context-menu' });
});

function dropEvent(dataTransfer: { files?: { path: string; name: string }[]; types: string[]; text?: string }): DragEvent & { prevented: boolean } {
  const event = {
    type: 'drop',
    prevented: false,
    preventDefault() {
      (this as { prevented: boolean }).prevented = true;
    },
    stopPropagation() {},
    dataTransfer: {
      files: dataTransfer.files ?? [],
      types: dataTransfer.types,
      getData: (t: string) => (t.startsWith('text') ? (dataTransfer.text ?? '') : ''),
    },
  };
  return event as unknown as DragEvent & { prevented: boolean };
}

it(R('JT-08 the drop listener exists only when enabled; text and URL drops are never intercepted; file drops show the selection first'), async () => {
  const off = harness({ enableDragDrop: false });
  expect(asFake(off.app.workspace.containerEl).listenerCount('drop')).toBe(0);

  const on = harness({ enableDragDrop: true });
  const container = asFake(on.app.workspace.containerEl);
  expect(container.listenerCount('drop')).toBe(1);

  const textDrop = dropEvent({ types: ['text/plain', 'text/uri-list'], text: 'https://example.com/doc.pdf' });
  container.dispatchEvent(textDrop as unknown as { type: string });
  await tick();
  expect(textDrop.prevented).toBe(false);
  expect(on.picker.confirmations).toEqual([]);
  expect(on.submitted).toEqual([]);

  const fileDrop = dropEvent({ types: ['Files'], files: [{ path: FILE_A, name: 'a.pdf' }] });
  container.dispatchEvent(fileDrop as unknown as { type: string });
  await tick();
  expect(fileDrop.prevented).toBe(true);
  expect(on.picker.confirmations).toEqual([{ kind: 'files', paths: [FILE_A] }]);
  expect(on.submitted).toEqual([{ selection: { kind: 'files', paths: [FILE_A] }, entry: 'drop' }]);

  on.picker.confirmAnswer = false;
  container.dispatchEvent(dropEvent({ types: ['Files'], files: [{ path: FILE_A, name: 'a.pdf' }] }) as unknown as { type: string });
  await tick();
  expect(on.submitted).toHaveLength(1);
});

it(R('JT-08 selectionFromDrop accepts local files only'), () => {
  expect(selectionFromDrop(dropEvent({ types: ['Files'], files: [{ path: FILE_A, name: 'a.pdf' }, { path: path.join(VAULT_ROOT, 'b.docx'), name: 'b.docx' }] }), legacyPath)).toEqual({
    kind: 'files',
    paths: [FILE_A, path.join(VAULT_ROOT, 'b.docx')],
  });
  expect(selectionFromDrop(dropEvent({ types: ['text/plain'], text: 'hello' }), legacyPath)).toBeNull();
  expect(selectionFromDrop(dropEvent({ types: ['text/uri-list'], text: 'https://example.com/x.pdf' }), legacyPath)).toBeNull();
  expect(selectionFromDrop(dropEvent({ types: ['Files'], files: [{ path: '', name: 'remote.pdf' }] }), legacyPath)).toBeNull();
});

it(R('JT-08 identical selections through command, ribbon, context menu and drop produce identical coordinator requests'), async () => {
  const h = harness({ enableContextMenu: true, enableDragDrop: true });
  asFake(h.plugin.ribbons[0].el).click();
  await tick();
  const menu = new Menu();
  h.app.workspace.trigger('file-menu', menu, vaultFile(h.app, 'inbox/a.pdf'), 'file-explorer');
  menu.items[0].click();
  await tick();
  asFake(h.app.workspace.containerEl).dispatchEvent(dropEvent({ types: ['Files'], files: [{ path: FILE_A, name: 'a.pdf' }] }) as unknown as { type: string });
  await tick();
  await h.coordinator.submit({ kind: 'files', paths: [FILE_A] }, 'command');
  expect(h.submitted.map((s) => s.entry).sort()).toEqual(['command', 'context-menu', 'drop', 'ribbon']);
  const requests = h.submitted.map((s) => h.coordinator.buildRequest(s.selection));
  for (const request of requests) expect(request).toEqual(requests[0]);
  expect(requests[0].inputs).toEqual([FILE_A]);
  expect(requests[0].outDir).toBe(path.join(VAULT_ROOT, 'markitdown-output'));
  expect(requests[0].cacheDir).toBe(path.join(PLUGIN_DIR, 'cache'));
});

it(R('JT-08 reload leaves exactly one ribbon icon and one listener of each kind'), () => {
  const h = harness({ enableContextMenu: true, enableDragDrop: true });
  h.plugin.unload();
  expect(h.plugin.ribbons).toEqual([]);
  expect(h.app.workspace.listenerCount('file-menu')).toBe(0);
  expect(asFake(h.app.workspace.containerEl).listenerCount('drop')).toBe(0);
  h.plugin.load();
  registerEntryPoints(h.plugin as unknown as ObsidianPlugin, h.coordinator, settingsV2({ enableContextMenu: true, enableDragDrop: true }), h.picker);
  expect(h.plugin.ribbons).toHaveLength(1);
  expect(h.app.workspace.listenerCount('file-menu')).toBe(1);
  expect(h.app.workspace.listenerCount('files-menu')).toBeLessThanOrEqual(1);
  expect(asFake(h.app.workspace.containerEl).listenerCount('drop')).toBe(1);
});
