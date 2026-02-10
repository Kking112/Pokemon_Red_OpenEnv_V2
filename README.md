# Pokemon Red OpenEnv

A production-oriented OpenEnv environment for Pokemon Red using PyBoy.

## What is implemented

- OpenEnv-compliant environment (`reset`, `step`, `state`) with WebSocket transport.
- PyBoy-backed execution with RAM-derived `game_state` per step.
- Modular reward system with configurable components.
- Action space with optional `SELECT` and `NOOP` always appended as the final action.
- Canonical state aliases backed by existing `pokemonred_puffer/pyboy_states` files.

## Installation

```bash
uv sync
```

## ROM requirement (legal)

This repository does not ship the Pokemon Red ROM.

You must provide your own legally obtained `.gb` file and place it in the root directory of the repository.



or set:

`POKEMON_RED_GB_PATH=/absolute/path/to/your/PokemonRed.gb`

Search the web for legal guidance on dumping your own cartridge in your region.

For Docker usage, mount your ROM file into the container and set:

`POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb`

## Run tests

```bash
uv run pytest -q
uv run pytest --cov=pokemon_red_env --cov-report=term-missing
```

## Validate OpenEnv manifest

```bash
uv run openenv validate --verbose .
```

## Run server

```bash
uv run uvicorn pokemon_red_env.server.app:app --host 0.0.0.0 --port 8000
```

## Docker usage

Build image:

```bash
uv run openenv build -t pokemon-red-openenv:latest
```

Run image with your legally obtained ROM mounted:

```bash
docker run --rm -p 8000:8000 \
  -v /absolute/path/to/your/PokemonRed.gb:/app/roms/PokemonRed.gb:ro \
  -e POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb \
  pokemon-red-openenv:latest
```

## Client example

```python
import asyncio
from pokemon_red_env import PokemonRedAction, PokemonRedEnv

async def main():
    async with PokemonRedEnv(base_url="http://localhost:8000") as env:
        result = await env.reset(init_state="game_start")
        while not result.done:
            # Example: NOOP is final index in legal_actions
            noop_action = result.observation.legal_actions[-1]
            result = await env.step(PokemonRedAction(action=noop_action))

asyncio.run(main())
```

## Random action demos

Run local client/server demo (spawns uvicorn automatically):

```bash
uv run demo.py
```

Run Docker demo (builds image on first run, then starts a container):

```bash
uv run demo_docker.py
```

Both demos run a dummy random-action agent for 100 steps by default and render
the game frames in your terminal.

## Action mapping

Default (`include_select=false`, `include_noop=true`):

- `0 up`
- `1 down`
- `2 left`
- `3 right`
- `4 a`
- `5 b`
- `6 start`
- `7 noop`

With `include_select=true`:

- `0 up`
- `1 down`
- `2 left`
- `3 right`
- `4 a`
- `5 b`
- `6 start`
- `7 select`
- `8 noop`

## State aliases

- `game_start` -> `home.state`
- `has_starter` -> `Bulbasaur.state`
- `has_pokedex` -> `has_pokedex.state`

These resolve against:

`/Users/neo/Desktop/My_Projects/Open_Source/OpenEnv/OpenEnv_Challenege/Pokemon_Red_OpenEnv_V2/pokemonred_puffer/pyboy_states`

## Notes

- OpenEnv dependency is pinned to latest upstream GitHub `main` via `openenv-core` source config.
- `pokered.sym` is treated as the source of truth for RAM addresses.
