from __future__ import annotations

from openenv.core.env_server import create_app

from pokemon_red_env.config import PokemonRedConfig
from pokemon_red_env.models import PokemonRedAction, PokemonRedObservation

from .environment import PokemonRedEnvironment


def create_pokemon_environment() -> PokemonRedEnvironment:
    config = PokemonRedConfig()
    return PokemonRedEnvironment(config=config)


app = create_app(
    create_pokemon_environment,
    PokemonRedAction,
    PokemonRedObservation,
    env_name="pokemon_red",
)
