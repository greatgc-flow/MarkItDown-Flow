/**
 * Output destination validation and nonrecursive folder selection
 * (20_SHELL.md REQ-SHL-09). Platform-aware real paths, no bare string-prefix
 * check; nonexistent destinations resolve through the nearest existing ancestor.
 */
import { comparablePath, joinPath } from '../pure/paths';
import type { FileSystemOps, HostPlatform } from '../process/types';

export { comparablePath, joinPath, separatorFor } from '../pure/paths';

export type DestinationRejection = 'absolute' | 'traversal' | 'escape' | 'symlink' | 'invalid' | 'not_directory';

export type DestinationResult =
  | { ok: true; absolute: string; existing: boolean }
  | { ok: false; diagnostic: 'shell.DESTINATION'; reason: DestinationRejection };

export interface PathOps {
  realpath: FileSystemOps['realpath'];
  isDirectory: FileSystemOps['isDirectory'];
  isSymlink: FileSystemOps['isSymlink'];
  platform: HostPlatform;
}

function isWithin(platform: HostPlatform, candidate: string, root: string): boolean {
  const c = comparablePath(platform, candidate);
  const r = comparablePath(platform, root);
  return c === r || c.startsWith(r + '/');
}

function reject(reason: DestinationRejection): DestinationResult {
  return { ok: false, diagnostic: 'shell.DESTINATION', reason };
}

/** Resolve `outputPath` against the vault root; reject absolute/traversing/escaping/symlinked destinations. */
export async function resolveDestination(vaultRoot: string, outputPath: string, ops: PathOps): Promise<DestinationResult> {
  if (typeof outputPath !== 'string' || outputPath.trim().length === 0) return reject('invalid');
  if (/[\u0000-\u001f\u007f]/.test(outputPath)) return reject('invalid');
  if (/^(?:[\\/]|[A-Za-z]:)/.test(outputPath)) return reject('absolute');
  const segments = outputPath.split(/[\\/]+/).filter((s) => s.length > 0);
  if (segments.length === 0) return reject('invalid');
  if (segments.some((s) => s === '..')) return reject('traversal');
  if (segments.some((s) => s === '.' || s.startsWith('.'))) return reject('invalid');

  const realVault = await ops.realpath(vaultRoot);
  if (realVault === null) return reject('invalid');

  // Nearest existing ancestor, checking every component on the way for symlinks.
  let existingDepth = segments.length;
  for (; existingDepth > 0; existingDepth--) {
    const candidate = joinPath(ops.platform, vaultRoot, ...segments.slice(0, existingDepth));
    if ((await ops.realpath(candidate)) !== null) break;
  }
  for (let depth = 1; depth <= existingDepth; depth++) {
    if (await ops.isSymlink(joinPath(ops.platform, vaultRoot, ...segments.slice(0, depth)))) return reject('symlink');
  }
  const ancestor = existingDepth === 0 ? vaultRoot : joinPath(ops.platform, vaultRoot, ...segments.slice(0, existingDepth));
  const realAncestor = await ops.realpath(ancestor);
  if (realAncestor === null) return reject('invalid');
  if (!isWithin(ops.platform, realAncestor, realVault)) return reject('escape');
  if (!(await ops.isDirectory(ancestor))) return reject('not_directory');
  return { ok: true, absolute: joinPath(ops.platform, vaultRoot, ...segments), existing: existingDepth === segments.length };
}

export interface DirEntry {
  name: string;
  kind: 'file' | 'dir' | 'symlink' | 'other';
}

export interface SelectionExclusions {
  outDir: string;
  cacheDir: string;
}

/** Immediate regular files only: no hidden entries, symlinks, directories, output or cache locations. */
export function selectImmediateFiles(
  folder: string,
  entries: readonly DirEntry[],
  exclusions: SelectionExclusions,
  platform: HostPlatform,
): string[] {
  const excluded = new Set([comparablePath(platform, exclusions.outDir), comparablePath(platform, exclusions.cacheDir)]);
  const out: string[] = [];
  for (const entry of entries) {
    if (entry.kind !== 'file') continue;
    if (entry.name.length === 0 || entry.name.startsWith('.')) continue;
    const full = joinPath(platform, folder, entry.name);
    if (excluded.has(comparablePath(platform, full))) continue;
    out.push(full);
  }
  return out;
}
