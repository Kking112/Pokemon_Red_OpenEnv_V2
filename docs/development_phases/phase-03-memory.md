# Phase 03 - Memory Subsystem

## Implemented

- Added `memory/addresses.py` with grouped canonical addresses.
- Added `memory/game_state.py` dataclasses and dict export.
- Added `memory/reader.py` utilities:
  - byte/word/bytes/BCD/bit reads
  - event flag lookups
  - custom read API
  - full game state extraction.
- Generated normalized data tables:
  - `pokemon_red_env/data/events.json`
  - `pokemon_red_env/data/maps.json`
  - `pokemon_red_env/data/curated_events.json`

## Validation

- Unit tests in `tests/test_memory_reader.py`.
- Canonical symbol corrections reflected from `pokered.sym`.
