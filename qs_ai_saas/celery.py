import os

from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "qs_ai_saas.settings.production"
)

app = Celery("qs_ai_saas")

app.config_from_object(
    "django.conf:settings",
    namespace="CELERY",
)

app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args, **kwargs):
    pass