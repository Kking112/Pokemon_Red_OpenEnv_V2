# Phase 02 - Types and Config

## Implemented

- Added typed models:
  - `PokemonRedAction`
  - `PokemonRedObservation`
  - `PokemonRedState`
- Added `PokemonRedConfig` (`BaseSettings`) with `POKEMON_RED_` env prefix.
- Added config invariants:
  - `action_freq >= press_duration + 1`
  - `max_steps >= 0`
  - downscale/count bounds.

## Validation

- Unit tests in `tests/test_config.py`
- Import checks through environment/client tests.
