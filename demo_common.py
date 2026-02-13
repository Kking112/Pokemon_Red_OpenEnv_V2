from __future__ import annotations

import asyncio
import random
import socket
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from pokemon_red_env import PokemonRedAction, PokemonRedEnv


def find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(base_url: str, timeout_s: float, process: Any | None = None) -> None:
    """Wait until the OpenEnv server responds on /health."""
    health_url = f"{base_url.rstrip('/')}/health"
    deadline = time.time() + timeout_s

    while time.time() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(
                f"Server process exited early with code {process.returncode} before becoming healthy."
            )
        try:
            with urlopen(health_url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            pass
        time.sleep(0.25)

    raise RuntimeError(f"Server did not become healthy at {health_url} within {timeout_s:.1f}s")


async def run_random_episode(
    *,
    base_url: str,
    steps: int = 100,
    init_state: str = "game_start",
    seed: int = 0,
    fps: float = 6.0,
    label: str = "pokemon_red",
) -> tuple[int, bool]:
    """Run a random policy episode."""
    rng = random.Random(seed)
    if fps < 0:
        raise ValueError("fps must be non-negative")
    delay_s = 0.0 if fps <= 0 else 1.0 / fps

    async with PokemonRedEnv(base_url=base_url) as env:
        result = await env.reset(init_state=init_state)
        start_total_reward = float(result.observation.game_state.get("total_reward", 0.0))
        print(
            f"{label} | step=0/{steps} action=reset reward=+0.000 "
            f"total_reward={start_total_reward:+.3f} done={result.done}"
        )
        if delay_s > 0:
            await asyncio.sleep(delay_s)

        steps_executed = 0
        while steps_executed < steps and not result.done:
            legal_actions = result.observation.legal_actions
            if not legal_actions:
                raise RuntimeError("No legal actions returned by server.")

            action = int(rng.choice(legal_actions))
            result = await env.step(PokemonRedAction(action=action))
            steps_executed += 1

            reward = float(result.reward or 0.0)
            total_reward = float(result.observation.game_state.get("total_reward", 0.0))
            action_name = str(result.observation.info.get("action_name", "unknown"))
            print(
                f"{label} | step={steps_executed}/{steps} action={action}({action_name}) "
                f"reward={reward:+.3f} total_reward={total_reward:+.3f} done={result.done}"
            )
            if delay_s > 0:
                await asyncio.sleep(delay_s)

        return steps_executed, bool(result.done)
