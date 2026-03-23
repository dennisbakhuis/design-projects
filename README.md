# design-projects
Parametric CAD designs using [CadQuery](https://cadquery.readthedocs.io/).

## Projects
1. My workbench

## Setup

```sh
uv sync
make pre-commit
```

## Usage

Each design lives in its own folder under `src/`. Run a design with:

```sh
uv run python src/<design>/main.py
```

## Development

```sh
make lint      # check with ruff
make format    # auto-format with ruff
make check     # lint + format check
```
