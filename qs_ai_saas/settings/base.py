from pathlib import Path

import os


# --------------------------------------------------
# BASE DIRECTORY
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# --------------------------------------------------
# SECURITY
# --------------------------------------------------

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key"
)

DEBUG = False

ALLOWED_HOSTS = []


# --------------------------------------------------
# APPLICATIONS
# --------------------------------------------------

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'django_redis',
]

LOCAL_APPS = [
    'users',
    'projects',
    'core',
    'boq',
    'pricing',
    'documents',
]

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + LOCAL_APPS
)


# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # tenant middleware
    'users.middleware.TenantMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# --------------------------------------------------
# URLS / WSGI
# --------------------------------------------------

ROOT_URLCONF = 'qs_ai_saas.urls'

WSGI_APPLICATION = 'qs_ai_saas.wsgi.application'


# --------------------------------------------------
# TEMPLATES
# --------------------------------------------------

TEMPLATES = [
    {
        'BACKEND': (
            'django.template.backends.django.'
            'DjangoTemplates'
        ),
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                (
                    'django.template.context_processors.debug'
                ),
                (
                    'django.template.context_processors.request'
                ),
                (
                    'django.contrib.auth.context_processors.auth'
                ),
                (
                    'django.contrib.messages.'
                    'context_processors.messages'
                ),
            ],
        },
    },
]


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": (
            "django.db.backends.postgresql"
        ),
        "NAME": os.getenv(
            "POSTGRES_DB",
            "qs_ai_db"
        ),
        "USER": os.getenv(
            "POSTGRES_USER",
            "qs_ai_user"
        ),
        "PASSWORD": os.getenv(
            "POSTGRES_PASSWORD",
            "qs_pw%#user"
        ),
        "HOST": os.getenv(
            "POSTGRES_HOST",
            "localhost"
        ),
        "PORT": os.getenv(
            "POSTGRES_PORT",
            "5432"
        ),
    }
}


# --------------------------------------------------
# PASSWORD VALIDATORS
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator'
        ),
    },
]


# --------------------------------------------------
# INTERNATIONALIZATION
# --------------------------------------------------

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------

STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# --------------------------------------------------
# DEFAULT PK
# --------------------------------------------------

DEFAULT_AUTO_FIELD = (
    'django.db.models.BigAutoField'
)


# --------------------------------------------------
# AUTH USER MODEL
# --------------------------------------------------

AUTH_USER_MODEL = "users.User"


# --------------------------------------------------
# REDIS CACHE
# --------------------------------------------------

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/1"
)

CACHES = {
    "default": {
        "BACKEND": (
            "django_redis.cache.RedisCache"
        ),
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": (
                "django_redis.client.DefaultClient"
            ),
        }
    }
}


# --------------------------------------------------
# CELERY
# --------------------------------------------------

CELERY_BROKER_URL = REDIS_URL

CELERY_RESULT_BACKEND = REDIS_URL

CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = "UTC"

CELERY_TASK_TRACK_STARTED = True

CELERY_TASK_TIME_LIMIT = 60 * 30

CELERY_TASK_SOFT_TIME_LIMIT = 60 * 25

CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_TASK_ACKS_LATE = True

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
}