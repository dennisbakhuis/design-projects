.PHONY: lint format check install pre-commit

install:
	uv sync

pre-commit:
	uv run pre-commit install

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

check: lint
	uv run ruff format --check src/
