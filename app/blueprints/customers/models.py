"""Customer model."""

from app.core.models import AuditableModel
from app.extensions import db


class Customer(AuditableModel):
    """A customer who books tours or makes inquiries."""

    __tablename__ = "customers"

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    nationality = db.Column(db.String(100), nullable=True)
    passport_number = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(50), default="direct", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────
    inquiries = db.relationship("Inquiry", back_populates="customer", lazy="dynamic")
    bookings = db.relationship("Booking", back_populates="customer", lazy="dynamic")
    quotations = db.relationship("Quotation", back_populates="customer", lazy="dynamic")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
