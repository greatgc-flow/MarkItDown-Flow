/**
 * JT-08 / REQ-SHL-08 (M2 X-05/X-06/X-17): a drop shows the selection in a
 * confirmation modal (Convert/Cancel, Cancel by default) before any work; the
 * file/folder pickers use a public DOM file input (no `electron.remote`) and
 * resolve paths through an injected resolver; drops resolve paths the same way.
 */
import * as path from 'node:path';
import { req } from './req';
import { asFake, createApp, mockState } from './__mocks__/obsidian';
import { dictionary } from '../src/pure/i18n';
import { folderRootOf, type PickerDocument, type PickerInput, pickWithDomInput } from '../src/process/dom-picker';
import { DropConfirmModal } from '../src/ui/drop-confirm-modal';
import { selectionFromDrop } from '../src/ui/entry-points';
import { VAULT_ROOT } from './fixtures/shell-settings';

const R = req('REQ-SHL-08');
const EN = dictionary('en');

const FILE_A = path.join(VAULT_ROOT, 'inbox', 'a.pdf');
const FILE_B = path.join(VAULT_ROOT, 'inbox', 'b c.docx');

beforeEach(() => mockState.reset());

function buttons(modal: DropConfirmModal): { convert: ReturnType<typeof asFake> | undefined; cancel: ReturnType<typeof asFake> | undefined } {
  const content = asFake(modal.contentEl);
  return {
    convert: content.findAll((e) => e.tagName === 'button' && e.textContent === EN['shell.drop.convert'])[0],
    cancel: content.findAll((e) => e.tagName === 'button' && e.textContent === EN['shell.drop.cancel'])[0],
  };
}

it(R('JT-08 the drop confirmation lists every dropped path literally and resolves true only through Convert'), async () => {
  const hostile = `${VAULT_ROOT}/<img src=x onerror=alert(1)>.pdf`;
  const modal = new DropConfirmModal(createApp(), { kind: 'files', paths: [FILE_A, FILE_B, hostile] }, 'en');
  modal.open();
  expect(mockState.openModals).toEqual([modal]);
  const content = asFake(modal.contentEl);
  for (const p of [FILE_A, FILE_B, hostile]) expect(content.textContent).toContain(p);
  expect(content.findAll((el) => ['img', 'script'].includes(el.tagName.toLowerCase()))).toEqual([]);
  expect(content.textContent).toContain('3');
  const { convert, cancel } = buttons(modal);
  expect(convert).toBeDefined();
  expect(cancel).toBeDefined();
  expect(cancel?.hasClass('mod-cta')).toBe(true);
  convert?.click();
  await expect(modal.decision).resolves.toBe(true);
  expect(mockState.openModals).toEqual([]);
});

it(R('JT-08 Cancel, close and Escape all decline; a decision is settled once'), async () => {
  const cancelled = new DropConfirmModal(createApp(), { kind: 'files', paths: [FILE_A] }, 'ko');
  cancelled.open();
  asFake(cancelled.contentEl).findAll((e) => e.tagName === 'button' && e.textContent === dictionary('ko')['shell.drop.cancel'])[0]?.click();
  await expect(cancelled.decision).resolves.toBe(false);
  const closed = new DropConfirmModal(createApp(), { kind: 'files', paths: [FILE_A] }, 'en');
  closed.open();
  closed.close();
  await expect(closed.decision).resolves.toBe(false);
  // Convert after close grants nothing.
  closed.confirm();
  await expect(closed.decision).resolves.toBe(false);
});

interface FakeInput extends PickerInput {
  attributes: Record<string, string>;
  clicked: number;
  removed: boolean;
  fire(type: 'change' | 'cancel'): void;
}

function fakeDocument(files: { path?: string; name: string; webkitRelativePath?: string }[], userActivation: boolean | undefined = undefined): { doc: PickerDocument; inputs: FakeInput[] } {
  const inputs: FakeInput[] = [];
  const doc: PickerDocument = {
    hasUserActivation: userActivation === undefined ? undefined : () => userActivation,
    createElement: () => {
      const listeners = new Map<string, (() => void)[]>();
      const input: FakeInput = {
        type: '',
        multiple: false,
        files: null,
        attributes: {},
        clicked: 0,
        removed: false,
        setAttribute(name: string, value: string) {
          this.attributes[name] = value;
        },
        addEventListener(type: string, listener: () => void) {
          listeners.set(type, [...(listeners.get(type) ?? []), listener]);
        },
        click() {
          this.clicked += 1;
        },
        remove() {
          this.removed = true;
        },
        fire(type) {
          if (type === 'change') this.files = files;
          for (const listener of listeners.get(type) ?? []) listener();
        },
      };
      inputs.push(input);
      return input;
    },
  };
  return { doc, inputs };
}

const pathOf = (file: unknown): string | null => (typeof (file as { path?: unknown }).path === 'string' ? (file as { path: string }).path : null);

it(R('JT-08 the DOM file picker opens a hidden multi-file input and resolves absolute paths through the resolver; cancel yields null'), async () => {
  const { doc, inputs } = fakeDocument([{ path: FILE_A, name: 'a.pdf' }, { path: FILE_B, name: 'b c.docx' }]);
  const pending = pickWithDomInput(doc, 'files', pathOf);
  expect(inputs).toHaveLength(1);
  expect(inputs[0].type).toBe('file');
  expect(inputs[0].multiple).toBe(true);
  expect(inputs[0].attributes.webkitdirectory).toBeUndefined();
  expect(inputs[0].clicked).toBe(1);
  inputs[0].fire('change');
  await expect(pending).resolves.toEqual({ kind: 'selected', paths: [FILE_A, FILE_B] });
  expect(inputs[0].removed).toBe(true);
  const cancelled = fakeDocument([]);
  const none = pickWithDomInput(cancelled.doc, 'files', pathOf);
  cancelled.inputs[0].fire('cancel');
  await expect(none).resolves.toEqual({ kind: 'cancelled' });
  // Files whose path cannot be resolved never become inputs; the outcome is distinguishable from a cancel (M3 N-05).
  const unresolved = fakeDocument([{ name: 'remote.pdf' }]);
  const empty = pickWithDomInput(unresolved.doc, 'files', pathOf);
  unresolved.inputs[0].fire('change');
  await expect(empty).resolves.toEqual({ kind: 'empty' });
});

it(R('JT-08 without Chromium user activation the picker settles immediately as blocked instead of leaking an input whose promise never settles (M3 N-06)'), async () => {
  const blocked = fakeDocument([{ path: FILE_A, name: 'a.pdf' }], false);
  await expect(pickWithDomInput(blocked.doc, 'files', pathOf)).resolves.toEqual({ kind: 'blocked' });
  expect(blocked.inputs).toEqual([]);
  // With activation (or without the API at all) the dialog opens as before.
  const active = fakeDocument([{ path: FILE_A, name: 'a.pdf' }], true);
  const pending = pickWithDomInput(active.doc, 'files', pathOf);
  expect(active.inputs[0].clicked).toBe(1);
  active.inputs[0].fire('change');
  await expect(pending).resolves.toEqual({ kind: 'selected', paths: [FILE_A] });
});

it(R('JT-08 the DOM folder picker uses webkitdirectory and derives the selected folder root from the relative paths'), async () => {
  const sep = process.platform === 'win32' ? '\\' : '/';
  const root = path.join(VAULT_ROOT, 'inbox');
  const files = [
    { path: `${root}${sep}sub${sep}a.pdf`, name: 'a.pdf', webkitRelativePath: 'inbox/sub/a.pdf' },
    { path: `${root}${sep}memo.txt`, name: 'memo.txt', webkitRelativePath: 'inbox/memo.txt' },
  ];
  const { doc, inputs } = fakeDocument(files);
  const pending = pickWithDomInput(doc, 'folder', pathOf);
  expect(inputs[0].attributes.webkitdirectory).toBeDefined();
  inputs[0].fire('change');
  await expect(pending).resolves.toEqual({ kind: 'selected', paths: [root] });
  expect(folderRootOf(`${root}${sep}sub${sep}a.pdf`, 'inbox/sub/a.pdf')).toBe(root);
  expect(folderRootOf(`${root}${sep}memo.txt`, 'inbox/memo.txt')).toBe(root);
  expect(folderRootOf(`${root}${sep}memo.txt`, '')).toBeNull();
  expect(folderRootOf(`${root}${sep}memo.txt`, 'elsewhere/x.txt')).toBeNull();
  // An empty folder (or one holding only subfolders) yields `empty`, which the plugin reports instead of doing nothing (M3 N-05).
  const emptyFolder = fakeDocument([]);
  const none = pickWithDomInput(emptyFolder.doc, 'folder', pathOf);
  emptyFolder.inputs[0].fire('change');
  await expect(none).resolves.toEqual({ kind: 'empty' });
});

it(R('JT-08 dropped files resolve their path through the injected resolver (webUtils) and fall back to File.path'), () => {
  const event = {
    type: 'drop',
    preventDefault() {},
    stopPropagation() {},
    dataTransfer: { files: [{ name: 'a.pdf' }], types: ['Files'] },
  } as unknown as DragEvent;
  expect(selectionFromDrop(event, pathOf)).toBeNull();
  expect(selectionFromDrop(event, () => FILE_A)).toEqual({ kind: 'files', paths: [FILE_A] });
  // node-apis.filePath is the single resolver (webUtils, then legacy File.path); the entry point has no fallback of its own (S-20).
  const legacy = { ...event, dataTransfer: { files: [{ name: 'b.docx', path: FILE_B }], types: ['Files'] } } as unknown as DragEvent;
  expect(selectionFromDrop(legacy, pathOf)).toEqual({ kind: 'files', paths: [FILE_B] });
});
