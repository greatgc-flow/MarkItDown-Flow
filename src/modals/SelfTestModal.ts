/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
import { App, Modal, Notice } from 'obsidian';
import * as path from 'path';
import * as fs from 'fs';
import type MarkitdownPlugin from '../../main';
import { runPythonScript, getPythonScriptPath } from '../utils/python';

/**
 * Image Pipeline self-test modal.
 *
 * Drives `python/selftest.py` against the bundled fixtures in
 * `tests/fixtures/images/` and renders a per-case table:
 *
 *   ┌────────────────────────┬──────────┬───────┬─────┬────────┐
 *   │ image                  │ kind     │ conf  │ esc │ time   │
 *   ├────────────────────────┼──────────┼───────┼─────┼────────┤
 *   │ case_1_doc_clean.png   │ document │ 78.4  │ no  │ 1.2 s  │
 *   │ case_2_doc_skewed.png  │ document │ 71.5  │ no  │ 1.4 s  │
 *   │ case_3_table.png       │ table    │ —     │ —   │ 0.8 s  │
 *   │ case_4_photo.png       │ photo    │  0.0  │ no  │ 0.1 s  │
 *   └────────────────────────┴──────────┴───────┴─────┴────────┘
 *
 * Above the table: dependency probe (which OCR engines + opencv + tesseract
 * binary are available) so the user can diagnose why a case fell through.
 *
 * Below the table: "Save report to vault" button — writes a .md file under
 * the output folder with the full JSON for archival / sharing.
 */
export class SelfTestModal extends Modal {
	private plugin: MarkitdownPlugin;

	constructor(app: App, plugin: MarkitdownPlugin) {
		super(app);
		this.plugin = plugin;
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.addClass('markitdown-modal');
		contentEl.createEl('h2', { text: 'Image pipeline self-test' });

		contentEl.createEl('p', {
			text:
				'Runs SmartImageRouter against four synthetic fixtures ' +
				'(clean document, skewed document, ruled table, photo) and reports ' +
				'classification + confidence + AI-escalation decision for each.',
		});

		const buttonContainer = contentEl.createDiv('markitdown-button-container');
		const runBtn = buttonContainer.createEl('button', {
			text: 'Run self-test',
			cls: 'mod-cta',
		});
		const closeBtn = buttonContainer.createEl('button', { text: 'Close' });
		closeBtn.addEventListener('click', () => this.close());

		const statusEl = contentEl.createDiv('markitdown-status-container');
		const resultEl = contentEl.createDiv();

		runBtn.addEventListener('click', async () => {
			runBtn.disabled = true;
			runBtn.setText('Running…');
			statusEl.empty();
			resultEl.empty();
			statusEl.createSpan({ text: 'Spawning Python selftest.py…' });

			try {
				const payload = await this.runSelfTest();
				statusEl.empty();
				statusEl.createSpan({
					text: `Completed in ${payload.elapsed_ms} ms across ${payload.image_count} image(s).`,
					cls: 'markitdown-status-success',
				});
				this.renderReport(resultEl, payload);
				runBtn.setText('Re-run');
				runBtn.disabled = false;
			} catch (err) {
				statusEl.empty();
				const msg = err instanceof Error ? err.message : String(err);
				statusEl.createSpan({
					text: `Self-test failed: ${msg}`,
					cls: 'markitdown-status-error',
				});
				runBtn.setText('Retry');
				runBtn.disabled = false;
			}
		});
	}

	onClose() {
		this.contentEl.empty();
	}

	// ─────────────────────────────────────────────────────────────────────
	// Internals
	// ─────────────────────────────────────────────────────────────────────

	/**
	 * Spawn python/selftest.py, parse the single stdout JSON line.
	 * Image dir defaults to tests/fixtures/images relative to the plugin dir,
	 * which works both for a developer clone (full repo) AND for a community-
	 * store install (where tests/ ships alongside python/).
	 *
	 * For community-store installs that strip tests/, we fall back to
	 * <pluginDir>/_selftest_fixtures/ — see writeFixturesIfMissing() below.
	 */
	private async runSelfTest(): Promise<SelfTestPayload> {
		const pluginDir = this.plugin.getPluginDir();
		const scriptPath = getPythonScriptPath('selftest.py', pluginDir);
		const imageDir = await this.resolveFixtureDir(pluginDir);

		const result = await runPythonScript(
			this.plugin.resolvedPythonPath,
			scriptPath,
			['--image-dir', imageDir],
		);

		if (result.exitCode !== 0) {
			let detail = 'Unknown error';
			try {
				const errJson = JSON.parse(result.stderr);
				detail = errJson.error || detail;
			} catch {
				detail = result.stderr || detail;
			}
			throw new Error(detail);
		}

		try {
			return JSON.parse(result.stdout) as SelfTestPayload;
		} catch {
			throw new Error('Self-test stdout was not valid JSON. Check the console.');
		}
	}

	/**
	 * Locate the fixtures directory. Order:
	 *   1. <pluginDir>/tests/fixtures/images  (developer clone)
	 *   2. <pluginDir>/_selftest_fixtures     (community-store install fallback)
	 * If neither exists, throws — the user can either run from a dev clone or
	 * we could later inline the fixtures via bundledScripts.ts (deferred).
	 */
	private async resolveFixtureDir(pluginDir: string): Promise<string> {
		const candidates = [
			path.join(pluginDir, 'tests', 'fixtures', 'images'),
			path.join(pluginDir, '_selftest_fixtures'),
		];
		for (const c of candidates) {
			try {
				const stat = await fs.promises.stat(c);
				if (stat.isDirectory()) return c;
			} catch {
				// fall through to the next candidate
			}
		}
		throw new Error(
			'No fixture directory found. Expected tests/fixtures/images/ in the plugin folder. ' +
			'If you installed via the Community Plugins browser, please clone the repo for now.'
		);
	}

	/**
	 * Render the JSON payload into the modal:
	 *   - dependency badges (which engines are available)
	 *   - per-case table (file, kind, confidence, escalate?, elapsed, status)
	 *   - "save report" button
	 */
	private renderReport(host: HTMLElement, payload: SelfTestPayload): void {
		host.empty();

		// Dependency badges
		const depsEl = host.createDiv('markitdown-status-container');
		depsEl.createEl('h3', { text: 'Dependencies detected' });
		const depList = depsEl.createDiv('markitdown-deps-row');
		for (const [name, present] of Object.entries(payload.deps)) {
			const span = depList.createSpan({ cls: 'markitdown-dep-pill' });
			span.setText(`${present ? '✓' : '✗'} ${name}`);
			span.addClass(present ? 'success' : 'error');
		}

		// Per-case table
		host.createEl('h3', { text: 'Cases' });
		const table = host.createEl('table', { cls: 'markitdown-selftest-table' });
		const thead = table.createEl('thead').createEl('tr');
		for (const h of ['Image', 'Kind', 'Confidence', 'Escalate?', 'Time', 'Status']) {
			thead.createEl('th', { text: h });
		}
		const tbody = table.createEl('tbody');
		for (const c of payload.cases) {
			const tr = tbody.createEl('tr');
			tr.createEl('td', { text: c.file });
			tr.createEl('td', { text: c.kind ?? '—' });
			tr.createEl('td', { text: c.confidence !== undefined && c.confidence !== null ? c.confidence.toFixed(1) : '—' });
			tr.createEl('td', { text: c.should_escalate_to_ai === undefined ? '—' : (c.should_escalate_to_ai ? 'yes' : 'no') });
			tr.createEl('td', { text: c.elapsed_ms !== undefined ? `${(c.elapsed_ms / 1000).toFixed(2)} s` : '—' });
			tr.createEl('td', { text: c.status ?? c.error ?? '—' });
		}

		// Save-report button
		const actions = host.createDiv('markitdown-button-container');
		const saveBtn = actions.createEl('button', { text: 'Save report to vault' });
		saveBtn.addEventListener('click', async () => {
			try {
				const filePath = await this.saveReport(payload);
				new Notice(`Saved self-test report: ${filePath}`);
			} catch (e) {
				const msg = e instanceof Error ? e.message : String(e);
				new Notice(`Could not save report: ${msg}`);
			}
		});
	}

	/** Write a markdown report next to the converted output folder. */
	private async saveReport(payload: SelfTestPayload): Promise<string> {
		// Use the configured output folder (vault-relative).
		const { resolveOutputFolder, getVaultBasePath } = await import('../utils/paths');
		const vaultPath = getVaultBasePath(this.app);
		if (!vaultPath) throw new Error('Could not resolve vault path');
		const outDir = resolveOutputFolder(vaultPath, this.plugin.settings.outputPath);
		const stamp = new Date().toISOString().replace(/[:.]/g, '-');
		const filePath = path.join(outDir, `markitdown-flow_selftest_${stamp}.md`);

		const lines: string[] = [];
		lines.push(`# MarkItDown Flow — Image Pipeline Self-test`);
		lines.push('');
		lines.push(`- Generated: ${new Date().toISOString()}`);
		lines.push(`- Image count: ${payload.image_count}`);
		lines.push(`- Total elapsed: ${payload.elapsed_ms} ms`);
		lines.push(`- Image dir: \`${payload.image_dir}\``);
		lines.push('');
		lines.push('## Dependencies');
		lines.push('');
		lines.push('| Component | Detected |');
		lines.push('|---|---|');
		for (const [k, v] of Object.entries(payload.deps)) {
			lines.push(`| ${k} | ${v ? '✓' : '✗'} |`);
		}
		lines.push('');
		lines.push('## Cases');
		lines.push('');
		lines.push('| File | Kind | Confidence | Escalate? | Time | Status |');
		lines.push('|---|---|---|---|---|---|');
		for (const c of payload.cases) {
			lines.push(
				`| ${c.file} ` +
				`| ${c.kind ?? '—'} ` +
				`| ${c.confidence !== undefined && c.confidence !== null ? c.confidence.toFixed(1) : '—'} ` +
				`| ${c.should_escalate_to_ai === undefined ? '—' : (c.should_escalate_to_ai ? 'yes' : 'no')} ` +
				`| ${c.elapsed_ms !== undefined ? `${(c.elapsed_ms / 1000).toFixed(2)} s` : '—'} ` +
				`| ${c.status ?? c.error ?? '—'} |`
			);
		}
		lines.push('');
		lines.push('## Raw JSON');
		lines.push('');
		lines.push('```json');
		lines.push(JSON.stringify(payload, null, 2));
		lines.push('```');

		await fs.promises.writeFile(filePath, lines.join('\n'), 'utf-8');
		return filePath;
	}
}

// ─────────────────────────────────────────────────────────────────────────
// Payload shape (mirrors python/selftest.py output)
// ─────────────────────────────────────────────────────────────────────────

interface SelfTestCase {
	file: string;
	kind?: string;
	status?: string;
	confidence?: number;
	method?: string;
	should_escalate_to_ai?: boolean;
	elapsed_ms?: number;
	error?: string;
	preprocess?: { skew_angle?: number; ops_applied?: string[]; was_upscaled?: boolean };
	breakdown?: Record<string, number>;
	engines?: Record<string, { conf: number; preview: string }>;
	text_preview?: string;
	table_summary?: {
		grid_cells: number;
		structure_confidence?: number;
		column_consistency?: number;
		unified_confidence?: number;
	};
}

interface SelfTestPayload {
	ok: boolean;
	image_count: number;
	elapsed_ms: number;
	image_dir: string;
	cfg: Record<string, unknown>;
	deps: Record<string, boolean>;
	cases: SelfTestCase[];
}

/* eslint-enable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Re-enable strict type checking */
