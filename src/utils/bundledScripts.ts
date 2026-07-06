/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises -- Node built-ins are untyped in the reviewer environment, and void-returning callbacks correctly handle async functions internally. */
/**
 * Bundled Python scripts as string constants.
 *
 * These are written to disk on first load so the plugin works when installed
 * via the Obsidian Community Plugins browser (which only downloads main.js,
 * manifest.json, and styles.css — the python/ directory is NOT shipped).
 *
 * The string contents themselves are NOT in this file — they are loaded from
 * `bundledPythonScripts.generated.ts`, which is auto-generated from the
 * canonical .py sources in python/ by scripts/generate-bundled-scripts.mjs.
 * The generator runs automatically before `npm run build` / `npm run dev` via
 * the prebuild / predev hooks in package.json.
 *
 * If the generated file is missing (fresh checkout, never ran a build), the
 * import below will fail with a clear TypeScript error — run
 * `npm run generate-bundled` to fix.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
	MARKITDOWN_WRAPPER_PY,
	IMAGE_ROUTER_PY,
	SELFTEST_PY,
	CHECK_INSTALL_PY,
	INSTALL_PACKAGE_PY,
} from './bundledPythonScripts.generated';

const SCRIPTS: Record<string, string> = {
	'check_install.py':       CHECK_INSTALL_PY,
	'install_package.py':     INSTALL_PACKAGE_PY,
	'markitdown_wrapper.py':  MARKITDOWN_WRAPPER_PY,
	'image_router.py':        IMAGE_ROUTER_PY,
	'selftest.py':            SELFTEST_PY,
};

/**
 * Ensure all bundled Python scripts exist in the plugin's python/ directory.
 *
 * Behaviour: writes only files that are MISSING. Existing files are left
 * untouched — this lets developers (and users running off a local clone)
 * edit `python/markitdown_wrapper.py` directly and have those changes take
 * effect without being clobbered on every reload.
 */
export async function ensurePythonScripts(pluginDir: string): Promise<void> {
	const pythonDir = path.join(pluginDir, 'python');
	try {
		await fs.promises.mkdir(pythonDir, { recursive: true });
	} catch {
		// Directory may already exist
	}

	for (const [filename, content] of Object.entries(SCRIPTS)) {
		const filePath = path.join(pythonDir, filename);
		try {
			await fs.promises.access(filePath);
			// File exists — skip (preserves local edits)
		} catch {
			await fs.promises.writeFile(filePath, content, 'utf-8');
		}
	}
}

/* eslint-enable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-return, @typescript-eslint/no-misused-promises */
