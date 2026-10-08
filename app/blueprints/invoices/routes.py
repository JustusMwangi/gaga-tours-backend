"""Invoice and payment management routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.invoices.schemas import (
    ConfirmPaymentSchema,
    CreateInvoiceSchema,
    InvoiceDetailResponseSchema,
    InvoiceListQuerySchema,
    InvoiceListResponseSchema,
    PaymentResponseSchema,
    RecordPaymentSchema,
    UpdateInvoiceSchema,
    UpdateInvoiceStatusSchema,
)
from app.blueprints.invoices.services import InvoiceService, PaymentService
from app.core.constants import Permissions
from app.core.decorators import audit_action, jwt_required, require_permission
from app.core.exceptions import ValidationError as AppValidationError

invoices_bp = Blueprint("invoices", __name__)


# -- GET / -------------------------------------------------------------------


@invoices_bp.route("/", methods=["GET"])
@jwt_required
@require_permission(Permissions.INVOICES_VIEW)
def list_invoices():
    schema = InvoiceListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InvoiceService.list_invoices(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        status=params.get("status"),
        customer_id=params.get("customer_id"),
    )
    return jsonify(InvoiceListResponseSchema().dump(result)), 200


# -- POST / ------------------------------------------------------------------


@invoices_bp.route("/", methods=["POST"])
@jwt_required
@audit_action("invoices.create", resource_type="invoice")
@require_permission(Permissions.INVOICES_MANAGE)
def create_invoice():
    schema = CreateInvoiceSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InvoiceService.create_invoice(data)
    return jsonify(InvoiceDetailResponseSchema().dump(result)), 201


# -- GET /<id> ---------------------------------------------------------------


@invoices_bp.route("/<uuid:invoice_id>", methods=["GET"])
@jwt_required
@require_permission(Permissions.INVOICES_VIEW)
def get_invoice(invoice_id):
    result = InvoiceService.get_invoice(invoice_id)
    return jsonify(InvoiceDetailResponseSchema().dump(result)), 200


# -- PUT /<id> ---------------------------------------------------------------


@invoices_bp.route("/<uuid:invoice_id>", methods=["PUT"])
@jwt_required
@audit_action(
    "invoices.update",
    resource_type="invoice",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("invoice_id")),
)
@require_permission(Permissions.INVOICES_MANAGE)
def update_invoice(invoice_id):
    schema = UpdateInvoiceSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InvoiceService.update_invoice(invoice_id, data)
    return jsonify(InvoiceDetailResponseSchema().dump(result)), 200


# -- PUT /<id>/status --------------------------------------------------------


@invoices_bp.route("/<uuid:invoice_id>/status", methods=["PUT"])
@jwt_required
@audit_action(
    "invoices.status_update",
    resource_type="invoice",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("invoice_id")),
)
@require_permission(Permissions.INVOICES_MANAGE)
def update_invoice_status(invoice_id):
    schema = UpdateInvoiceStatusSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InvoiceService.update_status(invoice_id, data["status"])
    return jsonify(InvoiceDetailResponseSchema().dump(result)), 200


# -- POST /<id>/payments/ ----------------------------------------------------


@invoices_bp.route("/<uuid:invoice_id>/payments/", methods=["POST"])
@jwt_required
@audit_action("payments.create", resource_type="payment")
@require_permission(Permissions.INVOICES_MANAGE)
def record_payment(invoice_id):
    schema = RecordPaymentSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = PaymentService.record_payment(invoice_id, data)
    return jsonify(PaymentResponseSchema().dump(result)), 201


# -- PUT /payments/<id>/confirm ----------------------------------------------


@invoices_bp.route("/payments/<uuid:payment_id>/confirm", methods=["PUT"])
@jwt_required
@audit_action(
    "payments.confirm",
    resource_type="payment",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("payment_id")),
)
@require_permission(Permissions.INVOICES_MANAGE)
def confirm_payment(payment_id):
    schema = ConfirmPaymentSchema()
    try:
        schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = PaymentService.confirm_payment(payment_id)
    return jsonify(PaymentResponseSchema().dump(result)), 200


# -- GET /<id>/payments/ -----------------------------------------------------


@invoices_bp.route("/<uuid:invoice_id>/payments/", methods=["GET"])
@jwt_required
@require_permission(Permissions.INVOICES_VIEW)
def list_payments(invoice_id):
    payments = PaymentService.list_payments(invoice_id)
    return jsonify({"payments": PaymentResponseSchema(many=True).dump(payments)}), 200
