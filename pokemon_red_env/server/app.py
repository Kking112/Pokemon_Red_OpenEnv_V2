from __future__ import annotations

import logging
from collections.abc import Callable

from openenv.core.env_server import create_app

from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.models import PokemonRedAction, PokemonRedObservation

from .environment import PokemonRedEnvironment

LOGGER = logging.getLogger(__name__)


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


def create_pokemon_environment() -> PokemonRedEnvironment:
    config = PokemonRedConfig()
    return PokemonRedEnvironment(config=config)


app = create_pokemon_app()
