.PHONY: setup test lint fmt check run data build serve products intent
PY ?= python3

setup:
	$(PY) -m pip install -q -e ".[dev]"

test:
	$(PY) -m pytest -q

lint:
	ruff check src tests && ruff format --check src tests

fmt:
	ruff format src tests && ruff check --fix src tests

check: lint test

# Regenerate data/: holidays from the `holidays` library (offline), population from the World Bank.
data:
	$(PY) -m bridgeday.main data

# Production build into dist/ with the base_url from config.toml.
build:
	$(PY) -m bridgeday.main build

# Local preview: build for localhost and serve it.
run:
	$(PY) -m bridgeday.main build --base-url http://127.0.0.1:8000 && $(PY) -m bridgeday.main serve

# The paid planners (PDFs, bundle zip, catalog.csv) into products/. Never commit or publish them.
products:
	$(PY) -m bridgeday.main products

# Pull Leave Intent counts from GoatCounter (needs GOATCOUNTER_TOKEN) into git-ignored private/.
intent:
	$(PY) -m bridgeday.main intent
