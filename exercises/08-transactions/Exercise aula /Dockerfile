FROM python:3.14-slim

# uv (Astral): instala as dependências a partir do pyproject.toml.
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Só as dependências primeiro, para esta camada ficar em cache enquanto o código muda.
COPY pyproject.toml .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev

COPY app/ ./app/
COPY data/ ./data/

CMD ["python", "-m", "app.main"]
