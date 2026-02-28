# Phase 10 - OpenEnv Validation Layout Fix

## Why this phase was added

The OpenEnv CLI validates environment projects relative to the current working
directory. Running `uv run openenv validate --verbose` from the repository root
previously failed because `openenv.yaml` existed only under `pokemon_red_env/`.

## Implemented changes

1. Added repository-root `openenv.yaml` with the canonical environment metadata
   and entrypoints:
   - `server: pokemon_red_env.server.app:app`
   - `client: pokemon_red_env.client:PokemonRedEnv`
2. Updated root `README.md` with an explicit OpenEnv validation command.
3. Updated root `AGENTS.md` test/validation command list to include
   `uv run openenv validate --verbose .`.
4. Updated phase 09 release notes to reflect dual-manifest handling:
   package-local manifest and root manifest for CLI compatibility.

## Validation and debug cycle

1. Ran validation from repo root:
   - `uv run openenv validate --verbose .`
   - Result: success
2. Re-ran quality checks:
   - `uv run ruff check pokemon_red_env tests`
   - `uv run pytest -q`
   - `uv run pytest --cov=pokemon_red_env --cov-report=term-missing`
   - Result: all passed

## Notes

- This phase is packaging/layout only. No runtime behavior of the environment,
  action mapping, RAM extraction, or reward logic was changed.
