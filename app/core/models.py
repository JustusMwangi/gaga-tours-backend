"""BaseModel, AuditableModel, and TimestampMixin definitions."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import declared_attr

from app.extensions import db


def _uuid_column():
    """UUID primary-key column portable across PostgreSQL and SQLite."""
    return Column(Uuid, primary_key=True, default=uuid.uuid4)


def _uuid_fk(target, nullable=False):
    """UUID foreign-key column portable across PostgreSQL and SQLite."""
    return Column(
        Uuid,
        ForeignKey(target, ondelete="CASCADE"),
        nullable=nullable,
    )


class TimestampMixin:
    """Adds created_at / updated_at to any model.

    Kept separate from BaseModel so junction tables (composite PK, no
    surrogate id) can reuse timestamps without inheriting db.Model.
    """

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BaseModel(TimestampMixin, db.Model):
    """Abstract base for all primary entities (UUID pk + timestamps)."""

    __abstract__ = True

    id = _uuid_column()

    def to_dict(self):
        """Convert model instance to a dictionary of column values."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class AuditableModel(BaseModel):
    """Abstract base for models needing audit fields and soft-delete."""

    __abstract__ = True

    @declared_attr
    def created_by(cls):
        return Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @declared_attr
    def updated_by(cls):
        return Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        self.deleted_at = datetime.now(timezone.utc)
