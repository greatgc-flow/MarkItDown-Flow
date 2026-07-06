# MarkItDown-Flow — Progress Log

> Plugin re-build kickoff. Goal: rebuild the user's experimental Obsidian plugin
> into a clean, systematic repository at `D:\PortableDev\workspace\MarkItDown-Flow\`
> (GitHub: https://github.com/greatgc-flow/MarkItDown-Flow).
>
> Source inputs:
> - Template — `D:\PortableDev\workspace\obsidian-markitdown\` (ethanolivertroy, v2.1.0)
> - Experimental wrapper — `D:\PortableDev\workspace\Vault\Conv\.obsidian\plugins\markitdown\python\markitdown_wrapper.py`
> - Experimental settings (with current options) — `D:\PortableDev\workspace\Vault\Conv\.obsidian\plugins\markitdown\data.json`
> - Requirements doc — `D:\PortableDev\workspace\2. 요청사항.txt`

---

## 0. URGENT — Security

⚠️  **Azure DocIntel API key is exposed in cleartext** in two places:
- `Vault\Conv\.obsidian\plugins\markitdown\data.json` (`docintel_credential`)
- `2. 요청사항.txt` (lines 159, 240)

Key value (partial, for identification only): `3LhBUazkTL...XJ3w3AAALACOG3qJL`

If this key was ever pushed to a public repo (including drafts of MarkItDown-Flow),
**rotate it now in the Azure portal**. New plugin design must never persist this
key in files that get committed.

---

## 1. Completed Files

**None.** No files have been created or modified on disk yet.

The `MarkItDown-Flow/` directory still contains only the original three entries
the user set up: `.git/`, `LICENSE`, `README.md` (a 3-line placeholder).

A PowerShell `Copy-Item` command was issued earlier to copy the template into
`MarkItDown-Flow/`, but the tool returned "Tool result missing due to internal
error" and a subsequent directory listing confirms the copy did NOT take effect.
**This must be re-run at the start of the next session.**

---

## 2. In-Progress

Nothing partially written. The session was spent in **research / planning** phase
— reading every file that the M1 plan touches so that the edits could be done
non-interactively in one sweep.

Files that have been **read and understood** (no edits yet):

| File | Purpose / What it tells us |
|---|---|
| `obsidian-markitdown/manifest.json` | Template manifest, id=`markitdown`, v2.1.0, isDesktopOnly |
| `obsidian-markitdown/package.json` | npm name, build scripts (esbuild + tsc), jest test setup |
| `obsidian-markitdown/main.ts` (412 L) | Plugin entry: commands, ribbon, file-menu, drag-drop, settings load/save |
| `obsidian-markitdown/src/converter/MarkitdownConverter.ts` (193 L) | TS→Python subprocess; uses `--extract-images/--image-dir` and parses `{success,images_extracted}` stdout JSON |
| `obsidian-markitdown/src/types/settings.ts` | Settings shape — `imageExtractionEnabled`, `imageSubfolderTemplate`, `extractImages`, `imageDir` etc. |
| `obsidian-markitdown/src/utils/paths.ts` (97 L) | Path utils — `resolveOutputFolder`, `resolveFilenameTemplate`, `resolveImageDir`, `toVaultRelative` |
| `obsidian-markitdown/src/utils/bundledScripts.ts` (227 L) | **CRITICAL**: inlines the wrapper.py as a TS string for community-store distribution (only main.js/manifest.json/styles.css get shipped) |
| `obsidian-markitdown/src/settings/SettingsTab.ts` (415 L) | Settings UI — has "Extract images" / "Image subfolder" toggles, Python status, install button |
| `obsidian-markitdown/src/modals/FileConvertModal.ts` (97 L) | File-picker modal |
| `obsidian-markitdown/src/utils/__tests__/paths.test.ts` | Tests reference `resolveImageDir` — must be renamed too |
| `obsidian-markitdown/python/markitdown_wrapper.py` (278 L) | Template wrapper — simple `convert + write file + print stdout JSON` |
| `Vault/Conv/.obsidian/plugins/markitdown/python/markitdown_wrapper.py` (917 L) | **Experimental wrapper** — the prize. See §4 for what it includes |
| `Vault/Conv/.obsidian/plugins/markitdown/data.json` | Current user settings (has new `assetExtractionEnabled`, `assetSubfolderTemplate`, `inputBasePath`, `outputFilenameTemplate=`{filename}_{ext}_{datetime}`) |

**Files NOT yet read** but in scope for M1:
- `obsidian-markitdown/src/modals/{FolderConvertModal,UrlConvertModal,HistoryModal,PreviewModal,SetupModal,BatchProgressModal}.ts`
- `obsidian-markitdown/src/settings/PluginArgsEditor.ts`
- `obsidian-markitdown/src/utils/{python,fileTypes,history,postprocess}.ts`
- `obsidian-markitdown/src/utils/__tests__/python.test.ts`
- `obsidian-markitdown/esbuild.config.mjs`, `tsconfig.json`, `version-bump.mjs`

---

## 3. Remaining Files (M1 Plan)

The M1 milestone = "compiles, builds, and runs as a working v0.1.0 with the
experimental wrapper attached." Concrete file actions, in order:

### Step A — Copy template into MarkItDown-Flow
1. Re-run PowerShell copy (exclude `.git/`, `node_modules/`, `main.js`,
   `.DS_Store`). Verify with a directory listing afterward.

### Step B — Replace wrapper + add stdout JSON for TS compatibility
2. Overwrite `MarkItDown-Flow/python/markitdown_wrapper.py` with the
   experimental 917-line version.
3. Patch the wrapper to emit, on success:
   `print(json.dumps({"success": True, "images_extracted": N,
   "processing_time_ms": ms}))` to stdout — the TS converter parses this.
   (Experimental wrapper currently only logs to file/console.)

### Step C — Rename `--extract-images / --image-dir` → `--extract-assets / --asset-dir`
Per user requirement (요청사항 line 83 — "asset"으로 의미 확장).
Touch each file listed below:
4. `MarkItDown-Flow/python/markitdown_wrapper.py` — argparse already uses
   `--extract-assets/--asset-dir`. Confirm and keep.
5. `MarkItDown-Flow/src/converter/MarkitdownConverter.ts` — change line ~114
   `--extract-images, --image-dir` → `--extract-assets, --asset-dir`.
6. `MarkItDown-Flow/src/types/settings.ts` — rename fields:
   - `imageExtractionEnabled` → `assetExtractionEnabled`
   - `imageSubfolderTemplate` → `assetSubfolderTemplate`
   - `extractImages` → `extractAssets`
   - `imageDir` → `assetDir`
   - Update `DEFAULT_SETTINGS` accordingly.
   - Also: `imagesExtracted` field in `ConversionLogEntry` / `ConversionResult`
     — keep as is, since the wrapper still reports the count under that key.
     (Or rename to `assetsExtracted` consistently — decide at edit time.)
7. `MarkItDown-Flow/src/utils/paths.ts` — `resolveImageDir` →
   `resolveAssetDir`.
8. `MarkItDown-Flow/src/utils/__tests__/paths.test.ts` — update imports and
   describe block names.
9. `MarkItDown-Flow/src/settings/SettingsTab.ts` — update toggle/label text
   ("Extract images" → "Extract assets", "Image subfolder" → "Asset
   subfolder"), and the setting field references.
10. `MarkItDown-Flow/main.ts` — `buildConversionOptions()` references
    `imageExtractionEnabled` / `imageSubfolderTemplate` / `resolveImageDir`.
    Update.
11. Grep the rest of `src/` for any other `image*` references; rename.

### Step D — Plugin identity rebrand
12. `MarkItDown-Flow/manifest.json`:
    - `id`: `markitdown` → `markitdown-flow`
    - `name`: `Markitdown File Converter` → `MarkItDown Flow`
    - `version`: `2.1.0` → `0.1.0`
    - `author`: `Ethan Troy` → `greatgc-flow`
    - `authorUrl`: `https://github.com/greatgc-flow/MarkItDown-Flow`
    - Keep `isDesktopOnly: true` (Python subprocess required).
13. `MarkItDown-Flow/manifest-beta.json` — same updates.
14. `MarkItDown-Flow/package.json` — `name` → `markitdown-flow`,
    `version` → `0.1.0`, update `description` & `author`.
15. `MarkItDown-Flow/versions.json` — replace existing entries with
    `{ "0.1.0": "0.15.0" }`.
16. `MarkItDown-Flow/README.md` — rewrite (current is "TEST"). Document the
    fork lineage, install steps, the 4-phase pipeline.
17. `MarkItDown-Flow/CHANGELOG.md` — start fresh: `## 0.1.0 — initial fork`.

### Step E — Add "Open log folder" command
18. `MarkItDown-Flow/main.ts` — add command `id: open-log-folder` that opens
    `~/omnidata_logs` in OS file manager (Electron `shell.openPath`).
    The wrapper logs to that directory.

### Step F — Build verification
19. `cd MarkItDown-Flow && npm install`
20. `npm run build` — must pass `tsc -noEmit -skipLibCheck && esbuild
    production`.
21. `npm test` — paths.test.ts and python.test.ts must still pass after the
    rename.

### Out of scope for M1 (deferred to M2+)
- **Input Base Path UI setting** (요청사항 line 84) — needed for
  structured output paths. Defer.
- **MECE UI restructure** (요청사항 line 85). Defer.
- **i18n in the TS UI** — wrapper already supports 8 langs; TS UI doesn't.
  Defer.
- **Updating `bundledScripts.ts`** with the new 917-line wrapper. For local
  install (copy `main.js` + `manifest.json` + `styles.css` + `python/` to
  `<vault>/.obsidian/plugins/markitdown-flow/`) the on-disk
  `python/markitdown_wrapper.py` is used. The inlined version in
  `bundledScripts.ts` is only the fallback for community-store installs,
  which is a separate milestone.
- **Image path defense logic** (요청사항 개선 2/3 — spaces, recursive
  subdirs). Already partially handled by experimental wrapper's
  `sanitize_path`; verify in M2.
- **Token-saving offline-first AI fallback** (요청사항 개선 5). Already
  implemented in `MarkItDownEngine.run_conversion()`; just verify wiring.

---

## 4. Key Design Decisions

### D1 — Start point: template + experimental wrapper merge
Reject "decompile main.js" or "from scratch." The template gives us a
well-organized TS layer; the experimental wrapper has all the Python-side
heavy lifting. Bridge them.

### D2 — M1 scope: thin and runnable, NOT feature-complete
v0.1.0 = "compiles, builds, runs the new wrapper end-to-end, with the
`--extract-assets` rename applied." All other requirements from
`2. 요청사항.txt` are deferred to M2+.

### D3 — Wrapper interface contract: stdout JSON to TS
Even though the experimental wrapper logs to `~/omnidata_logs/`, it MUST
also `print(json.dumps({"success": True, ...}))` to stdout on success, so
the existing `MarkitdownConverter.ts` can parse it without rewriting the
TS side. This is a one-line patch at the end of `main()` in the wrapper.

### D4 — `image*` → `asset*` rename is global
Per 요청사항 line 83, the rename is not just the CLI flag — it propagates
through TS types, settings UI, path helpers, and tests. Anything user-facing
or persisted ("Extract images" toggle, `imageExtractionEnabled` setting
key) gets renamed too. Migration cost is paid once.

### D5 — Plugin ID = `markitdown-flow`
Per Obsidian rules, `id` is immutable post-release. We pick `markitdown-flow`
now so it's stable from v0.1.0 onward. Different from the experimental
build's `id: "markitdown"` — users with the experimental version installed
will need to reinstall under the new id; their `data.json` will not auto-
migrate. (M2 task: write a one-time settings migrator if requested.)

### D6 — Desktop-only stays
`isDesktopOnly: true`. MarkItDown is a Python library invoked via
`child_process` — incompatible with mobile Obsidian. Documented as a known
limit, not a bug.

### D7 — `bundledScripts.ts` left as-is in M1
The inlined wrapper (a 100-line string in TS) is the simple template
version, not the 917-line experimental one. For local-install testing in
M1 this is fine because the on-disk `python/markitdown_wrapper.py`
overrides the inlined copy (`ensurePythonScripts` only writes when the file
is missing). Updating the inlined string is a community-store-prep task
for a later milestone.

### D8 — Credentials never in repo
`.gitignore` (already in template) excludes `data.json`. New README will
explicitly tell the user to enter the DocIntel key via the Obsidian
settings UI only, never in any file that gets committed.

---

## 5. Next Session — First Actions (in order)

1. **Verify state**: `Glob D:\PortableDev\workspace\MarkItDown-Flow\**\*` —
   confirm still only `.git/`, `LICENSE`, `README.md`. If anything else
   exists (e.g., partial copy from a hidden retry), inspect before
   overwriting.

2. **Re-run the file copy.** Use a more defensive PowerShell, capturing
   errors. Example:
   ```powershell
   $src='D:\PortableDev\workspace\obsidian-markitdown'
   $dst='D:\PortableDev\workspace\MarkItDown-Flow'
   $exclude=@('.git','node_modules','main.js','.DS_Store')
   $copied=@()
   Get-ChildItem -Path $src -Force | Where-Object { $exclude -notcontains $_.Name } | ForEach-Object {
       Copy-Item -Path $_.FullName -Destination (Join-Path $dst $_.Name) -Recurse -Force -ErrorAction Stop
       $copied += $_.Name
   }
   $copied
   Get-ChildItem $dst -Force | Select-Object Name | Format-Table -AutoSize
   ```
   Then verify with another `Glob`.

3. **Replace `python/markitdown_wrapper.py`** with the experimental 917-line
   version. Patch the bottom of `main()` to add the stdout JSON success
   line (see §3 Step B).

4. **Then** proceed through Step C → F per §3.

5. **DO NOT** copy `data.json` from the experimental build into the new
   repo — it contains the live API key.

---

## 6. Reference — Experimental Wrapper Capabilities

The 917-line `markitdown_wrapper.py` in `Vault\Conv\.obsidian\plugins\markitdown\python\`
implements (verified by reading source, not testing):

- **OmniDataPipeline** — N-invokable, no `sys.exit`, encapsulated.
- **4 independent phases**:
  1. `_run_offline` — direct MarkItDown call.
  2. `_run_ai` — multi-client fallback (OpenAI, Anthropic, Gemini) with
     custom endpoint support for Azure OpenAI / proxies.
  3. `_run_docintel` — Azure Document Intelligence 4.0 GA
     (API 2024-11-30), `prebuilt-layout` default, native MD output.
  4. `_run_content_understanding` — Azure Content Understanding
     (2025-05-01-preview).
- **Phase gating**: offline runs first; AI/DocIntel/CU triggered only when
  offline produces empty output, OR when MIME matches `*_target_mimes`, OR
  when `exhaustive_mode=True`. This is exactly requirement 개선 5.
- **i18n in 8 languages**: en, ko, ja, zh, hi, fr, es, ar.
- **Timezone**: `timezone_offset` parameter; falls back to system tz.
- **EXIF + GPS reverse geocoding** via geopy.
- **Recursive archive extraction**: zip/tar opened to temp dir, each entry
  processed recursively, output inlined under a collapsible block.
- **Inline base64 asset extraction**: matches both MD `![](data:...)` and
  HTML `<img src="data:...">`, decodes to physical files under sanitized
  paths, replaces with relative URLs.
- **`mask_secrets`** for log safety.
- **Logger** writes to `~/omnidata_logs/engine_YYYYMMDD.log`.
- **`ConfigManager.parse`** routes kwargs into 3 buckets:
  `md_init_args` (MarkItDown constructor), `md_convert_args` (convert()
  call), `engine_config` (our pipeline). Pre-spec'd params validated;
  unknown params passed through to MarkItDown convert() — forward-
  compatible with future MarkItDown releases.

The big gap vs requirements: **stdout JSON output is missing** (must be
added in M1 Step B), and the TS-side rename is not yet propagated.
