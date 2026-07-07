# Ein-Befehl-Schnittstelle (kompatibel mit make 3.81 — keine GNU-4-Features)

.PHONY: setup check lint test

setup:
	uv sync --frozen

check: lint test

lint:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest
