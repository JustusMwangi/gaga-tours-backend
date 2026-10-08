"""Invoice & Payment schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# -- Nested response helpers -------------------------------------------------


class CustomerInfoSchema(Schema):
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()


class BookingInfoSchema(Schema):
    id = fields.UUID()
    reference = fields.String()


# -- Request schemas ---------------------------------------------------------


class CreateInvoiceSchema(Schema):
    """Create a new invoice."""
    booking_id = fields.UUID(load_default=None)
    quotation_id = fields.UUID(load_default=None)
    customer_id = fields.UUID(load_default=None)
    subtotal = fields.Decimal(load_default=0, as_string=True)
    tax_amount = fields.Decimal(load_default=0, as_string=True)
    discount_amount = fields.Decimal(load_default=0, as_string=True)
    total_amount = fields.Decimal(load_default=0, as_string=True)
    currency = fields.String(
        load_default="USD", validate=validate.Length(min=3, max=3),
    )
    due_date = fields.Date(load_default=None)
    notes = fields.String(load_default=None)
    terms = fields.String(load_default=None)


class UpdateInvoiceSchema(Schema):
    """Update an existing invoice (all fields optional)."""
    booking_id = fields.UUID()
    quotation_id = fields.UUID()
    customer_id = fields.UUID()
    subtotal = fields.Decimal(as_string=True)
    tax_amount = fields.Decimal(as_string=True)
    discount_amount = fields.Decimal(as_string=True)
    total_amount = fields.Decimal(as_string=True)
    currency = fields.String(validate=validate.Length(min=3, max=3))
    due_date = fields.Date(allow_none=True)
    notes = fields.String(allow_none=True)
    terms = fields.String(allow_none=True)


class UpdateInvoiceStatusSchema(Schema):
    """Update an invoice's status."""
    status = fields.String(
        required=True,
        validate=validate.OneOf(
            ["draft", "sent", "paid", "partially_paid", "overdue", "cancelled"],
        ),
    )


class InvoiceListQuerySchema(Schema):
    """Query params for GET /invoices."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=20, validate=validate.Range(min=1, max=100),
    )
    search = fields.String(load_default=None)
    status = fields.String(load_default=None)
    customer_id = fields.UUID(load_default=None)


class RecordPaymentSchema(Schema):
    """Record a payment against an invoice."""
    amount = fields.Decimal(required=True, as_string=True)
    payment_method = fields.String(
        load_default="bank_transfer",
        validate=validate.OneOf(
            ["bank_transfer", "credit_card", "cash", "mpesa", "paypal", "other"],
        ),
    )
    payment_date = fields.Date(required=True)
    reference_number = fields.String(load_default=None)
    notes = fields.String(load_default=None)


class ConfirmPaymentSchema(Schema):
    """Validates the confirm-payment action (empty body)."""
    pass


# -- Response schemas --------------------------------------------------------


class PaymentResponseSchema(Schema):
    """Payment info."""
    id = fields.UUID()
    invoice_id = fields.UUID()
    amount = fields.Decimal(as_string=True)
    payment_method = fields.String()
    payment_date = fields.Date()
    reference_number = fields.String(allow_none=True)
    status = fields.String()
    notes = fields.String(allow_none=True)
    created_at = fields.DateTime()


class InvoiceResponseSchema(Schema):
    """Basic invoice info for list views."""
    id = fields.UUID()
    invoice_number = fields.String()
    customer_id = fields.UUID(allow_none=True)
    status = fields.String()
    total_amount = fields.Decimal(as_string=True)
    currency = fields.String()
    due_date = fields.Date(allow_none=True)
    issued_date = fields.Date(allow_none=True)
    paid_date = fields.Date(allow_none=True)
    created_at = fields.DateTime()


class InvoiceDetailResponseSchema(Schema):
    """Invoice detail with nested related objects."""
    id = fields.UUID()
    invoice_number = fields.String()
    booking_id = fields.UUID(allow_none=True)
    quotation_id = fields.UUID(allow_none=True)
    customer_id = fields.UUID(allow_none=True)
    subtotal = fields.Decimal(as_string=True)
    tax_amount = fields.Decimal(as_string=True)
    discount_amount = fields.Decimal(as_string=True)
    total_amount = fields.Decimal(as_string=True)
    currency = fields.String()
    status = fields.String()
    due_date = fields.Date(allow_none=True)
    notes = fields.String(allow_none=True)
    terms = fields.String(allow_none=True)
    issued_date = fields.Date(allow_none=True)
    paid_date = fields.Date(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    created_by = fields.UUID(allow_none=True)
    updated_by = fields.UUID(allow_none=True)

    # Nested
    customer = fields.Nested(CustomerInfoSchema, allow_none=True)
    booking = fields.Nested(BookingInfoSchema, allow_none=True)
    payments = fields.List(fields.Nested(PaymentResponseSchema))


class InvoiceListResponseSchema(Schema):
    """Paginated invoice list response."""
    invoices = fields.List(fields.Nested(InvoiceResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()
