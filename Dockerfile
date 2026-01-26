FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    apt-get update && apt-get install --no-install-recommends -yq \
    pandoc

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uv", "run", "fastapi", "run", "src/selina_wp4/main.py"]
