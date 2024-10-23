from flask import Flask, request
from app.logic import schedule as logic

# Initialize Flask app
flask_app = Flask(__name__)

# Configure the database
flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/scheduler_demo'
flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


@flask_app.route("/", methods=["GET"])
def get_event_logs():
    """Returns all the event logs from the db"""
    return {"message": "Hello World1"}


@flask_app.route("/task", methods=["GET"])
def get_all_tasks():
    """Returns all the event logs from the db"""
    return logic.get_all_active_task_schedules()


@flask_app.route("/task", methods=["POST"])
def create_task(*args, **kwargs):
    """Schedule a report generation task"""
    task = request.json.get("task")
    cron = request.json.get("cron")
    name = request.json.get("name")
    # logic.validate_task_and_cron(task=task, cron=cron)
    return logic.create_task_schedule(name=name, cron=cron, task=task)


@flask_app.route("/task/{id}", methods=["PUT"])
def update_task(id: str, task: str, name: str, cron: str):
    """Update a scheduled task"""
    logic.validate_task_and_cron(task=task, cron=cron)
    return logic.update_task_schedule(id=id, cron=cron, name=name, task=task)


@flask_app.route("/task/{id}", methods=["DELETE"])
def delete_task(id: str):
    """Update a scheduled task"""
    return logic.delete_task_schedule(id=id)


@flask_app.route("/task/{task_id}/history", methods=["GET"])
def get_task_history(task_id: int):
    """Schedule a report generation task"""
    return logic.get_task_run_record(task_id)


@flask_app.route("/celery-task", methods=["GET"])
def fetch_all_celery_tasks():
    from app.tasks.celery_app import celery_app

    tasks = list(sorted(iter(celery_app.tasks)))
    return [task for task in tasks if not task.startswith("celery")]

if __name__ == '__main__':
    flask_app.run(debug=True)
