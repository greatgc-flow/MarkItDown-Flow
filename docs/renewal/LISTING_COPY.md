# Listing copy for the v2 functionality

Use the following text when updating the repository description and the Obsidian
listing's short description / About fields. These service metadata fields are
separate from README.md; committing this file does not update them.

## Short description

Convert text documents to Markdown and identify originals that need external OCR.

## About

MarkItDown Flow is an Obsidian desktop plugin for local direct-text conversion. A scanned page excludes the whole PDF from complete Markdown. Inspect page composition, save existing text as an explicitly partial note, or copy selected originals for external transcription. Optional ExifTool support lets you preview and copy selected photo fields.

Install the engine in a separate virtual environment using BOOTSTRAP.md, then
select its interpreter in the plugin settings. The plugin does not install Python
or dependencies. Review README.md for supported formats, limitations, cache
retention, migration and rollback.

## Publication checks

- Replace inherited claims about automatic Azure/Gemini/Anthropic fallback,
  built-in offline OCR and guaranteed lossless output with the text above.
- Keep the existing plugin ID and listing; do not create a duplicate submission.
- Confirm the published metadata and release actually match before requesting
  another review. A passing GitHub CI run is not an Obsidian review verdict.
- Run the MAN-04 real-Obsidian minimum/current checks, including saving settings
  over an existing data.json on Windows, macOS and Linux. Obsidian's adapter
  `rename` refuses an existing destination (verified in the 1.15.1 app bundle), so
  the store moves the original aside to `data.json.bak` before the swap and
  restores it on failure; never introduce a delete-before-rename fallback.
