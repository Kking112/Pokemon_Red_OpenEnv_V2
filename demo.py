from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import subprocess
from pathlib import Path

from demo_common import find_free_port, run_random_episode, wait_for_health


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_ROM_PATH = REPO_ROOT / "PokemonRed.gb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a random-action Pokemon Red demo for 100 steps using the local "
            "OpenEnv client/server setup."
        )
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=100,
        help="Number of random actions to take.",
    )
    parser.add_argument(
        "--init-state",
        default="game_start",
        help="Initial state alias or state file name.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for action sampling.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=6.0,
        help="Render speed. Set 0 to render as fast as possible.",
    )
    parser.add_argument(
        "--render-width",
        type=int,
        default=64,
        help="Target render width in terminal character cells.",
    )
    parser.add_argument(
        "--rom-path",
        default=str(DEFAULT_ROM_PATH),
        help="Path to a legal Pokemon Red .gb ROM file.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port for spawned server. Use 0 for automatic free-port selection.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for an existing server when --use-existing-server is set.",
    )
    parser.add_argument(
        "--use-existing-server",
        action="store_true",
        help="Connect to an already-running server instead of launching uvicorn.",
    )
    parser.add_argument(
        "--server-timeout-s",
        type=float,
        default=60.0,
        help="Seconds to wait for server health before failing.",
    )
    return parser.parse_args()


def _start_local_server(port: int, rom_path: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["POKEMON_RED_GB_PATH"] = str(rom_path)
    env.setdefault("POKEMON_RED_HEADLESS", "true")

    cmd = [
        "uv",
        "run",
        "uvicorn",
        "pokemon_red_env.server.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    return subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def _stop_server(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=10)
    if process.poll() is None:
        process.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=5)


def main() -> None:
    args = parse_args()

    if args.steps <= 0:
        raise ValueError("--steps must be > 0")

    if args.use_existing_server:
        base_url = args.base_url.rstrip("/")
        wait_for_health(base_url, args.server_timeout_s)
        steps_executed, finished = asyncio.run(
            run_random_episode(
                base_url=base_url,
                steps=args.steps,
                init_state=args.init_state,
                seed=args.seed,
                fps=args.fps,
                render_width=args.render_width,
                label="pokemon_red (local existing server)",
            )
        )
        print(f"Completed {steps_executed} steps. episode_done={finished}")
        return

    rom_path = Path(args.rom_path).expanduser().resolve()
    if not rom_path.exists():
        raise FileNotFoundError(
            f"ROM file not found at {rom_path}. Set --rom-path or POKEMON_RED_GB_PATH."
        )

    port = args.port if args.port > 0 else find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = _start_local_server(port=port, rom_path=rom_path)
    try:
        wait_for_health(base_url, args.server_timeout_s, process=server)
        steps_executed, finished = asyncio.run(
            run_random_episode(
                base_url=base_url,
                steps=args.steps,
                init_state=args.init_state,
                seed=args.seed,
                fps=args.fps,
                render_width=args.render_width,
                label="pokemon_red (local spawned server)",
            )
        )
        print(f"Completed {steps_executed} steps. episode_done={finished}")
    finally:
        _stop_server(server)


if __name__ == "__main__":
    main()
