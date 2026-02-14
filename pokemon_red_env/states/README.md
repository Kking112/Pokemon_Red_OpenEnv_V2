# State Usage

This environment uses PyBoy states from this package directory:

`pokemon_red_env/states/`

All `.state` files in this folder are valid start states. Use either:
- a full filename like `home.state`,
- a basename like `home`,
- or one of the aliases below.

Canonical aliases:

- `has_starter` -> `Bulbasaur.state`
- `has_pokedex` -> `has_pokedex.state`
- `game_start` -> `home.state`

You can also pass a direct `.state` filename or absolute file path to `reset(init_state=...)`.
