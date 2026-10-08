"""Booking schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Nested response helpers ──────────────────────────────────────────────


class CustomerInfoSchema(Schema):
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()


class TourInfoSchema(Schema):
    id = fields.UUID()
    title = fields.String()


class InvoiceInfoSchema(Schema):
    id = fields.UUID()
    invoice_number = fields.String(allow_none=True)


class QuotationInfoSchema(Schema):
    id = fields.UUID()
    reference = fields.String(allow_none=True)


# ── Request schemas ──────────────────────────────────────────────────────


class CreateBookingSchema(Schema):
    """Create a new booking."""
    customer_id = fields.UUID(required=True)
    tour_id = fields.UUID(load_default=None)
    tour_date_id = fields.UUID(load_default=None)
    number_of_adults = fields.Integer(
        load_default=1, validate=validate.Range(min=0),
    )
    number_of_children = fields.Integer(
        load_default=0, validate=validate.Range(min=0),
    )
    total_amount = fields.Decimal(load_default=None, as_string=True)
    currency = fields.String(
        load_default="USD", validate=validate.Length(min=3, max=3),
    )
    special_requests = fields.String(load_default=None)
    internal_notes = fields.String(load_default=None)
    booking_date = fields.DateTime(load_default=None)


class UpdateBookingSchema(Schema):
    """Update an existing booking (all fields optional)."""
    customer_id = fields.UUID()
    tour_id = fields.UUID()
    tour_date_id = fields.UUID()
    inquiry_id = fields.UUID()
    number_of_adults = fields.Integer(validate=validate.Range(min=0))
    number_of_children = fields.Integer(validate=validate.Range(min=0))
    total_amount = fields.Decimal(as_string=True)
    currency = fields.String(validate=validate.Length(min=3, max=3))
    special_requests = fields.String(allow_none=True)
    internal_notes = fields.String(allow_none=True)
    booking_date = fields.DateTime(allow_none=True)


class UpdateBookingStatusSchema(Schema):
    """Update a booking's status."""
    status = fields.String(
        required=True,
        validate=validate.OneOf(
            ["pending", "confirmed", "in_progress", "completed", "cancelled"],
        ),
    )


class BookingListQuerySchema(Schema):
    """Query params for GET /bookings."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20, validate=validate.Range(min=1, max=100),
    )
    search = fields.String(load_default=None)
    status = fields.String(load_default=None)
    customer_id = fields.UUID(load_default=None)
    tour_id = fields.UUID(load_default=None)


# ── Response schemas ─────────────────────────────────────────────────────


class BookingResponseSchema(Schema):
    """Basic booking info for list views."""
    id = fields.UUID()
    reference = fields.String()
    customer_id = fields.UUID(allow_none=True)
    tour_id = fields.UUID(allow_none=True)
    status = fields.String()
    total_amount = fields.Decimal(as_string=True, allow_none=True)
    currency = fields.String()
    number_of_adults = fields.Integer()
    number_of_children = fields.Integer()
    booking_date = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()


class BookingDetailResponseSchema(Schema):
    """Booking detail with nested related objects."""
    id = fields.UUID()
    reference = fields.String()
    customer_id = fields.UUID(allow_none=True)
    tour_id = fields.UUID(allow_none=True)
    tour_date_id = fields.UUID(allow_none=True)
    inquiry_id = fields.UUID(allow_none=True)
    status = fields.String()
    total_amount = fields.Decimal(as_string=True, allow_none=True)
    currency = fields.String()
    number_of_adults = fields.Integer()
    number_of_children = fields.Integer()
    special_requests = fields.String(allow_none=True)
    internal_notes = fields.String(allow_none=True)
    booking_date = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    created_by = fields.UUID(allow_none=True)
    updated_by = fields.UUID(allow_none=True)

    # Nested
    customer = fields.Nested(CustomerInfoSchema, allow_none=True)
    tour = fields.Nested(TourInfoSchema, allow_none=True)
    invoice = fields.Nested(InvoiceInfoSchema, allow_none=True)
    quotation = fields.Nested(QuotationInfoSchema, allow_none=True)


class BookingListResponseSchema(Schema):
    """Paginated booking list response."""
    bookings = fields.List(fields.Nested(BookingResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()
