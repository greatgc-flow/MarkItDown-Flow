# FX-03 independent oracle notes (assemble)

Derived from `docs/renewal/10_SPEC.md` only (sections 1, 2.9, 5, 6, 7.2, 10.4). Input: `assembly-input.json`.
No engine source or other test files were read.

## Facts taken from the input

- Base body has anchors for pages 1..4; pages 2 and 4 have empty base text.
- Units: `p2` (page 2, eligible) and `p4` (page 4, eligible).
- Ledger: only `p2` has an entry, `status: ok`, `text: "Own OCR text"`, `created: 2026-11-09T00:00:00+00:00`,
  `key_id` starts `41a1c2a66238a20c`. `p4` has no entry -> pending with `meta.pending_reason = "no_provider"`.
- `meta.pages_total = 4`, `meta.now = 2026-11-09T00:00:00+00:00`.

## SPEC clauses used

| Clause | How it was applied |
|---|---|
| Encodings (header, p.1) | UTF-8, no BOM, `\n` line endings; sha256 lowercase hex. |
| REQ-ASM-01 / REQ-GEN-04 | Assemble is PURE: `generated` comes from `meta.now`, never from the clock. |
| REQ-ASM-03 / 6.4 | Frontmatter keys exactly in 6.4 order; strings JSON-quoted; integers bare. `provider`, `model`, `prompt_version` present because `units.total > 0`; `dpi` present because format is pdf. |
| 6.4 units equation | `done = cached + transcribed` -> 1 (p2 has an ok entry); `pending` 1 (p4); `failed` 0; `total = done + pending + failed = 2`. |
| REQ-ASM-04 / 6.1 | One `<!-- mdflow:page N -->` anchor for every page 1..4; pages 1 and 3 keep base text and get no block; exactly one blank line between page blocks. |
| 6.1 "base text ... may be empty" | Pages 2 and 4 have empty base text, so the anchor is followed directly by the block / marker (see ambiguity 1). |
| REQ-ASM-06 / 6.5 | Provenance block for p2 exactly per 6.5: `unit`, `key=<key_id[:16]>`, `provider`, `model`, `prompt`, `dpi`, `at`; heading `## OCR p2 (provider, model, date)`; text line; closing `<!-- /mdflow:ocr -->`. Placement = 1 per page unit. |
| REQ-ASM-10 / 6.5 | `at` = ledger `created`; heading date = local date of `at` (offset `+00:00` -> `2026-11-09`). `generated` = `meta.now`. |
| 6.6 / REQ-APR-03 vocabulary | Pending marker for p4: `<!-- mdflow:pending unit="p4" reason="no_provider" -->`; `no_provider` is in the closed reason list. |
| REQ-ASM-11 | `esc_text` on "Own OCR text", `esc_attr` on every attribute, `esc_head` on heading fields: all values contain none of `<!--`, `-->`, `"`, `--`, `\n`, so escaping is the identity here. |
| REQ-ASM-08 | `content_sha256` = sha256 of UTF-8 bytes after the closing `---\n`. Body is 430 bytes, LF only; hash `08fa087d16a3e04c17e41f7d34e5f4fe43c44fc5b18f4cc690873684293ad76e`. |
| 5.1 ordering | Assemble uses document order (page number): p2 block before p4 marker. |
| REQ-ASM-P1 | OCR text is only inside the delimited block; base lines are unchanged. |
| 7.2 | Ledger entry shape (`status`, `text`, `created`, `key_id`) read as specified. |

## Ambiguities (and the choice made)

1. **Empty base text on an anchored page.** 6.1 shows `<base text of page N, may be empty>` as a line. I read "empty" as
   "no line emitted", so the anchor is immediately followed by the block/marker, with no blank line in between.
   The alternative (an empty line between anchor and block) would contradict "exactly one blank line between blocks"
   for pages 2 and 4 when the following page starts.
2. **`tools` key order in frontmatter.** 6.4 says "keys in this order" and its example lists
   `mdflow, markitdown-gc, pypdfium2, pillow`. `meta.tools` in the input is alphabetically ordered. I followed the 6.4
   example order. If the implementation emits `meta.tools` insertion order the frontmatter line (not the body or the
   hash) would differ.
3. **Trailing newline.** 6.1 does not state whether the file ends with `\n`. Given the LF line-ending convention and
   that the body is a sequence of lines, I ended the file with a single `\n` after the pending marker. This affects
   `content_sha256`.
4. **"local date" of `at`.** Because Assemble is PURE and may not consult the machine timezone, "local" was read as
   the date in the timestamp's own UTC offset. With `+00:00` both readings give `2026-11-09`, so FX-03 does not
   distinguish them.
5. **`done` for p2.** The input has no unit status `cached`/`transcribed` distinction (both units are `eligible`);
   p2 is counted as done solely because its ledger entry exists with `status == ok` (REQ-LKP-01 hit semantics).
6. **Frontmatter `units` / `tools` flow-mapping spacing.** Copied verbatim from the 6.4 example
   (`{total: 2, done: 1, pending: 1, failed: 0}`, space after each colon and comma, no quotes on keys).
