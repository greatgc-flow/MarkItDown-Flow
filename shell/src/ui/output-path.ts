/**
 * Output destination validation and nonrecursive folder selection
 * (20_SHELL.md REQ-SHL-09). Platform-aware real paths, no bare string-prefix
 * check; nonexistent destinations resolve through the nearest existing ancestor.
 */
import { NotImplementedError } from '../pure/errors';
import type { FileSystemOps, HostPlatform } from '../process/types';

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

/** Resolve `outputPath` against the vault root; reject absolute/traversing/escaping/symlinked destinations. */
export async function resolveDestination(_vaultRoot: string, _outputPath: string, _ops: PathOps): Promise<DestinationResult> {
  throw new NotImplementedError('resolveDestination');
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
  _folder: string,
  _entries: readonly DirEntry[],
  _exclusions: SelectionExclusions,
  _platform: HostPlatform,
): string[] {
  throw new NotImplementedError('selectImmediateFiles');
}
