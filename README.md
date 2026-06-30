<p align="center">
  <img src="assets/jsonl-vault-spike-hero.svg" alt="JSONL Vault Spike hero" width="100%">
</p>

# jsonl-vault-spike

Project page: <https://viggomeesters.com/jsonl-vault-spike/>

[![Status](https://img.shields.io/badge/status-proof--of--concept-blue)](#)
[![Data](https://img.shields.io/badge/data-synthetic--only-green)](#safety-boundary)
[![Gate](https://img.shields.io/badge/gate-make%20check-111827)](#verification)

A public, synthetic proof of concept for replacing a Markdown/Obsidian-style vault with an **agent-readable JSONL context layer**.

The repo demonstrates the core shape:

```text
raw evidence -> typed JSONL records -> context bundles -> generated SQLite/Markdown views
```

## Why this exists

Markdown notes are good for humans but weak as an agent source of truth: links are implicit, claims blur into prose, provenance gets lost, and retrieval often depends on guesswork. This spike tests a stricter model where small typed records are canonical and human views are generated.

## Safety boundary

**No real personal data.**

This repository intentionally uses synthetic examples only. Do not add real vault exports, real names, messages, emails, file paths, credentials, screenshots, or real attachments. The checked-in media fixtures are tiny synthetic files used only to prove content-addressed storage and validation.

## Repository map

| Path | Role | Canonical? |
| --- | --- | --- |
| `raw/*.jsonl` | Synthetic source evidence | input |
| `records/*.jsonl` | Typed records: entities, projects, claims, relations, tasks, decisions, files, attachments, media links, plus 10,000 synthetic note records | yes |
| `fixtures/import-demo/` | Synthetic Markdown/mail/folder-drop input for the 9000x import flow | fixture input |
| `objects/sha256/` | Tiny synthetic content-addressed object fixtures used for hash/integrity tests | fixture input |
| `schema/*.schema.json` | JSON Schema contracts per record type | yes |
| `retrieval/*.jsonl` | Query hints for agents | yes |
| `evals/*.jsonl` | Retrieval expectations | yes |
| `reports/vault-schema-coverage.json` | Coverage proof for every vault-schema type/category pair | generated but tracked |
| `dist/` | SQLite and bundle outputs | generated |
| `views/markdown/` | Human-readable Markdown exports | generated examples |

## Quick start

```bash
git clone https://github.com/viggomeesters/jsonl-vault-spike.git
cd jsonl-vault-spike
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make check
```

## CLI

Run from the repo:

```bash
python3 scripts/generate_synthetic_dataset.py --count 10000
python3 scripts/vaultctx.py validate
python3 scripts/vaultctx.py query vault migration
python3 scripts/vaultctx.py bundle --goal "replace markdown with jsonl"
python3 scripts/vaultctx.py import-demo
python3 scripts/vaultctx.py render-import-demo-dashboard
python3 scripts/vaultctx.py verify-objects
python3 scripts/vaultctx.py render-media-report
python3 scripts/vaultctx.py build-sqlite
python3 scripts/vaultctx.py render-views
python3 scripts/vaultctx.py inspect-media --path objects/sha256/<prefix>/<sha256>.png
```

Media/file support is a complete synthetic MVP slice:

- `fixtures/import-demo/` models the source side: Markdown embeds, a synthetic mail with attachment manifest, and folder-drop files;
- `import-demo` turns those fixtures into generated demo records and content-addressed objects under `dist/import-demo/` without overwriting canonical records;
- `objects/sha256/` contains three tiny synthetic fixtures: PNG, PDF, and CSV;
- `records/files.jsonl` stores content hashes, MIME type, byte size, and synthetic blob refs;
- `records/attachments.jsonl` stores note/source attachment occurrences;
- `records/media_assets.jsonl` stores media metadata derived from files;
- `records/media_links.jsonl` stores resolved and missing media references;
- `verify-objects` proves file records match object bytes by SHA-256 and size;
- `render-media-report` writes an aggregate-only media summary.
- `render-import-demo-dashboard` writes a browsable HTML dashboard that shows the flow from source fixture to attachment/media link, file record, SHA-256 object and media asset.

No real filenames, real attachments, local paths, screenshots, OCR text, transcripts, thumbnails, or base64 payloads are committed.

Install as a package:

```bash
python3 -m pip install .
vaultctx validate
```


## Vault-schema coverage dataset

The repo includes `records/notes.jsonl` with **10,000 public-safe synthetic note records** generated from [`viggomeesters/vault-schema`](https://github.com/viggomeesters/vault-schema). The generator covers every current vault-schema `type/category` pair at least once, then scales deterministically.

Coverage proof lives in `reports/vault-schema-coverage.json`:

- 11 schema types;
- 88 type/category pairs;
- 0 missing pairs;
- 10,000 generated note records;
- generated `schema/note.schema.json` constraints for valid `vault_type`, valid `category` per `vault_type`, and valid `area` per `vault_type/category` pair.

The fixture is now matrix-strict for the fields that `vault-schema` exposes in `type_category_area`. It still does not invent deeper subtype-specific content fields that are not present in the public schema contract.

Regenerate after a schema change:

```bash
python3 scripts/generate_synthetic_dataset.py --count 10000
make check
```

## Agent usage

Agents should treat `records/*.jsonl` as the source of truth and use generated bundles for bounded context. A useful default flow is:

1. validate record contracts;
2. query relevant records;
3. generate a bundle for the current goal;
4. cite `source` / `evidence` records before making claims;
5. regenerate views and SQLite after canonical records change.

## Record model

The examples use `record_type` as the technical discriminator. Domain-specific subtypes remain explicit, for example `entity_type`, `source_type`, `relation_type`, `task_type`, and `vault_type`. See [`docs/RECORD_MODEL.md`](docs/RECORD_MODEL.md) for the practical migration model: Markdown notes become source/entity/relation/claim/task records with stable IDs and references, then Markdown views are regenerated from JSONL.

## Testing against a real Obsidian vault

Use [`docs/VAULT_EVALUATION.md`](docs/VAULT_EVALUATION.md) for the read-only, private dry-run protocol. The public repo stays synthetic; real-vault evaluation output belongs under `.local/` or `/tmp/` and must not be committed.

Local aggregate comparison:

```bash
python3 scripts/evaluate_obsidian_vault.py --vault /path/to/local/vault --limit 75 --out .local/vault-eval
```

This writes `aggregate-metrics.json`, `scorecard.json`, and `value-prop-comparison.html` under `.local/vault-eval/`. The report contains counts and percentages only: no note titles, paths, body text, names, or screenshots.

## Verification

Full local gate:

```bash
make check
python3 -m py_compile jsonl_vault_spike/*.py scripts/*.py tests/*.py
```

`make check` includes:

- repository guard for public-data safety and required public files;
- JSONL record validation;
- content-addressed synthetic object hash validation;
- tests;
- SQLite build;
- aggregate media report rendering;
- Markdown view rendering;
- demo bundle generation.

## Package and release

See [`docs/PACKAGE.md`](docs/PACKAGE.md). The README hero prompt/provenance is saved in [`docs/HERO_PROMPT.md`](docs/HERO_PROMPT.md).

## Contributing

Read [`CONTRIBUTORS.md`](CONTRIBUTORS.md), [`SUPPORT.md`](SUPPORT.md), and [`SECURITY.md`](SECURITY.md) first. Keep all examples synthetic.

## License

MIT. See [`LICENSE`](LICENSE).
