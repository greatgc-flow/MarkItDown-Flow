/**
 * Diagnostics-only SetupModal (20_SHELL.md REQ-SHL-10/17). Shows interpreter,
 * versions, probe status and copyable external bootstrap instructions.
 */
import { type App, Modal } from 'obsidian';
import { NotImplementedError } from '../pure/errors';
import type { UiLocale } from '../pure/i18n';
import type { SetupDeps, SetupDiagnostics } from '../process/setup';

export interface SetupModalDeps extends SetupDeps {
  writeClipboard: (text: string) => Promise<void>;
  locale: UiLocale;
}

export class SetupModal extends Modal {
  constructor(app: App, _deps: SetupModalDeps) {
    super(app);
  }

  /** Last collected diagnostics (null before the first refresh). */
  get diagnostics(): SetupDiagnostics | null {
    throw new NotImplementedError('SetupModal.diagnostics');
  }

  /** Re-run the version probe(s) and re-render. */
  async refresh(): Promise<void> {
    throw new NotImplementedError('SetupModal.refresh');
  }

  /** Copy buttons: write the rendered instruction text to the clipboard, nothing else. */
  async copyInstructions(_target: 'windows' | 'posix'): Promise<void> {
    throw new NotImplementedError('SetupModal.copyInstructions');
  }

  async copyDiagnostics(): Promise<void> {
    throw new NotImplementedError('SetupModal.copyDiagnostics');
  }

  override onOpen(): void {
    throw new NotImplementedError('SetupModal.onOpen');
  }

  override onClose(): void {
    throw new NotImplementedError('SetupModal.onClose');
  }
}
