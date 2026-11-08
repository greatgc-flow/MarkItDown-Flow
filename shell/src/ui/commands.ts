/**
 * The six frozen local command ids (20_SHELL.md REQ-SHL-02; R-F1). Ids are
 * registered without the `markitdown-flow:` prefix; the host adds it.
 */
import type { Plugin } from 'obsidian';
import { formatMessage, type UiLocale } from '../pure/i18n';

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

export type CommandActions = Record<CommandId, () => void | Promise<void>>;

const NAME_KEYS: Record<CommandId, string> = {
  'convert-file': 'shell.command.convertFile',
  'convert-folder': 'shell.command.convertFolder',
  'convert-url': 'shell.command.convertUrl',
  'view-conversion-history': 'shell.command.history',
  'open-log-folder': 'shell.command.logs',
  'run-image-pipeline-selftest': 'shell.command.selftest',
};

/** Register exactly the six commands on the plugin; each routes to its action. */
export function registerCommands(plugin: Plugin, actions: CommandActions, locale: UiLocale = 'en'): void {
  for (const id of COMMAND_IDS) {
    plugin.addCommand({
      id,
      name: formatMessage(locale, NAME_KEYS[id]),
      callback: () => {
        void actions[id]();
      },
    });
  }
}
