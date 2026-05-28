import { App, Notice, PluginSettingTab, Setting } from 'obsidian';
import type MarkitdownPlugin from '../../main';
import { PluginArgsEditor } from './PluginArgsEditor';
import { getStrings, type UIStrings } from '../utils/i18n';
import { DEFAULT_IMAGE_PIPELINE_CONFIG } from '../types/settings';

export class SettingsTab extends PluginSettingTab {
	plugin: MarkitdownPlugin;
	private pythonPathDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	constructor(app: App, plugin: MarkitdownPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	hide(): void {
		if (this.pythonPathDebounceTimer) {
			clearTimeout(this.pythonPathDebounceTimer);
			this.pythonPathDebounceTimer = null;
			this.plugin.refreshDependencies().catch(console.error);
		}
	}

	private cancelPythonPathDebounce(): void {
		if (this.pythonPathDebounceTimer) {
			clearTimeout(this.pythonPathDebounceTimer);
			this.pythonPathDebounceTimer = null;
		}
	}

	display(): void {
		this.cancelPythonPathDebounce();
		const { containerEl } = this;
		containerEl.empty();

		const t: UIStrings = getStrings();

		// ── Python ────────────────────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.sectionPython)
			.setHeading();

		new Setting(containerEl)
			.setName(t.pythonPath)
			.setDesc(t.pythonPathDesc)
			.addText(text => text
				.setPlaceholder('python')
				.setValue(this.plugin.settings.pythonPath)
				.onChange(async (value) => {
					this.plugin.settings.pythonPath = value;
					await this.plugin.saveSettings();
					if (this.pythonPathDebounceTimer) clearTimeout(this.pythonPathDebounceTimer);
					this.pythonPathDebounceTimer = setTimeout(async () => {
						this.pythonPathDebounceTimer = null;
						await this.plugin.refreshDependencies();
						if (this.containerEl.isConnected) this.display();
					}, 1500);
				}));

		const configuredPath = this.plugin.settings.pythonPath || 'python';
		const resolvedPath = this.plugin.resolvedPythonPath;
		if (resolvedPath && resolvedPath !== configuredPath) {
			containerEl.createDiv('markitdown-resolved-path-hint').setText(`Resolved: ${resolvedPath}`);
		}

		// Dependency status
		const deps = this.plugin.dependencyStatus;
		if (deps) {
			const statusContainer = containerEl.createDiv('markitdown-dep-status');
			this.renderDependencyRow(statusContainer, 'Python', deps.pythonInstalled, deps.pythonVersion ?? undefined);
			this.renderDependencyRow(statusContainer, 'markitdown', deps.markitdownInstalled, deps.markitdownVersion ?? undefined);
		}

		// ── Conversion ────────────────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.sectionConversion)
			.setHeading();

		new Setting(containerEl)
			.setName(t.outputFolder)
			.setDesc(t.outputFolderDesc)
			.addText(text => text
				.setPlaceholder('markitdown-output')
				.setValue(this.plugin.settings.outputPath)
				.onChange(async (value) => {
					this.plugin.settings.outputPath = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName(t.inputBasePath)
			.setDesc(t.inputBasePathDesc)
			.addText(text => text
				.setPlaceholder('/path/to/documents')
				.setValue(this.plugin.settings.inputBasePath)
				.onChange(async (value) => {
					this.plugin.settings.inputBasePath = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName(t.outputFilenameTemplate)
			.setDesc(t.outputFilenameTemplateDesc)
			.addText(text => text
				.setPlaceholder('{filename}')
				.setValue(this.plugin.settings.outputFilenameTemplate)
				.onChange(async (value) => {
					this.plugin.settings.outputFilenameTemplate = value || '{filename}';
					await this.plugin.saveSettings();
				}));

		// ── Behavior ──────────────────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.sectionBehavior)
			.setHeading();

		new Setting(containerEl)
			.setName(t.enableContextMenu)
			.setDesc(t.enableContextMenuDesc)
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.enableContextMenu)
				.onChange(async (value) => {
					this.plugin.settings.enableContextMenu = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName(t.enableDragDrop)
			.setDesc(t.enableDragDropDesc)
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.enableDragDrop)
				.onChange(async (value) => {
					this.plugin.settings.enableDragDrop = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName(t.enableBatchProgress)
			.setDesc(t.enableBatchProgressDesc)
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.enableBatchProgress)
				.onChange(async (value) => {
					this.plugin.settings.enableBatchProgress = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName(t.enableRecursive)
			.setDesc(t.enableRecursiveDesc)
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.enableRecursiveConversion)
				.onChange(async (value) => {
					this.plugin.settings.enableRecursiveConversion = value;
					await this.plugin.saveSettings();
				}));

		// ── Asset extraction ───────────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.sectionAssets)
			.setHeading();

		new Setting(containerEl)
			.setName(t.assetExtraction)
			.setDesc(t.assetExtractionDesc)
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.assetExtractionEnabled)
				.onChange(async (value) => {
					this.plugin.settings.assetExtractionEnabled = value;
					await this.plugin.saveSettings();
				}));

		if (this.plugin.settings.assetExtractionEnabled) {
			new Setting(containerEl)
				.setName(t.assetSubfolder)
				.setDesc(t.assetSubfolderDesc)
				.addText(text => text
					.setPlaceholder('{filename}-assets')
					.setValue(this.plugin.settings.assetSubfolderTemplate)
					.onChange(async (value) => {
						this.plugin.settings.assetSubfolderTemplate = value || '{filename}-assets';
						await this.plugin.saveSettings();
					}));
		}

		// ── Advanced ──────────────────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.sectionAdvanced)
			.setHeading();

		new Setting(containerEl)
			.setName('Azure Document Intelligence endpoint')
			.setDesc('Endpoint URL for Azure AI Document Intelligence (e.g. https://your-resource.cognitiveservices.azure.com/). Enter the API key in the Plugin Arguments editor below.')
			.addText(text => text
				.setPlaceholder('https://your-resource.cognitiveservices.azure.com/')
				.setValue(this.plugin.settings.docintelEndpoint)
				.onChange(async (value) => {
					this.plugin.settings.docintelEndpoint = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Enable plugins')
			.setDesc('Load third-party MarkItDown converter plugins registered via entry points.')
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.enablePlugins)
				.onChange(async (value) => {
					this.plugin.settings.enablePlugins = value;
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName('Plugin arguments')
			.setDesc('Pass arbitrary key-value pairs to the Python wrapper. Keys override any built-in defaults.');

		const pluginArgsContainer = containerEl.createDiv('markitdown-plugin-args');
		new PluginArgsEditor(
			pluginArgsContainer,
			this.plugin.settings.pluginArgs,
			async (entries) => {
				this.plugin.settings.pluginArgs = entries;
				await this.plugin.saveSettings();
			},
		).render();

		// ── Image pipeline ────────────────────────────────────────────────────
		this.renderImagePipelineSection(containerEl, t);
	}

	private renderDependencyRow(
		containerEl: HTMLElement,
		label: string,
		installed: boolean,
		version?: string,
	): void {
		const item = containerEl.createDiv('markitdown-dep-row');
		const icon = item.createSpan('markitdown-dep-icon');
		icon.addClass(installed ? 'success' : 'error');
		icon.setText(installed ? '✓' : '✗');

		let text = `${label}: ${installed ? 'Installed' : 'Not installed'}`;
		if (version) text += ` (${version})`;
		item.createSpan().setText(text);
	}

	private renderImagePipelineSection(containerEl: HTMLElement, t: UIStrings): void {
		new Setting(containerEl)
			.setName(t.sectionImagePipeline)
			.setHeading();

		new Setting(containerEl)
			.setName(t.imagePipelineEnabled)
			.setDesc(t.imagePipelineEnabledDesc)
			.addToggle(toggle => toggle
				.setValue(this.plugin.settings.imagePipelineEnabled)
				.onChange(async (value) => {
					this.plugin.settings.imagePipelineEnabled = value;
					await this.plugin.saveSettings();
					this.display();
				}));

		if (!this.plugin.settings.imagePipelineEnabled) return;

		// ── OCR Language ───────────────────────────────────────────────────────
		const knownLangs: Record<string, string> = {
			'kor+eng':     'Korean + English',
			'eng':         'English',
			'kor':         'Korean',
			'jpn':         'Japanese',
			'jpn+eng':     'Japanese + English',
			'chi_sim':     'Chinese (Simplified)',
			'chi_tra':     'Chinese (Traditional)',
			'chi_sim+eng': 'Chinese (Simplified) + English',
			'fra':         'French',
			'spa':         'Spanish',
			'ara':         'Arabic',
			'hin':         'Hindi',
			'__custom__':  'Custom…',
		};
		const currentLang = this.plugin.settings.ocrLang;
		const isKnown = currentLang in knownLangs && currentLang !== '__custom__';
		new Setting(containerEl)
			.setName(t.ocrLang)
			.setDesc(t.ocrLangDesc)
			.addDropdown(dd => {
				for (const [code, label] of Object.entries(knownLangs)) {
					dd.addOption(code, label);
				}
				dd.setValue(isKnown ? currentLang : '__custom__');
				dd.onChange(async (value) => {
					if (value === '__custom__') return;
					this.plugin.settings.ocrLang = value;
					await this.plugin.saveSettings();
					this.display();
				});
			});

		if (!isKnown) {
			new Setting(containerEl)
				.setName('  Custom language code')
				.setDesc('Free-form Tesseract-style code, e.g. "deu+eng" or "kor+jpn+eng".')
				.addText(text => text
					.setPlaceholder('kor+eng')
					.setValue(currentLang === '__custom__' ? '' : currentLang)
					.onChange(async (value) => {
						this.plugin.settings.ocrLang = value || 'kor+eng';
						await this.plugin.saveSettings();
					}));
		}

		// ── Advanced config (JSON) ─────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.advancedConfig)
			.setDesc(t.advancedConfigDesc)
			.addButton(btn => btn
				.setButtonText(t.advancedConfigReset)
				.onClick(async () => {
					this.plugin.settings.imagePipelineAdvancedConfig = DEFAULT_IMAGE_PIPELINE_CONFIG;
					await this.plugin.saveSettings();
					this.display();
				}));

		const configWrapper = containerEl.createDiv('markitdown-advanced-config');
		const textarea = configWrapper.createEl('textarea', {
			cls: 'markitdown-json-textarea',
			attr: { rows: '18', spellcheck: 'false' },
		});
		textarea.value = this.plugin.settings.imagePipelineAdvancedConfig || DEFAULT_IMAGE_PIPELINE_CONFIG;
		textarea.addEventListener('change', async () => {
			this.plugin.settings.imagePipelineAdvancedConfig = textarea.value;
			await this.plugin.saveSettings();
		});

		// ── Self-test ──────────────────────────────────────────────────────────
		new Setting(containerEl)
			.setName(t.selfTest)
			.setDesc(t.selfTestDesc)
			.addButton(button => button
				.setButtonText(t.selfTestBtn)
				.setCta()
				.onClick(() => this.plugin.openSelfTestModal()));
	}
}
