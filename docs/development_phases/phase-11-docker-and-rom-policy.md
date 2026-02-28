# Phase 11 - Docker Support Completion and ROM Policy

## Why this phase exists

You requested that all OpenEnv checks pass, Docker support be added and verified,
and that ROM handling be clearly documented with legal guidance.

## Implemented changes

1. Completed Docker support with a production-ready `server/Dockerfile`:
   - Multi-stage build
   - `uv`-based dependency install
   - Runtime healthcheck and `uvicorn` launch command
   - Runtime defaults for ROM/symbols/state paths
2. Added `.dockerignore` to keep build context small and deterministic.
   - Explicitly excludes `PokemonRed.gb` to prevent accidental ROM image bundling.
3. Added `PokemonRed.gb` to `.gitignore` so local ROM files are never committed.
4. Updated `README.md` with explicit legal ROM requirements:
   - Repo does not ship ROM content
   - Users must provide legally obtained `.gb`
   - Configurable via `POKEMON_RED_GB_PATH`
   - Added Docker run example using host-file mount for ROM delivery
5. Hardened Dockerfile env setup:
   - Set `PYTHONPATH` directly to `/app/env` to avoid undefined-variable warnings.
   - Set Docker ROM default to `/app/roms/PokemonRed.gb` and created `/app/roms` mount target.

## Validation and test/debug cycle

1. `uv run openenv validate --verbose .`
   - Result: passed with all modes enabled (`docker`, `openenv_serve`, `uv_run`, `python_module`)
2. `uv run ruff check pokemon_red_env tests server`
   - Result: passed
3. `uv run pytest -q`
   - Result: passed (`14 passed`)
4. `uv run openenv build -t pokemon-red-openenv:test`
   - Result: Docker image build succeeded end-to-end

## Notes

- Docker support is now both structurally valid (`validate`) and operationally
  verified (`openenv build`).
- ROM policy is explicit and compliant with legal-use expectations.
