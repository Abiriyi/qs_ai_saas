# Deployment Guide — QS AI SaaS on Fly.io

This project ships as a single Docker image that is deployed as **three Fly.io
apps** sharing the same codebase:

| App | Role | Command |
| --- | --- | --- |
| `qs-ai-api` | Web/API (Gunicorn + Django) | `fly.toml` |
| `qs-ai-worker` | Celery worker (documents, BoQ, pricing) | `fly.worker.toml` |
| `qs-ai-flower` | Celery monitoring dashboard | `fly.flower.toml` |

External services: **PostgreSQL**, **Redis**, **Tigris** (S3-compatible object
storage), **OpenAI**.

---

## 1. Prerequisites

```bash
fly auth signup            # or: fly auth login
fly apps create qs-ai-api
fly apps create qs-ai-worker
fly apps create qs-ai-flower
```

Provision a Postgres cluster and a Redis (Upstash or Fly Redis) instance, and
note their connection details.

---

## 2. Set secrets (never commit these)

Set the same DB/Redis/storage/OpenAI secrets on every app that needs them.
See [`SECRET_ROTATION.md`](./SECRET_ROTATION.md) for how to generate each one.

```bash
COMMON_SECRETS=(
  DJANGO_SECRET_KEY=...            # python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
  DJANGO_ALLOWED_HOSTS=qs-ai-api.fly.dev
  POSTGRES_DB=qs_ai_db
  POSTGRES_USER=qs_ai_user
  POSTGRES_PASSWORD=...
  POSTGRES_HOST=...                # e.g. <pg-app>.flycast or an Upstash host
  POSTGRES_PORT=5432
  REDIS_URL=rediss://...           # use rediss:// (TLS) for managed Redis
  TIGRIS_ACCESS_KEY=...
  TIGRIS_SECRET_KEY=...
  TIGRIS_BUCKET=...
  OPENAI_API_KEY=sk-proj-...
)

for app in qs-ai-api qs-ai-worker qs-ai-flower; do
  fly secrets set "${COMMON_SECRETS[@]}" --app "$app"
done
```

For a custom domain, also set `DJANGO_CSRF_TRUSTED_ORIGINS=https://your.domain`.

---

## 3. Deploy

```bash
# Web/API — runs migrations via the release_command, then serves traffic.
fly deploy --app qs-ai-api

# Celery worker (no HTTP service; just drains the queue).
fly deploy -c fly.worker.toml --app qs-ai-worker

# Flower dashboard (protect with FLOWER_BASIC_AUTH or keep it internal).
fly deploy -c fly.flower.toml --app qs-ai-flower
```

The first `qs-ai-api` deploy runs `python manage.py migrate --noinput`
automatically before switching traffic.

---

## 4. Create the first superuser

Django admin needs a user inside an organization. Use `fly ssh`:

```bash
fly ssh console --app qs-ai-api -C "python manage.py createsuperuser"
```

Because the custom user model requires an organization, either create an
`Organization` row in the admin first, or use a shell:

```bash
fly ssh console --app qs-ai-api -C "python manage.py shell"
```

```python
from users.models import Organization, User
org = Organization.objects.create(name="My Firm", type="firm")
User.objects.create_superuser(email="you@example.com", organization=org, password="...")
```

---

## 5. How the image is built

`Dockerfile` (multi-stage):

1. **builder** — installs build deps (libpq, tesseract, poppler) and builds
   Python wheels from `requirements.txt`.
2. **runtime** — slim image, non-root `appuser`, installs the pre-built
   wheels, copies the source, and runs `collectstatic` so WhiteNoise can serve
   static assets with no separate web server.

The default command is Gunicorn. The worker and flower apps override it via
their `[processes]` command in `fly.worker.toml` / `fly.flower.toml`.

### Static files

WhiteNoise serves everything under `/static/` directly from the app process
(content-hashed + gzip/brotli). No CDN or Nginx required. Media uploads go to
Tigris via `django-storages`.

---

## 6. Health checks & scaling

- `qs-ai-api` exposes `GET /healthz/` (DB-free) for Fly.io health checks; it is
  exempt from the HTTPS redirect so the probe gets a 200 over plain HTTP.
- Scale the web tier: `fly scale count web=2 --app qs-ai-api`
- Scale workers for throughput: `fly scale count worker=2 --app qs-ai-worker`
  (each worker runs `CELERY_CONCURRENCY=2` prefetching one task at a time).

---

## 7. Local development

```bash
cp .env.example .env      # fill in values
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver            # uses qs_ai_saas.settings.development
```

Run the worker locally too, otherwise queued tasks never execute:

```bash
celery -A qs_ai_saas worker --loglevel=info
```

Run the tests:

```bash
DJANGO_SETTINGS_MODULE=qs_ai_saas.settings.test python manage.py test
```
