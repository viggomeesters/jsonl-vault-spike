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
