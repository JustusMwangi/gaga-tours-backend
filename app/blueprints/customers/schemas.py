"""Customer schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Request schemas ───────────────────────────────────────────────────


VALID_SOURCES = ["direct", "website", "referral", "agent", "social_media"]


class CreateCustomerSchema(Schema):
    """Validate POST /customers body."""
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(load_default=None)
    phone = fields.String(validate=validate.Length(max=30), load_default=None)
    nationality = fields.String(validate=validate.Length(max=100), load_default=None)
    passport_number = fields.String(validate=validate.Length(max=50), load_default=None)
    address = fields.String(load_default=None)
    notes = fields.String(load_default=None)
    source = fields.String(
        validate=validate.OneOf(VALID_SOURCES),
        load_default="direct",
    )


class UpdateCustomerSchema(Schema):
    """Validate PUT /customers/<id> body — all fields optional."""
    first_name = fields.String(validate=validate.Length(min=1, max=100))
    last_name = fields.String(validate=validate.Length(min=1, max=100))
    email = fields.Email(allow_none=True)
    phone = fields.String(validate=validate.Length(max=30), allow_none=True)
    nationality = fields.String(validate=validate.Length(max=100), allow_none=True)
    passport_number = fields.String(validate=validate.Length(max=50), allow_none=True)
    address = fields.String(allow_none=True)
    notes = fields.String(allow_none=True)
    source = fields.String(validate=validate.OneOf(VALID_SOURCES))
    is_active = fields.Boolean()


class CustomerListQuerySchema(Schema):
    """Query params for GET /customers."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    source = fields.String(load_default=None, validate=validate.OneOf(VALID_SOURCES))
    is_active = fields.Boolean(load_default=None)


# ── Response schemas ──────────────────────────────────────────────────


class CustomerResponseSchema(Schema):
    """Basic customer info for list views."""
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()
    email = fields.Email(allow_none=True)
    phone = fields.String(allow_none=True)
    nationality = fields.String(allow_none=True)
    source = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()


class CustomerDetailResponseSchema(Schema):
    """Full customer detail."""
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()
    email = fields.Email(allow_none=True)
    phone = fields.String(allow_none=True)
    nationality = fields.String(allow_none=True)
    passport_number = fields.String(allow_none=True)
    address = fields.String(allow_none=True)
    notes = fields.String(allow_none=True)
    source = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class CustomerListResponseSchema(Schema):
    """Paginated customer list response."""
    customers = fields.List(fields.Nested(CustomerResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()
