# SkogsKvitto

## Lokal körning

```bash
uv venv && uv sync --dev
cp .env.example .env
docker compose up --build
```

`docker-compose.yml` läser miljövariabler från `.env.local` (om den finns) och annars `.env`. Inga lösenord får hårdkodas i compose-filen.

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
export STRIPE_PRICE_MONTHLY_ID=
export STRIPE_PRICE_YEARLY_ID=
export FREEMIUM_RECEIPT_LIMIT=10
export OPENAI_API_KEY=
export CLOUDINARY_URL=
export CLOUDINARY_CLOUD_NAME=
export CLOUDINARY_API_KEY=
export CLOUDINARY_API_SECRET=
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

## CI-regler

- Inga hardcoded secrets eller secret-liknande dummyvärden.
- Externa tjänster i CI ska ha tomma env-värden:
  - `OPENAI_API_KEY=""`
  - `GOOGLE_OAUTH_CLIENT_SECRET=""`
  - `STRIPE_SECRET_KEY=""`
  - `EMAIL_HOST_PASSWORD=""`
- CI-email ska använda `django.core.mail.backends.locmem.EmailBackend`.
- CI-Postgres ska använda `POSTGRES_HOST_AUTH_METHOD=trust` och `DATABASE_URL` utan lösenord.

## Deploy (Fly.io)

Deploy-workflows får referera till GitHub Secrets, men får aldrig innehålla fallbackvärden som ser ut som secrets.

Tillåtet:

```yaml
FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Förbjudet:

```yaml
FLY_API_TOKEN: ci-fly-secret
```

Följande secrets ska sättas i Fly.io (inte hårdkodas i repo):

- `DJANGO_SECRET_KEY`
- `DATABASE_URL`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `EMAIL_*` (om email används)
- `OPENAI_API_KEY` (om AI används)
- `CLOUDINARY_URL` eller `CLOUDINARY_*` beroende på miljö

## Filstorage i produktion

- MEDIA/file storage ska använda Cloudinary i produktion.
- Cloudinary credentials läses från env och får aldrig hårdkodas.
- Lägg inte till S3/R2/B2 eller andra storage-providers utan explicit beslut.

## Cloudinary backup/retention/export

- Aktivera backup/versioning i Cloudinary-kontot.
- Definiera retention-policy i Cloudinary för uppladdade kvitton/fakturor.
- Kör regelbunden exportstrategi för kvitton/fakturor (metadata + filer) till separat säker lagring enligt verksamhetskrav.

## Secret handling in CI

- Inga riktiga secrets får hårdkodas i CI-workflows.
- Externa tjänster ska ha tomma env-värden i CI (t.ex. OAuth, Stripe, OpenAI).
- Deploy/production-secrets ska endast hämtas från GitHub Secrets i deploy-workflows.
- Tester i CI ska använda `django.core.mail.backends.locmem.EmailBackend`.
