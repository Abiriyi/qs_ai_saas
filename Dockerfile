# syntax=docker/dockerfile:1

#############################################################################
# QS AI SaaS — production image
#
# Multi-stage build:
#   builder  -> compiles wheels / installs Python deps
#   runtime  -> slim image with only what is needed to serve the app
#
# The image is shared by three Fly.io apps (web / celery worker / flower);
# the entrypoint command is chosen per-app via fly.toml.
#############################################################################

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Build + runtime system libraries required by the scientific/PDF stack:
#   libpq5        -> psycopg (PostgreSQL)
#   tesseract-ocr -> pytesseract (OCR fallback)
#   libmagic1     -> python-magic
#   poppler-utils -> pdfplumber / PyMuPDF helpers
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libpq5 \
        tesseract-ocr \
        libmagic1 \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


#############################################################################

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=qs_ai_saas.settings.production \
    PORT=8000

# Runtime-only system libraries (no compilers).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        tesseract-ocr \
        libmagic1 \
        poppler-utils \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the app.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels \
        $(ls /wheels/*.whl | xargs -n1 basename) \
    && rm -rf /wheels

# Copy the application source.
COPY --chown=appuser:appuser . .

# Collect static files at build time so WhiteNoise can serve them without a
# separate web server. We pass a throwaway secret because production.py only
# needs a *set* value at import time (it is never used to sign anything here).
RUN DJANGO_SECRET_KEY=build-time-not-used python manage.py collectstatic --noinput

USER appuser

EXPOSE 8000

# Default command (Gunicorn web server). The worker and flower apps override
# this via their process command in fly.toml.
CMD exec gunicorn qs_ai_saas.wsgi:application \
        --bind 0.0.0.0:${PORT} \
        --workers ${WEB_CONCURRENCY:-3} \
        --threads 4 \
        --timeout 120 \
        --access-file - \
        --error-file -
