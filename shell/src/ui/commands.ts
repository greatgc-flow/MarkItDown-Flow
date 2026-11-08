/**
 * The six frozen local command ids (20_SHELL.md REQ-SHL-02; R-F1). Ids are
 * registered without the `markitdown-flow:` prefix; the host adds it.
 */
import type { Plugin } from 'obsidian';
import { NotImplementedError } from '../pure/errors';
import type { ShellCoordinator } from './coordinator';

export const PLUGIN_ID = 'markitdown-flow';

export const COMMAND_IDS = [
  'convert-file',
  'convert-folder',
  'convert-url',
  'view-conversion-history',
  'open-log-folder',
  'run-image-pipeline-selftest',
] as const;

export type CommandId = (typeof COMMAND_IDS)[number];

/** Register exactly the six commands on the plugin; each routes through the coordinator. */
export function registerCommands(_plugin: Plugin, _coordinator: ShellCoordinator): void {
  throw new NotImplementedError('registerCommands');
}
