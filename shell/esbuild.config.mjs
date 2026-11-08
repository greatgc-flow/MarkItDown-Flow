// Build input for the clean-room shell (20_SHELL.md REQ-SHL-01; 25_PACKAGING.md REQ-PKG-09/13/14).
// Bundles shell/src/main.ts into the repository-root main.js (the community-install asset next to
// manifest.json); styles.css is released from shell/styles.css as-is. Nothing outside shell/ is read.
import esbuild from 'esbuild';
import { builtinModules } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const production = process.argv.includes('production');
const shellDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.dirname(shellDir);

const context = await esbuild.context({
  absWorkingDir: shellDir,
  entryPoints: ['src/main.ts'],
  bundle: true,
  outfile: path.join(repoRoot, 'main.js'),
  format: 'cjs',
  platform: 'browser',
  target: 'es2022',
  logLevel: 'info',
  sourcemap: production ? false : 'inline',
  treeShaking: true,
  minify: false,
  external: ['obsidian', 'electron', '@electron/remote', ...builtinModules, ...builtinModules.map((name) => `node:${name}`)],
  banner: { js: '/* MarkItDown Flow 2.0.0 shell: clean-room build from shell/src (MIT). */' },
});

if (production) {
  await context.rebuild();
  await context.dispose();
} else {
  await context.watch();
}
