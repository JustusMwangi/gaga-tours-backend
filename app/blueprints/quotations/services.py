"""QuotationService: CRUD operations for quotations."""

import logging
import math
from uuid import UUID

from flask import g

from app.blueprints.quotations.models import Quotation, QuotationItem
from app.blueprints.quotations.repositories import (
    QuotationItemRepository,
    QuotationRepository,
)
from app.core.exceptions import BadRequestError, NotFoundError
from app.extensions import db

logger = logging.getLogger(__name__)

VALID_STATUSES = {"draft", "sent", "approved", "rejected", "expired", "converted"}

# Allowed status transitions: current -> set of allowed next statuses
STATUS_TRANSITIONS = {
    "draft": {"sent", "rejected"},
    "sent": {"approved", "rejected"},
    "approved": {"converted", "expired", "rejected"},
    "rejected": set(),
    "expired": {"rejected"},
    "converted": set(),
}


class QuotationService:
    """Static methods for all quotation management operations."""

    # ── POST / ─────────────────────────────────────────────────────────

    @staticmethod
    def create_quotation(data: dict) -> dict:
        """Create a new quotation with an auto-generated reference."""
        repo = QuotationRepository(db.session)
        reference = repo.get_next_reference()

        quotation = Quotation(
            reference=reference,
            booking_id=data.get("booking_id"),
            customer_id=data.get("customer_id"),
            tour_id=data.get("tour_id"),
            subtotal=data.get("subtotal", 0),
            tax_amount=data.get("tax_amount", 0),
            discount_amount=data.get("discount_amount", 0),
            total_amount=data.get("total_amount", 0),
            currency=data.get("currency", "USD"),
            valid_until=data.get("valid_until"),
            notes=data.get("notes"),
            terms=data.get("terms"),
            status="draft",
            created_by=g.user.id if hasattr(g, "user") and g.user else None,
        )

        repo.create(quotation)

        # Create items if provided
        items_data = data.get("items", [])
        if items_data:
            item_repo = QuotationItemRepository(db.session)
            for idx, item_data in enumerate(items_data):
                item = QuotationItem(
                    quotation_id=quotation.id,
                    description=item_data["description"],
                    item_type=item_data.get("item_type", "service"),
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data["unit_price"],
                    total_price=item_data["total_price"],
                    sort_order=item_data.get("sort_order", idx),
                    created_by=g.user.id if hasattr(g, "user") and g.user else None,
                )
                item_repo.create(item)

        db.session.commit()
        return quotation.to_dict()

    # ── GET / ──────────────────────────────────────────────────────────

    @staticmethod
    def list_quotations(
        page: int = 1,
        per_page: int = 20,
        search: str = None,
        status: str = None,
        customer_id=None,
        booking_id=None,
    ) -> dict:
        """List paginated quotations."""
        repo = QuotationRepository(db.session)

        items, total = repo.list_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            customer_id=customer_id,
            booking_id=booking_id,
        )

        return {
            "quotations": [q.to_dict() for q in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    # ── GET /<id> ──────────────────────────────────────────────────────

    @staticmethod
    def get_quotation(quotation_id: UUID) -> dict:
        """Return quotation detail with nested related info."""
        repo = QuotationRepository(db.session)
        quotation = repo.find_by_id(quotation_id)
        if not quotation or quotation.deleted_at:
            raise NotFoundError("Quotation not found")

        result = quotation.to_dict()

        # Nested customer info
        if quotation.customer:
            result["customer"] = {
                "id": quotation.customer.id,
                "first_name": quotation.customer.first_name,
                "last_name": quotation.customer.last_name,
            }

        # Nested booking info
        if quotation.booking:
            result["booking"] = {
                "id": quotation.booking.id,
                "reference": quotation.booking.reference,
            }

        # Nested tour info
        if quotation.tour:
            result["tour"] = {
                "id": quotation.tour.id,
                "title": quotation.tour.title,
            }

        # Nested items
        item_repo = QuotationItemRepository(db.session)
        items = item_repo.list_by_quotation(quotation.id)
        result["items"] = [i.to_dict() for i in items]

        return result

    # ── PUT /<id> ──────────────────────────────────────────────────────

    @staticmethod
    def update_quotation(quotation_id: UUID, data: dict) -> dict:
        """Update a quotation's fields and optionally replace items."""
        repo = QuotationRepository(db.session)
        quotation = repo.find_by_id(quotation_id)
        if not quotation or quotation.deleted_at:
            raise NotFoundError("Quotation not found")

        updatable = [
            "booking_id", "customer_id", "tour_id",
            "subtotal", "tax_amount", "discount_amount", "total_amount",
            "currency", "valid_until", "notes", "terms",
        ]

        for field in updatable:
            if field in data:
                setattr(quotation, field, data[field])

        quotation.updated_by = g.user.id if hasattr(g, "user") and g.user else None

        # Replace items if provided
        if "items" in data:
            item_repo = QuotationItemRepository(db.session)
            item_repo.delete_all_for_quotation(quotation.id)

            for idx, item_data in enumerate(data["items"]):
                item = QuotationItem(
                    quotation_id=quotation.id,
                    description=item_data["description"],
                    item_type=item_data.get("item_type", "service"),
                    quantity=item_data.get("quantity", 1),
                    unit_price=item_data["unit_price"],
                    total_price=item_data["total_price"],
                    sort_order=item_data.get("sort_order", idx),
                    created_by=g.user.id if hasattr(g, "user") and g.user else None,
                )
                item_repo.create(item)

        db.session.commit()
        return QuotationService.get_quotation(quotation_id)

    # ── PUT /<id>/status ───────────────────────────────────────────────

    @staticmethod
    def update_status(quotation_id: UUID, status: str) -> dict:
        """Update a quotation's status with transition validation."""
        if status not in VALID_STATUSES:
            raise BadRequestError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        repo = QuotationRepository(db.session)
        quotation = repo.find_by_id(quotation_id)
        if not quotation or quotation.deleted_at:
            raise NotFoundError("Quotation not found")

        current = quotation.status
        allowed = STATUS_TRANSITIONS.get(current, set())

        if status not in allowed:
            raise BadRequestError(
                f"Cannot transition from '{current}' to '{status}'. "
                f"Allowed: {', '.join(sorted(allowed)) if allowed else 'none'}"
            )

        quotation.status = status
        quotation.updated_by = g.user.id if hasattr(g, "user") and g.user else None

        if status == "sent":
            logger.info("Quotation %s sent — email notification placeholder", quotation.reference)

        db.session.commit()
        return quotation.to_dict()

    # ── POST /<id>/convert-to-invoice ──────────────────────────────────

    @staticmethod
    def convert_to_invoice(quotation_id: UUID) -> dict:
        """Convert an approved quotation to an invoice."""
        repo = QuotationRepository(db.session)
        quotation = repo.find_by_id(quotation_id)
        if not quotation or quotation.deleted_at:
            raise NotFoundError("Quotation not found")

        if quotation.status != "approved":
            raise BadRequestError(
                "Only approved quotations can be converted to invoices"
            )

        from app.blueprints.invoices.services import InvoiceService

        # Build invoice data from quotation
        item_repo = QuotationItemRepository(db.session)
        items = item_repo.list_by_quotation(quotation.id)

        invoice_data = {
            "booking_id": quotation.booking_id,
            "customer_id": quotation.customer_id,
            "subtotal": float(quotation.subtotal) if quotation.subtotal else 0,
            "tax_amount": float(quotation.tax_amount) if quotation.tax_amount else 0,
            "discount_amount": float(quotation.discount_amount) if quotation.discount_amount else 0,
            "total_amount": float(quotation.total_amount) if quotation.total_amount else 0,
            "currency": quotation.currency,
            "notes": quotation.notes,
            "items": [
                {
                    "description": item.description,
                    "item_type": item.item_type,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price),
                    "sort_order": item.sort_order,
                }
                for item in items
            ],
        }

        invoice_result = InvoiceService.create_invoice(invoice_data)

        # Mark quotation as converted
        quotation.status = "converted"
        quotation.updated_by = g.user.id if hasattr(g, "user") and g.user else None
        db.session.commit()

        return {
            "quotation": quotation.to_dict(),
            "invoice": invoice_result,
        }
