# Server and Client

This document covers the WebSocket server/client architecture used by Pokemon Red OpenEnv V2, how sessions are managed, how concurrency is controlled, and how the OpenEnv manifest is structured.

---

## Overview

Pokemon Red OpenEnv V2 uses [OpenEnv](https://github.com/meta-pytorch/OpenEnv)'s WebSocket transport layer to expose the emulator environment as a network service. A policy (agent) connects to the server as a client, sends discrete actions over WebSocket, and receives observations containing screen frames and RAM-derived game state in return.

This design decouples the emulator process from the learning process: the server runs PyBoy and manages emulator state, while one or more clients communicate with it over HTTP/WebSocket from any language or host.

---

## Server Architecture

### `create_pokemon_app()`

The primary server factory is `create_pokemon_app()` in `pokemon_red_env/server/app.py`. It wraps OpenEnv's generic `create_app()` with Pokemon-specific type bindings and configuration resolution.

```python
def create_pokemon_app(
    config: PokemonRedConfig | None = None,
    environment_factory: Callable[[], PokemonRedEnvironment] | None = None,
):
    resolved_config = config or PokemonRedConfig()
    max_concurrent_envs = _resolve_concurrency_limit(resolved_config)
    if environment_factory is None:
        def environment_factory() -> PokemonRedEnvironment:
            return PokemonRedEnvironment(config=resolved_config)

    return create_app(
        environment_factory,
        PokemonRedAction,
        PokemonRedObservation,
        env_name="pokemon_red",
        max_concurrent_envs=max_concurrent_envs,
    )
```

`create_app()` from `openenv.core.env_server` produces an ASGI application that:

- Accepts WebSocket connections at the session endpoint.
- Enforces the maximum concurrent session limit.
- Dispatches `reset` and `step` messages to the environment factory's instances.
- Serves type-validated observations back to clients.

The `environment_factory` argument is a zero-argument callable that must return a fresh `PokemonRedEnvironment` instance. OpenEnv calls it once per WebSocket session, so each connected client gets its own independent PyBoy instance.

### `create_pokemon_environment()`

A convenience helper for direct instantiation without standing up the full ASGI stack:

```python
def create_pokemon_environment() -> PokemonRedEnvironment:
    config = PokemonRedConfig()
    return PokemonRedEnvironment(config=config)
```

This is useful for testing or for embedding the environment directly in a training loop without a network hop.

### The `app` Singleton

The module-level `app` object at the bottom of `app.py` is the ASGI application instance that ASGI servers (uvicorn, gunicorn with uvicorn workers) load:

```python
app = create_pokemon_app()
```

This singleton is what `openenv.yaml` points to as `pokemon_red_env.server.app:app`. It is constructed once at import time using the configuration resolved from environment variables at that moment.

### Exports

`pokemon_red_env/server/__init__.py` exports the three public symbols:

```python
from .app import create_pokemon_app, create_pokemon_environment
from .environment import PokemonRedEnvironment
```

---

## Running the Server

### Local Development

Start the server with uvicorn directly from the repository root:

```bash
uv run uvicorn pokemon_red_env.server.app:app --host 0.0.0.0 --port 8000
```

The module path `pokemon_red_env.server.app:app` resolves to the `app` singleton exported by the server package. uvicorn must be able to import the package, so run this command from the repository root where `pyproject.toml` resides.

### Custom Configuration via Environment Variables

All configuration fields in `PokemonRedConfig` are read from environment variables at startup using the `POKEMON_RED_` prefix. Override any setting by prefixing the field name:

```bash
POKEMON_RED_HEADLESS=true \
POKEMON_RED_MAX_CONCURRENT_ENVS=4 \
POKEMON_RED_GB_PATH=/path/to/PokemonRed.gb \
uv run uvicorn pokemon_red_env.server.app:app --host 0.0.0.0 --port 8000
```

Key configuration variables:

| Variable | Default | Description |
|---|---|---|
| `POKEMON_RED_HEADLESS` | `true` | Run PyBoy without a display window |
| `POKEMON_RED_GB_PATH` | `./PokemonRed.gb` | Path to the ROM file |
| `POKEMON_RED_MAX_CONCURRENT_ENVS` | `1` | Maximum simultaneous sessions |
| `POKEMON_RED_INIT_STATE` | `has_pokedex` | Default save state alias |
| `POKEMON_RED_MAX_STEPS` | `163840` | Steps before episode auto-terminates |
| `POKEMON_RED_SCREEN_DOWNSCALE` | `1` | Integer downscale factor for screen frames |
| `POKEMON_RED_INCLUDE_GAME_STATE` | `true` | Include RAM-derived game state in observations |
| `POKEMON_RED_INCLUDE_STATE_DELTAS` | `true` | Include per-step state deltas in observations |

### Health Check

The OpenEnv server exposes a health check endpoint. Query it to confirm the server is ready before connecting clients:

```bash
curl http://localhost:8000/health
```

A successful response confirms the ASGI application is running and accepting connections.

---

## WebSocket Transport

OpenEnv's WebSocket protocol handles session lifecycle, message framing, and serialization automatically. From the application's perspective, the flow is:

1. **Session creation**: the client connects to the server's WebSocket endpoint. OpenEnv calls the `environment_factory` to instantiate a fresh `PokemonRedEnvironment` for that connection. The session is tracked until the WebSocket closes.

2. **Reset message**: the client sends a `reset` command (optionally including `init_state`, `seed`, or `episode_id`). The server calls `environment.reset()` and returns a serialized `PokemonRedObservation` as the first step result.

3. **Step message**: the client sends a `step` command containing a serialized `PokemonRedAction`. The server calls `environment.step(action)` and returns the resulting `PokemonRedObservation` along with `reward` and `done` fields.

4. **State message**: the client may request the current internal state. The server returns a serialized `PokemonRedState`.

5. **Session teardown**: when the WebSocket connection closes (client disconnect or server shutdown), the environment's `close()` method is called, stopping the underlying PyBoy instance.

All messages are JSON-serialized Pydantic models. OpenEnv handles framing and error propagation; the application layer only defines the typed models.

---

## Client Usage

### `PokemonRedEnv` Class

`PokemonRedEnv` in `pokemon_red_env/client.py` extends OpenEnv's generic `EnvClient` with Pokemon-specific type bindings:

```python
class PokemonRedEnv(EnvClient[PokemonRedAction, PokemonRedObservation, PokemonRedState]):
    ...
```

It is the standard interface for connecting to a running server from Python.

### `_step_payload()`

Converts a `PokemonRedAction` into the JSON-serializable dict sent over WebSocket:

```python
def _step_payload(self, action: PokemonRedAction) -> dict[str, Any]:
    return action.model_dump()
```

This produces `{"action": <int>}` for the transport layer.

### `_parse_result()`

Deserializes the server's step response into a typed `StepResult[PokemonRedObservation]`:

```python
def _parse_result(self, payload: dict[str, Any]) -> StepResult[PokemonRedObservation]:
    obs_data = payload.get("observation", {})
    obs_payload = dict(obs_data)
    obs_payload["reward"] = payload.get("reward")
    obs_payload["done"] = payload.get("done", False)

    observation = PokemonRedObservation.model_validate(obs_payload)
    return StepResult(
        observation=observation,
        reward=float(payload.get("reward")) if payload.get("reward") is not None else None,
        done=bool(payload.get("done", False)),
    )
```

### `_parse_state()`

Deserializes the server's state response into a `PokemonRedState` checkpoint:

```python
def _parse_state(self, payload: dict[str, Any]) -> PokemonRedState:
    return PokemonRedState.model_validate(payload)
```

`PokemonRedState` carries `total_reward`, `current_init_state`, `last_action`, and `done`.

### `reset()` with `init_state`

The client's `reset()` method accepts an optional `init_state` parameter that selects the save state alias to load on the server side:

```python
async def reset(
    self,
    seed: int | None = None,
    episode_id: str | None = None,
    init_state: str | None = None,
    **kwargs: Any,
) -> StepResult[PokemonRedObservation]:
```

Passing `init_state="game_start"` loads the earliest canonical state. Passing `None` falls back to the server's configured default (`POKEMON_RED_INIT_STATE`, default `has_pokedex`).

### Example Usage

```python
import asyncio
from pokemon_red_env import PokemonRedAction, PokemonRedEnv

async def main():
    async with PokemonRedEnv(base_url="http://localhost:8000") as env:
        # Reset to the default save state
        result = await env.reset(init_state="has_pokedex")
        print(f"Episode started: {result.observation.info.get('episode_id')}")

        step_count = 0
        while not result.done:
            # Use legal_actions from the observation to avoid invalid action errors
            noop_action = result.observation.legal_actions[-1]
            result = await env.step(PokemonRedAction(action=noop_action))
            step_count += 1

        print(f"Episode done after {step_count} steps, reward={result.reward}")

asyncio.run(main())
```

The `async with` block opens the WebSocket connection, and the context manager closes it cleanly when exiting. Each `reset()` call starts a new episode on the same server-side session.

---

## Session Management

OpenEnv creates one `PokemonRedEnvironment` instance per active WebSocket connection. Sessions are entirely independent: each has its own PyBoy emulator instance, its own memory reader, its own reward manager state, and its own episode counter.

When a client connects, the server-side session lifecycle is:

1. `environment_factory()` is called; a new `PokemonRedEnvironment` is constructed and a fresh PyBoy emulator is started.
2. The client sends `reset` to load a save state and start the first episode.
3. The client sends repeated `step` messages; each advances the emulator by `action_freq` ticks (default: 24).
4. When the WebSocket closes, `environment.close()` stops PyBoy with `save=False`.

Session state is not persisted between connections. If a client disconnects mid-episode and reconnects, a new environment instance is created and a fresh `reset()` is required.

---

## Concurrency Control

### `max_concurrent_envs` Configuration

The number of simultaneous sessions the server will accept is controlled by `POKEMON_RED_MAX_CONCURRENT_ENVS` (default: `1`). Set it to a higher integer to enable parallel training runs:

```bash
POKEMON_RED_MAX_CONCURRENT_ENVS=8 \
POKEMON_RED_HEADLESS=true \
uv run uvicorn pokemon_red_env.server.app:app --host 0.0.0.0 --port 8000
```

This value is passed directly to OpenEnv's `create_app()` as `max_concurrent_envs`. OpenEnv enforces the limit by rejecting new WebSocket connections once the cap is reached.

### `_resolve_concurrency_limit()` Logic

Before passing the limit to `create_app()`, the server runs it through `_resolve_concurrency_limit()`:

```python
def _resolve_concurrency_limit(config: PokemonRedConfig) -> int:
    max_concurrent_envs = max(1, int(config.max_concurrent_envs))
    if max_concurrent_envs <= 1:
        return 1

    if config.headless:
        return max_concurrent_envs

    LOGGER.warning(
        "Windowed PyBoy mode does not support multiple concurrent sessions; "
        "forcing max_concurrent_envs=1. Set POKEMON_RED_HEADLESS=true to enable it."
    )
    return 1
```

The rules are:

- The limit is always at least `1`.
- When `POKEMON_RED_HEADLESS=true`, the configured limit is used as-is.
- When `POKEMON_RED_HEADLESS=false` (windowed SDL2 mode) and the requested limit is greater than `1`, the limit is forced down to `1` and a warning is logged. Windowed PyBoy requires exclusive access to the SDL2 display surface and cannot safely multiplex across threads.

### `SUPPORTS_CONCURRENT_SESSIONS` Flag

`PokemonRedEnvironment` declares itself concurrency-safe at the class level:

```python
class PokemonRedEnvironment(
    Environment[PokemonRedAction, PokemonRedObservation, PokemonRedState]
):
    SUPPORTS_CONCURRENT_SESSIONS = True
```

This flag is an OpenEnv interface contract indicating that the environment implementation is safe to instantiate multiple times within the same process. Each instance manages its own PyBoy state without shared mutable globals. The server relies on this guarantee when creating one instance per session.

---

## OpenEnv Manifest

### Structure of `openenv.yaml`

The manifest file declares the package identity and the canonical entrypoints that OpenEnv's CLI and build tooling use to locate the server and client:

```yaml
name: pokemon_red_env
version: 0.1.0
description: Pokemon Red reinforcement learning environment powered by PyBoy and OpenEnv.
entrypoints:
  server: pokemon_red_env.server.app:app
  client: pokemon_red_env.client:PokemonRedEnv
```

- `server`: the ASGI application object. uvicorn and the OpenEnv build system use this dotted path to start the server.
- `client`: the `EnvClient` subclass. OpenEnv tooling uses this to identify the typed client for code generation or documentation.

### Why There Are Two Manifests

The repository contains two copies of `openenv.yaml` with identical contents:

| Path | Purpose |
|---|---|
| `openenv.yaml` (repository root) | Used by the OpenEnv CLI when run from the repository root (`uv run openenv validate --verbose .`) |
| `pokemon_red_env/openenv.yaml` | Bundled inside the package for distribution; used when the package is installed and the CLI resolves the manifest from the installed package tree |

The OpenEnv CLI resolves the manifest relative to the current working directory. Running validation from the repository root requires the root-level copy. The package-level copy ensures the manifest is available when the project is installed as a dependency or built into a Docker image with `uv run openenv build`.

---

## Validation

Run the OpenEnv CLI validator from the repository root to confirm the manifest, entrypoints, and importability are all correct:

```bash
uv run openenv validate --verbose .
```

The validator checks:

- `openenv.yaml` is present and well-formed.
- The `server` entrypoint resolves to an importable ASGI application.
- The `client` entrypoint resolves to an importable `EnvClient` subclass.
- The declared `name` and `version` fields are present.

A passing run produces output similar to:

```
Validating pokemon_red_env v0.1.0...
  server: pokemon_red_env.server.app:app ... ok
  client: pokemon_red_env.client:PokemonRedEnv ... ok
ready for multi-mode deployment
```

This validation step is part of the standard CI check sequence alongside `uv run pytest -q` and `uv run ruff check`.
