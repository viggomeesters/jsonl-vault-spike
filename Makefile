PYTHON ?= python3

.PHONY: check validate test build-sqlite render-views bundle clean

check: validate test build-sqlite render-views bundle

validate:
	$(PYTHON) scripts/vaultctx.py validate

test:
	$(PYTHON) -m pytest -q

build-sqlite:
	$(PYTHON) scripts/vaultctx.py build-sqlite

render-views:
	$(PYTHON) scripts/vaultctx.py render-views

bundle:
	mkdir -p dist/bundles
	$(PYTHON) scripts/vaultctx.py bundle --goal "decide JSONL migration" --output dist/bundles/migration-demo.json

clean:
	rm -rf dist/context.sqlite dist/bundles/*.json views/markdown/projects/*.md views/markdown/entities/*.md .pytest_cache __pycache__ scripts/__pycache__ tests/__pycache__
