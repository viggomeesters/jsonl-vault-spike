# Package

Build local artifacts:

```bash
python3 -m pip install build
python3 -m build
```

Install from a built wheel:

```bash
python3 -m venv /tmp/jsonl-vault-spike-venv
/tmp/jsonl-vault-spike-venv/bin/pip install dist/jsonl_vault_spike-0.1.0-py3-none-any.whl
/tmp/jsonl-vault-spike-venv/bin/vaultctx validate
```

The package includes an embedded synthetic dataset so `vaultctx validate` works outside a source checkout. When run from a checkout containing `records/` and `schema/`, the CLI uses the checkout data instead.

Release artifacts are attached to GitHub releases when created.
