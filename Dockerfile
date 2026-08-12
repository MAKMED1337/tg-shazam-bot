# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.12-slim

FROM ghcr.io/astral-sh/uv:0.9.26 AS uv
FROM mwader/static-ffmpeg:7.1.1 AS ffmpeg

FROM ${PYTHON_IMAGE} AS builder

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy

WORKDIR /app

# Dependencies stay cached when only application source changes.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM ${PYTHON_IMAGE} AS runtime

COPY --from=denoland/deno:bin-2.8.2 /deno /usr/local/bin/deno
COPY --from=ffmpeg /ffmpeg /usr/local/bin/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

CMD ["python", "-m", "shazam_bot"]
