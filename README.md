<p align="center">
  <img src="assets/jsonl-vault-spike-hero.svg" alt="JSONL Vault Spike hero" width="100%">
</p>

# jsonl-vault-spike

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

This repository intentionally uses synthetic examples only. Do not add real vault exports, names, messages, emails, file paths, credentials, screenshots, or attachments.

## Repository map

| Path | Role | Canonical? |
| --- | --- | --- |
| `raw/*.jsonl` | Synthetic source evidence | input |
| `records/*.jsonl` | Typed records: entities, projects, claims, relations, tasks, decisions, plus 10,000 synthetic note records | yes |
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
python3 scripts/vaultctx.py build-sqlite
python3 scripts/vaultctx.py render-views
```

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
- 10,000 generated note records.

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

## Testing against a real Obsidian vault

Use [`docs/VAULT_EVALUATION.md`](docs/VAULT_EVALUATION.md) for the read-only, private dry-run protocol. The public repo stays synthetic; real-vault evaluation output belongs under `.local/` or `/tmp/` and must not be committed.

## Verification

Full local gate:

```bash
make check
python3 -m py_compile jsonl_vault_spike/*.py scripts/*.py tests/*.py
```

`make check` includes:

- repository guard for public-data safety and required public files;
- JSONL record validation;
- tests;
- SQLite build;
- Markdown view rendering;
- demo bundle generation.

## Package and release

See [`docs/PACKAGE.md`](docs/PACKAGE.md). The README hero prompt/provenance is saved in [`docs/HERO_PROMPT.md`](docs/HERO_PROMPT.md).

## Contributing

Read [`CONTRIBUTORS.md`](CONTRIBUTORS.md), [`SUPPORT.md`](SUPPORT.md), and [`SECURITY.md`](SECURITY.md) first. Keep all examples synthetic.

## License

MIT. See [`LICENSE`](LICENSE).
