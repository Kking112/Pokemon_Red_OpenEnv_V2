# Pokemon Red OpenEnv

A production-oriented OpenEnv environment for Pokemon Red using PyBoy.

## What is implemented

- OpenEnv-compliant environment (`reset`, `step`, `state`) with WebSocket transport.
- PyBoy-backed execution with RAM-derived `game_state` per step.
- Modular reward system with configurable components.
- Action space with optional `SELECT` and `NOOP` always appended as the final action.
- Canonical state aliases backed by `.state` files in `pokemon_red_env/states/`.

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
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
```

## Parallel sessions

Set a higher concurrency limit for headless runs:

```bash
POKEMON_RED_MAX_CONCURRENT_ENVS=8 uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
```

OpenEnv creates one environment instance per WebSocket session.

- Works with `POKEMON_RED_HEADLESS=true`.
- In windowed mode (`POKEMON_RED_HEADLESS=false`), concurrency is forced to `1` and a warning is logged.

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
        result = await env.reset(init_state="has_pokedex")
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

Run with standard PyBoy window rendering (default; use `--headless` to keep it off-screen):

```bash
uv run demo_docker.py
```

Both demos run a dummy random-action agent for 100 steps by default and use the
standard PyBoy window (`window="SDL2"`) unless `--headless` is passed.

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

## Reward knobs

- Parallel env sessions: `POKEMON_RED_MAX_CONCURRENT_ENVS`
- Exploration novelty: `POKEMON_RED_EXPLORATION_WEIGHT`
- Early movement bonus: `POKEMON_RED_MOVEMENT_BONUS_WEIGHT`
- Early movement anneal steps: `POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS`
- Menu novelty: `POKEMON_RED_MENU_NOVELTY_WEIGHT`
- Menu interaction: `POKEMON_RED_MENU_INTERACTION_WEIGHT`
- Menu anneal steps: `POKEMON_RED_MENU_ANNEAL_STEPS`
- Menu novelty cap: `POKEMON_RED_MAX_MENU_SIGNATURES_PER_EPISODE`

## State aliases

- Default: `has_pokedex`

- `game_start` -> `home.state`
- `has_starter` -> `Bulbasaur.state`
- `has_pokedex` -> `has_pokedex.state`

These resolve against:

`pokemon_red_env/states/*.state`

## Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System architecture, component diagram, data flow, and design decisions |
| [Configuration](docs/configuration.md) | Complete reference for all `POKEMON_RED_*` environment variables |
| [Reward System](docs/reward-system.md) | Modular reward components, annealing mechanics, and extension guide |
| [Memory & Game State](docs/memory-and-game-state.md) | RAM address system, memory reader, state extraction, and temporal awareness |
| [Environment API](docs/environment-api.md) | Environment interface, action space, observations, and state aliases |
| [Server & Client](docs/server-and-client.md) | WebSocket server, client usage, concurrency, and OpenEnv validation |
| [Deployment](docs/deployment.md) | Setup, Docker, demo scripts, testing, and troubleshooting |

Development history is preserved in `docs/development_phases/`.

## Notes

- OpenEnv dependency is pinned to latest upstream GitHub `main` via `openenv-core` source config.
- `pokered.sym` is treated as the source of truth for RAM addresses.
- Much of the design of this environment is based off of the following two repositories: 1. https://github.com/drubinstein/pokemonred_puffer 2. https://github.com/PWhiddy/PokemonRedExperiments
- Additionally, significant credit given to the pred team: https://github.com/pret/pokered
