# Reward System

This document describes the modular reward architecture for Pokemon Red OpenEnv V2: how rewards
are structured, how each built-in component works, how to configure them, and how to extend the
system with custom components.

---

## Overview

The reward system is built around two primitives:

- **`BaseRewardComponent`** — an abstract dataclass that every reward component subclasses. It
  holds a `name`, a `weight`, and an `enabled` flag, and requires one method to be implemented:
  `calculate(state, prev_state) -> float`.
- **`RewardManager`** — an orchestrator that holds an ordered registry of components, calls each
  one per step, applies per-component weights, applies a global `reward_scale`, and records a
  per-step breakdown dictionary that agents can inspect.

Both are defined under `pokemon_red_env/rewards/` and exported from
`pokemon_red_env/rewards/__init__.py`.

---

## Architecture

### BaseRewardComponent

```python
# pokemon_red_env/rewards/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class BaseRewardComponent(ABC):
    name: str
    weight: float = 1.0
    enabled: bool = True

    @abstractmethod
    def calculate(self, state: dict, prev_state: dict) -> float:
        """Return the unweighted reward contribution for this component."""

    def reset(self) -> None:
        """Reset any episode-local state. Override when a component is stateful."""
```

Each `calculate` call receives two dictionaries:

- `state` — the current game state snapshot
- `prev_state` — the game state from the previous step

Components return an **unweighted** scalar. Clamping, weighting, and scaling are handled by the
manager, not by the component itself. Components that maintain episode-local state (such as sets
of seen coordinates or menu signatures) override `reset()` to clear that state at the start of
each episode.

### RewardManager

```python
# pokemon_red_env/rewards/manager.py
class RewardManager:
    def __init__(self, reward_scale: float = 1.0): ...
    def register(self, component: BaseRewardComponent) -> None: ...
    def register_defaults(self, config: PokemonRedConfig) -> None: ...
    def calculate(self, state: dict, prev_state: dict) -> float: ...
    def get_breakdown(self) -> dict[str, float]: ...
    def reset(self) -> None: ...
    def enable(self, name: str) -> None: ...
    def disable(self, name: str) -> None: ...
    def clear(self) -> None: ...
```

#### Aggregation formula

For each enabled component, the manager computes:

```
weighted_value = component.calculate(state, prev_state) * component.weight
```

All weighted values are summed, then multiplied by the global `reward_scale`:

```
total_reward = sum(weighted_value for each enabled component) * reward_scale
```

Disabled components contribute `0.0` and are still recorded in the breakdown with that value.

#### Breakdown

After each `calculate()` call the manager stores a snapshot of per-component weighted values.
Retrieve it with:

```python
breakdown = reward_manager.get_breakdown()
# e.g. {"exploration_novelty": 0.04, "movement_bonus_early": 0.0, "badges": 0.0, ...}
```

The environment exposes this in the `info` dictionary returned by `step()`:

```python
obs, reward, terminated, truncated, info = env.step(action)
print(info["reward_breakdown"])
```

#### Default registration order

`register_defaults(config)` registers components in this order (the order affects breakdown
dictionary iteration, but not reward magnitude):

1. `exploration_novelty` (ExplorationReward)
2. `movement_bonus_early` (ExplorationMovementReward)
3. `badges` (BadgeReward)
4. `levels` (LevelUpReward)
5. `events` (EventReward)
6. `menu_novelty` (MenuNoveltyReward)
7. `menu_bonus_early` (MenuInteractionReward)
8. `battle_win` (BattleWinReward)
9. `healing` (HealingReward)

---

## Built-in Components

### ExplorationReward

| Field | Value |
|---|---|
| Registered key | `exploration_novelty` |
| Source file | `pokemon_red_env/rewards/exploration.py` |
| Default weight | `0.02` |
| State keys read | `seen_coords_count` |

Rewards the agent for visiting map coordinates it has not seen before during the current episode.
The environment tracks a running count of unique `(x, y, map_id)` tuples in `seen_coords_count`.

**Formula:**

```
reward = max(state["seen_coords_count"] - prev_state["seen_coords_count"], 0)
```

Each newly discovered coordinate contributes `+1.0` (unweighted). The weighted contribution is
`1.0 * exploration_weight`.

**Reset behavior:** Stateless — no episode-local data. The `seen_coords_count` counter lives in
the environment and is reset externally.

---

### ExplorationMovementReward

| Field | Value |
|---|---|
| Registered key | `movement_bonus_early` |
| Source file | `pokemon_red_env/rewards/exploration.py` |
| Default weight | `0.003` |
| Default anneal steps | `120` |
| State keys read | `player_x`, `player_y`, `map_id`, `step_count` |
| Config knobs | `POKEMON_RED_MOVEMENT_BONUS_WEIGHT`, `POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS` |

Provides a warm-start movement bonus that encourages the agent to move around early in the
episode. The bonus decays linearly from `1.0` at step 1 down to `0.0` at `anneal_steps`, then
remains `0.0` for the rest of the episode.

**Formula:**

```
# Only fires when the player position or map changes
if (curr_x, curr_y, curr_map) == (prev_x, prev_y, prev_map):
    return 0.0

scale = max(anneal_steps - step_count, 0) / anneal_steps
return scale
```

The weighted contribution is `scale * movement_bonus_weight`.

**Reset behavior:** Stateless — `step_count` is provided by the environment state dictionary and
is reset externally.

---

### BadgeReward

| Field | Value |
|---|---|
| Registered key | `badges` |
| Source file | `pokemon_red_env/rewards/badges.py` |
| Default weight | `5.0` |
| State keys read | `badge_count` |
| Config knobs | `POKEMON_RED_BADGE_WEIGHT` |

Rewards the agent each time it earns a new Gym badge. The environment tracks the cumulative badge
count. This component fires at most 8 times per episode (one per Gym Leader).

**Formula:**

```
reward = max(state["badge_count"] - prev_state["badge_count"], 0)
```

The weighted contribution is `1.0 * badge_weight` per new badge (usually exactly `+5.0`).

**Reset behavior:** Stateless.

---

### LevelUpReward

| Field | Value |
|---|---|
| Registered key | `levels` |
| Source file | `pokemon_red_env/rewards/levels.py` |
| Default weight | `1.0` |
| State keys read | `level_sum` |
| Config knobs | `POKEMON_RED_LEVEL_WEIGHT` |

Rewards the agent for party Pokemon gaining experience and leveling up. `level_sum` is the sum of
all party member levels. When any Pokemon levels up the sum increases.

**Formula:**

```
reward = max(state["level_sum"] - prev_state["level_sum"], 0)
```

The weighted contribution equals the total number of levels gained this step times `level_weight`.

**Reset behavior:** Stateless.

---

### EventReward

| Field | Value |
|---|---|
| Registered key | `events` |
| Source file | `pokemon_red_env/rewards/events.py` |
| Default weight | `0.1` |
| State keys read | `event_count` |
| Config knobs | `POKEMON_RED_EVENT_WEIGHT` |

Rewards the agent for triggering new in-game event flags (story progression, item pickups, NPC
interactions, etc.). `event_count` is the count of distinct event flags that have been activated.

**Formula:**

```
reward = max(state["event_count"] - prev_state["event_count"], 0)
```

The weighted contribution is the number of new events times `event_weight`.

**Reset behavior:** Stateless.

---

### BattleWinReward

| Field | Value |
|---|---|
| Registered key | `battle_win` |
| Source file | `pokemon_red_env/rewards/battle.py` |
| Default weight | `2.0` |
| State keys read | `in_battle`, `battle_outcome` |
| Config knobs | `POKEMON_RED_BATTLE_WIN_WEIGHT` |

Rewards the agent for winning a battle. The component detects the transition from `in_battle > 0`
in the previous step to `in_battle == 0` in the current step, combined with `battle_outcome == 1`
(victory).

**Formula:**

```
if prev_in_battle and not curr_in_battle and state["battle_outcome"] == 1:
    return 1.0
return 0.0
```

The weighted contribution is `1.0 * battle_win_weight` on a winning transition.

**Reset behavior:** Stateless.

---

### HealingReward

| Field | Value |
|---|---|
| Registered key | `healing` |
| Source file | `pokemon_red_env/rewards/healing.py` |
| Default weight | `1.0` |
| State keys read | `party_hp_fraction` |
| Config knobs | `POKEMON_RED_HEALING_WEIGHT` |

Rewards the agent for recovering party HP. `party_hp_fraction` is a float in `[0.0, 1.0]`
representing the ratio of current total party HP to maximum total party HP. Only positive HP
changes are rewarded; HP loss is not penalized.

**Formula:**

```
reward = max(state["party_hp_fraction"] - prev_state["party_hp_fraction"], 0.0)
```

The weighted contribution is the HP fraction recovered times `healing_weight`.

**Reset behavior:** Stateless.

---

### MenuNoveltyReward

| Field | Value |
|---|---|
| Registered key | `menu_novelty` |
| Source file | `pokemon_red_env/rewards/menu.py` |
| Default weight | `0.004` |
| Default max signatures | `128` |
| State keys read | `text_box_id`, `current_menu_item`, `top_menu_item_x`, `top_menu_item_y`, `menu_watched_keys` |
| Config knobs | `POKEMON_RED_MENU_NOVELTY_WEIGHT`, `POKEMON_RED_MAX_MENU_SIGNATURES_PER_EPISODE` |

Rewards the agent for discovering unique menu states. A menu signature is a 5-tuple of game
memory values that together identify a distinct menu context:

```python
signature = (
    text_box_id,
    current_menu_item,
    top_menu_item_x,
    top_menu_item_y,
    menu_watched_keys,
)
```

The component maintains a set of seen signatures for the current episode. When a new signature is
encountered and the total count of seen signatures is below `max_unique_signatures`, the component
returns `1.0`. Once the cap is reached, no further novelty rewards are given for that episode.

**Formula:**

```
if signature in seen_signatures or len(seen_signatures) >= max_unique_signatures:
    return 0.0
seen_signatures.add(signature)
return 1.0
```

Setting `max_unique_signatures = 0` disables the component entirely for the episode. Setting it
to `None` removes the cap (unlimited novelty reward).

**Reset behavior:** Clears `_seen_signatures` at the start of each episode.

---

### MenuInteractionReward

| Field | Value |
|---|---|
| Registered key | `menu_bonus_early` |
| Source file | `pokemon_red_env/rewards/menu.py` |
| Default weight | `0.001` |
| Default anneal steps | `120` |
| State keys read | `text_box_id`, `current_menu_item`, `top_menu_item_x`, `top_menu_item_y`, `menu_watched_keys` |
| Config knobs | `POKEMON_RED_MENU_INTERACTION_WEIGHT`, `POKEMON_RED_MENU_ANNEAL_STEPS` |

Provides a small, time-decayed bonus for transitioning to a previously-seen menu state. This
complements `MenuNoveltyReward`: after a menu state loses novelty the agent still receives a
diminishing signal for re-entering it during the early phase of the episode.

The component tracks seen signatures across the episode. When the current signature differs from
the previous signature and the current signature has been seen before, it awards a scaled bonus.

**Formula:**

```
scale = max(anneal_steps - step_count, 0) / anneal_steps
# fires only on transitions to previously-seen menu signatures
if curr_signature != prev_signature and curr_signature in seen_signatures:
    return scale
return 0.0
```

The weighted contribution is `scale * menu_interaction_weight`.

**Reset behavior:** Clears `_seen_signatures` at the start of each episode.

---

## Annealing Mechanics

Two components use a linear annealing schedule: `ExplorationMovementReward` and
`MenuInteractionReward`. Both implement the same decay pattern:

```
scale(step) = (anneal_steps - step) / anneal_steps   for 0 < step < anneal_steps
scale(step) = 0.0                                     for step == 0 or step >= anneal_steps
```

**Example** with `anneal_steps = 120`:

| Step | Scale |
|------|-------|
| 0 | 0.000 (no bonus at step 0) |
| 1 | 0.992 |
| 30 | 0.750 |
| 60 | 0.500 |
| 90 | 0.250 |
| 119 | 0.008 |
| 120+ | 0.000 |

Setting `anneal_steps = 0` disables the component's output entirely (returns `0.0` always).

The purpose of annealing is to bootstrap early exploration without creating a persistent dense
reward that would mask more meaningful sparse signals (badges, levels, events) once the agent has
learned to navigate.

---

## Reward Breakdown

After every `step()` call the `RewardManager` records a dictionary mapping each component's
registered key to its weighted contribution for that step. The environment forwards this under the
`"reward_breakdown"` key in the `info` dictionary:

```python
obs, reward, terminated, truncated, info = env.step(action)
breakdown = info["reward_breakdown"]

# Example output after discovering a new map coordinate:
# {
#     "exploration_novelty": 0.02,
#     "movement_bonus_early": 0.0015,
#     "badges": 0.0,
#     "levels": 0.0,
#     "events": 0.0,
#     "menu_novelty": 0.0,
#     "menu_bonus_early": 0.0,
#     "battle_win": 0.0,
#     "healing": 0.0,
# }
```

Every registered component always appears in the breakdown, even if its contribution is `0.0`.
Disabled components are also listed with `0.0`.

The total reward returned by `step()` equals
`sum(breakdown.values()) * reward_scale`. Note that `reward_scale` is applied after the breakdown
is recorded, so breakdown values are pre-scale weighted contributions.

---

## Configuration Knobs

All reward-related settings are read from environment variables with the `POKEMON_RED_` prefix.
Defaults match those in `pokemon_red_env/config.py`.

| Environment Variable | Type | Default | Description |
|---|---|---|---|
| `POKEMON_RED_USE_MODULAR_REWARDS` | bool | `true` | Enable the modular reward manager |
| `POKEMON_RED_REWARD_SCALE` | float | `1.0` | Global multiplier applied after component aggregation |
| `POKEMON_RED_EXPLORATION_WEIGHT` | float | `0.02` | Weight for `exploration_novelty` |
| `POKEMON_RED_MOVEMENT_BONUS_WEIGHT` | float | `0.003` | Weight for `movement_bonus_early` |
| `POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS` | int | `120` | Steps over which movement bonus decays to zero |
| `POKEMON_RED_BADGE_WEIGHT` | float | `5.0` | Weight for `badges` |
| `POKEMON_RED_LEVEL_WEIGHT` | float | `1.0` | Weight for `levels` |
| `POKEMON_RED_EVENT_WEIGHT` | float | `0.1` | Weight for `events` |
| `POKEMON_RED_BATTLE_WIN_WEIGHT` | float | `2.0` | Weight for `battle_win` |
| `POKEMON_RED_HEALING_WEIGHT` | float | `1.0` | Weight for `healing` |
| `POKEMON_RED_MENU_NOVELTY_WEIGHT` | float | `0.004` | Weight for `menu_novelty` |
| `POKEMON_RED_MENU_INTERACTION_WEIGHT` | float | `0.001` | Weight for `menu_bonus_early` |
| `POKEMON_RED_MENU_ANNEAL_STEPS` | int | `120` | Steps over which menu interaction bonus decays to zero |
| `POKEMON_RED_MAX_MENU_SIGNATURES_PER_EPISODE` | int | `128` | Cap on unique menu signatures rewarded per episode |

All weight fields must be `>= 0`. All `anneal_steps` and signature cap fields must be `>= 0`.
The `PokemonRedConfig` validator (`pokemon_red_env/config.py`) raises `ValueError` on any invalid
value at startup.

---

## Writing Custom Components

Custom components can be registered alongside or in place of the defaults.

### Step 1 — Subclass BaseRewardComponent

```python
# my_project/rewards/my_component.py
from pokemon_red_env.rewards.base import BaseRewardComponent


class PokedexReward(BaseRewardComponent):
    """Reward the agent for seeing new Pokemon species."""

    def __init__(self, weight: float = 1.0, enabled: bool = True):
        super().__init__(name="pokedex_seen", weight=weight, enabled=enabled)

    def calculate(self, state: dict, prev_state: dict) -> float:
        prev_seen = int(prev_state.get("pokedex_seen_count", 0))
        curr_seen = int(state.get("pokedex_seen_count", 0))
        return float(max(curr_seen - prev_seen, 0))
```

Rules for `calculate()`:

- Return an **unweighted** float. The manager applies `component.weight` automatically.
- Return `0.0` when the component should not fire, not a negative value (unless you
  intentionally want a penalty — the manager will still multiply by `weight`).
- Both `state` and `prev_state` are plain dictionaries; use `.get(key, default)` defensively.

### Step 2 — Override reset() if the component is stateful

```python
class PokedexNoveltyReward(BaseRewardComponent):
    def __init__(self, weight: float = 1.0, enabled: bool = True):
        super().__init__(name="pokedex_novelty", weight=weight, enabled=enabled)
        self._seen_species: set[int] = set()

    def calculate(self, state: dict, prev_state: dict) -> float:
        species_id = int(state.get("last_seen_species_id", 0))
        if species_id == 0 or species_id in self._seen_species:
            return 0.0
        self._seen_species.add(species_id)
        return 1.0

    def reset(self) -> None:
        self._seen_species.clear()
```

### Step 3 — Register with the RewardManager

**Option A: Add to the existing default set**

```python
from pokemon_red_env.rewards import RewardManager
from pokemon_red_env.config import PokemonRedConfig
from my_project.rewards.my_component import PokedexReward

config = PokemonRedConfig()
manager = RewardManager()
manager.register_defaults(config)           # registers all built-in components
manager.register(PokedexReward(weight=2.0)) # appended after the defaults
```

**Option B: Replace defaults entirely**

```python
from pokemon_red_env.rewards import RewardManager, ExplorationReward, BadgeReward
from my_project.rewards.my_component import PokedexReward

manager = RewardManager(reward_scale=1.0)
manager.register(ExplorationReward(weight=0.02))
manager.register(BadgeReward(weight=5.0))
manager.register(PokedexReward(weight=2.0))
```

**Option C: Disable a default component at runtime**

```python
manager.register_defaults(config)
manager.disable("menu_bonus_early")   # zero out without removing
```

### Step 4 — Inject the custom manager into the environment

Pass your configured manager when constructing `PokemonRedEnvironment`:

```python
from pokemon_red_env import PokemonRedEnvironment

env = PokemonRedEnvironment(config=config, reward_manager=manager)
```

Your component's key will appear automatically in `info["reward_breakdown"]` during rollouts.

---

## MovementReward (Legacy)

`MovementReward` is defined in `pokemon_red_env/rewards/movement.py` and exported from
`pokemon_red_env/rewards/__init__.py`, but it is **not registered by default**.

```python
class MovementReward(BaseRewardComponent):
    """Dense reward: +1 for any step where the player position changes."""
    def __init__(self, weight: float = 1.0, target_direction: str | None = None, ...): ...
```

It supports an optional `target_direction` argument (`"up"`, `"down"`, `"left"`, `"right"`) to
reward only directional movement. Without it, any position change awards `1.0`.

This component was removed from the default set because a dense movement reward masks exploration
novelty and leads to agents that pace back and forth rather than advancing through the game. It is
retained for experimentation and custom setups. To re-enable it:

```python
from pokemon_red_env.rewards import MovementReward

manager.register(MovementReward(weight=0.1))
```

The legacy `POKEMON_RED_MOVEMENT_WEIGHT` environment variable (default `1.0`) is still accepted
by `PokemonRedConfig` for backward compatibility but has no effect on the default reward
registration.
