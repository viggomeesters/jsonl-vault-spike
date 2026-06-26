PYTHON ?= python3

.PHONY: check generate validate verify-objects test build-sqlite render-media-report render-views bundle clean

check: repo-guard validate verify-objects test build-sqlite render-media-report render-views bundle

generate:
	$(PYTHON) scripts/generate_synthetic_dataset.py --count 10000

repo-guard:
	$(PYTHON) scripts/validate_repository.py

validate:
	$(PYTHON) scripts/vaultctx.py validate

verify-objects:
	$(PYTHON) scripts/vaultctx.py verify-objects

test:
	$(PYTHON) -m pytest -q

build-sqlite:
	$(PYTHON) scripts/vaultctx.py build-sqlite

render-media-report:
	$(PYTHON) scripts/vaultctx.py render-media-report

render-views:
	$(PYTHON) scripts/vaultctx.py render-views

bundle:
	mkdir -p dist/bundles
	$(PYTHON) scripts/vaultctx.py bundle --goal "decide JSONL migration" --output dist/bundles/migration-demo.json

clean:
	rm -rf dist/context.sqlite dist/bundles/*.json views/markdown/projects/*.md views/markdown/entities/*.md .pytest_cache __pycache__ scripts/__pycache__ tests/__pycache__ jsonl_vault_spike/__pycache__
