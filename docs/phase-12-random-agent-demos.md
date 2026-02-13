# Phase 12 - Random Agent Demo Scripts (Local + Docker)

## Why this phase exists

You requested two runnable demo entrypoints for this environment:

1. `demo.py` for the regular local client/server flow.
2. `demo_docker.py` for the Docker-container server flow.

Both demos needed to:

- Use a dummy policy (random legal actions).
- Run a single environment instance for 100 steps.
- Display gameplay to the user in the standard PyBoy window by default.
- Execute without errors.

## Implemented changes

### 1) Added shared demo utility module: `demo_common.py`

Implemented shared primitives used by both demo scripts:

- `find_free_port()`:
  - Chooses an available local TCP port for server/container binding.
- `wait_for_health(base_url, timeout_s, process=None)`:
  - Polls `/health` until the environment server is ready.
  - Detects early process exit when a local server process is passed.
- `run_random_episode(...)`:
  - Connects with `PokemonRedEnv` client.
  - Calls `reset(init_state=...)`.
  - Samples random actions from `observation.legal_actions`.
  - Steps for up to `steps` actions (default `100`).
  - Prints step/action/reward metadata.

### 2) Added `demo.py` (local client/server demo)

Created local demo entrypoint that:

- Spawns a local uvicorn server by default:
  - `uv run uvicorn pokemon_red_env.server.app:app --host 127.0.0.1 --port <port>`
- Sets ROM path via `POKEMON_RED_GB_PATH`.
- Waits for `/health`.
- Runs random-action episode for `100` steps by default.
- Uses `POKEMON_RED_HEADLESS=false` unless `--headless` is passed.
- Cleans up the uvicorn process on exit.

CLI options include:

- `--steps` (default `100`)
- `--init-state` (default `game_start`)
- `--seed`
- `--fps`
- `--headless`
- `--rom-path`
- `--port`
- `--use-existing-server` + `--base-url`
- `--server-timeout-s`

### 3) Added `demo_docker.py` (Docker-backed demo)

Created Docker demo entrypoint that:

- Verifies Docker availability.
- Builds image when needed (or when forced):
  - `uv run openenv build -t <image>`
- Starts containerized server with ROM mount:
  - Host ROM -> `/app/roms/PokemonRed.gb` (read-only)
- `POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb`
- `POKEMON_RED_HEADLESS` set by `--headless` flag (default `false`)
- Waits for `/health`.
- Runs random-action episode for `100` steps by default.
- Uses PyBoy `SDL2` window mode when `--headless` is omitted.
- Stops container on exit (unless `--keep-container` is used).

CLI options include:

- `--steps` (default `100`)
- `--init-state` (default `game_start`)
- `--seed`
- `--fps`
- `--headless`
- `--rom-path`
- `--image`
- `--force-build`
- `--skip-build`
- `--port`
- `--server-timeout-s`
- `--keep-container`

### 4) Updated `README.md`

Added a "Random action demos" section with direct commands:

 - `uv run demo.py`
- `uv run demo_docker.py`

and clarified both run a random dummy agent for 100 steps with standard window rendering by default.

## Validation / test-debug-retest cycle

### Code quality + regression checks

1. `uv run ruff check demo.py demo_common.py demo_docker.py README.md`
   - Result: passed.
2. `uv run pytest -q`
   - Result: passed (`14 passed`).
3. `uv run openenv validate --verbose .`
   - Result: passed (`docker`, `openenv_serve`, `uv_run`, `python_module` all YES).

### Demo smoke tests

1. Local demo short run:
   - `uv run demo.py --steps 5 --fps 0 --headless`
   - Result: passed; 5 random steps executed in headless mode.
2. Docker demo short run:
   - `uv run demo_docker.py --steps 5 --fps 0 --headless`
   - Result: passed; image build succeeded, container started, 5 steps executed in headless mode.

### Final requested-behavior verification (100 steps)

1. Local demo full default-step run:
   - `uv run demo.py --fps 0 --headless`
   - Result: passed; completed 100 random steps in headless mode.
2. Docker demo full default-step run:
   - `uv run demo_docker.py --fps 0 --headless --skip-build`
   - Result: passed; completed 100 random steps in headless mode, no errors.

## Notes

- Both demos intentionally use a dummy random policy and only sample from legal action indices returned by the environment.
- Default rendering behavior is windowed PyBoy mode (`headless=False`). Headless mode stays supported via `--headless`.
