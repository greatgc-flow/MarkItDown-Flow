/**
 * File/folder selection through a public DOM file input (20_SHELL.md
 * REQ-SHL-08). No `electron.remote`: the renderer's `<input type="file">`
 * (with `webkitdirectory` for folders) is clicked programmatically and the
 * absolute paths are resolved through an injected resolver (Electron
 * `webUtils.getPathForFile`, falling back to the legacy `File.path`).
 * Pure with respect to the DOM: the document is injected so tests use a fake.
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
}

export type PathResolver = (file: unknown) => string | null;

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

/** Opens the picker; resolves the selected absolute paths (folder mode: the one folder root) or null when cancelled/empty. */
export function pickWithDomInput(doc: PickerDocument, mode: 'files' | 'folder', pathOf: PathResolver): Promise<string[] | null> {
  return new Promise((resolve) => {
    const input = doc.createElement('input');
    input.type = 'file';
    input.multiple = mode === 'files';
    if (mode === 'folder') input.setAttribute('webkitdirectory', '');
    input.setAttribute('style', 'display:none');
    let settled = false;
    const finish = (paths: string[] | null): void => {
      if (settled) return;
      settled = true;
      input.remove();
      resolve(paths && paths.length > 0 ? paths : null);
    };
    input.addEventListener('change', () => {
      const files = Array.from((input.files ?? []) as ArrayLike<unknown>);
      if (mode === 'files') {
        const paths: string[] = [];
        for (const file of files) {
          const path = pathOf(file);
          if (!path) return finish(null);
          paths.push(path);
        }
        return finish(paths);
      }
      const roots = new Set<string>();
      for (const file of files) {
        const path = pathOf(file);
        const relative = (file as { webkitRelativePath?: unknown }).webkitRelativePath;
        if (!path || typeof relative !== 'string') return finish(null);
        const root = folderRootOf(path, relative);
        if (!root) return finish(null);
        roots.add(root);
      }
      return finish(roots.size === 1 ? [...roots] : null);
    });
    input.addEventListener('cancel', () => finish(null));
    input.click();
  });
}
