"""Celery configuration for background task processing.

Usage::

    # In your code
    from app.core.celery import celery_app

    @celery_app.task
    def my_task():
        ...

Worker::

    celery -A celery_worker:celery_app worker --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab
from flask import Flask


def make_celery(app: Flask = None) -> Celery:
    """Create and configure a Celery instance.

    If *app* is provided, Celery is configured from Flask's config and
    tasks run inside the Flask application context.
    """
    celery = Celery(
        "app",
        broker=app.config.get("CELERY_BROKER_URL") if app else None,
        backend=app.config.get("CELERY_RESULT_BACKEND") if app else None,
    )

    if app:
        celery.flask_app = app

        celery.conf.update(
            broker_url=app.config.get("CELERY_BROKER_URL"),
            result_backend=app.config.get("CELERY_RESULT_BACKEND"),
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,  # 30 minutes
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            # Beat schedule — add periodic tasks here
            beat_schedule={
                "cleanup-expired-tokens": {
                    "task": "app.core.tasks.cleanup_expired_tokens",
                    "schedule": 3600.0,  # every hour
                },
                "cleanup-old-notifications": {
                    "task": "app.tasks.usage_tasks.cleanup_old_notifications",
                    "schedule": crontab(hour=5, minute=0),
                },
            },
        )

        class ContextTask(celery.Task):
            """Ensure every task runs within the Flask application context."""
            def __call__(self, *args, **kwargs):
                with celery.flask_app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Module-level instance — configured when init_celery() is called.
celery_app = Celery("app")


def init_celery(app: Flask) -> Celery:
    """Initialise Celery with Flask app.  Call from create_app()."""
    global celery_app
    celery_app = make_celery(app)
    return celery_app
