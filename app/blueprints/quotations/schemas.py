"""Quotation schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Nested response helpers ──────────────────────────────────────────────


class CustomerInfoSchema(Schema):
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()


class BookingInfoSchema(Schema):
    id = fields.UUID()
    reference = fields.String()


class TourInfoSchema(Schema):
    id = fields.UUID()
    title = fields.String()


# ── Request schemas ──────────────────────────────────────────────────────


class QuotationItemSchema(Schema):
    """A line item within a quotation (for create/update)."""
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    item_type = fields.String(
        load_default="service",
        validate=validate.OneOf(
            ["service", "accommodation", "transport", "activity", "other"],
        ),
    )
    quantity = fields.Integer(load_default=1, validate=validate.Range(min=1))
    unit_price = fields.Decimal(required=True, as_string=True)
    total_price = fields.Decimal(required=True, as_string=True)
    sort_order = fields.Integer(load_default=0)


class CreateQuotationSchema(Schema):
    """Create a new quotation."""
    booking_id = fields.UUID(load_default=None)
    customer_id = fields.UUID(load_default=None)
    tour_id = fields.UUID(load_default=None)
    subtotal = fields.Decimal(load_default=None, as_string=True)
    tax_amount = fields.Decimal(load_default=None, as_string=True)
    discount_amount = fields.Decimal(load_default=None, as_string=True)
    total_amount = fields.Decimal(load_default=None, as_string=True)
    currency = fields.String(
        load_default="USD", validate=validate.Length(min=3, max=3),
    )
    valid_until = fields.Date(load_default=None)
    notes = fields.String(load_default=None)
    terms = fields.String(load_default=None)
    items = fields.List(fields.Nested(QuotationItemSchema), load_default=[])


class UpdateQuotationSchema(Schema):
    """Update an existing quotation (all fields optional)."""
    booking_id = fields.UUID()
    customer_id = fields.UUID()
    tour_id = fields.UUID()
    subtotal = fields.Decimal(as_string=True)
    tax_amount = fields.Decimal(as_string=True)
    discount_amount = fields.Decimal(as_string=True)
    total_amount = fields.Decimal(as_string=True)
    currency = fields.String(validate=validate.Length(min=3, max=3))
    valid_until = fields.Date(allow_none=True)
    notes = fields.String(allow_none=True)
    terms = fields.String(allow_none=True)
    items = fields.List(fields.Nested(QuotationItemSchema))


class UpdateQuotationStatusSchema(Schema):
    """Update a quotation's status."""
    status = fields.String(
        required=True,
        validate=validate.OneOf(
            ["draft", "sent", "approved", "rejected", "expired", "converted"],
        ),
    )


class QuotationListQuerySchema(Schema):
    """Query params for GET /quotations."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20, validate=validate.Range(min=1, max=100),
    )
    search = fields.String(load_default=None)
    status = fields.String(load_default=None)
    customer_id = fields.UUID(load_default=None)
    booking_id = fields.UUID(load_default=None)


# ── Response schemas ─────────────────────────────────────────────────────


class QuotationItemResponseSchema(Schema):
    """Quotation item for response."""
    id = fields.UUID()
    description = fields.String()
    item_type = fields.String()
    quantity = fields.Integer()
    unit_price = fields.Decimal(as_string=True)
    total_price = fields.Decimal(as_string=True)
    sort_order = fields.Integer()


class QuotationResponseSchema(Schema):
    """Basic quotation info for list views."""
    id = fields.UUID()
    reference = fields.String()
    customer_id = fields.UUID(allow_none=True)
    booking_id = fields.UUID(allow_none=True)
    tour_id = fields.UUID(allow_none=True)
    status = fields.String()
    total_amount = fields.Decimal(as_string=True, allow_none=True)
    currency = fields.String()
    valid_until = fields.Date(allow_none=True)
    created_at = fields.DateTime()


class QuotationDetailResponseSchema(Schema):
    """Quotation detail with nested related objects."""
    id = fields.UUID()
    reference = fields.String()
    booking_id = fields.UUID(allow_none=True)
    customer_id = fields.UUID(allow_none=True)
    tour_id = fields.UUID(allow_none=True)
    subtotal = fields.Decimal(as_string=True)
    tax_amount = fields.Decimal(as_string=True)
    discount_amount = fields.Decimal(as_string=True)
    total_amount = fields.Decimal(as_string=True)
    currency = fields.String()
    status = fields.String()
    valid_until = fields.Date(allow_none=True)
    notes = fields.String(allow_none=True)
    terms = fields.String(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    created_by = fields.UUID(allow_none=True)
    updated_by = fields.UUID(allow_none=True)

    # Nested
    customer = fields.Nested(CustomerInfoSchema, allow_none=True)
    booking = fields.Nested(BookingInfoSchema, allow_none=True)
    tour = fields.Nested(TourInfoSchema, allow_none=True)
    items = fields.List(fields.Nested(QuotationItemResponseSchema))


class QuotationListResponseSchema(Schema):
    """Paginated quotation list response."""
    quotations = fields.List(fields.Nested(QuotationResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()
