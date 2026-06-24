# Architecture

## Layers

1. **Raw evidence** (`raw/*.jsonl`) — append-only source material with hashes and provenance.
2. **Canonical records** (`records/*.jsonl`) — typed, stable, agent-readable truth units.
3. **Retrieval hints/evals** (`retrieval/`, `evals/`) — quality contract for agents.
4. **Generated runtime** (`dist/context.sqlite`) — rebuildable query artifact.
5. **Generated views** (`views/markdown/`) — human-readable exports, not source of truth.

## Record principles

Every canonical record should have:

- stable `id`
- `kind`
- short `summary` or title
- provenance through `source_ids` / `evidence_ids`
- `privacy`
- freshness/confidence where relevant
- explicit relations instead of implicit WikiLinks

## Non-goals

- no real private data
- no Obsidian plugin
- no automatic migration of an existing vault
- no generated embedding/vector store yet

## Vault-schema coverage fixture

`records/notes.jsonl` is a large synthetic fixture generated from the public `vault-schema` type/category matrix. It is intentionally not a copy of a real vault. The dataset proves that downstream validation, SQLite projection, bundle generation, and retrieval experiments can handle all schema categories at 10,000-record scale.

Generation contract:

```bash
python3 scripts/generate_synthetic_dataset.py --count 10000
```

The generator also syncs the embedded package dataset under `jsonl_vault_spike/data/` so wheel/sdist installs can run `vaultctx validate` outside a checkout.
