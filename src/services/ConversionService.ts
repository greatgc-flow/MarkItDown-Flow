/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
import { App, Notice, TFile } from 'obsidian';
import * as path from 'path';
import {
	ConversionOptions,
	ConversionResult,
	PluginArgEntry,
} from '../types/settings';
import {
	getVaultBasePath,
	resolveOutputFolder,
	resolveStructuredOutputPath,
	resolveAssetDir,
	toVaultRelative,
} from '../utils/paths';
import { addHistoryEntry } from '../utils/history';
import { SetupModal } from '../modals/SetupModal';
import type MarkitdownPlugin from '../../main';

/**
 * Encapsulates everything to do with running a single conversion:
 *
 *   1. Build ConversionOptions from the current settings (incl. the Image
 *      Pipeline UI → pluginArgs injection logic).
 *   2. Call the underlying converter.
 *   3. Append a history entry, persist settings.
 *   4. Surface a user-facing Notice.
 *   5. Optionally open the result.
 *
 * Lives behind `plugin.conversionService`. The plugin keeps thin wrapper
 * methods (convertVaultFile / convertExternalFile / buildConversionOptions /
 * postConversionNotice) that delegate here, so existing modal callsites keep
 * working without change.
 */
export class ConversionService {
	constructor(private plugin: MarkitdownPlugin) {}

	private get app(): App {
		return this.plugin.app;
	}

	// ─────────────────────────────────────────────────────────────────────
	// Public — conversion entry points
	// ─────────────────────────────────────────────────────────────────────

	/**
	 * Convert a file that already exists in the vault (e.g. from the right-click
	 * context menu). Records history, shows a Notice, and opens the output.
	 */
	async convertVaultFile(file: TFile): Promise<void> {
		const vaultPath = getVaultBasePath(this.app);
		if (!vaultPath) {
			new Notice('Could not determine vault path. This plugin requires a local vault.');
			return;
		}

		if (!this.plugin.dependencyStatus.markitdownInstalled) {
			new SetupModal(this.app, this.plugin).open();
			return;
		}

		const inputPath = path.join(vaultPath, file.path);
		const outputFolder = resolveOutputFolder(vaultPath, this.plugin.settings.outputPath);
		const outputPath = resolveStructuredOutputPath(
			inputPath,
			this.plugin.settings.inputBasePath,
			outputFolder,
			this.plugin.settings.outputFilenameTemplate || '{filename}',
		);

		new Notice('Converting file...');
		const result = await this.runAndRecord(inputPath, outputPath);

		this.postConversionNotice('Converted', result);
		if (result.success) {
			await this.openConvertedFile(outputPath, vaultPath);
		}
	}

	/**
	 * Convert a file that is NOT in the vault (e.g. one written to a temp path
	 * by FileConvertModal / FolderConvertModal / the drag-drop handler).
	 * Records history but does NOT show a Notice or open the file — the caller
	 * decides because the UX around external sources varies (drag-drop wants to
	 * insert a wiki-link, the modal wants to close itself, etc.).
	 */
	async convertExternalFile(
		inputPath: string,
		outputPath: string,
	): Promise<ConversionResult> {
		return this.runAndRecord(inputPath, outputPath);
	}

	// ─────────────────────────────────────────────────────────────────────
	// Public — UI helpers (reused by modals via plugin.postConversionNotice)
	// ─────────────────────────────────────────────────────────────────────

	/**
	 * Show a one-shot Notice summarising a conversion outcome.
	 *
	 * On success: `<label>` or `<label> (N assets extracted)` when assets > 0.
	 * On failure: `<label> failed: <error>`.
	 */
	postConversionNotice(label: string, result: ConversionResult): void {
		if (result.success) {
			const msg = result.assetsExtracted
				? `${label} (${result.assetsExtracted} assets extracted)`
				: `${label} successfully`;
			new Notice(msg);
		} else {
			new Notice(`${label} failed: ${result.error}`);
		}
	}

	/** Open the converted file in the active workspace leaf. */
	async openConvertedFile(outputPath: string, vaultPath: string): Promise<void> {
		const relativePath = toVaultRelative(outputPath, vaultPath);
		const existingFile = this.app.vault.getAbstractFileByPath(relativePath);
		if (existingFile instanceof TFile) {
			await this.app.workspace.getLeaf().openFile(existingFile);
		}
	}

	// ─────────────────────────────────────────────────────────────────────
	// Public — options builder (also exposed via plugin for testability)
	// ─────────────────────────────────────────────────────────────────────

	/**
	 * Translate current settings into a ConversionOptions object the converter
	 * understands. Resolution order for keys that overlap between the Image
	 * Pipeline UI and the Plugin Arguments editor:
	 *
	 *   Manual `PluginArgEntry[]` > Image Pipeline UI > wrapper defaults.
	 *
	 * The manual editor is the documented escape hatch for advanced users
	 * to override a single key without disabling the structured UI.
	 */
	buildConversionOptions(outputPath: string, inputPath?: string): ConversionOptions {
		const settings = this.plugin.settings;
		const options: ConversionOptions = {
			enablePlugins: settings.enablePlugins,
			docintelEndpoint: settings.docintelEndpoint || undefined,
			docintelCredential: settings.docintelCredential || undefined,
			llmApiKey: settings.llmApiKey || undefined,
		};

		const baseArgs: Record<string, unknown> =
			settings.pluginArgs.length > 0
				? ConversionService.pluginArgsToRecord(settings.pluginArgs)
				: {};

		if (settings.imagePipelineEnabled) {
			this.injectImagePipelineArgs(baseArgs);
		}

		if (Object.keys(baseArgs).length > 0) {
			options.pluginArgs = baseArgs;
		}

		if (settings.assetExtractionEnabled) {
			options.extractAssets = true;
			options.assetDir = resolveAssetDir(
				outputPath,
				settings.assetSubfolderTemplate,
			);
		}

		if (inputPath && (settings.enableAutoFrontmatter || settings.autoTags.trim())) {
			options.postProcess = { settings, inputPath };
		}

		return options;
	}

	// ─────────────────────────────────────────────────────────────────────
	// Internals
	// ─────────────────────────────────────────────────────────────────────

	/**
	 * Common path: build options → convert → append history → save.
	 * Returns the raw ConversionResult so callers can branch on success/fail.
	 */
	private async runAndRecord(inputPath: string, outputPath: string): Promise<ConversionResult> {
		const options = this.buildConversionOptions(outputPath, inputPath);
		const startTime = Date.now();
		const result = await this.plugin.converter.convert(inputPath, outputPath, options);
		const elapsed = Date.now() - startTime;

		addHistoryEntry(this.plugin.settings, {
			inputFile: inputPath,
			outputFile: outputPath,
			timestamp: new Date().toISOString(),
			success: result.success,
			error: result.error,
			processingTimeMs: elapsed,
			assetsExtracted: result.assetsExtracted,
		});
		await this.plugin.saveSettings();

		return result;
	}

	/**
	 * Fold the Image Pipeline section's settings into pluginArgs.
	 *
	 * Manual entries already present in `args` (from PluginArgsEditor) are NOT
	 * overwritten — that's the documented override path for advanced users.
	 *
	 * Keys mirror ConfigManager.PARAM_SPEC in python/markitdown_wrapper.py.
	 * Keep both sides in sync when adding new toggles.
	 */
	private injectImagePipelineArgs(args: Record<string, unknown>): void {
		const settings = this.plugin.settings;
		const inject = (key: string, value: unknown) => {
			if (!(key in args)) args[key] = value;
		};

		// Parse the advanced JSON config and inject every key.
		// Each key maps directly to a Python PARAM_SPEC entry.
		try {
			const cfg = JSON.parse(settings.imagePipelineAdvancedConfig || '{}') as Record<string, unknown>;
			for (const [key, value] of Object.entries(cfg)) {
				inject(key, value);
			}
		} catch {
			// Malformed JSON — Python falls back to PARAM_SPEC defaults.
		}

		// ocrLang is a top-level UI setting; overrides the JSON config value.
		inject('ocr_lang', settings.ocrLang);
	}

	/** Convert PluginArgEntry[] into a wrapper-ready Record. Static — pure. */
	private static pluginArgsToRecord(entries: PluginArgEntry[]): Record<string, unknown> {
		const record: Record<string, unknown> = Object.create(null);
		for (const entry of entries) {
			if (!entry.key.trim()) continue;
			// Reject prototype pollution keys
			if (entry.key === '__proto__' || entry.key === 'constructor' || entry.key === 'prototype') continue;
			try {
				record[entry.key] = JSON.parse(entry.value);
			} catch {
				record[entry.key] = entry.value;
			}
		}
		return record;
	}
}
