
from app.logic import schedule as logic

from .celery_app import celery_app


@celery_app.task(bind=True)
@logic.with_task_logging()
def generate_pipeline_report(self, *args, **kwargs) -> str:
    print("Hello from celery")



@celery_app.task(bind=True)
@logic.with_task_logging()
def new_task(self, *args, **kwargs) -> str:
    print("New Task")


@celery_app.task(bind=True)
@logic.with_task_logging()
def third_task(self, *args, **kwargs) -> str:
    print("Third Task")
