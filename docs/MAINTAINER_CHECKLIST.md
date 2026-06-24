# Maintainer checklist

Before release:

- [ ] `make check`
- [ ] `python3 -m py_compile jsonl_vault_spike/*.py scripts/*.py tests/*.py`
- [ ] `python3 -m build`
- [ ] Fresh clone smoke installs dependencies and validates records.
- [ ] Privacy scan finds only guard-pattern definitions, not real data.
- [ ] Release notes state synthetic-data boundary.

Do not add GitHub Actions by default; local gates are the repo-complete contract.
