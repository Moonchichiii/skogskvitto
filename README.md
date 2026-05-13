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
export POSTGRES_PASSWORD=
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export GOOGLE_OAUTH_CLIENT_ID=
export GOOGLE_OAUTH_CLIENT_SECRET=
export STRIPE_SECRET_KEY=
export STRIPE_PRICE_MONTHLY_ID=price_dummy_monthly
export STRIPE_PRICE_YEARLY_ID=price_dummy_yearly
export FREEMIUM_RECEIPT_LIMIT=10
export OPENAI_API_KEY=
export EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend
export DEFAULT_FROM_EMAIL=noreply@example.test
export EMAIL_HOST=localhost
export EMAIL_PORT=1025
export EMAIL_HOST_USER=
export EMAIL_HOST_PASSWORD=

uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run ruff check .
uv run mypy .
uv run pytest
```

## Secret handling in CI

- Inga riktiga secrets får hårdkodas i CI-workflows.
- Externa tjänster ska ha tomma env-värden i CI (t.ex. OAuth, Stripe, OpenAI).
- Deploy/production-secrets ska endast hämtas från GitHub Secrets i deploy-workflows.
- Tester i CI ska använda `django.core.mail.backends.locmem.EmailBackend`.
