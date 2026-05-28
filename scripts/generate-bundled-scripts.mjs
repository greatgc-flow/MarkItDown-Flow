#!/usr/bin/env node
/**
 * generate-bundled-scripts.mjs
 * ──────────────────────────────────────────────────────────────────────────
 * Reads the Python source files in `python/` and emits a TypeScript module
 * `src/utils/bundledPythonScripts.generated.ts` exporting each file's contents
 * as a string constant.
 *
 * Why:
 *   When MarkItDown-Flow is installed via the Obsidian Community Plugins
 *   browser, only main.js / manifest.json / styles.css are downloaded —
 *   the python/ directory is NOT shipped. ensurePythonScripts() (in
 *   src/utils/bundledScripts.ts) writes these inlined strings to the
 *   plugin's python/ directory on first load so the wrapper can be invoked.
 *
 *   We could maintain the strings by hand, but they are ~62 KB + ~40 KB of
 *   Python code and would silently drift the moment a contributor edits the
 *   .py files without remembering to update the inline copies. This script
 *   makes the .py files the single source of truth — `npm run build`
 *   regenerates the bundle before esbuild runs.
 *
 * Escaping:
 *   We use JSON.stringify, which returns a valid double-quoted JavaScript
 *   string literal (handles backslash, double-quote, control chars,
 *   non-BMP characters, etc.). The result is directly drop-in as the
 *   right-hand side of `const X = ...`.
 *
 * Output:
 *   src/utils/bundledPythonScripts.generated.ts (gitignored)
 *
 * Run:
 *   node scripts/generate-bundled-scripts.mjs
 *   (also runs automatically via package.json prebuild/predev hooks)
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

const SOURCES = [
	{ from: 'python/markitdown_wrapper.py', exportName: 'MARKITDOWN_WRAPPER_PY' },
	{ from: 'python/image_router.py',       exportName: 'IMAGE_ROUTER_PY' },
	{ from: 'python/selftest.py',           exportName: 'SELFTEST_PY' },
	{ from: 'python/check_install.py',      exportName: 'CHECK_INSTALL_PY' },
	{ from: 'python/install_package.py',    exportName: 'INSTALL_PACKAGE_PY' },
];

const OUTPUT = 'src/utils/bundledPythonScripts.generated.ts';

async function main() {
	const entries = [];
	for (const { from, exportName } of SOURCES) {
		const abs = join(projectRoot, from);
		const content = await readFile(abs, 'utf-8');
		entries.push({ from, exportName, content, bytes: Buffer.byteLength(content, 'utf-8') });
	}

	const totalBytes = entries.reduce((s, e) => s + e.bytes, 0);

	const header = `// AUTO-GENERATED — do not edit by hand.
// Source: python/*.py
// Generator: scripts/generate-bundled-scripts.mjs
// Run \`npm run generate-bundled\` (or any npm build / dev script) to refresh.
//
// Bundled total: ${totalBytes.toLocaleString()} bytes across ${entries.length} files.

`;

	const body = entries.map(({ from, exportName, content, bytes }) =>
		`/** ${from} (${bytes.toLocaleString()} bytes) */\n` +
		`export const ${exportName} = ${JSON.stringify(content)};\n`
	).join('\n');

	const outPath = join(projectRoot, OUTPUT);
	await mkdir(dirname(outPath), { recursive: true });
	await writeFile(outPath, header + body, 'utf-8');

	console.log(`generate-bundled-scripts: wrote ${OUTPUT} (${totalBytes.toLocaleString()} bytes of Python from ${entries.length} files)`);
}

main().catch(err => {
	console.error('generate-bundled-scripts FAILED:', err);
	process.exit(1);
});
