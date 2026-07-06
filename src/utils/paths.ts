/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
import { App, FileSystemAdapter } from 'obsidian';
import * as path from 'path';
import * as fs from 'fs';

/**
 * Get the absolute vault base path. Returns null if not a local vault.
 */
export function getVaultBasePath(app: App): string | null {
	if (app.vault.adapter instanceof FileSystemAdapter) {
		return app.vault.adapter.getBasePath();
	}
	return null;
}

/**
 * Resolve the output folder path, creating it if needed.
 */
export function resolveOutputFolder(vaultPath: string, outputSetting: string): string {
	let outputFolder: string;

	if (outputSetting) {
		outputFolder = path.resolve(vaultPath, outputSetting);
	} else {
		outputFolder = path.join(vaultPath, 'markitdown-output');
	}

	// Prevent path traversal outside the vault
	const resolvedVault = path.resolve(vaultPath);
	if (!outputFolder.startsWith(resolvedVault + path.sep) && outputFolder !== resolvedVault) {
		outputFolder = path.join(vaultPath, 'markitdown-output');
	}

	if (!fs.existsSync(outputFolder)) {
		fs.mkdirSync(outputFolder, { recursive: true });
	}

	return outputFolder;
}

/**
 * Resolve an output filename template using variables from the input path.
 * Supported variables:
 *   {filename} — original file name without extension
 *   {ext}      — original file extension (without dot)
 *   {date}     — conversion date as YYYY-MM-DD
 *   {datetime} — conversion datetime as YYYY-MM-DD_HHmmss
 *
 * Returns the resolved name without .md extension (caller appends it).
 * Characters invalid in filenames are stripped from the result.
 */
export function resolveFilenameTemplate(template: string, inputPath: string): string {
	const baseName = path.basename(inputPath, path.extname(inputPath));
	const ext = path.extname(inputPath).replace(/^\./, '');

	const now = new Date();
	const pad = (n: number) => String(n).padStart(2, '0');
	const date = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
	const datetime = `${date}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;

	let resolved = template
		.replace(/\{filename\}/g, baseName)
		.replace(/\{ext\}/g, ext)
		.replace(/\{date\}/g, date)
		.replace(/\{datetime\}/g, datetime);

	// Remove characters invalid in filenames
	resolved = resolved.replace(/[/\\:*?"<>|]/g, '');

	// Fall back to the original filename if the result is empty after sanitisation
	if (!resolved.trim()) {
		resolved = baseName;
	}

	return resolved;
}

/**
 * Compute the asset extraction directory for a given output markdown file.
 * Applies the template (e.g., "{filename}-assets") to generate the folder name.
 * "Assets" covers any inline-extracted file (images, embedded media, etc.)
 * physically written out by the wrapper's AssetProcessor.
 */
export function resolveAssetDir(outputMdPath: string, template: string): string {
	const dir = path.dirname(outputMdPath);
	const baseName = path.basename(outputMdPath, '.md');
	// Strip path separators from template to prevent path traversal
	const sanitizedTemplate = template.replace(/[/\\]/g, '-');
	const folderName = sanitizedTemplate.replace('{filename}', baseName);
	return path.join(dir, folderName);
}

/**
 * Given an absolute path and the vault base path, return the vault-relative path.
 * Normalizes separators to forward slashes for Obsidian compatibility.
 */
export function toVaultRelative(absolutePath: string, vaultPath: string): string {
	return path.relative(vaultPath, absolutePath).replace(/\\/g, '/');
}

/**
 * Compute the full output .md path for a given input file, optionally mirroring
 * the source directory hierarchy under outputFolder.
 *
 * When inputBasePath is provided and inputPath is a descendant of it, the
 * relative subdirectory is appended to outputFolder so the source tree is
 * preserved.  The subdirectory is created automatically.
 *
 * Example:
 *   inputBasePath  = /home/user/docs
 *   inputPath      = /home/user/docs/reports/q1/report.pdf
 *   outputFolder   = /vault/markitdown-output
 *   → output       = /vault/markitdown-output/reports/q1/report.md
 *
 * Without inputBasePath (or when inputPath is not under it):
 *   → output       = /vault/markitdown-output/report.md
 */
export function resolveStructuredOutputPath(
	inputPath: string,
	inputBasePath: string | null | undefined,
	outputFolder: string,
	filenameTemplate: string,
): string {
	const resolvedName = resolveFilenameTemplate(filenameTemplate, inputPath);

	if (inputBasePath) {
		const normalizedInput = path.resolve(inputPath);
		const normalizedBase  = path.resolve(inputBasePath);
		if (normalizedInput.startsWith(normalizedBase + path.sep)) {
			const relative   = path.relative(normalizedBase, normalizedInput);
			const relDir     = path.dirname(relative);
			const subFolder  = (relDir && relDir !== '.') ? path.join(outputFolder, relDir) : outputFolder;
			if (!fs.existsSync(subFolder)) {
				fs.mkdirSync(subFolder, { recursive: true });
			}
			return path.join(subFolder, `${resolvedName}.md`);
		}
	}

	return path.join(outputFolder, `${resolvedName}.md`);
}
