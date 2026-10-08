"""Immutable GDPR consent records.

Each row is an append-only log entry recording that a data subject
granted or withdrew consent for a specific processing purpose.
These records must never be updated or deleted.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Uuid

from app.extensions import db


class ConsentRecord(db.Model):
    __tablename__ = "consent_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    purpose = Column(String(50), nullable=False, index=True)
    consent_given = Column(Boolean, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    source = Column(String(100), nullable=False, default="website")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
