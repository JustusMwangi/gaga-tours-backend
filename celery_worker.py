"""Celery worker entry point.

Usage::

    celery -A celery_worker:celery_app worker --loglevel=info
    celery -A celery_worker:celery_app beat --loglevel=info
"""

import os

from app import create_app

os.environ.setdefault("FLASK_ENV", "development")

flask_app = create_app(os.environ.get("FLASK_ENV", "development"))

from app.core.celery import celery_app  # noqa: E402
from app.core import tasks  # noqa: E402, F401
from app.blueprints.consent import tasks as consent_tasks  # noqa: E402, F401

celery_app.flask_app = flask_app
