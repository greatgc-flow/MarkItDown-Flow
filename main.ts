/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
import { Notice, Plugin, TFile, MarkdownView, MarkdownFileInfo, Editor } from 'obsidian';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import {
	MarkitdownSettings,
	DEFAULT_SETTINGS,
	ConversionOptions,
	ConversionResult,
	DependencyStatus,
	TriedPath,
} from './src/types/settings';
import { MarkitdownConverter } from './src/converter/MarkitdownConverter';
import { ConversionService } from './src/services/ConversionService';
import { checkDependencies, installPackage } from './src/utils/python';
import { getVaultBasePath, resolveOutputFolder, toVaultRelative } from './src/utils/paths';
import { isConvertible } from './src/utils/fileTypes';
import { ensurePythonScripts } from './src/utils/bundledScripts';
import { SettingsTab } from './src/settings/SettingsTab';
import { FileConvertModal } from './src/modals/FileConvertModal';
import { FolderConvertModal } from './src/modals/FolderConvertModal';
import { UrlConvertModal } from './src/modals/UrlConvertModal';
import { HistoryModal } from './src/modals/HistoryModal';
import { SetupModal } from './src/modals/SetupModal';
import { SelfTestModal } from './src/modals/SelfTestModal';

/**
 * Plugin entry. Owns the lifecycle (load/unload, settings persistence,
 * dependency discovery, command + UI registration) and delegates the
 * conversion pipeline itself to ConversionService.
 *
 * Public surface is preserved for backwards compatibility with existing
 * callsites in the modals (FileConvertModal etc.): convertVaultFile,
 * convertExternalFile, buildConversionOptions, postConversionNotice,
 * openConvertedFile are all thin wrappers around the service.
 */
export default class MarkitdownPlugin extends Plugin {
	settings: MarkitdownSettings = DEFAULT_SETTINGS;
	dependencyStatus: DependencyStatus = {
		pythonInstalled: false,
		pythonVersion: null,
		markitdownInstalled: false,
		markitdownVersion: null,
	};
	converter: MarkitdownConverter = new MarkitdownConverter('python', '.');
	pythonDiscoveryLog: TriedPath[] = [];
	conversionService!: ConversionService;

	private _resolvedPythonPath = 'python';

	/** The Python path actually used after discovery/fallback resolution. */
	get resolvedPythonPath(): string {
		return this._resolvedPythonPath;
	}

	async onload() {
		await this.loadSettings();

		const pluginDir = this.getPluginDir();

		// Ensure bundled Python scripts exist on disk (community plugin installs
		// only include main.js, manifest.json, and styles.css — no python/ dir)
		await ensurePythonScripts(pluginDir);

		const depCheck = await checkDependencies(this.settings.pythonPath, pluginDir);
		this.dependencyStatus = depCheck.status;
		this.pythonDiscoveryLog = depCheck.triedPaths;
		// Use the resolved python path (handles python→python3 fallback)
		this._resolvedPythonPath = depCheck.resolvedPythonPath;
		this.converter = new MarkitdownConverter(this.resolvedPythonPath, pluginDir);
		this.conversionService = new ConversionService(this);

		// Ribbon icon
		this.addRibbonIcon('file-text', 'Convert to Markdown', () => {
			this.openConvertModal();
		});

		// Commands
		this.addCommand({
			id: 'convert-file',
			name: 'Convert file to Markdown',
			callback: () => this.openConvertModal(),
		});

		this.addCommand({
			id: 'convert-folder',
			name: 'Convert folder to Markdown',
			callback: () => this.openFolderModal(),
		});

		this.addCommand({
			id: 'convert-url',
			name: 'Convert URL to Markdown',
			callback: () => this.openUrlModal(),
		});

		this.addCommand({
			id: 'view-conversion-history',
			name: 'View conversion history',
			callback: () => new HistoryModal(this.app, this).open(),
		});

		this.addCommand({
			id: 'open-log-folder',
			name: 'Open log folder',
			callback: () => this.openLogFolder(),
		});

		this.addCommand({
			id: 'run-image-pipeline-selftest',
			name: 'Run image pipeline self-test',
			callback: () => this.openSelfTestModal(),
		});

		// Context menu
		if (this.settings.enableContextMenu) {
			this.registerFileMenu();
		}

		// Drag-and-drop conversion
		if (this.settings.enableDragDrop) {
			this.registerDropHandler();
		}

		// Settings tab
		this.addSettingTab(new SettingsTab(this.app, this));
	}

	onunload() {
		// registerEvent handles cleanup automatically
	}

	// ─────────────────────────────────────────────────────────────────────
	// Modal openers (gated on dependency presence)
	// ─────────────────────────────────────────────────────────────────────

	/** Open file conversion modal, or setup modal if not installed. */
	private openConvertModal() {
		if (!this.dependencyStatus.markitdownInstalled) {
			new SetupModal(this.app, this).open();
			return;
		}
		new FileConvertModal(this.app, this).open();
	}

	/** Open folder conversion modal, or setup modal if not installed. */
	private openFolderModal() {
		if (!this.dependencyStatus.markitdownInstalled) {
			new SetupModal(this.app, this).open();
			return;
		}
		new FolderConvertModal(this.app, this).open();
	}

	/** Open URL conversion modal, or setup modal if not installed. */
	private openUrlModal() {
		if (!this.dependencyStatus.markitdownInstalled) {
			new SetupModal(this.app, this).open();
			return;
		}
		new UrlConvertModal(this.app, this).open();
	}

	/**
	 * Open the SmartImageRouter self-test modal. Public so that
	 * SettingsTab's "Run self-test" button can call it without re-importing.
	 */
	openSelfTestModal(): void {
		new SelfTestModal(this.app, this).open();
	}

	// ─────────────────────────────────────────────────────────────────────
	// Event-source registrations (right-click menu, drag-and-drop)
	// ─────────────────────────────────────────────────────────────────────

	/** Register right-click context menu on supported file types. */
	private registerFileMenu() {
		this.registerEvent(
			this.app.workspace.on('file-menu', (menu, file) => {
				if (!(file instanceof TFile)) return;
				if (!isConvertible(file.extension)) return;

				menu.addItem((item) => {
					item.setTitle('Convert to Markdown')
						.setIcon('file-text')
						.onClick(() => this.convertVaultFile(file));
				});
			})
		);
	}

	/** Register drag-and-drop handler for converting dropped files. */
	private registerDropHandler() {
		this.registerEvent(
			this.app.workspace.on('editor-drop', (evt: DragEvent, editor: Editor, _info: MarkdownView | MarkdownFileInfo) => {
				if (evt.defaultPrevented) return;
				
				const files = evt.dataTransfer?.files;
				if (!files || files.length === 0) return;

				const convertibleFiles: File[] = [];
				for (let i = 0; i < files.length; i++) {
					const file = files[i];
					const ext = path.extname(file.name).toLowerCase().replace(/^\./, '');
					if (isConvertible(ext)) {
						convertibleFiles.push(file);
					}
				}
				if (convertibleFiles.length === 0) return;

				evt.preventDefault();
				for (const file of convertibleFiles) {
					this.handleDroppedFile(file, editor).catch((error) => {
						const msg = error instanceof Error ? error.message : String(error);
						new Notice(`Drop conversion error: ${msg}`);
					});
				}
			})
		);
	}

	/** Handle a single dropped file: write to temp, convert, insert link, clean up. */
	private async handleDroppedFile(file: File, editor: Editor): Promise<void> {
		const vaultPath = getVaultBasePath(this.app);
		if (!vaultPath) {
			new Notice('Could not determine vault path. This plugin requires a local vault.');
			return;
		}

		if (!this.dependencyStatus.markitdownInstalled) {
			new SetupModal(this.app, this).open();
			return;
		}

		new Notice(`Converting dropped file: ${file.name}...`);

		const outputFolder = resolveOutputFolder(vaultPath, this.settings.outputPath);
		const baseName = path.basename(file.name, path.extname(file.name));
		const outputPath = path.join(outputFolder, `${baseName}.md`);

		// DOM File → temp file on disk
		const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
		const tempFilePath = path.join(outputFolder, `tmp_${Date.now()}_${safeName}`);
		const buffer = await file.arrayBuffer();
		await fs.promises.writeFile(tempFilePath, Buffer.from(buffer));

		try {
			const result = await this.convertExternalFile(tempFilePath, outputPath);
			if (result.success) {
				const relativePath = toVaultRelative(outputPath, vaultPath);
				const linkText = `[[${relativePath.replace(/\.md$/, '')}]]`;
				const cursor = editor.getCursor();
				editor.replaceRange(linkText, cursor);
			}
			this.postConversionNotice(`Converted ${file.name}`, result);
		} finally {
			await fs.promises.unlink(tempFilePath).catch(() => {});
		}
	}

	// ─────────────────────────────────────────────────────────────────────
	// Conversion — thin wrappers around ConversionService. Kept on the
	// Plugin for backwards compatibility with existing modal callsites.
	// ─────────────────────────────────────────────────────────────────────

	/** Convert a file that already exists in the vault (context menu). */
	async convertVaultFile(file: TFile): Promise<void> {
		return this.conversionService.convertVaultFile(file);
	}

	/** Convert an external file (file-picker modal / drag-drop). */
	async convertExternalFile(inputPath: string, outputPath: string): Promise<ConversionResult> {
		return this.conversionService.convertExternalFile(inputPath, outputPath);
	}

	/** Build ConversionOptions for the current settings (testability hook). */
	buildConversionOptions(outputPath: string, inputPath?: string): ConversionOptions {
		return this.conversionService.buildConversionOptions(outputPath, inputPath);
	}

	/** Show a Notice summarising a conversion outcome. */
	postConversionNotice(label: string, result: ConversionResult): void {
		this.conversionService.postConversionNotice(label, result);
	}

	/** Open a converted file in the workspace. */
	async openConvertedFile(outputPath: string, vaultPath: string): Promise<void> {
		return this.conversionService.openConvertedFile(outputPath, vaultPath);
	}

	// ─────────────────────────────────────────────────────────────────────
	// Plugin lifecycle helpers (dependency management, paths, log folder)
	// ─────────────────────────────────────────────────────────────────────

	/** Get the absolute path to the plugin directory. */
	getPluginDir(): string {
		const vaultPath = getVaultBasePath(this.app);
		if (vaultPath && this.manifest.dir) {
			return path.join(vaultPath, this.manifest.dir);
		}
		// Non-local vaults (e.g., Obsidian Sync without local adapter) cannot resolve plugin dir
		console.warn('markitdown-flow: Could not resolve vault base path. Plugin features may not work correctly.');
		return path.resolve(this.manifest.dir ?? '.');
	}

	/**
	 * Open the engine's log folder in the OS file manager.
	 *
	 * The Python wrapper writes per-day logs to `~/omnidata_logs/engine_YYYYMMDD.log`
	 * (see LoggerSetup in python/markitdown_wrapper.py). We create the directory
	 * up-front so the file manager has something to open even before the first
	 * conversion has been run.
	 *
	 * Uses Electron's `shell.openPath` for cross-platform open. Falls back to a
	 * Notice if Electron is unavailable (shouldn't happen on supported desktop
	 * builds; the plugin is documented as desktop-only).
	 */
	async openLogFolder(): Promise<void> {
		const logsDir = path.join(os.homedir(), 'omnidata_logs');
		try {
			await fs.promises.mkdir(logsDir, { recursive: true });
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			new Notice(`Could not create log folder: ${msg}`);
			return;
		}
		try {
			// eslint-disable-next-line @typescript-eslint/no-var-requires, @typescript-eslint/no-require-imports -- Requires electron module dynamically for desktop environments
			const { shell } = require('electron');
			const failureReason = await shell.openPath(logsDir);
			// Electron returns "" on success, an error string on failure.
			if (failureReason) {
				new Notice(`Could not open log folder: ${failureReason}`);
			}
		} catch (err) {
			const msg = err instanceof Error ? err.message : String(err);
			new Notice(`Log folder is at ${logsDir} (failed to launch file manager: ${msg})`);
		}
	}

	/** Install markitdown package using the resolved Python path. */
	async installMarkitdown(onProgress?: (line: string) => void): Promise<boolean> {
		const pluginDir = this.getPluginDir();
		const success = await installPackage(
			this._resolvedPythonPath,
			pluginDir,
			'markitdown[all]',
			onProgress,
		);
		if (success) {
			this.dependencyStatus.markitdownInstalled = true;
		}
		return success;
	}

	/** Refresh dependency status and resolved Python path. */
	async refreshDependencies(): Promise<void> {
		const pluginDir = this.getPluginDir();
		const depCheck = await checkDependencies(this.settings.pythonPath, pluginDir);
		this.dependencyStatus = depCheck.status;
		this.pythonDiscoveryLog = depCheck.triedPaths;
		this._resolvedPythonPath = depCheck.resolvedPythonPath;
		this.converter = new MarkitdownConverter(this.resolvedPythonPath, pluginDir);
		this.conversionService = new ConversionService(this);
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}
}

/* eslint-enable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Re-enable strict type checking */
