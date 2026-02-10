from __future__ import annotations

import argparse
import asyncio
import contextlib
import subprocess
import uuid
from pathlib import Path

from demo_common import find_free_port, run_random_episode, wait_for_health


REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_ROM_PATH = REPO_ROOT / "PokemonRed.gb"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a random-action Pokemon Red demo for 100 steps using the "
            "Dockerized OpenEnv server."
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
        "--image",
        default="pokemon-red-openenv:latest",
        help="Docker image name for the OpenEnv server.",
    )
    parser.add_argument(
        "--force-build",
        action="store_true",
        help="Always rebuild the Docker image before running.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Do not build image even if missing; fail instead.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Host port to expose container server on. Use 0 for automatic free port.",
    )
    parser.add_argument(
        "--server-timeout-s",
        type=float,
        default=90.0,
        help="Seconds to wait for container health before failing.",
    )
    parser.add_argument(
        "--keep-container",
        action="store_true",
        help="Keep the container running after the demo exits.",
    )
    return parser.parse_args()


def _docker_cmd(*parts: str, capture_output: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *parts],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=capture_output,
        check=False,
    )


def _ensure_docker_available() -> None:
    probe = _docker_cmd("version", "--format", "{{.Server.Version}}", capture_output=True)
    if probe.returncode != 0:
        message = probe.stderr.strip() or probe.stdout.strip() or "unknown docker error"
        raise RuntimeError(f"Docker is not available: {message}")


def _image_exists(image: str) -> bool:
    result = _docker_cmd("image", "inspect", image, capture_output=True)
    return result.returncode == 0


def _build_image(image: str) -> None:
    cmd = ["uv", "run", "openenv", "build", "-t", image]
    process = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Failed to build Docker image {image}")


def _start_container(image: str, container_name: str, host_port: int, rom_path: Path) -> str:
    run_result = _docker_cmd(
        "run",
        "--rm",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{host_port}:8000",
        "-v",
        f"{rom_path}:/app/roms/PokemonRed.gb:ro",
        "-e",
        "POKEMON_RED_GB_PATH=/app/roms/PokemonRed.gb",
        "-e",
        "POKEMON_RED_HEADLESS=true",
        image,
        capture_output=True,
    )
    if run_result.returncode != 0:
        message = run_result.stderr.strip() or run_result.stdout.strip()
        raise RuntimeError(f"Failed to start container: {message}")
    return run_result.stdout.strip()


def _stop_container(container_name: str) -> None:
    _docker_cmd("stop", container_name)


def _container_logs(container_name: str) -> str:
    result = _docker_cmd("logs", "--tail", "120", container_name, capture_output=True)
    return result.stdout.strip() or result.stderr.strip()


def main() -> None:
    args = parse_args()

    if args.steps <= 0:
        raise ValueError("--steps must be > 0")

    rom_path = Path(args.rom_path).expanduser().resolve()
    if not rom_path.exists():
        raise FileNotFoundError(
            f"ROM file not found at {rom_path}. Set --rom-path to a valid .gb file."
        )

    _ensure_docker_available()

    image_exists = _image_exists(args.image)
    if args.force_build:
        _build_image(args.image)
    elif not image_exists:
        if args.skip_build:
            raise RuntimeError(
                f"Docker image {args.image} does not exist and --skip-build was set."
            )
        _build_image(args.image)

    host_port = args.port if args.port > 0 else find_free_port()
    container_name = f"pokemon-red-demo-{uuid.uuid4().hex[:8]}"
    _start_container(args.image, container_name, host_port, rom_path)

    base_url = f"http://127.0.0.1:{host_port}"
    keep_container = bool(args.keep_container)
    try:
        wait_for_health(base_url, args.server_timeout_s)
        steps_executed, finished = asyncio.run(
            run_random_episode(
                base_url=base_url,
                steps=args.steps,
                init_state=args.init_state,
                seed=args.seed,
                fps=args.fps,
                render_width=args.render_width,
                label="pokemon_red (docker server)",
            )
        )
        print(f"Completed {steps_executed} steps. episode_done={finished}")
    except Exception as exc:
        logs = _container_logs(container_name)
        if logs:
            print("\nContainer logs (tail):")
            print(logs)
        raise RuntimeError(f"Demo failed: {exc}") from exc
    finally:
        if keep_container:
            print(f"Container kept alive: {container_name} on {base_url}")
        else:
            with contextlib.suppress(Exception):
                _stop_container(container_name)


if __name__ == "__main__":
    main()
