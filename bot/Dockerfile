FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backnote ./backnote
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

VOLUME ["/app/data"]
CMD ["uv", "run", "--no-sync", "backnote"]
