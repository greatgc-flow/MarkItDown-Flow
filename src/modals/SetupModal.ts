import { App, Modal, Notice, Setting, normalizePath } from 'obsidian';
import type MarkitdownPlugin from '../../main';
import * as path from 'path';
import { spawn } from 'child_process';
import * as fs from 'fs';

export class SetupModal extends Modal {
	private plugin: MarkitdownPlugin;
	private logEl!: HTMLElement;

	constructor(app: App, plugin: MarkitdownPlugin) {
		super(app);
		this.plugin = plugin;
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.addClass('markitdown-modal');
		contentEl.empty();
		contentEl.createEl('h2', { text: 'Markitdown Auto-Setup Wizard' });

		contentEl.createEl('p', {
			text: 'This wizard will automatically set up a Python virtual environment (Venv) and install all required packages (MarkItDown, OCR engines, etc.) so you do not have to touch the terminal.',
			cls: 'setting-item-description',
		});

		// Suggest default path if empty
		const adapter = this.app.vault.adapter as any;
		const basePath = adapter.basePath || '';
		const defaultEnvPath = path.join(basePath, '.obsidian', 'plugins', 'markitdown-flow', 'env');

		if (!this.plugin.settings.envRootPath) {
			this.plugin.settings.envRootPath = defaultEnvPath;
			this.plugin.saveSettings().catch(console.error);
		}

		new Setting(contentEl)
			.setName('Environment Root Folder')
			.setDesc('Where to install the Python virtual environment.')
			.addText(text => text
				.setValue(this.plugin.settings.envRootPath)
				.onChange(async (value) => {
					this.plugin.settings.envRootPath = value;
					await this.plugin.saveSettings();
				}));

		const buttonContainer = contentEl.createDiv('markitdown-button-container');
		buttonContainer.style.marginTop = '20px';

		const cancelBtn = buttonContainer.createEl('button', { text: 'Cancel' });
		cancelBtn.addEventListener('click', () => this.close());

		const installBtn = buttonContainer.createEl('button', {
			text: '🚀 Start Installation',
			cls: 'mod-cta',
		});

		this.logEl = contentEl.createDiv('markitdown-setup-log');
		this.logEl.setCssStyles({
			display: 'none',
			marginTop: '15px',
			padding: '10px',
			background: 'var(--background-secondary)',
			border: '1px solid var(--background-modifier-border)',
			borderRadius: '4px',
			fontFamily: 'monospace',
			fontSize: '12px',
			maxHeight: '300px',
			overflowY: 'auto',
			whiteSpace: 'pre-wrap',
		});

		installBtn.addEventListener('click', async () => {
			if (!this.plugin.settings.envRootPath) {
				new Notice('Please specify an environment root folder.');
				return;
			}
			
			installBtn.disabled = true;
			installBtn.setText('Installing...');
			cancelBtn.disabled = true;
			this.logEl.setCssStyles({ display: 'block' });
			this.logEl.empty();

			try {
				await this.runAutoSetup(this.plugin.settings.envRootPath);
				
				// Update python path in settings to the new venv
				const isWin = process.platform === 'win32';
				const newPythonPath = path.join(
					this.plugin.settings.envRootPath,
					isWin ? 'Scripts' : 'bin',
					isWin ? 'python.exe' : 'python'
				);
				this.plugin.settings.pythonPath = newPythonPath;
				await this.plugin.saveSettings();
				
				this.log('✅ Setup completed successfully!');
				this.log(`✅ Configured Python Path: ${newPythonPath}`);
				
				new Notice('Markitdown setup completed successfully!');
				await this.plugin.refreshDependencies();
				
				const closeBtn = buttonContainer.createEl('button', { text: 'Close', cls: 'mod-cta' });
				closeBtn.addEventListener('click', () => this.close());
				installBtn.style.display = 'none';
				cancelBtn.style.display = 'none';
			} catch (error) {
				const msg = error instanceof Error ? error.message : String(error);
				this.log(`❌ Error: ${msg}`);
				installBtn.disabled = false;
				installBtn.setText('Try again');
				cancelBtn.disabled = false;
			}
		});
	}

	private log(message: string) {
		const lineEl = this.logEl.createEl('div', { text: message });
		lineEl.scrollIntoView();
	}

	private async runAutoSetup(envPath: string): Promise<void> {
		const isWin = process.platform === 'win32';
		
		this.log(`Starting auto-setup in: ${envPath}`);
		this.log('Checking for Astral uv (Ultra-fast Python package manager)...');
		
		// 1. Install `uv` if not present, then use it to create venv and install packages.
		// uv is a standalone binary that can automatically download python and create venvs.
		
		const uvCmd = isWin ? 'uv.exe' : 'uv';
		let hasUv = await this.checkCommand(uvCmd);
		
		if (!hasUv) {
			this.log('uv not found. Downloading uv...');
			if (isWin) {
				await this.runShell('powershell', ['-ExecutionPolicy', 'ByPass', '-c', 'irm https://astral.sh/uv/install.ps1 | iex']);
			} else {
				await this.runShell('sh', ['-c', 'curl -LsSf https://astral.sh/uv/install.sh | sh']);
			}
			// Update PATH so we can use uv immediately
			const uvPath = isWin ? path.join(process.env.USERPROFILE || '', '.local', 'bin') : path.join(process.env.HOME || '', '.local', 'bin');
			process.env.PATH = `${uvPath}${path.delimiter}${process.env.PATH}`;
			
			hasUv = await this.checkCommand(uvCmd);
			if (!hasUv) {
				// Fallback to python -m venv if uv installation failed for some reason
				this.log('uv installation failed or not in PATH. Falling back to system python...');
				await this.runFallbackSetup(envPath);
				return;
			}
		}
		
		this.log('✅ uv is ready.');
		
		// 2. Use uv to create a venv (it will download python 3.12 automatically if missing!)
		this.log('Creating virtual environment and fetching Python 3.12...');
		await this.runShell(uvCmd, ['venv', envPath, '--python', '3.12']);
		
		// 3. Use uv pip to install all requirements
		this.log('Installing MarkItDown and optional dependencies (OCR, PDF)...');
		const pythonExe = path.join(envPath, isWin ? 'Scripts' : 'bin', isWin ? 'python.exe' : 'python');
		
		await this.runShell(uvCmd, [
			'pip', 'install',
			'--python', pythonExe,
			'markitdown[all]', 'easyocr', 'pdfplumber', 'pdfminer.six', 'opencv-python'
		]);
		
		this.log('✅ Packages installed successfully.');
	}
	
	private async runFallbackSetup(envPath: string): Promise<void> {
		const isWin = process.platform === 'win32';
		this.log('Creating virtual environment using system python...');
		await this.runShell(isWin ? 'python' : 'python3', ['-m', 'venv', envPath]);
		
		const pipExe = path.join(envPath, isWin ? 'Scripts' : 'bin', isWin ? 'pip.exe' : 'pip');
		this.log('Upgrading pip...');
		await this.runShell(pipExe, ['install', '--upgrade', 'pip']);
		
		this.log('Installing MarkItDown and dependencies...');
		await this.runShell(pipExe, ['install', 'markitdown[all]', 'easyocr', 'pdfplumber', 'pdfminer.six', 'opencv-python']);
	}

	private runShell(command: string, args: string[]): Promise<void> {
		return new Promise((resolve, reject) => {
			const child = spawn(command, args, { shell: true });
			
			child.stdout.on('data', (data) => {
				const text = data.toString().trim();
				if (text) this.log(text);
			});
			
			child.stderr.on('data', (data) => {
				const text = data.toString().trim();
				if (text) this.log(`[STDERR] ${text}`);
			});
			
			child.on('close', (code) => {
				if (code === 0) resolve();
				else reject(new Error(`Command ${command} exited with code ${code}`));
			});
			
			child.on('error', (err) => {
				reject(err);
			});
		});
	}
	
	private checkCommand(command: string): Promise<boolean> {
		return new Promise((resolve) => {
			const isWin = process.platform === 'win32';
			const testCmd = isWin ? 'where' : 'which';
			const child = spawn(testCmd, [command], { shell: true });
			child.on('close', (code) => {
				resolve(code === 0);
			});
			child.on('error', () => {
				resolve(false);
			});
		});
	}

	onClose() {
		this.contentEl.empty();
	}
}
