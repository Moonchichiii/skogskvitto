FROM python:3.13-slim AS tailwind
WORKDIR /build
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /usr/local/bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 \
    && chmod +x /usr/local/bin/tailwindcss
RUN mkdir -p /build/static/css \
    && printf '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n' > /build/input.css \
    && tailwindcss -i /build/input.css -o /build/static/css/app.css --minify

FROM python:3.13-slim AS builder
WORKDIR /app
ENV UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv
COPY pyproject.toml README.md ./
RUN uv venv /app/.venv \
    && uv sync --python /app/.venv/bin/python --no-dev

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser
COPY --from=builder --chown=1000:1000 /app/.venv /app/.venv
COPY --from=tailwind --chown=1000:1000 /build/static /app/static
COPY --chown=1000:1000 . /app
USER 1000:1000
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
