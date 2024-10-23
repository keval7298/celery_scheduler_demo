import os

from celery import Celery

celery_app = None

celery_app = Celery(
    "worker", backend="redis://localhost:6379/0", broker="redis://localhost:6379/0"
)

celery_app.conf.update(task_track_started=True)
