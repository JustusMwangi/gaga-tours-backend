"""Notification cleanup tasks."""

import logging
from datetime import datetime, timedelta, timezone

from app.core.celery import celery_app
from app.extensions import db

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_old_notifications():
    """Delete read notifications older than 90 days.

    Runs daily at 5:00 AM.
    """
    from app.blueprints.notifications.models import Notification

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    deleted = (
        db.session.query(Notification)
        .filter(
            Notification.read_at.isnot(None),
            Notification.created_at < cutoff,
        )
        .delete(synchronize_session="fetch")
    )
    db.session.commit()

    logger.info("cleanup_old_notifications: deleted %d old notifications", deleted)
    return f"deleted={deleted}"
