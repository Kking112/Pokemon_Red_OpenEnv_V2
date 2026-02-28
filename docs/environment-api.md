# Environment API Reference

This document is the primary API reference for `PokemonRedEnvironment`, the OpenEnv-compatible
Pokemon Red emulation environment backed by PyBoy.

---

## Table of Contents

1. [Overview](#overview)
2. [Initialization](#initialization)
3. [Reset Flow](#reset-flow)
4. [Step Flow](#step-flow)
5. [Observation Schema](#observation-schema)
6. [Action Space](#action-space)
7. [State Aliases](#state-aliases)
8. [Available Save States](#available-save-states)
9. [Done Conditions](#done-conditions)
10. [Error Handling](#error-handling)
11. [Concurrency](#concurrency)

---

## Overview

`PokemonRedEnvironment` implements the OpenEnv `Environment` interface, parameterized as:

```python
Environment[PokemonRedAction, PokemonRedObservation, PokemonRedState]
```

It wraps PyBoy (a Game Boy emulator) and exposes a synchronous `reset` / `step` API over a
running Pokemon Red ROM. Every call returns a `PokemonRedObservation` containing a screen image,
structured RAM-derived game state, legal actions, reward, done flag, and a metadata `info` dict.

The environment is safe for concurrent use across multiple sessions (see
[Concurrency](#concurrency)).

---

## Initialization

```python
from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.server.environment import PokemonRedEnvironment

config = PokemonRedConfig()          # reads POKEMON_RED_* env vars
env = PokemonRedEnvironment(config)
```

During `__init__` the following occurs in order:

1. **ROM validation** - If `fail_fast_on_missing_rom` is `True` (default) and the file at
   `gb_path` does not exist, a `FileNotFoundError` is raised immediately.

2. **StateRegistry construction** - A `StateRegistry` is built from `state_dir`, loading the
   default alias table (`game_start`, `has_starter`, `has_pokedex`) plus any caller-supplied
   aliases.

3. **Action binding construction** - `build_action_bindings` produces the ordered list of
   `ActionBinding` objects based on `include_select` and `include_noop` config flags.

4. **PyBoy instance creation** - PyBoy is created with:
   - `window="null"` (headless) or `window="SDL2"` (windowed) based on `config.headless`
   - `sound_emulated=False`, `log_level="CRITICAL"`
   - Optional symbol file loaded from `symbols_path` when it exists
   - Emulation speed set to unlimited (`0`) in headless mode

5. **MemoryReader construction** - Wraps PyBoy RAM with typed read helpers; loads `events.json`,
   `maps.json`, and `curated_events.json` look-up tables from `events_data_path` and
   `maps_data_path`.

6. **RewardManager construction** - Built with `reward_scale`; default modular reward components
   are registered when `use_modular_rewards` is `True`.

7. **Internal state initialization** - `PokemonRedState` is created with a fresh episode UUID,
   `step_count=0`, `total_reward=0.0`. The `_seen_coords` set, `_prev_state_dict`, `_prev_reward`,
   and `_prev_action_name` fields are zeroed.

### Key Configuration Fields

| Field | Default | Description |
|-------|---------|-------------|
| `headless` | `True` | Run without a display window |
| `gb_path` | `PokemonRed.gb` | Path to the ROM file |
| `state_dir` | `pokemon_red_env/states/` | Directory containing `.state` files |
| `init_state` | `"has_pokedex"` | Default save state alias or filename |
| `action_freq` | `24` | Game Boy frames advanced per step |
| `press_duration` | `8` | Frames the button is held before release |
| `max_steps` | `163840` | Episode step limit (`0` = unlimited) |
| `screen_downscale` | `1` | Pixel stride for screen downsampling |
| `include_game_state` | `True` | Include RAM-derived state in observations |
| `include_state_deltas` | `True` | Include per-step delta fields in game_state |
| `event_flags_mode` | `"curated"` | `"curated"`, `"all"`, or `"none"` |
| `terminate_on_blackout` | `True` | End episode when party HP reaches zero |
| `include_select` | `False` | Add SELECT button to action space |
| `include_noop` | `True` | Add NOOP as the final action |
| `use_modular_rewards` | `True` | Use the component-based reward system |

All fields can be overridden via `POKEMON_RED_<FIELD>` environment variables.

---

## Reset Flow

```python
obs = env.reset(seed=None, episode_id=None, init_state="has_pokedex")
```

The `init_state` keyword argument may be passed through `**kwargs`. The full sequence is:

1. **Alias resolution** - `StateRegistry.resolve(init_state, default_alias=config.init_state)`
   is called. The resolver applies the alias table first, then tries direct filename lookup, then
   absolute path. If nothing matches, a `FileNotFoundError` is raised listing available states.

2. **Save state loading** - The resolved `.state` file is opened and passed to
   `pyboy.load_state()`. One rendered frame is ticked to advance the emulator into a valid state.

3. **Reward and exploration reset** - `reward_manager.reset()` clears per-episode reward
   component state. `_seen_coords` is cleared.

4. **PokemonRedState reset** - A new `PokemonRedState` is constructed with a new episode UUID
   (or the caller-supplied `episode_id`), `step_count=0`, `total_reward=0.0`.

5. **Initial game state extraction** - `MemoryReader.extract_game_state()` reads all RAM fields.
   The initial position is added to `_seen_coords` and `seen_coords_count` is set.

6. **Temporal awareness initialization** - Three fields are injected into the game state dict:
   - `state_deltas = {}` (empty on reset; no previous step exists)
   - `prev_step_reward = 0.0`
   - `prev_action_name = ""`

7. **Previous-state bookkeeping** - `_prev_state_dict` is set to the initial game state dict.
   `_prev_reward` and `_prev_action_name` are zeroed.

8. **Screen capture** - `pyboy.screen.ndarray` is captured, converted from RGBA to RGB, optionally
   downscaled, and encoded as a base64 PNG string.

9. **Observation construction** - Returns a `PokemonRedObservation` with `reward=0.0`,
   `done=False`, and an `info` dict containing `episode_id`, `init_state` (resolved filename),
   and `seed`.

---

## Step Flow

```python
obs = env.step(PokemonRedAction(action=0))  # 0 = up
```

1. **Done guard** - If `_state.done` is already `True`, returns an error observation
   (`"episode_already_done"`).

2. **Action validation** - `action_idx` is checked against `[0, len(_action_bindings))`. An
   out-of-range index returns an error observation without advancing the emulator.

3. **Button press/release** - For non-NOOP actions, `pyboy.send_input(binding.press_event)` is
   called, followed immediately by `pyboy.send_input(binding.release_event, delay=press_duration)`.
   NOOP sends no input.

4. **Frame ticking** - `pyboy.tick(action_freq - 1, render=False)` advances silent frames, then
   `pyboy.tick(1, render=True)` produces the visible frame. Total frames per step: `action_freq`
   (default 24, approximately one second of Game Boy time).

5. **Game state extraction** - `MemoryReader.extract_game_state()` reads current RAM. The new
   position is added to `_seen_coords`; `seen_coords_count` is updated.

6. **State delta computation** - When `include_state_deltas` is `True` and a previous state
   exists, `_compute_state_deltas` is called. Delta keys:
   - `delta_player_x`, `delta_player_y`, `delta_seen_coords_count`
   - `delta_badge_count`, `delta_level_sum`, `delta_event_count`, `delta_player_money`
   - `map_changed` (bool), `battle_started` (bool)

7. **Temporal feedback injection** - `prev_step_reward` and `prev_action_name` from the previous
   step are injected into the current game state dict.

8. **Reward calculation** - `RewardManager.calculate(curr, prev)` (modular) or the simple
   four-component formula (exploration, badges, levels, events) is called. The result is added
   to `_state.total_reward`.

9. **Done condition check** - `max_steps` and `terminate_on_blackout` conditions are evaluated
   (see [Done Conditions](#done-conditions)).

10. **Screen capture** - Same pipeline as reset.

11. **Observation construction** - Returns a `PokemonRedObservation` with the `info` dict
    containing `action_name`, `reward_breakdown`, and `done_reason`.

12. **State bookkeeping** - `_prev_state_dict`, `_prev_reward`, and `_prev_action_name` are
    updated for use in the next step.

---

## Observation Schema

`PokemonRedObservation` is a Pydantic model returned by both `reset` and `step`.

### Top-level fields

| Field | Type | Description |
|-------|------|-------------|
| `screen_b64` | `str` | Base64-encoded PNG of the current Game Boy screen |
| `screen_shape` | `list[int]` | Frame dimensions as `[height, width, channels]` |
| `game_state` | `dict[str, Any]` | Structured RAM-derived game state (empty if `include_game_state=False`) |
| `legal_actions` | `list[int]` | Valid action indices for this step |
| `reward` | `float` | Reward earned this step (0.0 on reset) |
| `done` | `bool` | Whether the episode has ended |
| `info` | `dict[str, Any]` | Metadata for logging and debugging |

### screen_b64 and screen_shape

The screen is always RGB (`channels=3`). Native Game Boy resolution is 160x144 pixels
(`screen_shape = [144, 160, 3]`). When `screen_downscale > 1`, both dimensions are reduced by
that stride factor.

To decode the screen in Python:

```python
import base64, io
from PIL import Image

img = Image.open(io.BytesIO(base64.b64decode(obs.screen_b64)))
```

### game_state fields

All fields derived from live Game Boy RAM. Present when `include_game_state=True`.

**Player and map:**

| Field | Type | Description |
|-------|------|-------------|
| `player_x` | `int` | Player X tile coordinate on current map |
| `player_y` | `int` | Player Y tile coordinate on current map |
| `map_id` | `int` | Numeric map identifier |
| `map_name` | `str` | Human-readable map name (from maps.json) |
| `map_tileset` | `int` | Current map tileset index |
| `last_map` | `int` | ID of the previously visited map |
| `walk_counter` | `int` | Overworld step counter (used for random encounters) |
| `seen_coords_count` | `int` | Total unique (x, y, map_id) positions visited this episode |

**Party:**

| Field | Type | Description |
|-------|------|-------------|
| `party_count` | `int` | Number of Pokemon in party (0-6) |
| `party_hp` | `list[int]` | Current HP for each party member |
| `party_max_hp` | `list[int]` | Max HP for each party member |
| `party_levels` | `list[int]` | Level for each party member |
| `party_hp_fraction` | `float` | Ratio of total current HP to total max HP |
| `level_sum` | `int` | Sum of all party member levels |
| `party` | `list[dict]` | Detailed per-member data (see below) |

Each `party` entry contains:
- `species` (int), `level` (int), `hp` (int), `max_hp` (int)
- `status` (int, bitmask), `type1` (int), `type2` (int), `move1` (int), `exp` (int)

**Badges and progression:**

| Field | Type | Description |
|-------|------|-------------|
| `badges` | `list[int]` | 8-element list, 1 if badge earned (Boulder, Cascade, ..., Earth) |
| `badge_count` | `int` | Number of badges earned |
| `event_count` | `int` | Total event flag bits set in RAM |
| `event_flags` | `dict[str, bool]` | Named event flags (scope controlled by `event_flags_mode`) |
| `pokedex_owned_count` | `int` | Number of Pokemon species owned |
| `pokedex_seen_count` | `int` | Number of Pokemon species seen |
| `play_time_hours` | `int` | In-game play time (hours) |

**Battle:**

| Field | Type | Description |
|-------|------|-------------|
| `in_battle` | `int` | `0` = overworld, `1` = wild, `2` = trainer |
| `battle_outcome` | `int or null` | Battle result byte (null when not in battle) |
| `enemy_hp` | `int or null` | Enemy Pokemon current HP (null when not in battle) |
| `enemy_max_hp` | `int or null` | Enemy Pokemon max HP (null when not in battle) |
| `enemy_level` | `int or null` | Enemy Pokemon level (null when not in battle) |
| `enemy_species` | `int or null` | Enemy Pokemon species ID (null when not in battle) |
| `battle_mon_hp` | `int or null` | Active party Pokemon HP in battle (null when not in battle) |
| `player_move_num` | `int or null` | Player's selected move number (null when not in battle) |

**Items and inventory:**

| Field | Type | Description |
|-------|------|-------------|
| `num_bag_items` | `int` | Number of item slots used in the bag |
| `num_box_items` | `int` | Number of item slots used in the PC box |
| `player_money` | `int` | Current money in Pokedollars (decoded from BCD) |

**UI state:**

| Field | Type | Description |
|-------|------|-------------|
| `text_box_id` | `int` | Active text box identifier (0 = none) |
| `current_menu_item` | `int` | Currently selected menu cursor position |
| `menu_watched_keys` | `int` | Key mask for the active menu |
| `top_menu_item_x` | `int` | X position of the top-most visible menu entry |
| `top_menu_item_y` | `int` | Y position of the top-most visible menu entry |
| `letter_printing_delay_flags` | `int` | Text speed flags |

**Episode tracking:**

| Field | Type | Description |
|-------|------|-------------|
| `step_count` | `int` | Number of steps taken in the current episode |
| `total_reward` | `float` | Cumulative reward for the current episode |

**Temporal awareness (injected by environment, not from RAM):**

| Field | Type | Description |
|-------|------|-------------|
| `state_deltas` | `dict[str, int or float or bool]` | Changes from the previous step (empty on reset) |
| `prev_step_reward` | `float` | Reward received on the previous step (0.0 on reset) |
| `prev_action_name` | `str` | Name of the action taken on the previous step (`""` on reset) |

`state_deltas` keys when `include_state_deltas=True`:

| Key | Type | Description |
|-----|------|-------------|
| `delta_player_x` | `int` | Change in X coordinate |
| `delta_player_y` | `int` | Change in Y coordinate |
| `delta_seen_coords_count` | `int` | New unique tiles visited this step |
| `delta_badge_count` | `int` | Badges earned this step |
| `delta_level_sum` | `int` | Total level increase this step |
| `delta_event_count` | `int` | Event flags newly set this step |
| `delta_player_money` | `int` | Money gained (positive) or lost (negative) this step |
| `map_changed` | `bool` | `True` if the player moved to a different map |
| `battle_started` | `bool` | `True` if a battle began this step |

### info dict

Returned by `reset`:

| Key | Type | Description |
|-----|------|-------------|
| `episode_id` | `str` | UUID identifying this episode |
| `init_state` | `str` | Resolved save state filename (e.g. `"has_pokedex.state"`) |
| `seed` | `int or null` | Seed passed to reset (informational only) |

Returned by `step`:

| Key | Type | Description |
|-----|------|-------------|
| `action_name` | `str` | Human-readable name of the executed action (e.g. `"up"`, `"noop"`) |
| `reward_breakdown` | `dict[str, float]` | Per-component reward contributions |
| `done_reason` | `str or null` | `"max_steps_reached"`, `"blackout"`, or `null` |

On error (invalid action, reset failure, step failure):

| Key | Type | Description |
|-----|------|-------------|
| `error` | `str` | Error message and traceback |

---

## Action Space

### Default action space (8 actions, `include_select=False`, `include_noop=True`)

| Index | Name | PyBoy Event |
|-------|------|-------------|
| 0 | `up` | `PRESS_ARROW_UP` / `RELEASE_ARROW_UP` |
| 1 | `down` | `PRESS_ARROW_DOWN` / `RELEASE_ARROW_DOWN` |
| 2 | `left` | `PRESS_ARROW_LEFT` / `RELEASE_ARROW_LEFT` |
| 3 | `right` | `PRESS_ARROW_RIGHT` / `RELEASE_ARROW_RIGHT` |
| 4 | `a` | `PRESS_BUTTON_A` / `RELEASE_BUTTON_A` |
| 5 | `b` | `PRESS_BUTTON_B` / `RELEASE_BUTTON_B` |
| 6 | `start` | `PRESS_BUTTON_START` / `RELEASE_BUTTON_START` |
| 7 | `noop` | (none) |

### With SELECT enabled (9 actions, `include_select=True`)

| Index | Name | PyBoy Event |
|-------|------|-------------|
| 0-6 | (same as above) | |
| 7 | `select` | `PRESS_BUTTON_SELECT` / `RELEASE_BUTTON_SELECT` |
| 8 | `noop` | (none) |

### Ordering contract

Actions are always appended in this order:
1. Base gameplay actions (up, down, left, right, a, b, start) — indices 0-6
2. SELECT (optional) — index 7 when enabled
3. NOOP (optional) — always last

### NOOP semantics

When `noop` is selected, no input event is sent to PyBoy. The emulator still advances
`action_freq` frames. This is useful for observing the game without acting, or for training
agents that need an explicit "do nothing" option.

### PokemonRedAction validation

The `PokemonRedAction` Pydantic model validates `action` with `ge=0, le=8`. This covers the
maximum 9-action space (0-8 with SELECT enabled). The environment performs a secondary runtime
check against the actual binding list length and returns an error observation for out-of-range
indices.

```python
from pokemon_red_env.models import PokemonRedAction

action = PokemonRedAction(action=0)  # up
obs = env.step(action)
```

---

## State Aliases

The `StateRegistry` maps short alias strings to concrete `.state` filenames. Resolution order:

1. Alias table lookup
2. Direct filename lookup (`.state` extension appended if absent)
3. Absolute path (if the string is an absolute path and the file exists)
4. `FileNotFoundError` listing all available states and aliases

### Built-in aliases

| Alias | Resolves to | Game progression point |
|-------|-------------|----------------------|
| `game_start` | `home.state` | Professor Oak's lab, before receiving a starter |
| `has_starter` | `Bulbasaur.state` | Received Bulbasaur from Oak, has Pokedex |
| `has_pokedex` | `has_pokedex.state` | Has Pokedex (default start state) |

Note: Passing a bare filename without extension (e.g., `"home"`) also works — the
registry appends `.state` and checks the states directory as a fallback. This is
filename resolution, not an alias.

The default `init_state` config value is `"has_pokedex"`.

### Passing a state to reset

```python
# By alias
obs = env.reset(init_state="game_start")

# By bare filename (extension is added automatically)
obs = env.reset(init_state="cut")

# By full filename
obs = env.reset(init_state="cut.state")

# By absolute path
obs = env.reset(init_state="/path/to/custom.state")
```

### Adding custom states

Place any `.state` file produced by PyBoy into the `state_dir` directory
(`pokemon_red_env/states/` by default). It will be available immediately by filename without
restarting the server. Custom aliases can be injected at `StateRegistry` construction time:

```python
registry = StateRegistry(state_dir, aliases={"my_alias": "my_save.state"})
```

---

## Available Save States

The following 29 `.state` files are included in `pokemon_red_env/states/`. All represent
real game progression checkpoints.

| Filename | Description |
|----------|-------------|
| `init.state` | Very early game start |
| `home.state` | Professor Oak's lab (pre-starter) |
| `fast_text_start.state` | Game start with fast text speed enabled |
| `Bulbasaur.state` | Received Bulbasaur, has Pokedex |
| `Charmander.state` | Received Charmander, has Pokedex |
| `Squirtle.state` | Received Squirtle, has Pokedex |
| `has_pokedex.state` | Has Pokedex (default; starter obtained) |
| `has_pokedex_nballs.state` | Has Pokedex with extra Poke Balls |
| `cut.state` | HM01 Cut obtained |
| `cut2.state` | Cut obtained, alternate save point |
| `cut3.state` | Cut obtained, third alternate save point |
| `with_cut_vermillion.state` | In Vermilion City after obtaining Cut |
| `mtmoon.state` | At Mt. Moon |
| `rocktunnel.state` | At Rock Tunnel |
| `rocktunnel2.state` | Rock Tunnel, alternate save point |
| `game_corner.state` | At the Celadon Game Corner |
| `pokeflute.state` | Poke Flute obtained |
| `surf.state` | HM03 Surf obtained |
| `seafoam.state` | At Seafoam Islands |
| `seafoam_1f_right.state` | Seafoam Islands 1F, right side |
| `safari_glitched.state` | Safari Zone (glitched entry state) |
| `victory_road.state` | At Victory Road entrance |
| `victory_road_2.state` | Victory Road, second section |
| `victory_road_3.state` | Victory Road, third section |
| `victory_road_4.state` | Victory Road, fourth section |
| `victory_road_5.state` | Victory Road, fifth section |
| `beat_lance_1.state` | After defeating Lance (Elite Four) |
| `beat_champion.state` | After defeating the Pokemon League Champion |
| `error.state` | Debug/error recovery state |

---

## Done Conditions

An episode ends (`done=True`) when any of the following conditions is met:

### max_steps_reached

```
step_count >= max_steps   (when max_steps > 0)
```

Default `max_steps` is `163840` steps. Set `max_steps=0` for an unlimited episode.

`done_reason` in the `info` dict will be `"max_steps_reached"`.

### blackout

```
terminate_on_blackout=True  AND  party_count > 0  AND  sum(party_hp) <= 0
```

Triggered when all party Pokemon have fainted (HP at zero). The game would normally warp the
player to the last visited Pokemon Center with half their money deducted.

`done_reason` in the `info` dict will be `"blackout"`.

### Episode already done

If `step` is called after the episode has ended, an error observation is returned immediately
with `info={"error": "episode_already_done"}` without advancing the emulator. Call `reset` to
start a new episode.

---

## Error Handling

When a non-fatal error occurs inside `reset` or `step`, the environment returns a terminal error
observation rather than raising an exception. This keeps the server alive across bad inputs.

Error observation characteristics:
- `screen_b64`: blank black 160x144 PNG
- `screen_shape`: `[144, 160, 3]`
- `game_state`: `{}`
- `legal_actions`: current legal action list
- `reward`: `0.0`
- `done`: `True`
- `info`: `{"error": "<message with traceback>"}`

After an error observation, `_state.done` is set to `True`. The caller must `reset` to continue.

Common error messages:

| Error | Cause |
|-------|-------|
| `"episode_already_done"` | `step` called after episode ended |
| `"invalid_action_index: N not in [...]"` | Action index out of legal range |
| `"reset_failed: ..."` | Exception during reset (e.g. missing state file) |
| `"step_failed: ..."` | Unexpected exception during step |

---

## Concurrency

```python
PokemonRedEnvironment.SUPPORTS_CONCURRENT_SESSIONS = True
```

The class-level flag signals to the OpenEnv server that multiple sessions may run simultaneously.

### Headless mode (recommended for concurrency)

In headless mode (`config.headless=True`), each environment instance runs independently with its
own PyBoy instance. The emulator speed is set to unlimited (`0`), making sessions CPU-bound.
Multiple sessions can run concurrently across threads or processes without coordination.

The server-level limit is controlled by `POKEMON_RED_MAX_CONCURRENT_ENVS` (default `1`). Increase
this to allow the server to accept more simultaneous WebSocket sessions.

### Windowed mode

Windowed mode (`config.headless=False`) requires PyBoy to run on the main thread because SDL2
is not thread-safe. The environment dispatches PyBoy calls to the main event loop via
`asyncio.run_coroutine_threadsafe`. Requesting more than one concurrent session in windowed
mode will produce a server-level warning and is not recommended for production use.

### Session isolation

Each `PokemonRedEnvironment` instance holds its own:
- PyBoy emulator instance
- `_seen_coords` set
- `_prev_state_dict`, `_prev_reward`, `_prev_action_name`
- `PokemonRedState` (episode metadata)
- `RewardManager` (component accumulators)

There is no shared mutable state between environment instances.
