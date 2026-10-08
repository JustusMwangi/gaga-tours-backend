"""Booking model."""

from app.core.models import AuditableModel
from app.extensions import db


class Booking(AuditableModel):
    """A customer booking for a tour."""

    __tablename__ = "bookings"

    reference = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(
        db.Uuid,
        db.ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    tour_id = db.Column(
        db.Uuid,
        db.ForeignKey("tours.id", ondelete="SET NULL"),
        nullable=True,
    )
    tour_date_id = db.Column(
        db.Uuid,
        db.ForeignKey("tour_dates.id", ondelete="SET NULL"),
        nullable=True,
    )
    inquiry_id = db.Column(
        db.Uuid,
        db.ForeignKey("inquiries.id", ondelete="SET NULL"),
        nullable=True,
    )
    number_of_adults = db.Column(db.Integer, default=1, nullable=False)
    number_of_children = db.Column(db.Integer, default=0, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    special_requests = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    booking_date = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    customer = db.relationship("Customer", back_populates="bookings")
    tour = db.relationship("Tour")
    tour_date = db.relationship("TourDate")
    inquiry = db.relationship("Inquiry")
    invoice = db.relationship(
        "Invoice", back_populates="booking", uselist=False,
    )
    quotation = db.relationship(
        "Quotation", back_populates="booking", uselist=False,
    )

    def __repr__(self):
        return f"<Booking {self.reference}>"
