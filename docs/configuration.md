# Configuration Reference

This document is the authoritative reference for all configuration settings in Pokemon Red OpenEnv V2.

---

## Overview

Configuration is managed by `pokemon_red_env/config.py` using `PokemonRedConfig`, a Pydantic `BaseSettings` subclass. All settings can be overridden via environment variables using the prefix `POKEMON_RED_`. Environment variable names are case-insensitive.

```python
from pokemon_red_env.config import PokemonRedConfig

# Load from environment / defaults
cfg = PokemonRedConfig()

# Override programmatically (for testing or scripting)
cfg = PokemonRedConfig(headless=False, max_steps=10_000)
```

Pydantic validates every field at construction time. If any constraint is violated, a `ValidationError` is raised before the environment starts.

Settings are resolved in this priority order (highest to lowest):

1. Values passed explicitly to `PokemonRedConfig(...)` in code
2. Environment variables (e.g. `POKEMON_RED_HEADLESS=true`)
3. A `.env` file in the working directory (Pydantic Settings auto-discovery)
4. Compiled-in defaults defined in `config.py`

---

## Complete Configuration Reference

### Emulator Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_HEADLESS` | `headless` | `bool` | `True` | Run PyBoy without a display window. Set to `false` for interactive debugging. Windowed mode forces `max_concurrent_envs` to `1`. |
| `POKEMON_RED_GB_PATH` | `gb_path` | `str` | `<repo>/PokemonRed.gb` | Absolute path to the Game Boy ROM file. You must supply a legally obtained copy. |
| `POKEMON_RED_SYMBOLS_PATH` | `symbols_path` | `str` | `<repo>/Assembly_RAM_Addresses/pokered.sym` | Path to the `.sym` symbol file used to resolve RAM addresses. |
| `POKEMON_RED_STATE_DIR` | `state_dir` | `str` | `<repo>/pokemon_red_env/states` | Directory containing `.state` save-state files used by `init_state` aliases. |
| `POKEMON_RED_INIT_STATE` | `init_state` | `str` | `"has_pokedex"` | Name of the save-state alias loaded on `reset()`. Built-in aliases: `game_start`, `has_starter`, `has_pokedex`. |
| `POKEMON_RED_FAIL_FAST_ON_MISSING_ROM` | `fail_fast_on_missing_rom` | `bool` | `True` | Raise an error at startup if the ROM file is not found. Set to `false` only in unit-test environments that mock PyBoy. |

### Timing Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_ACTION_FREQ` | `action_freq` | `int` | `24` | Number of Game Boy frames advanced per environment step. Must satisfy `action_freq >= press_duration + 1`. Higher values make the game play faster relative to wall-clock time. |
| `POKEMON_RED_PRESS_DURATION` | `press_duration` | `int` | `8` | Number of frames a button is held down within each step. Must be less than `action_freq`. |
| `POKEMON_RED_MAX_STEPS` | `max_steps` | `int` | `163840` | Maximum number of steps per episode. `0` means unlimited. At the limit, `done=True` is returned. |

### Observation Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_SCREEN_DOWNSCALE` | `screen_downscale` | `int` | `1` | Integer downscale factor applied to the 160x144 screen. `1` = full resolution, `2` = 80x72, `4` = 40x36. Must be >= 1. |
| `POKEMON_RED_INCLUDE_GAME_STATE` | `include_game_state` | `bool` | `True` | Include the structured `game_state` dictionary (RAM-derived values: badges, party, map, etc.) in each observation. |
| `POKEMON_RED_INCLUDE_STATE_DELTAS` | `include_state_deltas` | `bool` | `True` | Include a `state_deltas` dictionary in each observation containing only fields that changed since the previous step. Requires `include_game_state=true`. |
| `POKEMON_RED_EVENT_FLAGS_MODE` | `event_flags_mode` | `Literal["curated", "all", "none"]` | `"curated"` | Controls which event flags are included in observations. `curated` = hand-selected meaningful flags, `all` = full event-flag array (up to `event_flags_max_count`), `none` = omit event flags entirely. |
| `POKEMON_RED_EVENT_FLAGS_MAX_COUNT` | `event_flags_max_count` | `int` | `1024` | Maximum number of event flags included when `event_flags_mode="all"`. Must be >= 0. |

### Reward Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_USE_MODULAR_REWARDS` | `use_modular_rewards` | `bool` | `True` | Enable the modular reward manager. When `false`, a single scalar reward of `0.0` is returned each step. |
| `POKEMON_RED_REWARD_SCALE` | `reward_scale` | `float` | `1.0` | Global multiplier applied to the total reward after all components are summed. |
| `POKEMON_RED_EXPLORATION_WEIGHT` | `exploration_weight` | `float` | `0.02` | Weight for `exploration_novelty`: reward for visiting map tiles not seen in the current episode. Must be >= 0. |
| `POKEMON_RED_MOVEMENT_BONUS_WEIGHT` | `movement_bonus_weight` | `float` | `0.003` | Peak weight for `movement_bonus_early`: a warm-start bonus rewarding any movement early in training. Anneals to zero over `movement_bonus_anneal_steps`. Must be >= 0. |
| `POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS` | `movement_bonus_anneal_steps` | `int` | `120` | Number of steps over which `movement_bonus_early` linearly decays to zero. `0` disables annealing (bonus is always active). Must be >= 0. |
| `POKEMON_RED_BADGE_WEIGHT` | `badge_weight` | `float` | `5.0` | Reward awarded when a new gym badge is obtained. Must be >= 0. |
| `POKEMON_RED_LEVEL_WEIGHT` | `level_weight` | `float` | `1.0` | Reward awarded per Pokemon level gained. Must be >= 0. |
| `POKEMON_RED_EVENT_WEIGHT` | `event_weight` | `float` | `0.1` | Reward per novel event flag triggered (story progression). Must be >= 0. |
| `POKEMON_RED_BATTLE_WIN_WEIGHT` | `battle_win_weight` | `float` | `2.0` | Reward per battle victory. |
| `POKEMON_RED_HEALING_WEIGHT` | `healing_weight` | `float` | `1.0` | Reward for visiting a Pokemon Center and healing the party. |
| `POKEMON_RED_MENU_NOVELTY_WEIGHT` | `menu_novelty_weight` | `float` | `0.004` | Weight for `menu_novelty`: reward for encountering a menu-state signature not seen before in the current episode. Must be >= 0. |
| `POKEMON_RED_MENU_INTERACTION_WEIGHT` | `menu_interaction_weight` | `float` | `0.001` | Peak weight for `menu_bonus_early`: a small decaying bonus for any menu interaction, including non-novel ones. Anneals to zero over `menu_anneal_steps`. Must be >= 0. |
| `POKEMON_RED_MENU_ANNEAL_STEPS` | `menu_anneal_steps` | `int` | `120` | Number of steps over which `menu_bonus_early` linearly decays to zero. Must be >= 0. |
| `POKEMON_RED_MAX_MENU_SIGNATURES_PER_EPISODE` | `max_menu_signatures_per_episode` | `int` | `128` | Maximum number of distinct menu signatures tracked per episode for novelty purposes. Once the cap is reached, no further `menu_novelty` rewards are issued that episode. Must be >= 0. |
| `POKEMON_RED_MOVEMENT_WEIGHT` | `movement_weight` | `float` | `1.0` | **Legacy field.** Retained for backward compatibility. The dense `MovementReward` component is no longer registered by default. This field has no effect unless a custom reward manager re-registers it. |

### Action Space Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_INCLUDE_SELECT` | `include_select` | `bool` | `False` | Add the SELECT button as a discrete action. When `false`, action indices are 0-7 (with NOOP at 7). When `true`, action indices are 0-8 (SELECT at 7, NOOP at 8). |
| `POKEMON_RED_INCLUDE_NOOP` | `include_noop` | `bool` | `True` | Include a NOOP (no operation) action as the final index. It is strongly recommended to keep this enabled. |

### Concurrency Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_MAX_CONCURRENT_ENVS` | `max_concurrent_envs` | `int` | `1` | Maximum number of simultaneous WebSocket environment sessions the server will allow. Must be >= 1. Headless mode required for values > 1; windowed mode logs a warning and clamps to 1. |

### Termination Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_TERMINATE_ON_BLACKOUT` | `terminate_on_blackout` | `bool` | `True` | End the episode immediately when the player blacks out (all Pokemon fainted). When `false`, the episode continues from the blackout recovery point. |

### Data Path Settings

| Environment Variable | Python Field | Type | Default | Description |
|---|---|---|---|---|
| `POKEMON_RED_EVENTS_DATA_PATH` | `events_data_path` | `str` | `<repo>/pokemon_red_env/data/events.json` | Path to the JSON file mapping event flag names to RAM addresses. Used by the modular reward system and observation builder. |
| `POKEMON_RED_MAPS_DATA_PATH` | `maps_data_path` | `str` | `<repo>/pokemon_red_env/data/maps.json` | Path to the JSON file mapping map IDs to human-readable names. Used by `game_state` observation and exploration tracking. |

---

## Validation Rules

All constraints are enforced by a `model_validator` that runs at construction time. Violating any constraint raises a `pydantic.ValidationError` before the environment initializes.

| Rule | Constraint | Rationale |
|---|---|---|
| Button timing | `action_freq >= press_duration + 1` | At least one frame must pass after the button is released before the next action. |
| Episode length | `max_steps >= 0` | `0` is the sentinel for unlimited steps; negative values are meaningless. |
| Concurrency | `max_concurrent_envs >= 1` | At least one environment must be allowed. |
| Screen resolution | `screen_downscale >= 1` | A factor < 1 would upsample, not downscale; factor of 0 is undefined. |
| Event flags | `event_flags_max_count >= 0` | Zero disables the feature; negative is meaningless. |
| Movement anneal | `movement_bonus_anneal_steps >= 0` | Zero means no annealing (bonus is permanent); negative is meaningless. |
| Menu anneal | `menu_anneal_steps >= 0` | Zero means no annealing; negative is meaningless. |
| Menu cap | `max_menu_signatures_per_episode >= 0` | Zero disables menu novelty reward for the episode; negative is meaningless. |
| Reward weights (non-negative) | `movement_bonus_weight >= 0`, `menu_novelty_weight >= 0`, `menu_interaction_weight >= 0`, `badge_weight >= 0`, `level_weight >= 0`, `event_weight >= 0`, `exploration_weight >= 0` | Negative reward weights invert the signal and are almost always a misconfiguration. |

---

## Example .env File

The following is a complete annotated `.env` file showing every supported setting. Copy it to your project root and adjust as needed. Fields at their default value are shown commented out.

```dotenv
# =============================================================================
# Pokemon Red OpenEnv - Environment Configuration
# =============================================================================

# --- Emulator ---

# Absolute path to your legally obtained Pokemon Red ROM.
POKEMON_RED_GB_PATH=/absolute/path/to/your/PokemonRed.gb

# Run without a display window (required for servers and multi-session training).
# POKEMON_RED_HEADLESS=true

# Path to the pokered.sym symbol file for RAM address resolution.
# POKEMON_RED_SYMBOLS_PATH=/absolute/path/to/Assembly_RAM_Addresses/pokered.sym

# Directory containing .state save-state files.
# POKEMON_RED_STATE_DIR=/absolute/path/to/pokemon_red_env/states

# Save-state alias to load on reset(). Options: game_start, has_starter, has_pokedex.
# POKEMON_RED_INIT_STATE=has_pokedex

# Raise an error at startup if the ROM file is missing. Disable only in mock test environments.
# POKEMON_RED_FAIL_FAST_ON_MISSING_ROM=true

# --- Timing ---

# Frames advanced per environment step (must be >= press_duration + 1).
# POKEMON_RED_ACTION_FREQ=24

# Frames a button is held within each step.
# POKEMON_RED_PRESS_DURATION=8

# Maximum steps per episode. 0 = unlimited.
# POKEMON_RED_MAX_STEPS=163840

# --- Observation ---

# Integer downscale factor for the 160x144 screen. 1=full, 2=80x72, 4=40x36.
# POKEMON_RED_SCREEN_DOWNSCALE=1

# Include structured RAM-derived game state in observations.
# POKEMON_RED_INCLUDE_GAME_STATE=true

# Include per-step state deltas (only changed fields) in observations.
# POKEMON_RED_INCLUDE_STATE_DELTAS=true

# Which event flags to include: curated | all | none.
# POKEMON_RED_EVENT_FLAGS_MODE=curated

# Maximum event flags included when event_flags_mode=all.
# POKEMON_RED_EVENT_FLAGS_MAX_COUNT=1024

# --- Rewards ---

# Enable the modular reward manager.
# POKEMON_RED_USE_MODULAR_REWARDS=true

# Global multiplier on the total reward signal.
# POKEMON_RED_REWARD_SCALE=1.0

# Weight for novel tile exploration reward.
# POKEMON_RED_EXPLORATION_WEIGHT=0.02

# Peak weight for the early-game movement warm-start bonus.
# POKEMON_RED_MOVEMENT_BONUS_WEIGHT=0.003

# Steps over which the movement bonus linearly decays to zero.
# POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS=120

# Reward per gym badge earned.
# POKEMON_RED_BADGE_WEIGHT=5.0

# Reward per Pokemon level gained.
# POKEMON_RED_LEVEL_WEIGHT=1.0

# Reward per novel story event flag triggered.
# POKEMON_RED_EVENT_WEIGHT=0.1

# Reward per battle victory.
# POKEMON_RED_BATTLE_WIN_WEIGHT=2.0

# Reward for healing at a Pokemon Center.
# POKEMON_RED_HEALING_WEIGHT=1.0

# Weight for novel menu-state signature discovery reward.
# POKEMON_RED_MENU_NOVELTY_WEIGHT=0.004

# Peak weight for the early-game menu interaction bonus.
# POKEMON_RED_MENU_INTERACTION_WEIGHT=0.001

# Steps over which the menu interaction bonus decays to zero.
# POKEMON_RED_MENU_ANNEAL_STEPS=120

# Maximum distinct menu signatures tracked per episode for novelty.
# POKEMON_RED_MAX_MENU_SIGNATURES_PER_EPISODE=128

# --- Action Space ---

# Include the SELECT button as a discrete action.
# POKEMON_RED_INCLUDE_SELECT=false

# Include a NOOP (no-op) action as the final action index.
# POKEMON_RED_INCLUDE_NOOP=true

# --- Concurrency ---

# Maximum simultaneous environment sessions. Requires headless=true for > 1.
# POKEMON_RED_MAX_CONCURRENT_ENVS=1

# --- Termination ---

# End the episode immediately when the player blacks out.
# POKEMON_RED_TERMINATE_ON_BLACKOUT=true

# --- Data Paths ---

# Path to events.json (event flag name -> RAM address mapping).
# POKEMON_RED_EVENTS_DATA_PATH=/absolute/path/to/pokemon_red_env/data/events.json

# Path to maps.json (map ID -> name mapping).
# POKEMON_RED_MAPS_DATA_PATH=/absolute/path/to/pokemon_red_env/data/maps.json
```

---

## Configuration Recipes

### Headless Multi-Session Training

Run 8 parallel environment sessions for distributed RL training. Requires headless mode.

```bash
POKEMON_RED_HEADLESS=true \
POKEMON_RED_MAX_CONCURRENT_ENVS=8 \
POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb \
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Or as a `.env` file:

```dotenv
POKEMON_RED_HEADLESS=true
POKEMON_RED_MAX_CONCURRENT_ENVS=8
POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb
```

Notes:
- Each WebSocket session creates one independent environment instance.
- Memory usage scales linearly with session count (approximately 150-200 MB per session).
- Do not set `POKEMON_RED_HEADLESS=false` with more than one session; the server will log a warning and cap concurrency at 1.

### Windowed Single-Session Debugging

Render the game in a PyBoy SDL2 window for interactive inspection. Observation deltas and game state are both enabled to support per-step introspection.

```dotenv
POKEMON_RED_HEADLESS=false
POKEMON_RED_MAX_CONCURRENT_ENVS=1
POKEMON_RED_GB_PATH=/path/to/PokemonRed.gb
POKEMON_RED_INCLUDE_GAME_STATE=true
POKEMON_RED_INCLUDE_STATE_DELTAS=true
POKEMON_RED_MAX_STEPS=0
```

Notes:
- `MAX_STEPS=0` runs indefinitely until the episode terminates naturally.
- The SDL2 window opens on the default display; ensure a display server is available (not headless server SSH without X forwarding).

### Custom Reward Tuning for Exploration-Heavy Training

Emphasize map exploration and suppress sparse milestone rewards to encourage the agent to navigate the world rather than grind battles.

```dotenv
POKEMON_RED_HEADLESS=true
POKEMON_RED_GB_PATH=/path/to/PokemonRed.gb

# Boost exploration signal
POKEMON_RED_EXPLORATION_WEIGHT=0.05

# Longer movement warm-start to help early navigation
POKEMON_RED_MOVEMENT_BONUS_WEIGHT=0.01
POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS=500

# Suppress sparse milestone signals
POKEMON_RED_BADGE_WEIGHT=1.0
POKEMON_RED_LEVEL_WEIGHT=0.2
POKEMON_RED_EVENT_WEIGHT=0.05

# Keep menu exploration moderate
POKEMON_RED_MENU_NOVELTY_WEIGHT=0.002
POKEMON_RED_MENU_INTERACTION_WEIGHT=0.0005
POKEMON_RED_MENU_ANNEAL_STEPS=300

# Scale total reward down to keep magnitude stable
POKEMON_RED_REWARD_SCALE=0.5
```

### Minimal Observation Mode for Faster Training

Strip the observation to screen pixels only. Useful when training a purely vision-based agent or when observation serialization throughput is a bottleneck.

```dotenv
POKEMON_RED_HEADLESS=true
POKEMON_RED_GB_PATH=/path/to/PokemonRed.gb

# Reduce screen size to cut bandwidth and observation size
POKEMON_RED_SCREEN_DOWNSCALE=2

# Omit structured state (saves serialization overhead)
POKEMON_RED_INCLUDE_GAME_STATE=false
POKEMON_RED_INCLUDE_STATE_DELTAS=false

# Omit event flags entirely
POKEMON_RED_EVENT_FLAGS_MODE=none

# Trim action space if SELECT is unused
POKEMON_RED_INCLUDE_SELECT=false
```

Notes:
- Disabling `include_game_state` also implicitly disables `include_state_deltas` because deltas are derived from game state.
- With `event_flags_mode=none` and `include_game_state=false`, the only observation field is the downscaled screen array.
- The reward system reads RAM directly regardless of observation settings, so reward signals are unaffected.
