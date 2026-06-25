# Agent-first vault migration

Design a JSONL-first personal context layer with generated views.

Status: `active`

## Claims

- Do not migrate Markdown notes one-to-one; extract entities, claims, relations, sources, tasks, and decisions. (confidence: high)
- SQLite is useful as a query artifact, but JSONL records remain the canonical source for Git review and agent edits. (confidence: high)

## Relations

- uses_pattern: project.schema-contract
