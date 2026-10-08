"""Notification models for tracking user notifications and preferences."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.core.models import BaseModel, _uuid_fk
from app.extensions import db


class NotificationType(str, Enum):
    """Types of notifications."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationChannel(str, Enum):
    """Channels for delivering notifications."""

    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class NotificationCategory(str, Enum):
    """Categories of notifications for preference management."""

    SYSTEM = "system"
    SECURITY = "security"
    TEAM = "team"
    ACTIVITY = "activity"


class Notification(BaseModel):
    """Notification record for a user."""

    __tablename__ = "notifications"

    # Recipient
    user_id = _uuid_fk("users.id")

    # Notification content — stored as plain strings (not SQLAlchemy Enum)
    # to stay portable across PostgreSQL and SQLite
    type = Column(String(20), nullable=False, default=NotificationType.INFO.value)
    category = Column(String(20), nullable=False, default=NotificationCategory.SYSTEM.value)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Optional action data (e.g., link to resource)
    data = Column(db.JSON, nullable=True)

    # Delivery tracking
    channel = Column(String(20), nullable=False, default=NotificationChannel.IN_APP.value)
    read_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "read_at"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Notification {self.title} for {self.user_id}>"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_as_read(self):
        if not self.read_at:
            self.read_at = datetime.now(timezone.utc)


class NotificationPreference(BaseModel):
    """User preferences for notification delivery per category."""

    __tablename__ = "notification_preferences"

    user_id = _uuid_fk("users.id")

    # Category this preference applies to — stored as plain string
    category = Column(String(20), nullable=False)

    # Channel preferences
    email_enabled = Column(Boolean, default=True, server_default="1", nullable=False)
    in_app_enabled = Column(Boolean, default=True, server_default="1", nullable=False)
    push_enabled = Column(Boolean, default=False, server_default="0", nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    # Unique constraint: one preference per user per category
    __table_args__ = (
        db.UniqueConstraint("user_id", "category", name="uq_notification_pref_user_category"),
    )

    def __repr__(self):
        return f"<NotificationPreference {self.category} for {self.user_id}>"


# Default preferences for new users
DEFAULT_NOTIFICATION_PREFERENCES = {
    NotificationCategory.SYSTEM: {"email": True, "in_app": True, "push": False},
    NotificationCategory.SECURITY: {"email": True, "in_app": True, "push": False},
    NotificationCategory.TEAM: {"email": True, "in_app": True, "push": False},
    NotificationCategory.ACTIVITY: {"email": False, "in_app": True, "push": False},
}
