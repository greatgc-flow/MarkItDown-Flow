/**
 * Plugin entry (20_SHELL.md REQ-SHL-02/08). A single `Platform.isDesktop`
 * guard precedes every lifecycle registration and all Node API access;
 * mobile returns without registrations or engine work.
 */
import { Plugin } from 'obsidian';
import { NotImplementedError } from './pure/errors';
import type { ShellCoordinator } from './ui/coordinator';

export default class MarkItDownFlowPlugin extends Plugin {
  /** Null on mobile and before `onload` completes. */
  get coordinator(): ShellCoordinator | null {
    throw new NotImplementedError('MarkItDownFlowPlugin.coordinator');
  }

  /** True when the desktop guard passed and registrations were made. */
  get desktopActive(): boolean {
    throw new NotImplementedError('MarkItDownFlowPlugin.desktopActive');
  }

  override async onload(): Promise<void> {
    throw new NotImplementedError('MarkItDownFlowPlugin.onload');
  }

  override onunload(): void {
    throw new NotImplementedError('MarkItDownFlowPlugin.onunload');
  }
}
