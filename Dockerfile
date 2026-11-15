# syntax=docker/dockerfile:1

# --- build stage: resolve dependencies and install the project -------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (cached unless the lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable

# Then build and install the project itself (non-editable, for the container)
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# --- runtime stage: only the venv ships, no build tooling -------------------
FROM python:3.12-slim-bookworm

RUN useradd --create-home appuser
USER appuser

WORKDIR /app

COPY --from=build /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=3001

EXPOSE 3001

ENTRYPOINT ["redis"]
