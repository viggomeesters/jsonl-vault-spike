# Agent Instructions — jsonl-vault-spike

This repo is a synthetic MVP for an agent-first JSONL vault/context layer.

## Source of truth

- `records/*.jsonl` is canonical synthetic record data.
- `schema/*.schema.json` defines the record contracts.
- `raw/*.jsonl` is synthetic raw evidence only.
- `dist/` and `views/` are generated artifacts.

## Safety

- Do not add real personal vault data, real names, real emails, real paths, credentials, exports, screenshots, or real attachments.
- Tiny synthetic attachment/media fixtures are allowed only under `fixtures/import-demo/`, `objects/sha256/`, plus the matching package-data mirrors, and must be covered by fixture/public-safety tests and `verify-objects`.
- Keep examples synthetic and public-safe.
- If using this against a real vault later, build a separate importer with dry-run and redaction gates first.

## Required checks

Run before finishing:

```bash
make check
python3 -m py_compile jsonl_vault_spike/*.py scripts/*.py tests/*.py
```
