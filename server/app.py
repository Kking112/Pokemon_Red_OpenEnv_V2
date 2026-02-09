from __future__ import annotations

import os

import uvicorn

from pokemon_red_env.server.app import app


def main() -> None:
    host = os.getenv("POKEMON_RED_HOST", "0.0.0.0")
    port = int(os.getenv("POKEMON_RED_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
