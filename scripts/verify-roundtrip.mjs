#!/usr/bin/env node
/**
 * verify-roundtrip.mjs
 * ─────────────────────────────────────────────────────────────────────────
 * One-shot verification that the generated TS bundle round-trips correctly:
 *
 *   python/*.py
 *     → scripts/generate-bundled-scripts.mjs
 *       → src/utils/bundledPythonScripts.generated.ts  (TS string literals)
 *         → at runtime, ensurePythonScripts() writes the string back to disk
 *           → that disk file MUST be byte-identical to the original .py
 *
 * If any step corrupts the content (escape bug, encoding mismatch, BOM, etc.)
 * this script catches it. Run after generate-bundled-scripts.mjs.
 *
 * Exits non-zero on any mismatch.
 */

import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');

const PAIRS = [
	{ orig: 'python/markitdown_wrapper.py', exportName: 'MARKITDOWN_WRAPPER_PY' },
	{ orig: 'python/image_router.py',       exportName: 'IMAGE_ROUTER_PY' },
	{ orig: 'python/check_install.py',      exportName: 'CHECK_INSTALL_PY' },
	{ orig: 'python/install_package.py',    exportName: 'INSTALL_PACKAGE_PY' },
];

// We parse the generated TS file by reading it as text and pulling out the
// string literal that follows each `export const X = `. Since the generator
// uses JSON.stringify, every value is a JSON string we can JSON.parse back.
async function loadGeneratedExports() {
	const tsPath = join(projectRoot, 'src/utils/bundledPythonScripts.generated.ts');
	const src = await readFile(tsPath, 'utf-8');
	const out = {};
	const re = /export const (\w+)\s*=\s*("(?:[^"\\]|\\.)*")\s*;/g;
	let m;
	while ((m = re.exec(src)) !== null) {
		out[m[1]] = JSON.parse(m[2]);
	}
	return out;
}

async function main() {
	console.log('verify-roundtrip: loading generated exports…');
	const exports_ = await loadGeneratedExports();

	const tmpDir = join(projectRoot, '.verify-roundtrip-tmp');
	if (existsSync(tmpDir)) await rm(tmpDir, { recursive: true, force: true });
	await mkdir(tmpDir, { recursive: true });

	let failures = 0;
	for (const { orig, exportName } of PAIRS) {
		const origAbs = join(projectRoot, orig);
		const origBuf = await readFile(origAbs);
		const fromBundle = exports_[exportName];
		if (fromBundle === undefined) {
			console.error(`  MISS  ${exportName}: not found in generated file`);
			failures++;
			continue;
		}

		// Write the bundled string back to disk exactly as ensurePythonScripts does.
		const replayPath = join(tmpDir, orig.split('/').pop());
		await writeFile(replayPath, fromBundle, 'utf-8');
		const replayBuf = await readFile(replayPath);

		const sizeMatch = origBuf.length === replayBuf.length;
		const contentMatch = origBuf.equals(replayBuf);

		if (sizeMatch && contentMatch) {
			console.log(`  OK    ${orig} ↔ ${exportName}  (${origBuf.length} bytes, byte-identical)`);
		} else {
			console.error(`  FAIL  ${orig}: size match=${sizeMatch}, content match=${contentMatch}`);
			console.error(`        orig=${origBuf.length}b, replay=${replayBuf.length}b`);
			failures++;
		}
	}

	// Also confirm the replayed wrapper.py is still valid Python — catches
	// any escape bug that produced a syntactically wrong file even if the
	// bytes happened to round-trip (defensive belt-and-suspenders).
	console.log('verify-roundtrip: py_compile on replayed wrapper + router…');
	for (const f of ['markitdown_wrapper.py', 'image_router.py']) {
		const r = spawnSync('python', ['-m', 'py_compile', join(tmpDir, f)], { encoding: 'utf-8' });
		if (r.status === 0) {
			console.log(`  OK    py_compile ${f}`);
		} else {
			console.error(`  FAIL  py_compile ${f}: exit=${r.status}\n${r.stderr}`);
			failures++;
		}
	}

	await rm(tmpDir, { recursive: true, force: true });

	if (failures > 0) {
		console.error(`verify-roundtrip FAILED: ${failures} mismatch(es)`);
		process.exit(1);
	}
	console.log('verify-roundtrip: all checks passed.');
}

main().catch(err => {
	console.error('verify-roundtrip CRASHED:', err);
	process.exit(2);
});
