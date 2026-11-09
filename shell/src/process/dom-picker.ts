/**
 * File/folder selection through a public DOM file input (20_SHELL.md
 * REQ-SHL-08). No `electron.remote`: the renderer's `<input type="file">`
 * (with `webkitdirectory` for folders) is clicked programmatically and the
 * absolute paths are resolved through an injected resolver (Electron
 * `webUtils.getPathForFile`, falling back to the legacy `File.path`).
 * Pure with respect to the DOM: the document is injected so tests use a fake.
 *
 * Outcomes are distinguishable (M3 N-05/N-06): a cancelled dialog, an empty or
 * unresolvable selection, and a click that Chromium would ignore for lack of
 * user activation each settle the promise with their own kind, so the caller
 * can notify instead of silently doing nothing.
 */

export interface PickerInput {
  type: string;
  multiple: boolean;
  files: ArrayLike<unknown> | null;
  setAttribute(name: string, value: string): void;
  addEventListener(type: string, listener: () => void): void;
  click(): void;
  remove(): void;
}

export interface PickerDocument {
  createElement(tag: 'input'): PickerInput;
  /** Chromium transient user activation (`navigator.userActivation.isActive`); undefined when the host has no such API. */
  hasUserActivation?: () => boolean;
}

export type PathResolver = (file: unknown) => string | null;

export type PickOutcome =
  /** Absolute paths (files) or the one selected folder root (folder mode). */
  | { kind: 'selected'; paths: string[] }
  /** The dialog was dismissed. */
  | { kind: 'cancelled' }
  /** The dialog returned nothing usable: no files, an empty folder, or paths the host could not resolve. */
  | { kind: 'empty' }
  /** No user activation: `input.click()` would be ignored and no event would ever fire. */
  | { kind: 'blocked' };

/**
 * Root folder of a `webkitdirectory` entry: the absolute path minus the part of
 * `webkitRelativePath` below its first segment. Null when the two disagree.
 */
export function folderRootOf(absolutePath: string, relativePath: string): string | null {
  const slash = relativePath.indexOf('/');
  if (relativePath.length === 0) return null;
  const below = slash < 0 ? '' : relativePath.slice(slash + 1);
  const normalizedAbs = absolutePath.replace(/\\/g, '/');
  if (below.length > 0 && !normalizedAbs.endsWith('/' + below)) return null;
  const topName = slash < 0 ? relativePath : relativePath.slice(0, slash);
  const root = below.length > 0 ? absolutePath.slice(0, absolutePath.length - below.length - 1) : absolutePath.slice(0, absolutePath.length - relativePath.length - 1);
  if (!root.replace(/\\/g, '/').endsWith('/' + topName)) return null;
  return root;
}

/** Opens the picker and resolves with a `PickOutcome`; never leaves an input or an unsettled promise behind. */
export function pickWithDomInput(doc: PickerDocument, mode: 'files' | 'folder', pathOf: PathResolver): Promise<PickOutcome> {
  if (doc.hasUserActivation && !doc.hasUserActivation()) return Promise.resolve({ kind: 'blocked' });
  return new Promise((resolve) => {
    const input = doc.createElement('input');
    input.type = 'file';
    input.multiple = mode === 'files';
    if (mode === 'folder') input.setAttribute('webkitdirectory', '');
    input.setAttribute('style', 'display:none');
    let settled = false;
    const finish = (outcome: PickOutcome): void => {
      if (settled) return;
      settled = true;
      input.remove();
      resolve(outcome);
    };
    const selected = (paths: string[]): PickOutcome => (paths.length > 0 ? { kind: 'selected', paths } : { kind: 'empty' });
    input.addEventListener('change', () => {
      const files = Array.from((input.files ?? []) as ArrayLike<unknown>);
      if (mode === 'files') {
        const paths: string[] = [];
        for (const file of files) {
          const path = pathOf(file);
          if (!path) return finish({ kind: 'empty' });
          paths.push(path);
        }
        return finish(selected(paths));
      }
      const roots = new Set<string>();
      for (const file of files) {
        const path = pathOf(file);
        const relative = (file as { webkitRelativePath?: unknown }).webkitRelativePath;
        if (!path || typeof relative !== 'string') return finish({ kind: 'empty' });
        const root = folderRootOf(path, relative);
        if (!root) return finish({ kind: 'empty' });
        roots.add(root);
      }
      return finish(roots.size === 1 ? selected([...roots]) : { kind: 'empty' });
    });
    input.addEventListener('cancel', () => finish({ kind: 'cancelled' }));
    input.click();
  });
}
