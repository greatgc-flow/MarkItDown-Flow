#!/usr/bin/env node
/**
 * Publish a staged FX-71 recording into `shell/test/fixtures/fx71` (20_SHELL.md
 * REQ-SHL-11/17; 30_TESTPLAN FX-71). The recorder (`tools/record_protocol.py`,
 * engine-owned) writes a recording to a staging directory; this script is the
 * shell owner's publication step: it verifies every file of the staged
 * recording against the staged manifest (byte count and SHA-256), requires the
 * published and staged file sets to be identical, copies the bytes verbatim and
 * verifies the published copy again. It never edits a stream or the manifest.
 *
 * Usage: npm run fx71:publish -- <staged-dir>   (or FX71_STAGED=<staged-dir>)
 * Without an argument the most recently written FX-71 manifest under
 * `build/trace/redgreen/` (the recorder's staging area) is used and named.
 */
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const shellDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const PUBLISHED = path.join(shellDir, 'test', 'fixtures', 'fx71');

function fail(message) {
  console.error(`publish-fx71: ${message}`);
  process.exit(1);
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

/** Every manifest entry must exist with the recorded byte count and digest; no extra file besides the manifest itself. */
function verify(dir, label) {
  const manifestPath = path.join(dir, 'manifest.json');
  if (!fs.existsSync(manifestPath)) fail(`${label}: no manifest.json in ${dir}`);
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.v !== 1 || manifest.fixture !== 'FX-71') fail(`${label}: not an FX-71 v1 manifest`);
  const names = Object.keys(manifest.files).sort();
  const present = fs.readdirSync(dir).filter((n) => n !== 'manifest.json').sort();
  if (JSON.stringify(names) !== JSON.stringify(present)) {
    fail(`${label}: file set differs from the manifest\n  manifest: ${names.join(', ')}\n  present:  ${present.join(', ')}`);
  }
  for (const name of names) {
    const entry = manifest.files[name];
    const bytes = fs.readFileSync(path.join(dir, name));
    if (bytes.length !== entry.bytes) fail(`${label}: ${name} has ${bytes.length} bytes, manifest says ${entry.bytes}`);
    const digest = sha256(bytes);
    if (digest !== entry.sha256) fail(`${label}: ${name} sha256 ${digest} != manifest ${entry.sha256}`);
  }
  return { manifest, names };
}

/** Newest staged FX-71 manifest under the recorder's staging area. */
function newestStaged() {
  const area = path.join(path.dirname(shellDir), 'build', 'trace', 'redgreen');
  if (!fs.existsSync(area)) fail(`no staging area ${area}; pass <staged-dir>`);
  let best = null;
  for (const name of fs.readdirSync(area)) {
    const manifestPath = path.join(area, name, 'manifest.json');
    if (!fs.existsSync(manifestPath)) continue;
    let fixture;
    try {
      fixture = JSON.parse(fs.readFileSync(manifestPath, 'utf8')).fixture;
    } catch {
      continue;
    }
    if (fixture !== 'FX-71') continue;
    const mtime = fs.statSync(manifestPath).mtimeMs;
    if (!best || mtime > best.mtime) best = { dir: path.join(area, name), mtime };
  }
  if (!best) fail(`no FX-71 manifest under ${area}; pass <staged-dir>`);
  console.log(`using the newest staged recording: ${best.dir}`);
  return best.dir;
}

const stagedArg = process.argv[2] ?? process.env.FX71_STAGED;
const staged = stagedArg ? path.resolve(process.cwd(), stagedArg) : newestStaged();
if (path.resolve(staged) === path.resolve(PUBLISHED)) fail('the staged directory is the published directory');

const { manifest, names } = verify(staged, 'staged');
const host = manifest.recording_host ?? {};
console.log(`staged recording verified: ${names.length} files + manifest; host python ${host.python ?? '?'}, Core ${manifest.engine?.['markitdown-gc'] ?? '?'}`);

fs.mkdirSync(PUBLISHED, { recursive: true });
// Remove published files that the staged recording does not contain, so the sets stay identical.
for (const stale of fs.readdirSync(PUBLISHED)) {
  if (stale !== 'manifest.json' && !names.includes(stale)) fs.rmSync(path.join(PUBLISHED, stale));
}
for (const name of [...names, 'manifest.json']) {
  fs.copyFileSync(path.join(staged, name), path.join(PUBLISHED, name));
}
verify(PUBLISHED, 'published');
console.log(`published ${names.length} files + manifest to ${PUBLISHED}; published copy verified byte for byte`);
