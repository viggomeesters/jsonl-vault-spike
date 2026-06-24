# jsonl-vault-spike

Synthetic MVP for an agent-first replacement layer for a Markdown/Obsidian-style vault.

This repo contains **no personal vault data**. All records are fictional but shaped like a real personal context system:

- raw append-only evidence
- typed JSONL records
- explicit claims/sources/relations/tasks/decisions
- generated SQLite index
- generated Markdown views
- bounded agent context bundles

## Quickstart

```bash
make check
python3 scripts/vaultctx.py query vault schema
python3 scripts/vaultctx.py bundle --goal "decide JSONL migration" --output dist/bundles/migration.json
python3 scripts/vaultctx.py build-sqlite
python3 scripts/vaultctx.py render-views
```

## Design rule

Do not convert notes 1:1 into JSONL. Normalize knowledge into records:

```text
raw evidence -> sources -> claims/entities/projects/tasks/decisions -> relations -> bundles/views/indexes
```

`records/*.jsonl` is canonical. `dist/` and `views/` are generated.
