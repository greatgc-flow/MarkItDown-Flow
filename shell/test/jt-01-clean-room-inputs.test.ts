/**
 * JT-01 / REQ-SHL-01 (machine check only): build inputs and imports of the
 * clean-room shell reject the retired v1 inputs (root `src/`, `main.ts`,
 * `styles.css`, v1 tests, bundled Python wrappers). This test asserts nothing
 * about authorship; the R15 attestation is a separate manual gate (MAN-01) and
 * is deliberately not checked here.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { req, REPO_ROOT } from './req';

const R = req('REQ-SHL-01');

const SHELL = path.join(REPO_ROOT, 'shell');

function tsFiles(dir: string): string[] {
  return fs
    .readdirSync(dir, { recursive: true, encoding: 'utf8' })
    .filter((f) => f.endsWith('.ts') && !f.includes('node_modules'))
    .map((f) => path.join(dir, f));
}

function imports(text: string): string[] {
  const out: string[] = [];
  const re = /(?:from\s+|import\s*\(|require\s*\(|jest\.mock\s*\()\s*['"]([^'"]+)['"]/g;
  for (const m of text.matchAll(re)) out.push(m[1]);
  return out;
}

const RETIRED_ROOT_INPUTS = ['src', 'main.ts', 'styles.css', 'esbuild.config.mjs', 'jest.config.js', 'tsconfig.json', 'package.json', 'plugin', 'python', 'scripts', 'version-bump.mjs', 'manifest-beta.json'];

it(R('JT-01 the retired v1 shell inputs are absent from the repository root'), () => {
  for (const name of RETIRED_ROOT_INPUTS) {
    expect({ name, present: fs.existsSync(path.join(REPO_ROOT, name)) }).toEqual({ name, present: false });
  }
  // The build config is the step-10 esbuild configuration under shell/, not the former root one.
  expect(fs.existsSync(path.join(SHELL, 'esbuild.config.mjs'))).toBe(true);
});

it(R('JT-01 the shell build config bundles shell/src/main.ts only and references no path outside shell/'), () => {
  const configPath = path.join(SHELL, 'esbuild.config.mjs');
  expect(fs.existsSync(configPath)).toBe(true);
  const text = fs.readFileSync(configPath, 'utf8');
  expect(text).toMatch(/src\/main\.ts/);
  expect(text).not.toMatch(/\.\.\//);
  for (const retired of ['bundledPythonScripts', 'generate-bundled-scripts', 'plugin/', 'python/', 'scripts/', 'omnidata', 'peerhub']) {
    expect({ retired, found: text.includes(retired) }).toEqual({ retired, found: false });
  }
  const pkg = JSON.parse(fs.readFileSync(path.join(SHELL, 'package.json'), 'utf8')) as { scripts: Record<string, string> };
  expect(pkg.scripts.build).toMatch(/esbuild/);
  expect(pkg.scripts.build).not.toContain('process.exit(1)');
  expect(fs.existsSync(path.join(SHELL, 'styles.css'))).toBe(true);
});

it(R('JT-01 every shell import resolves inside shell/ or to obsidian, node builtins or pinned dev tooling'), () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(SHELL, 'package.json'), 'utf8')) as { devDependencies: Record<string, string>; dependencies?: Record<string, string> };
  expect(pkg.dependencies ?? {}).toEqual({});
  const bare = new Set(['obsidian', 'electron', ...Object.keys(pkg.devDependencies)]);
  // This file names the retired inputs it scans for, so it is excluded from its own scan.
  // The build config is a build input too and must exist for the scan to be complete.
  const buildConfig = path.join(SHELL, 'esbuild.config.mjs');
  expect(fs.existsSync(buildConfig)).toBe(true);
  const files = [...tsFiles(path.join(SHELL, 'src')), ...tsFiles(path.join(SHELL, 'test')), buildConfig].filter((f) => path.resolve(f) !== path.resolve(__filename));
  expect(files.length).toBeGreaterThan(10);
  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8');
    for (const spec of imports(text)) {
      if (spec.startsWith('node:')) continue;
      if (spec.startsWith('.')) {
        const resolved = path.resolve(path.dirname(file), spec);
        const inside = resolved.startsWith(SHELL + path.sep);
        expect({ file, spec, inside }).toEqual({ file, spec, inside: true });
        continue;
      }
      const root = spec.startsWith('@') ? spec.split('/').slice(0, 2).join('/') : spec.split('/')[0];
      expect({ file, spec, known: bare.has(root) }).toEqual({ file, spec, known: true });
    }
    // Relative imports that escape shell/ are caught above; these are v1-only generated/runtime artifacts.
    for (const retired of ['bundledPythonScripts', 'generate-bundled-scripts', 'omnidata_logs/']) {
      expect({ file, retired, found: text.includes(retired) }).toEqual({ file, retired, found: false });
    }
  }
});

it(R('JT-01 no shell source file re-exports or copies the retired v1 shell or its styles'), () => {
  const files = tsFiles(path.join(SHELL, 'src'));
  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8');
    // Upstream/v1 identifiers only; product words the migration notices must mention (e.g. Azure DocIntel) are not markers.
    for (const marker of ['obsidian-markitdown', 'ethanolivertroy', 'markitdown-plugin', 'MarkitdownPlugin', 'bundledPythonScripts', 'omnidata_logs/']) {
      expect({ file, marker, found: text.includes(marker) }).toEqual({ file, marker, found: false });
    }
  }
  const stylesPath = path.join(SHELL, 'styles.css');
  expect(fs.existsSync(stylesPath)).toBe(true);
  const styles = fs.readFileSync(stylesPath, 'utf8');
  expect(styles.length).toBeGreaterThan(0);
  expect(styles).not.toContain('markitdown-plugin');
});
