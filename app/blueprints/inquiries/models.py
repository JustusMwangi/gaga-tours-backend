"""Inquiry model definition."""

import random
import string

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)

from app.core.models import AuditableModel
from app.extensions import db


def _generate_reference():
    """Generate a random INQ-XXXX reference as a fallback."""
    suffix = "".join(random.choices(string.digits, k=4))
    return f"INQ-{suffix}"


class Inquiry(AuditableModel):
    """A tour inquiry submitted by a prospective customer."""

    __tablename__ = "inquiries"

    reference = Column(String(50), unique=True, nullable=False, default=_generate_reference)
    customer_id = Column(
        Uuid,
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    tour_id = Column(
        Uuid,
        ForeignKey("tours.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    message = Column(Text, nullable=True)
    travel_date = Column(Date, nullable=True)
    flexible_dates = Column(Boolean, default=False, nullable=False)
    group_size_adults = Column(Integer, default=1, nullable=False)
    group_size_children = Column(Integer, default=0, nullable=False)
    budget = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    status = Column(String(20), default="new", nullable=False)  # new/contacted/quoted/converted/closed
    source = Column(String(50), default="website", nullable=False)
    assigned_to = Column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    internal_notes = Column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    customer = db.relationship("Customer", back_populates="inquiries")
    tour = db.relationship("Tour")
    assignee = db.relationship("User", foreign_keys=[assigned_to])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<Inquiry {self.reference}>"
