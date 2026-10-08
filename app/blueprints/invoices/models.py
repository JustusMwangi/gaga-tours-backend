"""Invoice and Payment models."""

from app.core.models import AuditableModel
from app.extensions import db


class Invoice(AuditableModel):
    """An invoice tied to a booking or quotation."""

    __tablename__ = "invoices"

    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    booking_id = db.Column(
        db.Uuid,
        db.ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    quotation_id = db.Column(
        db.Uuid,
        db.ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id = db.Column(
        db.Uuid,
        db.ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    subtotal = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    currency = db.Column(db.String(3), default="USD", nullable=False)
    status = db.Column(db.String(20), default="draft", nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)
    issued_date = db.Column(db.Date, nullable=True)
    paid_date = db.Column(db.Date, nullable=True)

    # -- Relationships -------------------------------------------------------
    booking = db.relationship("Booking", back_populates="invoice")
    quotation = db.relationship("Quotation")
    customer = db.relationship("Customer")
    payments = db.relationship(
        "Payment",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Invoice {self.invoice_number}>"


class Payment(AuditableModel):
    """A payment recorded against an invoice."""

    __tablename__ = "payments"

    invoice_id = db.Column(
        db.Uuid,
        db.ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(50), default="bank_transfer", nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    reference_number = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)
    notes = db.Column(db.Text, nullable=True)

    # -- Relationships -------------------------------------------------------
    invoice = db.relationship("Invoice", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id}>"
