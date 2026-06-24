# Repo complete status

Status: public-ready proof of concept.

## Included

- Public README with hero.
- Hero prompt/provenance saved in `docs/HERO_PROMPT.md`.
- Synthetic-only data boundary.
- JSONL record schemas and validator.
- Generated SQLite and Markdown views.
- Package metadata and console script.
- Embedded synthetic package dataset, so the installed CLI can validate outside a checkout.
- Governance docs and issue/PR routing.
- Repository guard wired into `make check`.

## Gates

```bash
make check
python3 -m py_compile jsonl_vault_spike/*.py scripts/*.py tests/*.py
python3 -m build
```

## Release

Initial release: `v0.1.0` with wheel and source distribution attached.
