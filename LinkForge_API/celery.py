import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LinkForge_API.settings')

app = Celery('LinkForge_API')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
