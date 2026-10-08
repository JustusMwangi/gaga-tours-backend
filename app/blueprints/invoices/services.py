"""InvoiceService & PaymentService: business logic for invoices and payments."""

import math
from datetime import date
from decimal import Decimal
from uuid import UUID

from flask import g

from app.blueprints.invoices.models import Invoice, Payment
from app.blueprints.invoices.repositories import InvoiceRepository, PaymentRepository
from app.core.exceptions import BadRequestError, NotFoundError
from app.extensions import db

VALID_STATUSES = {"draft", "sent", "paid", "partially_paid", "overdue", "cancelled"}

# Allowed status transitions: current_status -> set of allowed next statuses
STATUS_TRANSITIONS = {
    "draft": {"sent"},
    "sent": {"paid", "partially_paid", "overdue", "cancelled"},
    "partially_paid": {"paid", "overdue", "cancelled"},
    "overdue": {"paid", "cancelled"},
}


class InvoiceService:
    """Static methods for invoice management."""

    # -- POST / --------------------------------------------------------------

    @staticmethod
    def create_invoice(data: dict) -> dict:
        """Create a new invoice with an auto-generated invoice number."""
        repo = InvoiceRepository(db.session)
        invoice_number = repo.get_next_number()

        invoice = Invoice(
            invoice_number=invoice_number,
            booking_id=data.get("booking_id"),
            quotation_id=data.get("quotation_id"),
            customer_id=data.get("customer_id"),
            subtotal=data.get("subtotal", 0),
            tax_amount=data.get("tax_amount", 0),
            discount_amount=data.get("discount_amount", 0),
            total_amount=data.get("total_amount", 0),
            currency=data.get("currency", "USD"),
            due_date=data.get("due_date"),
            notes=data.get("notes"),
            terms=data.get("terms"),
            status="draft",
            created_by=g.user.id if hasattr(g, "user") and g.user else None,
        )

        repo.create(invoice)
        db.session.commit()
        return invoice.to_dict()

    # -- GET / ---------------------------------------------------------------

    @staticmethod
    def list_invoices(
        page: int = 1,
        per_page: int = 20,
        search: str = None,
        status: str = None,
        customer_id=None,
    ) -> dict:
        """List paginated invoices."""
        repo = InvoiceRepository(db.session)

        items, total = repo.list_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            customer_id=customer_id,
        )

        return {
            "invoices": [i.to_dict() for i in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    # -- GET /<id> -----------------------------------------------------------

    @staticmethod
    def get_invoice(invoice_id: UUID) -> dict:
        """Return invoice detail with nested customer, booking, and payments."""
        repo = InvoiceRepository(db.session)
        invoice = repo.find_by_id(invoice_id)
        if not invoice or invoice.deleted_at:
            raise NotFoundError("Invoice not found")

        result = invoice.to_dict()

        # Nested customer info
        if invoice.customer:
            result["customer"] = {
                "id": invoice.customer.id,
                "first_name": invoice.customer.first_name,
                "last_name": invoice.customer.last_name,
            }

        # Nested booking info
        if invoice.booking:
            result["booking"] = {
                "id": invoice.booking.id,
                "reference": invoice.booking.reference,
            }

        # Payments summary
        payment_repo = PaymentRepository(db.session)
        payments = payment_repo.list_by_invoice(invoice_id)
        result["payments"] = [p.to_dict() for p in payments]

        return result

    # -- PUT /<id> -----------------------------------------------------------

    @staticmethod
    def update_invoice(invoice_id: UUID, data: dict) -> dict:
        """Update an invoice's editable fields."""
        repo = InvoiceRepository(db.session)
        invoice = repo.find_by_id(invoice_id)
        if not invoice or invoice.deleted_at:
            raise NotFoundError("Invoice not found")

        updatable = [
            "booking_id", "quotation_id", "customer_id",
            "subtotal", "tax_amount", "discount_amount", "total_amount",
            "currency", "due_date", "notes", "terms",
        ]

        for field in updatable:
            if field in data:
                setattr(invoice, field, data[field])

        invoice.updated_by = g.user.id if hasattr(g, "user") and g.user else None
        db.session.commit()
        return invoice.to_dict()

    # -- PUT /<id>/status ----------------------------------------------------

    @staticmethod
    def update_status(invoice_id: UUID, status: str) -> dict:
        """Update an invoice's status with transition validation."""
        if status not in VALID_STATUSES:
            raise BadRequestError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        repo = InvoiceRepository(db.session)
        invoice = repo.find_by_id(invoice_id)
        if not invoice or invoice.deleted_at:
            raise NotFoundError("Invoice not found")

        allowed = STATUS_TRANSITIONS.get(invoice.status, set())
        if status not in allowed:
            raise BadRequestError(
                f"Cannot transition from '{invoice.status}' to '{status}'. "
                f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none'}"
            )

        # Side effects
        if status == "sent" and invoice.issued_date is None:
            invoice.issued_date = date.today()
        if status == "paid":
            invoice.paid_date = date.today()

        invoice.status = status
        invoice.updated_by = g.user.id if hasattr(g, "user") and g.user else None
        db.session.commit()
        return invoice.to_dict()


class PaymentService:
    """Static methods for payment management."""

    # -- POST /<invoice_id>/payments/ ----------------------------------------

    @staticmethod
    def record_payment(invoice_id: UUID, data: dict) -> dict:
        """Record a payment against an invoice and update invoice status."""
        inv_repo = InvoiceRepository(db.session)
        invoice = inv_repo.find_by_id(invoice_id)
        if not invoice or invoice.deleted_at:
            raise NotFoundError("Invoice not found")

        pay_repo = PaymentRepository(db.session)

        payment = Payment(
            invoice_id=invoice_id,
            amount=data["amount"],
            payment_method=data.get("payment_method", "bank_transfer"),
            payment_date=data["payment_date"],
            reference_number=data.get("reference_number"),
            notes=data.get("notes"),
            status="pending",
            created_by=g.user.id if hasattr(g, "user") and g.user else None,
        )

        pay_repo.create(payment)

        # Recalculate invoice paid status
        _recalculate_invoice_status(invoice)

        db.session.commit()
        return payment.to_dict()

    # -- PUT /payments/<id>/confirm ------------------------------------------

    @staticmethod
    def confirm_payment(payment_id: UUID) -> dict:
        """Confirm a payment and recalculate invoice status."""
        pay_repo = PaymentRepository(db.session)
        payment = pay_repo.find_by_id(payment_id)
        if not payment or payment.deleted_at:
            raise NotFoundError("Payment not found")

        payment.status = "confirmed"
        payment.updated_by = g.user.id if hasattr(g, "user") and g.user else None

        # Recalculate parent invoice status
        inv_repo = InvoiceRepository(db.session)
        invoice = inv_repo.find_by_id(payment.invoice_id)
        if invoice and not invoice.deleted_at:
            _recalculate_invoice_status(invoice)

        db.session.commit()
        return payment.to_dict()

    # -- GET /<invoice_id>/payments/ -----------------------------------------

    @staticmethod
    def list_payments(invoice_id: UUID) -> list:
        """List all payments for an invoice."""
        inv_repo = InvoiceRepository(db.session)
        invoice = inv_repo.find_by_id(invoice_id)
        if not invoice or invoice.deleted_at:
            raise NotFoundError("Invoice not found")

        pay_repo = PaymentRepository(db.session)
        payments = pay_repo.list_by_invoice(invoice_id)
        return [p.to_dict() for p in payments]


def _recalculate_invoice_status(invoice):
    """Set invoice to paid or partially_paid based on confirmed payments."""
    confirmed = (
        db.session.query(Payment)
        .filter(
            Payment.invoice_id == invoice.id,
            Payment.status == "confirmed",
            Payment.deleted_at.is_(None),
        )
        .all()
    )
    total_paid = sum(p.amount for p in confirmed) if confirmed else Decimal("0")

    if invoice.total_amount and total_paid >= invoice.total_amount:
        invoice.status = "paid"
        invoice.paid_date = date.today()
    elif total_paid > 0 and invoice.status not in ("paid", "cancelled"):
        invoice.status = "partially_paid"
