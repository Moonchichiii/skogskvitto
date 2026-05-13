# SkogsKvitto

```bash
uv venv && uv sync --dev
cp .env.example .env
docker compose up --build
```

## Kvalitetskontroller

Miljövariabler i `config/settings.py` är obligatoriska även för lokala checks.

```bash
export DJANGO_SECRET_KEY=devsecret
export DJANGO_DEBUG=1
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
export DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000
export POSTGRES_DB=skogskvitto
export POSTGRES_USER=skogskvitto
export POSTGRES_PASSWORD=skogskvitto
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export GOOGLE_OAUTH_CLIENT_ID=dummy
export GOOGLE_OAUTH_CLIENT_SECRET=dummy
export STRIPE_SECRET_KEY=dummy
export STRIPE_PRICE_MONTHLY_ID=price_dummy_monthly
export STRIPE_PRICE_YEARLY_ID=price_dummy_yearly
export FREEMIUM_RECEIPT_LIMIT=10

uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run mypy .
uv run pytest
```
