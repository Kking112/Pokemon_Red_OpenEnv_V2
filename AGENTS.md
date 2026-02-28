# AGENTS

## Architecture

- Package root: `pokemon_red_env/`
- OpenEnv models: `pokemon_red_env/models.py`
- Config: `pokemon_red_env/config.py`
- Server app/environment: `pokemon_red_env/server/`
- Memory subsystem: `pokemon_red_env/memory/`
- Rewards subsystem: `pokemon_red_env/rewards/`
- Data tables: `pokemon_red_env/data/`
- State alias docs: `pokemon_red_env/states/`

## Extension points

- Add RAM fields by extending `Addresses` and `MemoryReader.extract_game_state`.
- Add reward logic via new `BaseRewardComponent` subclasses and `RewardManager.register`.
- Add state aliases in `pokemon_red_env/state_registry.py`.

## Action policy

- `NOOP` is always final action index when enabled.
- `SELECT` is optional and inserted before `NOOP` when enabled.

## Test commands

```bash
uv run ruff check pokemon_red_env tests
uv run pytest -q
uv run pytest --cov=pokemon_red_env --cov-report=term-missing
uv run openenv validate --verbose .
```

## SDL2 Window Responsiveness

When running in non-headless mode (`headless=False`), the environment provides:

- **`pump_events()`**: Call periodically during idle time to process SDL2 window events without advancing emulation. Uses `pyboy.tick(0, render=False)`. Prevents the OS from marking the window as unresponsive during long pauses (e.g., VLM forward passes, PPO updates).
- **`is_headless`** property: Check whether the environment has an SDL2 window.
- **`timeout_s`** on `step()`: Optional watchdog thread that flags long-running steps. Checks at natural boundaries (after action execution, after state extraction).

## Operational constraints

- Environment config is immutable per server process.
- Change reward/profile settings by launching separate server instances.
- Existing states are reused from `pokemon_red_env/states`; users can add new `.state` files there.
