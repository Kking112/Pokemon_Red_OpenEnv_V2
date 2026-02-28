# Deployment Guide

This guide covers everything needed to get Pokemon Red OpenEnv V2 running locally, in Docker, and verified for production use.

---

## Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 used in Docker image |
| [uv](https://docs.astral.sh/uv/) | latest | Package manager and task runner |
| Docker | any recent | Required only for Docker deployment |
| Pokemon Red ROM | N/A | Legal `.gb` file you must supply yourself |

Install `uv` if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## ROM Policy (Legal Requirement)

**This repository does not ship the Pokemon Red ROM file and never will.**

You must provide your own legally obtained `.gb` ROM file. Owning a legitimate cartridge and dumping it yourself is the most common legal path; consult the laws in your region for specifics.

The repository enforces this policy at multiple levels:

- `PokemonRed.gb` is listed in `.gitignore`, preventing it from being committed to version control.
- `PokemonRed.gb` is listed in `.dockerignore`, preventing it from being bundled into any Docker image build context.
- The Dockerfile mounts the ROM at runtime (`/app/roms/`) rather than copying it during build.
- The server raises a startup error if `POKEMON_RED_FAIL_FAST_ON_MISSING_ROM=true` (the default) and the ROM file is not found.

The ROM path is configurable via the `POKEMON_RED_GB_PATH` environment variable. The default lookup path is `<repo root>/PokemonRed.gb`.

---

## Local Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Pokemon_Red_OpenEnv_V2
```

### 2. Install dependencies

```bash
uv sync
```

This installs all runtime and development dependencies declared in `pyproject.toml`, including `openenv-core` (pinned to the upstream GitHub `main` branch), `pyboy`, `uvicorn`, `pydantic`, `numpy`, `pillow`, and dev tools (`pytest`, `ruff`, `pytest-cov`).

### 3. Set the ROM path

Place your legally obtained `PokemonRed.gb` in the repository root, or point the environment variable to its absolute path:

```bash
export POKEMON_RED_GB_PATH=/absolute/path/to/your/PokemonRed.gb
```

You can also write this to a `.env` file in the repository root. Pydantic Settings will pick it up automatically:

```dotenv
POKEMON_RED_GB_PATH=/absolute/path/to/your/PokemonRed.gb
```

### 4. Verify installation

```bash
uv run pytest -q
```

All tests should pass. The test suite mocks PyBoy and does not require the ROM file to be present.

---

## Running the Server Locally

Start the OpenEnv server with `uvicorn`:

```bash
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
```

The server starts listening on port 8000. The health endpoint is available at `http://localhost:8000/health`.

### Common environment variable overrides

```bash
# Headless mode (required for multi-session and CI)
POKEMON_RED_HEADLESS=true uv run uvicorn server.app:app --host 0.0.0.0 --port 8000

# Parallel sessions (headless required for > 1)
POKEMON_RED_HEADLESS=true \
POKEMON_RED_MAX_CONCURRENT_ENVS=8 \
POKEMON_RED_GB_PATH=/path/to/PokemonRed.gb \
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000

# Windowed single-session for interactive debugging
POKEMON_RED_HEADLESS=false \
POKEMON_RED_GB_PATH=/path/to/PokemonRed.gb \
uv run uvicorn server.app:app --host 127.0.0.1 --port 8000
```

See `docs/configuration.md` for the complete list of environment variables and their defaults.

---

## Docker Deployment

### Dockerfile architecture

The `server/Dockerfile` uses a two-stage build:

1. **Builder stage** (`python:3.12-slim`): installs `git`, `ca-certificates`, and `uv`, then runs `uv sync` with the lockfile (`uv.lock`) if present, or falls back to a fresh resolve. The virtual environment is built into `/app/env/.venv`.
2. **Runtime stage** (`python:3.12-slim`): copies the compiled virtual environment and source tree from the builder. The PATH is set to use the virtual environment's binaries. No build tools are present in the final image.

Runtime defaults set in the image:

| Variable | Default in image |
|---|---|
| `POKEMON_RED_GB_PATH` | `/app/roms/PokemonRed.gb` |
| `POKEMON_RED_SYMBOLS_PATH` | `/app/env/Assembly_RAM_Addresses/pokered.sym` |
| `POKEMON_RED_STATE_DIR` | `/app/env/pokemonred_puffer/pyboy_states` |

The ROM mount point `/app/roms/` is created during build but is empty; you supply the ROM at `docker run` time.

Port 8000 is exposed. A health check polls `http://localhost:8000/health` every 30 seconds with a 5-second timeout, starting after 10 seconds, with 3 retries before the container is marked unhealthy.

### Building the image

Use the OpenEnv CLI wrapper:

```bash
uv run openenv build -t pokemon-red-openenv:latest
```

This invokes Docker build via the OpenEnv manifest and tags the resulting image.

### Running the container

Mount your ROM file into the container and set the ROM path environment variable:

```bash
docker run --rm -p 8000:8000 \
  -v /absolute/path/to/your/PokemonRed.gb:/app/roms/PokemonRed.gb:ro \
  -e POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb \
  pokemon-red-openenv:latest
```

The ROM is mounted read-only (`:ro`). The container image itself contains no ROM data.

### Multi-session headless container

```bash
docker run --rm -p 8000:8000 \
  -v /absolute/path/to/your/PokemonRed.gb:/app/roms/PokemonRed.gb:ro \
  -e POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb \
  -e POKEMON_RED_HEADLESS=true \
  -e POKEMON_RED_MAX_CONCURRENT_ENVS=8 \
  pokemon-red-openenv:latest
```

### Health check behavior

The container reports `healthy` once `GET /health` returns HTTP 200. The check runs:

- Start period: 10 seconds (no checks during startup)
- Interval: every 30 seconds
- Timeout: 5 seconds per check
- Retries: 3 failures before `unhealthy`

---

## Demo Scripts

Two ready-to-run demo scripts are provided. Both run a random-action policy for 100 steps by default and use the standard PyBoy SDL2 window unless `--headless` is passed.

### `demo.py` - Local server demo

Spawns a local `uvicorn` server automatically, runs the random agent, then shuts the server down on exit.

```bash
# Default: 100 steps, windowed PyBoy rendering
uv run demo.py --rom-path /path/to/PokemonRed.gb

# Headless, fast (no frame delay)
uv run demo.py --headless --fps 0 --rom-path /path/to/PokemonRed.gb

# Connect to an already-running server
uv run demo.py --use-existing-server --base-url http://127.0.0.1:8000
```

CLI arguments:

| Argument | Default | Description |
|---|---|---|
| `--steps` | `100` | Number of random actions to take |
| `--init-state` | `has_pokedex` | Save-state alias or filename to reset into |
| `--seed` | `0` | Random seed for action sampling |
| `--fps` | `6.0` | Render speed; `0` = as fast as possible |
| `--headless` | off | Run PyBoy without a display window |
| `--rom-path` | `./PokemonRed.gb` | Path to a legal `.gb` ROM file |
| `--port` | `0` (auto) | Port for the spawned server; `0` picks a free port |
| `--base-url` | `http://127.0.0.1:8000` | Base URL when `--use-existing-server` is set |
| `--use-existing-server` | off | Skip launching uvicorn; connect to a running server |
| `--server-timeout-s` | `60.0` | Seconds to wait for the server health check before failing |

### `demo_docker.py` - Docker server demo

Builds the Docker image if needed, starts a container, runs the random agent, then stops the container on exit.

```bash
# Default: build if needed, 100 steps, windowed (SDL2 window from container)
uv run demo_docker.py --rom-path /path/to/PokemonRed.gb

# Headless, fast
uv run demo_docker.py --headless --fps 0 --rom-path /path/to/PokemonRed.gb

# Skip rebuild if image exists
uv run demo_docker.py --skip-build --headless --rom-path /path/to/PokemonRed.gb

# Force rebuild before running
uv run demo_docker.py --force-build --rom-path /path/to/PokemonRed.gb

# Keep the container alive after the demo finishes
uv run demo_docker.py --keep-container --rom-path /path/to/PokemonRed.gb
```

CLI arguments:

| Argument | Default | Description |
|---|---|---|
| `--steps` | `100` | Number of random actions to take |
| `--init-state` | `has_pokedex` | Save-state alias or filename to reset into |
| `--seed` | `0` | Random seed for action sampling |
| `--fps` | `6.0` | Render speed; `0` = as fast as possible |
| `--headless` | off | Run PyBoy in headless mode inside the container |
| `--rom-path` | `./PokemonRed.gb` | Path to a legal `.gb` ROM file on the host |
| `--image` | `pokemon-red-openenv:latest` | Docker image name to use or build |
| `--force-build` | off | Always rebuild the Docker image before running |
| `--skip-build` | off | Never build; fail if the image does not exist |
| `--port` | `0` (auto) | Host port to expose the container on; `0` picks a free port |
| `--server-timeout-s` | `90.0` | Seconds to wait for container health before failing |
| `--keep-container` | off | Leave the container running after the demo exits |

### `demo_common.py` - Shared utilities

Both demo scripts import shared primitives from `demo_common.py`:

- `find_free_port()`: binds to port 0 on `127.0.0.1` and returns the OS-assigned port number. Used when `--port 0` is specified.
- `wait_for_health(base_url, timeout_s, process=None)`: polls `GET /health` every 250 ms until HTTP 200 is returned or `timeout_s` elapses. If a subprocess handle is passed, it also detects early process exit and raises immediately.
- `run_random_episode(base_url, steps, init_state, seed, fps, label)`: async coroutine that connects via `PokemonRedEnv`, calls `reset(init_state=...)`, then samples random actions from `observation.legal_actions` for up to `steps` steps. Prints per-step `action/reward/total_reward/done` output. Returns `(steps_executed, episode_done)`.

---

## Testing

### Run all tests

```bash
uv run pytest -q
```

Expected output: all tests pass. The test suite mocks PyBoy and does not require a real ROM file.

### Run with coverage

```bash
uv run pytest --cov=pokemon_red_env --cov-report=term-missing
```

### Run linting

```bash
uv run ruff check pokemon_red_env tests
```

To also lint the demo scripts and server:

```bash
uv run ruff check pokemon_red_env tests server demo.py demo_common.py demo_docker.py
```

### Test suite overview

The `tests/` directory contains 8 test files plus `conftest.py`:

| File | What it covers |
|---|---|
| `test_action_space.py` | Action schema bounds: valid indices 0-7, invalid index 8+ rejected |
| `test_app_concurrency.py` | Session creation, max concurrency enforcement, windowed-mode warning, multi-WebSocket sessions |
| `test_client.py` | `PokemonRedEnv` client: reset, step, context manager lifecycle |
| `test_config.py` | Pydantic validation rules: concurrency bounds, reward weight constraints, timing constraints |
| `test_environment.py` | Full `reset`/`step` cycle, observation structure, action rejection for out-of-range values |
| `test_memory_reader.py` | RAM reader: symbol resolution, badge extraction, map ID parsing |
| `test_rewards.py` | All reward components: movement anneal, exploration novelty, menu novelty with reset, menu interaction decay |
| `test_state_deltas.py` | State delta computation: only changed fields included, empty delta on unchanged state |
| `conftest.py` | Shared fixtures: mock PyBoy, mock ROM path, mock config |

---

## OpenEnv Validation

The OpenEnv CLI validates the environment manifest and checks that all declared deployment modes are structurally correct:

```bash
uv run openenv validate --verbose .
```

This checks four modes:

| Mode | What it validates |
|---|---|
| `docker` | `server/Dockerfile` exists and `openenv build` can produce a valid image |
| `openenv_serve` | The server module exports a valid ASGI app at `server.app:app` |
| `uv_run` | The package is runnable via `uv run` |
| `python_module` | The package is importable as a Python module |

All four modes must report `YES` for the environment to be considered release-ready.

---

## Troubleshooting

### ROM not found at startup

**Symptom:** Server raises `FileNotFoundError` or `ValidationError` mentioning the ROM path on startup.

**Fix:** Set `POKEMON_RED_GB_PATH` to the absolute path of your legally obtained `.gb` file:

```bash
export POKEMON_RED_GB_PATH=/absolute/path/to/PokemonRed.gb
```

If you only need to run tests (which mock PyBoy), set `POKEMON_RED_FAIL_FAST_ON_MISSING_ROM=false` to suppress the startup check.

---

### PyBoy display errors in headless mode

**Symptom:** Error mentioning `SDL2`, `display`, or `window` when running on a server without a display.

**Fix:** Ensure headless mode is active:

```bash
export POKEMON_RED_HEADLESS=true
```

In Docker, the image defaults to the headless configuration set by `POKEMON_RED_HEADLESS`. If you pass `--headless` to the demo scripts, they propagate `-e POKEMON_RED_HEADLESS=true` to the container automatically.

---

### Port already in use

**Symptom:** `uvicorn` fails to bind with `OSError: [Errno 98] Address already in use`.

**Fix:** Change the port:

```bash
uv run uvicorn server.app:app --host 0.0.0.0 --port 8001
```

Or use the demo scripts with `--port 0` to let the OS pick a free port automatically.

---

### Docker build failures

**Symptom:** `uv run openenv build` exits non-zero during dependency installation.

Common causes and fixes:

- **No internet access in build context:** The Dockerfile installs `openenv-core` from GitHub. Ensure the build machine has outbound internet access on HTTPS (port 443).
- **`git` not found:** The builder stage installs `git` via `apt-get`. If the base image or network is unavailable, this step fails. Verify `apt-get` is reachable.
- **Stale lockfile:** If `uv.lock` is present but out of sync with `pyproject.toml`, the `--frozen` sync will fail. Run `uv lock` locally to regenerate the lockfile, then rebuild.

---

### OpenEnv validation failures

**Symptom:** `uv run openenv validate --verbose .` reports one or more modes as `NO`.

| Failing mode | Likely cause | Fix |
|---|---|---|
| `docker` | `server/Dockerfile` missing or `openenv build` fails | Ensure the Dockerfile is present and Docker is running |
| `openenv_serve` | `server.app:app` not importable or missing ASGI interface | Check for import errors: `uv run python -c "from server.app import app"` |
| `uv_run` | Package not installable | Run `uv sync` and check for dependency errors |
| `python_module` | `pokemon_red_env` package not importable | Run `uv run python -c "import pokemon_red_env"` and check for missing files |

---

### Windowed mode with multiple sessions

**Symptom:** Warning logged: `Windowed mode does not support concurrent sessions; clamping max_concurrent_envs to 1.`

**Explanation:** PyBoy's SDL2 renderer is single-threaded and cannot run more than one window per process. Setting `POKEMON_RED_MAX_CONCURRENT_ENVS > 1` while `POKEMON_RED_HEADLESS=false` is a configuration conflict. The server enforces this by clamping concurrency to 1 and logging a warning.

**Fix:** Enable headless mode for any multi-session deployment:

```bash
POKEMON_RED_HEADLESS=true POKEMON_RED_MAX_CONCURRENT_ENVS=8 uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
```
