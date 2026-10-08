"""InquiryService: CRUD and conversion operations for inquiries."""

import logging
import math
from uuid import UUID

from app.blueprints.inquiries.models import Inquiry
from app.blueprints.inquiries.repositories import InquiryRepository
from app.core.exceptions import BadRequestError, NotFoundError
from app.extensions import db

logger = logging.getLogger(__name__)


class InquiryService:
    """Static methods for all inquiry management operations."""

    # ── POST / ─────────────────────────────────────────────────────

    @staticmethod
    def create_inquiry(data: dict) -> dict:
        """Create a new inquiry with an auto-generated reference."""
        repo = InquiryRepository(db.session)

        reference = repo.get_next_reference()

        inquiry = Inquiry(
            reference=reference,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data.get("phone"),
            tour_id=data.get("tour_id"),
            message=data.get("message"),
            travel_date=data.get("travel_date"),
            flexible_dates=data.get("flexible_dates", False),
            group_size_adults=data.get("group_size_adults", 1),
            group_size_children=data.get("group_size_children", 0),
            budget=data.get("budget"),
            currency=data.get("currency", "USD"),
            source=data.get("source", "website"),
            assigned_to=data.get("assigned_to"),
            internal_notes=data.get("internal_notes"),
        )

        repo.create(inquiry)
        db.session.commit()

        return inquiry.to_dict()

    # ── GET / ──────────────────────────────────────────────────────

    @staticmethod
    def list_inquiries(
        page: int = 1,
        per_page: int = 20,
        search: str = None,
        status: str = None,
        tour_id: UUID = None,
    ) -> dict:
        """List paginated inquiries with optional filters."""
        repo = InquiryRepository(db.session)

        inquiries, total = repo.list_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            tour_id=tour_id,
        )

        return {
            "inquiries": inquiries,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    # ── GET /<id> ──────────────────────────────────────────────────

    @staticmethod
    def get_inquiry(inquiry_id: UUID) -> dict:
        """Return a single inquiry with related objects."""
        repo = InquiryRepository(db.session)

        inquiry = repo.find_by_id(inquiry_id)
        if not inquiry or inquiry.is_deleted:
            raise NotFoundError("Inquiry not found")

        result = inquiry.to_dict()

        # Attach nested tour info
        if inquiry.tour:
            result["tour"] = {
                "id": inquiry.tour.id,
                "title": inquiry.tour.title,
            }
        else:
            result["tour"] = None

        # Attach nested customer info
        if inquiry.customer:
            result["customer"] = {
                "id": inquiry.customer.id,
                "first_name": inquiry.customer.first_name,
                "last_name": inquiry.customer.last_name,
            }
        else:
            result["customer"] = None

        # Attach nested assignee info
        if inquiry.assignee:
            result["assignee"] = {
                "id": inquiry.assignee.id,
                "first_name": inquiry.assignee.first_name,
                "last_name": inquiry.assignee.last_name,
            }
        else:
            result["assignee"] = None

        return result

    # ── PUT /<id> ──────────────────────────────────────────────────

    @staticmethod
    def update_inquiry(inquiry_id: UUID, data: dict) -> dict:
        """Update an existing inquiry."""
        repo = InquiryRepository(db.session)

        inquiry = repo.find_by_id(inquiry_id)
        if not inquiry or inquiry.is_deleted:
            raise NotFoundError("Inquiry not found")

        updatable_fields = [
            "first_name", "last_name", "email", "phone", "tour_id",
            "message", "travel_date", "flexible_dates", "group_size_adults",
            "group_size_children", "budget", "currency", "status", "source",
            "assigned_to", "internal_notes", "customer_id",
        ]

        for field in updatable_fields:
            if field in data:
                setattr(inquiry, field, data[field])

        db.session.commit()

        return inquiry.to_dict()

    # ── POST /<id>/convert ─────────────────────────────────────────

    @staticmethod
    def convert_to_booking(inquiry_id: UUID, data: dict) -> dict:
        """Convert an inquiry into a booking.

        Steps:
        1. Find inquiry, validate status != 'converted'
        2. Find or create Customer (by email)
        3. Create Booking linking to customer and inquiry
        4. Update inquiry status to 'converted', set customer_id
        5. Return booking dict
        """
        repo = InquiryRepository(db.session)

        inquiry = repo.find_by_id(inquiry_id)
        if not inquiry or inquiry.is_deleted:
            raise NotFoundError("Inquiry not found")

        if inquiry.status == "converted":
            raise BadRequestError("Inquiry has already been converted to a booking")

        # Step 2: Find or create customer
        from app.blueprints.customers.services import CustomerService

        customer = CustomerService.find_or_create_by_email(
            email=inquiry.email,
            first_name=inquiry.first_name,
            last_name=inquiry.last_name,
            phone=inquiry.phone,
            source="inquiry",
        )

        # Step 3: Create booking
        from app.blueprints.bookings.services import BookingService

        booking_data = {
            "customer_id": customer["id"],
            "inquiry_id": inquiry.id,
            "tour_id": data.get("tour_id", inquiry.tour_id),
            "tour_date_id": data.get("tour_date_id"),
            "number_of_adults": data.get("number_of_adults", inquiry.group_size_adults),
            "number_of_children": data.get("number_of_children", inquiry.group_size_children),
            "total_amount": data.get("total_amount"),
            "special_requests": data.get("special_requests"),
        }

        booking = BookingService.create_booking(booking_data)

        # Step 4: Update inquiry status
        inquiry.status = "converted"
        inquiry.customer_id = customer["id"]
        db.session.commit()

        return booking
