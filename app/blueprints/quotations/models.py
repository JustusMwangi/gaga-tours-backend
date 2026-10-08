"""Quotation and QuotationItem models."""

from app.core.models import AuditableModel
from app.extensions import db


class Quotation(AuditableModel):
    """A price quotation for a customer, optionally linked to a booking."""

    __tablename__ = "quotations"

    reference = db.Column(db.String(50), unique=True, nullable=False)
    booking_id = db.Column(
        db.Uuid,
        db.ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    subtotal = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    status = db.Column(db.String(20), default="draft", nullable=False)
    valid_until = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────
    booking = db.relationship("Booking", back_populates="quotation")
    customer = db.relationship("Customer", back_populates="quotations")
    tour = db.relationship("Tour")
    items = db.relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Quotation {self.reference}>"


class QuotationItem(AuditableModel):
    """A line item within a quotation."""

    __tablename__ = "quotation_items"

    quotation_id = db.Column(
        db.Uuid,
        db.ForeignKey("quotations.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = db.Column(db.String(500), nullable=False)
    item_type = db.Column(db.String(50), default="service", nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────
    quotation = db.relationship("Quotation", back_populates="items")

    def __repr__(self):
        return f"<QuotationItem {self.description[:30]}>"
