"""Public-facing models (not behind authentication)."""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Uuid

from app.extensions import db


class Subscriber(db.Model):
    """Newsletter subscriber — not tenant-scoped, global."""

    __tablename__ = "subscribers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    unsubscribe_token = Column(
        String(64), unique=True, nullable=True, index=True,
        default=lambda: secrets.token_urlsafe(32),
    )
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
