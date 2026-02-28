# Architecture: Pokemon Red OpenEnv V2

## 1. Project Overview

Pokemon Red OpenEnv V2 is a production-oriented reinforcement learning environment that wraps the original Game Boy game _Pokemon Red_ in an [OpenEnv](https://github.com/meta-pytorch/OpenEnv)-compliant server. An RL policy communicates with the environment over WebSocket, sending discrete button actions and receiving game-screen images and RAM-derived game-state observations in return.

The environment is backed by [PyBoy](https://github.com/Baekalfen/PyBoy), a cycle-accurate Game Boy emulator that exposes a Python API for input injection, frame capture, and direct RAM reads. OpenEnv provides the wire protocol, session lifecycle management, and HTTP/WebSocket server scaffolding. The project adds Pokemon-specific reward shaping, memory parsing, and a typed client.

Key properties:

- **OpenEnv-compliant** — implements `reset`, `step`, and `state` exactly as the OpenEnv `Environment` interface specifies.
- **Headless by default** — no display required; runs at maximum emulation speed for training.
- **Parallel sessions** — multiple independent WebSocket sessions can each run their own emulator instance when `POKEMON_RED_HEADLESS=true`.
- **Modular reward system** — individual reward components are registered at startup and are independently configurable via environment variables.
- **Temporal awareness** — each observation carries state deltas (changes since the previous step) and the reward received for the previous action, giving the policy a richer local context without requiring it to track its own history.

---

## 2. High-Level Architecture

```
+--------------------+
|   Pokemon Red ROM  |
|    PokemonRed.gb   |
+--------+-----------+
         |  loaded via pyboy.load_state()
         v
+--------------------+       tick / send_input
|   PyBoy Emulator   +<-------------------------------+
|  (Game Boy core)   |                                |
+--------+-----------+                                |
         |  pyboy.screen.ndarray / pyboy.memory[addr] |
         v                                            |
+---------------------+    +------------------------+ |
|   MemoryReader      |    |    ActionSpace         | |
|  (RAM address map,  |    |  (build_action_bindings| |
|   event flags,      |    |   ActionBinding list)  | |
|   map/event tables) |    +------------------------+ |
+--------+------------+                               |
         |  GameState dataclass                       |
         v                                            |
+--------------------+                               |
|   PokemonRed       |<--- RewardManager             |
|   Environment      |     (modular components)      |
|                    |                               |
|  reset() / step()  +-------------------------------+
|  state property    |    PyBoy input dispatch
+--------+-----------+
         |  PokemonRedObservation (screen_b64, game_state, reward, done)
         v
+--------------------+
|  OpenEnv Server    |
|  (uvicorn/ASGI,    |
|   WebSocket,       |
|   session routing) |
+--------+-----------+
         |  JSON over WebSocket
         v
+--------------------+
|   PokemonRedEnv    |
|   (typed client,   |
|    EnvClient base) |
+--------------------+
         |  StepResult[PokemonRedObservation]
         v
+--------------------+
|   RL Policy        |
+--------------------+
```

Data always flows downward during a step. The ROM is loaded once per session at `reset()`. Subsequent calls to `step()` inject button inputs into the running emulator and read the resulting RAM state without reloading.

---

## 3. Package Structure

```
pokemon_red_env/
├── __init__.py                 # Public exports: PokemonRedEnv, PokemonRedConfig, models, MemoryReader, Addresses
├── config.py                   # PokemonRedConfig — all runtime settings as Pydantic BaseSettings
├── models.py                   # PokemonRedAction, PokemonRedObservation, PokemonRedState (OpenEnv wire types)
├── action_space.py             # ActionBinding dataclass and build_action_bindings() factory
├── client.py                   # PokemonRedEnv — typed WebSocket client wrapping OpenEnv EnvClient
├── state_registry.py           # StateRegistry — alias resolution for PyBoy .state files
│
├── memory/
│   ├── __init__.py             # Re-exports MemoryReader
│   ├── addresses.py            # Addresses class with all known RAM address constants (AddressSpec)
│   ├── game_state.py           # GameState, PartyMemberState, BattleState, ProgressState dataclasses
│   └── reader.py               # MemoryReader — reads RAM bytes and assembles GameState
│
├── rewards/
│   ├── __init__.py             # Public exports for all reward classes
│   ├── base.py                 # BaseRewardComponent abstract class
│   ├── manager.py              # RewardManager — registers and aggregates components
│   ├── exploration.py          # ExplorationReward (novelty), ExplorationMovementReward (annealed early bonus)
│   ├── badges.py               # BadgeReward — reward per new gym badge earned
│   ├── levels.py               # LevelUpReward — reward per level gained across party
│   ├── events.py               # EventReward — reward per new game event flag set
│   ├── battle.py               # BattleWinReward — reward for winning a battle
│   ├── healing.py              # HealingReward — reward for recovering party HP
│   ├── menu.py                 # MenuNoveltyReward, MenuInteractionReward
│   └── movement.py             # MovementReward (legacy, not registered by default)
│
├── server/
│   ├── __init__.py             # Empty init
│   ├── app.py                  # create_pokemon_app() factory; module-level app instance
│   └── environment.py          # PokemonRedEnvironment — the OpenEnv Environment implementation
│
├── data/
│   ├── events.json             # Normalized event flag table (id, name, address, bit)
│   ├── maps.json               # Map ID → name lookup table
│   └── curated_events.json     # Ordered subset of events used in "curated" mode
│
└── states/
    ├── home.state              # Alias: game_start — title screen
    ├── Bulbasaur.state         # Alias: has_starter — just received first Pokemon
    └── has_pokedex.state       # Alias: has_pokedex (default) — received Pokedex from Oak
```

Supporting files at the repository root:

```
PokemonRed.gb                   # ROM (not shipped; must be provided by user)
Assembly_RAM_Addresses/
└── pokered.sym                 # Symbol file — source of truth for RAM address names
demo.py                         # Local demo: spawns server + random-action client
demo_docker.py                  # Docker-oriented demo variant
```

---

## 4. Core Data Flow

### 4.1 reset()

```
client.reset(init_state="has_pokedex")
    │
    ▼ WebSocket JSON → OpenEnv server
PokemonRedEnvironment.reset(init_state="has_pokedex")
    │
    ├─ 1. StateRegistry.resolve("has_pokedex")
    │      └─ maps alias → pokemon_red_env/states/has_pokedex.state
    │
    ├─ 2. pyboy.load_state(file_handle)
    │      Restores emulator RAM and registers to the saved checkpoint.
    │
    ├─ 3. pyboy.tick(1, render=True)
    │      Advance one frame to stabilize the display.
    │
    ├─ 4. reward_manager.reset()
    │      Clears episode-local state in each reward component.
    │
    ├─ 5. self._seen_coords.clear()
    │      Fresh exploration set for the new episode.
    │
    ├─ 6. PokemonRedState constructed
    │      episode_id = uuid4(), step_count = 0, total_reward = 0.0
    │
    ├─ 7. memory.extract_game_state(...)
    │      MemoryReader reads RAM → GameState dataclass → dict.
    │
    ├─ 8. _update_seen_coords(game_state)
    │      Adds (player_x, player_y, map_id) to seen_coords set.
    │
    ├─ 9. Temporal context initialised
    │      game_state["state_deltas"] = {}
    │      game_state["prev_step_reward"] = 0.0
    │      game_state["prev_action_name"] = ""
    │
    ├─ 10. _capture_screen()
    │       pyboy.screen.ndarray → RGBA strip → RGB → optional downscale → PNG → base64.
    │
    └─ 11. PokemonRedObservation returned
            screen_b64, screen_shape, game_state, legal_actions, reward=0.0, done=False
```

### 4.2 step()

```
client.step(PokemonRedAction(action=0))   # action 0 = "up"
    │
    ▼ WebSocket JSON → OpenEnv server
PokemonRedEnvironment.step(action)
    │
    ├─ 1. Guard: episode already done? → error_observation
    │
    ├─ 2. Validate action index in [0, len(action_bindings))
    │
    ├─ 3. _run_action(action_idx)
    │      ├─ ActionBinding.press_event sent to pyboy
    │      ├─ ActionBinding.release_event sent after press_duration frames
    │      └─ pyboy.tick(action_freq - 1, render=False)
    │         pyboy.tick(1, render=True)          # final frame rendered
    │
    ├─ 4. state.step_count += 1
    │
    ├─ 5. memory.extract_game_state(...)
    │      Same RAM-read pipeline as reset step 7.
    │
    ├─ 6. _update_seen_coords(game_state)
    │      Adds current (x, y, map_id) if not yet visited.
    │
    ├─ 7. Temporal awareness
    │      _compute_state_deltas(curr_state, prev_state)
    │      → delta_player_x, delta_player_y, delta_seen_coords_count,
    │        delta_badge_count, delta_level_sum, delta_event_count,
    │        delta_player_money, map_changed (bool), battle_started (bool)
    │      game_state["state_deltas"]   = computed deltas
    │      game_state["prev_step_reward"] = self._prev_reward
    │      game_state["prev_action_name"] = self._prev_action_name
    │
    ├─ 8. _calculate_reward(game_state)
    │      RewardManager.calculate(curr, prev) OR simple fallback
    │      → total float reward + per-component breakdown dict
    │
    ├─ 9. _check_done(game_state)
    │      step_count >= max_steps → "max_steps_reached"
    │      party_count > 0 AND sum(party_hp) == 0 → "blackout"
    │
    ├─ 10. _capture_screen()
    │       Same screen pipeline as reset.
    │
    ├─ 11. PokemonRedObservation returned
    │       info contains: action_name, reward_breakdown, done_reason
    │
    └─ 12. State bookkeeping
            self._prev_state_dict = dict(game_state)
            self._prev_reward = reward
            self._prev_action_name = action_name
```

---

## 5. OpenEnv Contract

`PokemonRedEnvironment` inherits from OpenEnv's `Environment[PokemonRedAction, PokemonRedObservation, PokemonRedState]` (from `openenv.core.env_server.interfaces`).

| OpenEnv method | Implementation | Notes |
|---|---|---|
| `reset(seed, episode_id, **kwargs)` | `_reset_impl` | `init_state` kwarg selects the PyBoy checkpoint |
| `step(action, timeout_s, **kwargs)` | `_step_impl` | `timeout_s` accepted but ignored; PyBoy is synchronous |
| `state` property | `self._state` | Returns `PokemonRedState` with `episode_id`, `step_count`, `total_reward`, `done` |
| `close()` | `pyboy.stop(save=False)` | Dispatches to main thread in windowed mode |

The class also sets `SUPPORTS_CONCURRENT_SESSIONS = True`, which tells the OpenEnv server that multiple WebSocket sessions may each create their own environment instance.

**Type contracts** (`pokemon_red_env/models.py`):

```python
class PokemonRedAction(Action):
    action: int = Field(ge=0, le=8)   # discrete index into action_bindings

class PokemonRedObservation(Observation):
    screen_b64: str                    # base64-encoded PNG frame
    screen_shape: list[int]            # [height, width, channels]
    game_state: dict[str, Any]         # RAM-derived fields + temporal context
    legal_actions: list[int]           # valid indices for current episode
    info: dict[str, Any]               # debug metadata

class PokemonRedState(State):
    total_reward: float
    current_init_state: str
    last_action: int | None
    done: bool
```

**Server entry point** (`pokemon_red_env/server/app.py`):

```python
def create_pokemon_app(
    config: PokemonRedConfig | None = None,
    environment_factory: Callable[[], PokemonRedEnvironment] | None = None,
):
    ...
    return create_app(
        environment_factory,
        PokemonRedAction,
        PokemonRedObservation,
        env_name="pokemon_red",
        max_concurrent_envs=max_concurrent_envs,
    )

app = create_pokemon_app()   # module-level instance for uvicorn
```

**Client** (`pokemon_red_env/client.py`):

```python
class PokemonRedEnv(EnvClient[PokemonRedAction, PokemonRedObservation, PokemonRedState]):
    async def reset(self, init_state: str | None = None, ...) -> StepResult[PokemonRedObservation]:
        ...
```

The client communicates over WebSocket, serialises actions via `model_dump()`, and deserialises responses with `PokemonRedObservation.model_validate()`.

---

## 6. Threading Model

PyBoy's SDL2-based windowed rendering must run on the OS main thread. Headless (`window="null"`) has no such constraint. The environment handles both modes transparently.

```python
# pokemon_red_env/server/environment.py

def __init__(self, config: PokemonRedConfig):
    self._main_thread_id = threading.get_ident()   # captured at construction time
    try:
        self._main_loop = asyncio.get_running_loop()
    except RuntimeError:
        self._main_loop = None

def reset(self, ...):
    if self.config.headless:
        return self._reset_impl(...)                   # direct call, any thread
    return self._dispatch_on_main_thread(self._reset_impl, ...)

def _dispatch_on_main_thread(self, func, *args, **kwargs):
    if threading.get_ident() == self._main_thread_id:
        return func(*args, **kwargs)                   # already on main thread
    future = asyncio.run_coroutine_threadsafe(
        self._run_on_main_loop(func, *args, **kwargs),
        self._main_loop,
    )
    return future.result()                             # blocks caller until done
```

**Headless mode** (default, `POKEMON_RED_HEADLESS=true`):

- PyBoy uses `window="null"` and `emulation_speed=0` (maximum speed).
- `reset()` and `step()` call `_reset_impl` / `_step_impl` directly on whichever thread the OpenEnv server dispatches to.
- Multiple concurrent sessions are supported; each session creates its own `PokemonRedEnvironment` and its own `PyBoy` instance.
- Concurrency limit is controlled by `POKEMON_RED_MAX_CONCURRENT_ENVS`.

**Windowed mode** (`POKEMON_RED_HEADLESS=false`):

- PyBoy uses `window="SDL2"` and normal emulation speed.
- All PyBoy calls are marshalled back to the main thread via `asyncio.run_coroutine_threadsafe`.
- `max_concurrent_envs` is forced to `1` regardless of configuration; a warning is logged.

---

## 7. Key Design Decisions

### 7.1 Modular Reward System

Rather than computing a single reward formula, all reward logic lives in independent `BaseRewardComponent` subclasses. Each component receives the current and previous game-state dicts and returns an unweighted float. The `RewardManager` applies each component's weight, sums the results, and applies the global `reward_scale`.

```
rewards/
  exploration.py   → ExplorationReward (exploration_novelty)
                   → ExplorationMovementReward (movement_bonus_early, annealed)
  badges.py        → BadgeReward
  levels.py        → LevelUpReward
  events.py        → EventReward
  battle.py        → BattleWinReward
  healing.py       → HealingReward
  menu.py          → MenuNoveltyReward, MenuInteractionReward
```

Default registration order matters for the breakdown dict but not for the total. Components can be disabled at runtime via `RewardManager.disable(name)` without touching configuration. A simple non-modular fallback path (`_calculate_simple_reward`) is retained for testing and is active when `use_modular_rewards=False`.

The full per-component breakdown is passed back to the client in `obs.info["reward_breakdown"]` every step, which simplifies debugging reward shaping without needing separate logging infrastructure.

### 7.2 Temporal Awareness

Every observation includes fields that describe _change_ since the previous step, rather than just current values:

```python
game_state["state_deltas"] = {
    "delta_player_x": ...,
    "delta_player_y": ...,
    "delta_seen_coords_count": ...,
    "delta_badge_count": ...,
    "delta_level_sum": ...,
    "delta_event_count": ...,
    "delta_player_money": ...,
    "map_changed": bool,
    "battle_started": bool,
}
game_state["prev_step_reward"] = <reward earned in the previous step>
game_state["prev_action_name"] = <name of the previous action, e.g. "up">
```

On `reset()` these fields are zeroed/empty so the policy always sees a consistent schema. This design means a policy using only the current observation can still reason about recent change without maintaining external state.

### 7.3 Exploration via seen_coords

The environment maintains `self._seen_coords: set[tuple[int, int, int]]` which accumulates `(player_x, player_y, map_id)` triples across the episode. The count of unique coordinates is embedded in every observation as `seen_coords_count`. The `ExplorationReward` component rewards the per-step increment in this count, giving a dense novelty signal without requiring full map-coverage tracking.

The set is cleared in `reset()` so each episode starts fresh. For the reward, only the delta matters; the absolute count is also provided for the policy's use.

### 7.4 Action Space Design

```python
# action_space.py
def build_action_bindings(include_select: bool, include_noop: bool = True) -> list[ActionBinding]:
```

The action ordering contract is:

1. Base actions: `up`, `down`, `left`, `right`, `a`, `b`, `start` (indices 0-6, always present)
2. Optional `select` (index 7 when included)
3. Optional `noop` — always appended as the final index

This means `legal_actions[-1]` is always the no-op in any configuration, which clients can rely on. The action schema enforces `ge=0, le=8` to cover the largest possible action space (all buttons + noop).

Each action occupies `action_freq` emulator ticks (default 24 frames at 60 fps = ~0.4 seconds of game time). The button is held for `press_duration` frames (default 8) within that window.

### 7.5 State Alias Registry

PyBoy save states are stored as binary `.state` files in `pokemon_red_env/states/`. The `StateRegistry` resolves human-readable aliases to file paths:

| Alias | File |
|---|---|
| `game_start` | `home.state` |
| `has_starter` | `Bulbasaur.state` |
| `has_pokedex` (default) | `has_pokedex.state` |

Clients can also pass absolute paths or bare filenames (with or without the `.state` suffix). Unresolvable requests raise `FileNotFoundError` with a list of available states and aliases included in the message.

### 7.6 Error Observations

Non-fatal errors in `reset()` or `step()` do not crash the session. Instead they return a terminal `PokemonRedObservation` with `done=True`, a blank black screen, and the error details in `info["error"]`. This allows the client to detect and handle failures gracefully without the WebSocket being torn down unexpectedly.

---

## 8. Technology Stack

| Library | Version requirement | Role |
|---|---|---|
| [PyBoy](https://github.com/Baekalfen/PyBoy) | `>=2.7.0` | Game Boy emulator: ROM execution, input injection, frame and RAM access |
| [openenv-core](https://github.com/meta-pytorch/OpenEnv) | latest `main` (git source) | Environment interface, WebSocket server, client base class, wire protocol |
| [Pydantic](https://docs.pydantic.dev/) | `>=2.12.5` | Type-validated models for actions, observations, state; `model_validate` for deserialization |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | `>=2.12.0` | `PokemonRedConfig` as a `BaseSettings` subclass; environment variable loading with `POKEMON_RED_` prefix |
| [uvicorn](https://www.uvicorn.org/) | `>=0.40.0` | ASGI server hosting the OpenEnv WebSocket application |
| [numpy](https://numpy.org/) | `>=2.2.6` | Screen array manipulation; `pyboy.screen.ndarray` access |
| [Pillow](https://python-pillow.org/) | `>=12.1.0` | PNG encoding of screen frames for base64 transmission |

Python version requirement: `>=3.10` (uses `match`, `|` union types, `int.bit_count()`).

**Development dependencies:**

| Tool | Version | Role |
|---|---|---|
| pytest | `>=9.0.2` | Test runner |
| pytest-cov | `>=7.0.0` | Coverage reporting |
| pytest-mock | `>=3.15.1` | PyBoy mocking in unit tests |
| ruff | `>=0.15.0` | Linter and formatter |

---

## 9. Cross-Reference Index

The following documents provide deeper coverage of specific subsystems:

| Document | Topic |
|---|---|
| `docs/configuration.md` | All `POKEMON_RED_*` environment variables and their defaults |
| `docs/reward-system.md` | Reward component API, registration, weights, and anneal schedules |
| `docs/memory-and-game-state.md` | RAM addresses, event flags, `game_state` dict schema |
| `docs/environment-api.md` | `reset()` / `step()` signatures, observation schema, error handling |
| `docs/server-and-client.md` | Server startup, WebSocket protocol, `PokemonRedEnv` client usage |
| `docs/deployment.md` | Docker build, ROM mounting, parallel session configuration |
| `README.md` | Quick-start installation, demo scripts, action mapping table |
