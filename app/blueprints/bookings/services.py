"""BookingService: CRUD operations for bookings."""

import math
from decimal import Decimal
from uuid import UUID

from flask import g

from app.blueprints.bookings.models import Booking
from app.blueprints.bookings.repositories import BookingRepository
from app.core.exceptions import BadRequestError, NotFoundError
from app.extensions import db

VALID_STATUSES = {"pending", "confirmed", "in_progress", "completed", "cancelled"}


class BookingService:
    """Static methods for all booking management operations."""

    # ── POST / ─────────────────────────────────────────────────────────

    @staticmethod
    def create_booking(data: dict) -> dict:
        """Create a new booking with an auto-generated reference."""
        repo = BookingRepository(db.session)
        reference = repo.get_next_reference()

        booking = Booking(
            reference=reference,
            customer_id=data.get("customer_id"),
            tour_id=data.get("tour_id"),
            tour_date_id=data.get("tour_date_id"),
            number_of_adults=data.get("number_of_adults", 1),
            number_of_children=data.get("number_of_children", 0),
            total_amount=data.get("total_amount"),
            currency=data.get("currency", "USD"),
            special_requests=data.get("special_requests"),
            internal_notes=data.get("internal_notes"),
            booking_date=data.get("booking_date"),
            status="pending",
            created_by=g.user.id if hasattr(g, "user") and g.user else None,
        )

        repo.create(booking)
        db.session.commit()
        return booking.to_dict()

    # ── GET / ──────────────────────────────────────────────────────────

    @staticmethod
    def list_bookings(
        page: int = 1,
        per_page: int = 20,
        search: str = None,
        status: str = None,
        customer_id=None,
        tour_id=None,
    ) -> dict:
        """List paginated bookings."""
        repo = BookingRepository(db.session)

        items, total = repo.list_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            customer_id=customer_id,
            tour_id=tour_id,
        )

        return {
            "bookings": [b.to_dict() for b in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    # ── GET /<id> ──────────────────────────────────────────────────────

    @staticmethod
    def get_booking(booking_id: UUID) -> dict:
        """Return booking detail with nested related info."""
        repo = BookingRepository(db.session)
        booking = repo.find_by_id(booking_id)
        if not booking or booking.deleted_at:
            raise NotFoundError("Booking not found")

        result = booking.to_dict()

        # Nested customer info
        if booking.customer:
            result["customer"] = {
                "id": booking.customer.id,
                "first_name": booking.customer.first_name,
                "last_name": booking.customer.last_name,
            }

        # Nested tour info
        if booking.tour:
            result["tour"] = {
                "id": booking.tour.id,
                "title": booking.tour.title,
            }

        # Nested invoice info
        if booking.invoice:
            result["invoice"] = {
                "id": booking.invoice.id,
                "invoice_number": getattr(booking.invoice, "invoice_number", None),
            }

        # Nested quotation info
        if booking.quotation:
            result["quotation"] = {
                "id": booking.quotation.id,
                "reference": getattr(booking.quotation, "reference", None),
            }

        return result

    # ── PUT /<id> ──────────────────────────────────────────────────────

    @staticmethod
    def update_booking(booking_id: UUID, data: dict) -> dict:
        """Update a booking's fields."""
        repo = BookingRepository(db.session)
        booking = repo.find_by_id(booking_id)
        if not booking or booking.deleted_at:
            raise NotFoundError("Booking not found")

        updatable = [
            "customer_id", "tour_id", "tour_date_id", "inquiry_id",
            "number_of_adults", "number_of_children", "total_amount",
            "currency", "special_requests", "internal_notes", "booking_date",
        ]

        for field in updatable:
            if field in data:
                setattr(booking, field, data[field])

        booking.updated_by = g.user.id if hasattr(g, "user") and g.user else None
        db.session.commit()
        return booking.to_dict()

    # ── PUT /<id>/status ───────────────────────────────────────────────

    @staticmethod
    def update_status(booking_id: UUID, status: str) -> dict:
        """Update a booking's status."""
        if status not in VALID_STATUSES:
            raise BadRequestError(
                f"Invalid status '{status}'. Must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            )

        repo = BookingRepository(db.session)
        booking = repo.find_by_id(booking_id)
        if not booking or booking.deleted_at:
            raise NotFoundError("Booking not found")

        booking.status = status
        booking.updated_by = g.user.id if hasattr(g, "user") and g.user else None
        db.session.commit()
        return booking.to_dict()

    # ── POST /<id>/quotation ───────────────────────────────────────────

    @staticmethod
    def create_quotation_from_booking(booking_id: UUID) -> dict:
        """Create a quotation from an existing booking."""
        repo = BookingRepository(db.session)
        booking = repo.find_by_id(booking_id)
        if not booking or booking.deleted_at:
            raise NotFoundError("Booking not found")

        if booking.quotation:
            raise BadRequestError("Booking already has a quotation")

        from app.blueprints.quotations.services import QuotationService

        quotation_data = {
            "booking_id": booking.id,
            "customer_id": booking.customer_id,
            "tour_id": booking.tour_id,
            "number_of_adults": booking.number_of_adults,
            "number_of_children": booking.number_of_children,
            "total_amount": (
                float(booking.total_amount) if booking.total_amount else None
            ),
            "currency": booking.currency,
            "special_requests": booking.special_requests,
        }

        return QuotationService.create_quotation(quotation_data)

    # ── POST /<id>/invoice ─────────────────────────────────────────────

    @staticmethod
    def create_invoice_from_booking(booking_id: UUID) -> dict:
        """Create an invoice from an existing booking."""
        repo = BookingRepository(db.session)
        booking = repo.find_by_id(booking_id)
        if not booking or booking.deleted_at:
            raise NotFoundError("Booking not found")

        if booking.invoice:
            raise BadRequestError("Booking already has an invoice")

        from app.blueprints.invoices.services import InvoiceService

        invoice_data = {
            "booking_id": booking.id,
            "customer_id": booking.customer_id,
            "total_amount": (
                float(booking.total_amount) if booking.total_amount else None
            ),
            "currency": booking.currency,
        }

        return InvoiceService.create_invoice(invoice_data)
