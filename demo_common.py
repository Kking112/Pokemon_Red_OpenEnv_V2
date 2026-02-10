from __future__ import annotations

import asyncio
import base64
import io
import os
import random
import shutil
import socket
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np
from PIL import Image

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


def _decode_screen(screen_b64: str, screen_shape: list[int]) -> np.ndarray:
    if not screen_b64:
        h, w, c = (screen_shape + [144, 160, 3])[:3]
        return np.zeros((int(h), int(w), int(c)), dtype=np.uint8)

    image_bytes = base64.b64decode(screen_b64)
    with Image.open(io.BytesIO(image_bytes)) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


class TerminalRenderer:
    """Render RGB frames as ANSI truecolor blocks in the terminal."""

    def __init__(self, width: int = 64):
        self.width = max(16, int(width))
        term_value = os.getenv("TERM", "").lower()
        self._enabled = sys.stdout.isatty() and term_value not in {"", "dumb"}

    def render(self, frame: np.ndarray, header: str) -> None:
        if not self._enabled:
            print(header)
            return

        if frame.ndim != 3 or frame.shape[2] != 3:
            frame = np.zeros((144, 160, 3), dtype=np.uint8)

        term_cols = shutil.get_terminal_size(fallback=(120, 40)).columns
        target_width = min(self.width, max(16, term_cols - 2))
        stride = max(1, int(np.ceil(frame.shape[1] / target_width)))
        sampled = frame[::stride, ::stride, :]

        if sampled.shape[0] % 2 == 1:
            sampled = sampled[:-1, :, :]

        lines: list[str] = [header]
        for y in range(0, sampled.shape[0], 2):
            top = sampled[y]
            bottom = sampled[y + 1]
            parts: list[str] = []
            for x in range(sampled.shape[1]):
                tr, tg, tb = top[x]
                br, bg, bb = bottom[x]
                parts.append(
                    f"\x1b[38;2;{int(tr)};{int(tg)};{int(tb)}m"
                    f"\x1b[48;2;{int(br)};{int(bg)};{int(bb)}m▀"
                )
            parts.append("\x1b[0m")
            lines.append("".join(parts))

        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write("\n".join(lines))
        sys.stdout.write("\n")
        sys.stdout.flush()


async def run_random_episode(
    *,
    base_url: str,
    steps: int = 100,
    init_state: str = "game_start",
    seed: int = 0,
    fps: float = 6.0,
    render_width: int = 64,
    label: str = "pokemon_red",
) -> tuple[int, bool]:
    """Run a random policy episode and render every frame."""
    rng = random.Random(seed)
    renderer = TerminalRenderer(width=render_width)
    delay_s = 0.0 if fps <= 0 else 1.0 / fps

    async with PokemonRedEnv(base_url=base_url) as env:
        result = await env.reset(init_state=init_state)
        frame = _decode_screen(
            result.observation.screen_b64,
            result.observation.screen_shape,
        )
        start_total_reward = float(result.observation.game_state.get("total_reward", 0.0))
        renderer.render(
            frame,
            (
                f"{label} | step=0/{steps} action=reset reward=+0.000 "
                f"total_reward={start_total_reward:+.3f} done={result.done}"
            ),
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

            frame = _decode_screen(
                result.observation.screen_b64,
                result.observation.screen_shape,
            )
            reward = float(result.reward or 0.0)
            total_reward = float(result.observation.game_state.get("total_reward", 0.0))
            action_name = str(result.observation.info.get("action_name", "unknown"))
            renderer.render(
                frame,
                (
                    f"{label} | step={steps_executed}/{steps} action={action}({action_name}) "
                    f"reward={reward:+.3f} total_reward={total_reward:+.3f} done={result.done}"
                ),
            )
            if delay_s > 0:
                await asyncio.sleep(delay_s)

        return steps_executed, bool(result.done)
