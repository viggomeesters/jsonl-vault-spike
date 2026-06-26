# Changelog

## v0.1.0 — 2026-06-24

- Initial public proof of concept.
- Added synthetic JSONL records, JSON Schemas, validation CLI, context bundle generation, SQLite projection, Markdown views, and repo-complete safety/docs layer.
- Added 10,000 public-safe synthetic note records covering all 88 current `vault-schema` type/category pairs, plus deterministic generator and coverage report.
- Added generated variant-strict note schema constraints for `vault_type`, category-per-type, and area-per-type/category validity.
- Built the 9000x synthetic import/demo flow: Markdown note embeds, synthetic mail attachments, and folder-drop fixtures now generate demo records, content-addressed objects, aggregate report data, and a browsable HTML dashboard. The package includes fixture data and object fixtures; gates cover import-demo, dashboard rendering, object verification, package-data smoke, and public-safety boundaries.
- Reworked synthetic media support into a complete test MVP: content-addressed `objects/sha256/` fixtures, `file` / `attachment` / `media_asset` / `media_link` records, object hash verification, aggregate media reporting, SQLite tables, generated Markdown indexes, and package-data coverage. Binary payloads still never live in JSONL, and OCR/transcription/vision remain proposal-only future work.
