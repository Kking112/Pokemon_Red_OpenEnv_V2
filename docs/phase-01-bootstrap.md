# Phase 01 - Bootstrap

## Implemented

- Created `pokemon_red_env` package scaffold with OpenEnv manifest.
- Added dependencies via `uv`:
  - Runtime: `openenv-core` (GitHub source), `pyboy`, `numpy`, `pillow`, `pydantic`, `pydantic-settings`
  - Dev: `pytest`, `pytest-cov`, `pytest-mock`, `ruff`
- Added pytest config in `pyproject.toml`.

## Validation

- `uv sync`
- `uv run python -c "import pokemon_red_env"`
- `uv run ruff check pokemon_red_env tests`
