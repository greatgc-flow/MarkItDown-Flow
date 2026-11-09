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

/** Comparable form of a real path: forward slashes, no trailing slash, case-folded on Windows. */
export function comparablePath(platform: HostPlatform, path: string): string {
  const slashed = path.replace(/\\/g, '/').replace(/\/+$/, '');
  return platform === 'win32' ? slashed.toLowerCase() : slashed;
}
