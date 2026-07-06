/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
import * as fs from 'fs';
import { ConversionOptions, ConversionResult } from '../types/settings';
import { runPythonScript, getPythonScriptPath } from '../utils/python';
import { SUPPORTED_EXTENSIONS } from '../utils/fileTypes';
import { applyPostConversionHooks } from '../utils/postprocess';

/**
 * Strip absolute filesystem paths from a message before showing it to the
 * user. We never want to leak internal directory structure through a Notice
 * or history entry. Matches "/aaa/bbb/" style runs of POSIX-looking segments
 * — Windows paths are uncommon in Python tracebacks but `runPythonScript`
 * normalises the wrapper's reports anyway.
 */
const PATH_LIKE = /(?:\/[\w.-]+)+\//g;
const sanitisePaths = (s: string): string => s.replace(PATH_LIKE, '…/');

export class MarkitdownConverter {
	constructor(
		private pythonPath: string,
		private pluginDir: string
	) {}

	getSupportedExtensions(): string[] {
		return SUPPORTED_EXTENSIONS.map(ext => `.${ext}`);
	}

	canConvert(ext: string): boolean {
		const normalized = ext.startsWith('.') ? ext.toLowerCase() : `.${ext.toLowerCase()}`;
		return this.getSupportedExtensions().includes(normalized);
	}

	/**
	 * Convert a URL (YouTube, web page, etc.) to Markdown.
	 *
	 * Note: post-processing hooks (frontmatter / auto-tags) are honoured if
	 * present on the options, matching the file path. Earlier versions
	 * intentionally skipped them for URLs; we now treat both paths uniformly
	 * because the hooks are no-ops unless explicitly configured.
	 */
	async convertUrl(
		url: string,
		outputPath: string,
		options?: ConversionOptions,
	): Promise<ConversionResult> {
		return this.runWrapper(['--url', url], outputPath, options);
	}

	/**
	 * Convert a file to Markdown.
	 */
	async convert(
		inputPath: string,
		outputPath: string,
		options?: ConversionOptions,
	): Promise<ConversionResult> {
		return this.runWrapper(['--input', inputPath], outputPath, options);
	}

	// ─────────────────────────────────────────────────────────────────────
	// Internals
	// ─────────────────────────────────────────────────────────────────────

	/** Builds the full CLI argv for `python markitdown_wrapper.py`. */
	private buildArgs(
		sourceArgs: string[],
		outputPath: string,
		options?: ConversionOptions,
	): string[] {
		// Argument array — never string interpolation (shell: false on spawn).
		const args: string[] = [...sourceArgs, '--output', outputPath];

		if (options?.enablePlugins) {
			args.push('--enable-plugins');
		}
		if (options?.pluginArgs && Object.keys(options.pluginArgs).length > 0) {
			args.push('--plugin-args', JSON.stringify(options.pluginArgs));
		}
		if (options?.docintelEndpoint) {
			args.push('--docintel-endpoint', options.docintelEndpoint);
		}
		if (options?.extractAssets && options?.assetDir) {
			args.push('--extract-assets', '--asset-dir', options.assetDir);
		}
		return args;
	}

	/**
	 * Spawns the wrapper with the given args, then translates its exit
	 * code / stdout / stderr into a ConversionResult. Applies optional
	 * post-conversion hooks when the file was produced successfully.
	 */
	private async runWrapper(
		sourceArgs: string[],
		outputPath: string,
		options?: ConversionOptions,
	): Promise<ConversionResult> {
		const startTime = Date.now();
		const scriptPath = getPythonScriptPath('markitdown_wrapper.py', this.pluginDir);
		const args = this.buildArgs(sourceArgs, outputPath, options);

		// T7: Check for missing API keys if AI features are enabled
		if (options?.docintelEndpoint && !options?.docintelCredential?.trim()) {
			return {
				success: false,
				error: 'API key is missing: docintelCredential is required when docintelEndpoint is set',
				processingTime: Date.now() - startTime,
			};
		}

		// T5: Pass API keys via environment variables, not CLI arguments
		const env: Record<string, string> = {};
		if (options?.docintelCredential) {
			env['DOCINTEL_CREDENTIAL'] = options.docintelCredential;
		}
		if (options?.llmApiKey) {
			env['LLM_API_KEY'] = options.llmApiKey;
		}

		try {
			const result = await runPythonScript(this.pythonPath, scriptPath, args, env);

			if (result.exitCode !== 0) {
				return {
					success: false,
					error: `Conversion failed: ${MarkitdownConverter.parseError(result.stderr)}`,
					processingTime: Date.now() - startTime,
				};
			}

			if (!fs.existsSync(outputPath)) {
				return {
					success: false,
					error: 'Output file was not created',
					processingTime: Date.now() - startTime,
				};
			}

			// Optional post-processing hooks (frontmatter, tags). Hook failures
			// must NOT fail the conversion — log and proceed.
			if (options?.postProcess) {
				try {
					const raw = fs.readFileSync(outputPath, 'utf-8');
					const processed = applyPostConversionHooks(
						raw,
						options.postProcess.inputPath,
						options.postProcess.settings,
					);
					if (processed !== raw) {
						fs.writeFileSync(outputPath, processed, 'utf-8');
					}
				} catch (hookError: unknown) {
					console.warn('markitdown-flow: post-conversion hook error:', hookError);
				}
			}

			return {
				success: true,
				outputPath,
				processingTime: Date.now() - startTime,
				assetsExtracted: MarkitdownConverter.parseAssetsExtracted(result.stdout),
			};
		} catch (error: unknown) {
			const rawMessage = error instanceof Error ? error.message : String(error);
			return {
				success: false,
				error: `Conversion error: ${sanitisePaths(rawMessage)}`,
				processingTime: Date.now() - startTime,
			};
		}
	}

	/** Parse the wrapper's stderr (single JSON line) into a clean message. */
	private static parseError(stderr: string): string {
		let msg = 'Unknown error';
		try {
			const errJson = JSON.parse(stderr);
			msg = errJson?.error || msg;
		} catch {
			msg = stderr || msg;
		}
		return sanitisePaths(msg);
	}

	/** Parse the wrapper's stdout (single JSON line) for the asset count. */
	private static parseAssetsExtracted(stdout: string): number {
		try {
			const response = JSON.parse(stdout);
			return response?.assets_extracted ?? 0;
		} catch {
			// stdout may be empty or non-JSON — count as zero.
			return 0;
		}
	}
}

/* eslint-enable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Re-enable strict type checking */
