# Active Context

## Project Environment

- Working directory (project root): `/home/ubuntu/projects/qs_ai_saas`
- Local virtual environment: `.venv` (target: `ubuntu@ubuntu-vm:~/projects/qs_ai_saas`)
- Django settings module: `qs_ai_saas.settings.development`


## Technology Stack

- **Framework:** Django 5.2.11
- **Language:** Python (managed by `.venv`; `python` resolves to `.venv/bin/python`)
- **Web server:** Gunicorn + WhiteNoise
- **Async/task:** Celery 5.6.3 (broker/result backend: Redis) + Flower 2.0.1
- **Cache:** Redis (`redis://127.0.0.1:6379/1`) via `django-redis`
- **API framework:** Django REST Framework 3.17.1
- **Object storage (prod):** Tigris (S3-compatible) via `django-storages`
- **AI/ML:** OpenAI client + Groq (OpenAI-compatible); `AI_PROVIDER` toggles `openai` vs `groq`
- **Testing:** `pytest` (v9.0.2) + Django's `manage.py test`
- **Database:** PostgreSQL

## Apps

### Django / Third-Party

- `django.contrib.admin`, `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles`
- `django_redis`, `storages`, `rest_framework`

### Local Apps (`INSTALLED_APPS`)

- `users` — custom user model (`AUTH_USER_MODEL = 'users.User'`); includes `TenantMiddleware`
- `projects`
- `core` — shared services, pagination, throttling, sentry init
- `documents`
- `boq`
- `pricing`
- `tribunal`
- `audit`

## Database Engine

- **ENGINE:** `django.db.backends.postgresql`
- **NAME:** `qs_ai_db` (env: `POSTGRES_DB`)
- **USER:** `qs_ai_user` (env: `POSTGRES_USER`)
- **PASSWORD:** from `POSTGRES_PASSWORD`
- **HOST:** `localhost` (env: `POSTGRES_HOST`)
- **PORT:** `5432` (env: `POSTGRES_PORT`)

## Key Environment Variables (`.env` at project root)

- `DJANGO_SECRET_KEY` (required)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `REDIS_URL` (defaults to `redis://127.0.0.1:6379/1`)
- `DJANGO_ALLOWED_HOSTS`
- `TIGRIS_ACCESS_KEY`, `TIGRIS_SECRET_KEY`, `TIGRIS_BUCKET`
- `OPENAI_API_KEY`, `OPENAI_MODEL` (default: `gpt-4.1`)
- `AI_PROVIDER` (default: `openai`), `GROQ_API_KEY`, `GROQ_BASE_URL` (default: `https://api.groq.com/openai/v1`), `GROQ_MODEL` (default: `openai/gpt-oss-120b`)

## Notes / Pitfalls

- `.gitignore` already ignores `.venv/`, `__pycache__/`, `*.sqlite3`, `.env`, `staticfiles/`, `media/`, `*.sql`, etc.
- `test.sqlite3` and `qs_ai_db_local.sql` exist but are **not** part of the real DB config; the app targets PostgreSQL.
- Production overrides `STORAGES["default"]` to S3 (Tigris); `base.py` uses local filesystem storage for dev/tests.
- Business logic lives in `services.py` (not views/serializers); use `select_related`/`prefetch_related` to avoid N+1.
