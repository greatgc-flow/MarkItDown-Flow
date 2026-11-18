# Listing copy for the v2 functionality

Use the following text when updating the repository description and the Obsidian
listing's short description / About fields. These service metadata fields are
separate from README.md; committing this file does not update them.

## Short description

Convert local documents to Markdown, with selective OCR planning and explicit
approval for remote transcription. Desktop only; requires a separately installed
Python engine.

## About

MarkItDown Flow is a desktop Obsidian plugin backed by the `mdflow` Python engine
and `markitdown-gc`. It converts local documents to Markdown, classifies OCR needs,
and lets you review selected pages and images before sending them to a configured
OpenAI-compatible endpoint. Local conversion is the default. Remote transcription
can incur provider charges.

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
