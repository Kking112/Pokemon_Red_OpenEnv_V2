# Phase 04 - Rewards

## Implemented

- Added reward base + manager architecture.
- Added built-in components:
  - exploration novelty (`exploration_novelty`)
  - movement warm-start bonus (`movement_bonus_early`)
  - badges
  - levels
  - events
  - battle wins
  - healing
  - menu novelty (`menu_novelty`)
  - early menu interaction (`menu_bonus_early`)

Movement exploration is now an annealed bonus only and decays to zero after the configured
`movement_bonus_anneal_steps`.

Menu rewards are novelty-driven and include:

- new menu-signature discovery (`menu_novelty`)
- a small, decayed interaction reward for non-novel menu transitions (`menu_bonus_early`)

Legacy dense `MovementReward` is no longer enabled by default.
- Added breakdown reporting through manager.

## Config knobs

- `POKEMON_RED_EXPLORATION_WEIGHT`
- `POKEMON_RED_MOVEMENT_BONUS_WEIGHT`
- `POKEMON_RED_MOVEMENT_BONUS_ANNEAL_STEPS`
- `POKEMON_RED_BADGE_WEIGHT`
- `POKEMON_RED_LEVEL_WEIGHT`
- `POKEMON_RED_EVENT_WEIGHT`
- `POKEMON_RED_MENU_NOVELTY_WEIGHT`
- `POKEMON_RED_MENU_INTERACTION_WEIGHT`
- `POKEMON_RED_MENU_ANNEAL_STEPS`
- `POKEMON_RED_MAX_MENU_SIGNATURES_PER_EPISODE`

## Validation

- Unit tests in `tests/test_rewards.py`.
