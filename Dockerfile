FROM oven/bun:1.2-slim AS assets

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY assets ./assets
COPY static ./static
COPY templates ./templates
COPY apps ./apps
COPY config ./config

RUN bun run css:build


FROM python:3.13-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./

RUN uv venv /app/.venv \
    && uv sync --python /app/.venv/bin/python --frozen --no-dev


FROM python:3.13-slim AS runtime

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

COPY --from=builder --chown=1000:1000 /app/.venv /app/.venv
COPY --chown=1000:1000 . /app
COPY --from=assets --chown=1000:1000 /app/static/css/app.css /app/static/css/app.css

RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_SECRET_KEY=build-only-secret \
    DJANGO_ALLOWED_HOSTS=localhost \
    DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost \
    DATABASE_URL=postgresql://build_only:build_only@localhost:5432/build_only?sslmode=disable \
    POSTGRES_CONN_MAX_AGE=60 \
    CLOUDINARY_CLOUD_NAME=dakjlrean \
    python manage.py collectstatic --noinput

USER 1000:1000

EXPOSE 8080

CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8080", "--workers", "2"]