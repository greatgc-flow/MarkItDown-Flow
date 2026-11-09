/**
 * Platform-aware path helpers shared by the UI and process layers
 * (20_SHELL.md REQ-SHL-09/18). Pure string operations; no filesystem access.
 */
import type { HostPlatform } from '../process/types';

export function separatorFor(platform: HostPlatform): string {
  return platform === 'win32' ? '\\' : '/';
}

/** Join a base path and relative segments with the platform separator. */
export function joinPath(platform: HostPlatform, base: string, ...segments: string[]): string {
  const sep = separatorFor(platform);
  let out = base.replace(/[\\/]+$/, '');
  for (const segment of segments) {
    for (const part of segment.split(/[\\/]+/)) if (part.length > 0) out += sep + part;
  }
  return out;
}

/**
 * Parent directory of an absolute path (pure string operation). A drive or POSIX
 * root is its own parent; a bare name without separators is returned unchanged.
 */
export function parentPath(platform: HostPlatform, path: string): string {
  const trimmed = path.replace(/[\\/]+$/, '');
  if (/^[A-Za-z]:$/.test(trimmed)) return trimmed + separatorFor(platform);
  const index = Math.max(trimmed.lastIndexOf('/'), trimmed.lastIndexOf('\\'));
  if (index < 0) return trimmed.length === 0 ? path.slice(0, 1) : trimmed;
  if (index === 0) return trimmed.slice(0, 1);
  const parent = trimmed.slice(0, index);
  return /^[A-Za-z]:$/.test(parent) ? parent + separatorFor(platform) : parent;
}

/** Absolute on either platform: POSIX root, drive letter or UNC (REQ-SHL-04/12; the only interpreter form ever executed). */
export function isAbsolutePath(value: string): boolean {
  return /^(?:\/|\\\\|[A-Za-z]:[\\/])/.test(value);
}

/** Comparable form of a real path: forward slashes, no trailing slash, case-folded on Windows. */
export function comparablePath(platform: HostPlatform, path: string): string {
  const slashed = path.replace(/\\/g, '/').replace(/\/+$/, '');
  return platform === 'win32' ? slashed.toLowerCase() : slashed;
}
