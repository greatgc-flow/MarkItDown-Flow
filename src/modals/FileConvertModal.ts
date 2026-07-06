/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
import { App, Modal, Notice } from 'obsidian';
import * as path from 'path';
import * as fs from 'fs';
import type MarkitdownPlugin from '../../main';
import { FILE_INPUT_ACCEPT } from '../utils/fileTypes';
import { getVaultBasePath, resolveOutputFolder, resolveStructuredOutputPath } from '../utils/paths';

export class FileConvertModal extends Modal {
	private plugin: MarkitdownPlugin;

	constructor(app: App, plugin: MarkitdownPlugin) {
		super(app);
		this.plugin = plugin;
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.addClass('markitdown-modal');
		contentEl.createEl('h2', { text: 'Convert file to Markdown' });

		contentEl.createEl('p', { text: 'Select a file to convert:' });

		const fileInputContainer = contentEl.createDiv('markitdown-file-input-container');
		const fileInput = fileInputContainer.createEl('input', {
			attr: { type: 'file', accept: FILE_INPUT_ACCEPT },
		});

		const buttonContainer = contentEl.createDiv('markitdown-button-container');
		const convertButton = buttonContainer.createEl('button', {
			text: 'Convert',
			cls: 'mod-cta',
		});

		convertButton.addEventListener('click', async () => {
			if (!fileInput.files || fileInput.files.length === 0) {
				new Notice('Please select a file first');
				return;
			}

			const file = fileInput.files[0];
			convertButton.disabled = true;
			convertButton.setText('Converting...');

			try {
				const vaultPath = getVaultBasePath(this.app);
				if (!vaultPath) {
					new Notice('Could not determine vault path. This plugin requires a local vault.');
					convertButton.disabled = false;
					convertButton.setText('Convert');
					return;
				}

				const outputFolder = resolveOutputFolder(vaultPath, this.plugin.settings.outputPath);
				const outputPath = resolveStructuredOutputPath(
					file.name,
					this.plugin.settings.inputBasePath,
					outputFolder,
					this.plugin.settings.outputFilenameTemplate || '{filename}',
				);

				// Write the DOM File to a temp file on disk
				const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
				const tempFilePath = path.join(outputFolder, `tmp_${Date.now()}_${safeName}`);
				const buffer = await file.arrayBuffer();
				await fs.promises.writeFile(tempFilePath, Buffer.from(buffer));

				try {
					const result = await this.plugin.convertExternalFile(tempFilePath, outputPath);

					this.plugin.postConversionNotice('Converted', result);
					if (result.success) {
						await this.plugin.openConvertedFile(outputPath, vaultPath);
						this.close();
					} else {
						convertButton.disabled = false;
						convertButton.setText('Convert');
					}
				} finally {
					// Clean up temp file
					await fs.promises.unlink(tempFilePath).catch(() => {});
				}
			} catch (error) {
				const msg = error instanceof Error ? error.message : String(error);
				new Notice(`Error: ${msg}`);
				convertButton.disabled = false;
				convertButton.setText('Convert');
			}
		});
	}

	onClose() {
		this.contentEl.empty();
	}
}
