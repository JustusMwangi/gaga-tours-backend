"""Inquiry schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Nested response helpers ──────────────────────────────────────────────


class TourInfoSchema(Schema):
    id = fields.UUID()
    title = fields.String()


class CustomerInfoSchema(Schema):
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()


class AssigneeInfoSchema(Schema):
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()


# ── Request schemas ──────────────────────────────────────────────────────


class CreateInquirySchema(Schema):
    """Validate POST /inquiries payload."""
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    phone = fields.String(validate=validate.Length(max=30), allow_none=True)
    tour_id = fields.UUID(load_default=None)
    message = fields.String(allow_none=True)
    travel_date = fields.Date(load_default=None)
    flexible_dates = fields.Boolean(load_default=False)
    group_size_adults = fields.Integer(load_default=1, validate=validate.Range(min=0))
    group_size_children = fields.Integer(load_default=0, validate=validate.Range(min=0))
    budget = fields.Decimal(load_default=None, as_string=True, allow_none=True)
    currency = fields.String(load_default="USD", validate=validate.Length(equal=3))
    source = fields.String(load_default="website", validate=validate.Length(max=50))
    assigned_to = fields.UUID(load_default=None)
    internal_notes = fields.String(allow_none=True)


class UpdateInquirySchema(Schema):
    """Validate PUT /inquiries/<id> payload. All fields optional."""
    first_name = fields.String(validate=validate.Length(min=1, max=100))
    last_name = fields.String(validate=validate.Length(min=1, max=100))
    email = fields.Email()
    phone = fields.String(validate=validate.Length(max=30), allow_none=True)
    tour_id = fields.UUID(allow_none=True)
    message = fields.String(allow_none=True)
    travel_date = fields.Date(allow_none=True)
    flexible_dates = fields.Boolean()
    group_size_adults = fields.Integer(validate=validate.Range(min=0))
    group_size_children = fields.Integer(validate=validate.Range(min=0))
    budget = fields.Decimal(as_string=True, allow_none=True)
    currency = fields.String(validate=validate.Length(equal=3))
    status = fields.String(validate=validate.OneOf(
        ["new", "contacted", "quoted", "converted", "closed"],
    ))
    source = fields.String(validate=validate.Length(max=50))
    assigned_to = fields.UUID(allow_none=True)
    internal_notes = fields.String(allow_none=True)
    customer_id = fields.UUID(allow_none=True)


class ConvertInquirySchema(Schema):
    """Validate POST /inquiries/<id>/convert payload."""
    tour_id = fields.UUID(load_default=None)
    tour_date_id = fields.UUID(load_default=None)
    number_of_adults = fields.Integer(load_default=None, validate=validate.Range(min=0))
    number_of_children = fields.Integer(load_default=None, validate=validate.Range(min=0))
    total_amount = fields.Decimal(load_default=None, as_string=True, allow_none=True)
    special_requests = fields.String(load_default=None, allow_none=True)


class InquiryListQuerySchema(Schema):
    """Query params for GET /inquiries."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    status = fields.String(load_default=None, validate=validate.OneOf(
        ["new", "contacted", "quoted", "converted", "closed"],
    ))
    tour_id = fields.UUID(load_default=None)


# ── Response schemas ─────────────────────────────────────────────────────


class InquiryResponseSchema(Schema):
    """Basic inquiry info for list views."""
    id = fields.UUID()
    reference = fields.String()
    first_name = fields.String()
    last_name = fields.String()
    email = fields.Email()
    phone = fields.String()
    tour_id = fields.UUID()
    status = fields.String()
    source = fields.String()
    travel_date = fields.Date()
    group_size_adults = fields.Integer()
    created_at = fields.DateTime()


class InquiryDetailResponseSchema(Schema):
    """Full inquiry detail with nested relationships."""
    id = fields.UUID()
    reference = fields.String()
    first_name = fields.String()
    last_name = fields.String()
    email = fields.Email()
    phone = fields.String()
    tour_id = fields.UUID()
    customer_id = fields.UUID()
    assigned_to = fields.UUID()
    message = fields.String()
    travel_date = fields.Date()
    flexible_dates = fields.Boolean()
    group_size_adults = fields.Integer()
    group_size_children = fields.Integer()
    budget = fields.Decimal(as_string=True)
    currency = fields.String()
    status = fields.String()
    source = fields.String()
    internal_notes = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    created_by = fields.UUID()
    updated_by = fields.UUID()

    # Nested relationships
    tour = fields.Nested(TourInfoSchema, allow_none=True)
    customer = fields.Nested(CustomerInfoSchema, allow_none=True)
    assignee = fields.Nested(AssigneeInfoSchema, allow_none=True)


class InquiryListResponseSchema(Schema):
    """Paginated inquiry list response."""
    inquiries = fields.List(fields.Nested(InquiryResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()
