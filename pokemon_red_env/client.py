from __future__ import annotations

from typing import Any

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from .models import PokemonRedAction, PokemonRedObservation, PokemonRedState


class PokemonRedEnv(EnvClient[PokemonRedAction, PokemonRedObservation, PokemonRedState]):
    """Typed OpenEnv WebSocket client for the Pokemon Red environment."""

    def _step_payload(self, action: PokemonRedAction) -> dict[str, Any]:
        return action.model_dump()

    def _parse_result(self, payload: dict[str, Any]) -> StepResult[PokemonRedObservation]:
        obs_data = payload.get("observation", {})
        obs_payload = dict(obs_data)
        obs_payload["reward"] = payload.get("reward")
        obs_payload["done"] = payload.get("done", False)

        observation = PokemonRedObservation.model_validate(obs_payload)
        return StepResult(
            observation=observation,
            reward=float(payload.get("reward")) if payload.get("reward") is not None else None,
            done=bool(payload.get("done", False)),
        )

    def _parse_state(self, payload: dict[str, Any]) -> PokemonRedState:
        return PokemonRedState.model_validate(payload)

    async def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        init_state: str | None = None,
        **kwargs: Any,
    ) -> StepResult[PokemonRedObservation]:
        reset_kwargs: dict[str, Any] = {}
        if seed is not None:
            reset_kwargs["seed"] = seed
        if episode_id is not None:
            reset_kwargs["episode_id"] = episode_id
        if init_state is not None:
            reset_kwargs["init_state"] = init_state
        reset_kwargs.update(kwargs)
        return await super().reset(**reset_kwargs)
