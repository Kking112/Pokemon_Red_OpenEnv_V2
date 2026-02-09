# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE} AS builder

WORKDIR /app

# Build args are set by `openenv build`.
ARG BUILD_MODE=standalone
ARG ENV_NAME=pokemon-red-openenv

# Install tooling needed for uv + git-based dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

# Copy full environment source.
COPY . /app/env
WORKDIR /app/env

# Install dependencies with uv. Prefer lockfile when available.
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --no-editable; \
    else \
        uv sync --no-install-project --no-editable; \
    fi

RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-editable; \
    else \
        uv sync --no-editable; \
    fi

FROM ${BASE_IMAGE}

WORKDIR /app

# Copy virtual environment and source tree.
COPY --from=builder /app/env/.venv /app/.venv
COPY --from=builder /app/env /app/env

# Use project venv binaries by default.
ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app/env"

# Runtime defaults (override with docker run -e ... as needed).
# ROM is expected to be mounted at runtime for legal/compliance reasons.
RUN mkdir -p /app/roms
ENV POKEMON_RED_GB_PATH="/app/roms/PokemonRed.gb"
ENV POKEMON_RED_SYMBOLS_PATH="/app/env/Assembly_RAM_Addresses/pokered.sym"
ENV POKEMON_RED_STATE_DIR="/app/env/pokemonred_puffer/pyboy_states"

EXPOSE 8000

# OpenEnv health endpoint is provided by create_app.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["sh", "-c", "cd /app/env && uvicorn server.app:app --host 0.0.0.0 --port 8000"]
