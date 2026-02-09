from __future__ import annotations

from typing import Any

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class PokemonRedAction(Action):
    """Discrete action sent by the policy."""

    action: int = Field(ge=0, le=16, description="Discrete action index")


class PokemonRedObservation(Observation):
    """Observation contract returned by reset/step."""

    screen_b64: str = Field(default="", description="Base64-encoded PNG frame")
    screen_shape: list[int] = Field(
        default_factory=lambda: [144, 160, 3],
        description="Frame shape as [height, width, channels]",
    )
    game_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured RAM-derived game state",
    )
    legal_actions: list[int] = Field(
        default_factory=list,
        description="Valid action indices for the current state",
    )
    info: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional environment metadata for debugging/logging",
    )


class PokemonRedState(State):
    """Environment internal state for checkpoint/debug access."""

    total_reward: float = Field(default=0.0)
    current_init_state: str = Field(default="")
    last_action: int | None = Field(default=None)
    done: bool = Field(default=False)
