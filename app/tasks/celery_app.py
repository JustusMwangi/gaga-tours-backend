"""Worker entrypoint: ``celery -A app.tasks.celery_app:celery_app worker``.

Re-exports the configured Celery instance so the worker process can
discover it without importing the full Flask app factory directly.
"""

from app.core.celery import celery_app  # noqa: F401
