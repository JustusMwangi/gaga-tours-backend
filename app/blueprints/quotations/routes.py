"""Quotation management routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.quotations.schemas import (
    CreateQuotationSchema,
    QuotationDetailResponseSchema,
    QuotationListQuerySchema,
    QuotationListResponseSchema,
    UpdateQuotationSchema,
    UpdateQuotationStatusSchema,
)
from app.blueprints.quotations.services import QuotationService
from app.core.constants import Permissions
from app.core.decorators import audit_action, jwt_required, require_permission
from app.core.exceptions import ValidationError as AppValidationError

quotations_bp = Blueprint("quotations", __name__)


# ── GET / ────────────────────────────────────────────────────────────────


@quotations_bp.route("/", methods=["GET"])
@jwt_required
@require_permission(Permissions.QUOTATIONS_VIEW)
def list_quotations():
    schema = QuotationListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = QuotationService.list_quotations(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        status=params.get("status"),
        customer_id=params.get("customer_id"),
        booking_id=params.get("booking_id"),
    )
    return jsonify(QuotationListResponseSchema().dump(result)), 200


# ── POST / ───────────────────────────────────────────────────────────────


@quotations_bp.route("/", methods=["POST"])
@jwt_required
@audit_action("quotations.create", resource_type="quotation")
@require_permission(Permissions.QUOTATIONS_MANAGE)
def create_quotation():
    schema = CreateQuotationSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = QuotationService.create_quotation(data)
    return jsonify(QuotationDetailResponseSchema().dump(result)), 201


# ── GET /<id> ────────────────────────────────────────────────────────────


@quotations_bp.route("/<uuid:quotation_id>", methods=["GET"])
@jwt_required
@require_permission(Permissions.QUOTATIONS_VIEW)
def get_quotation(quotation_id):
    result = QuotationService.get_quotation(quotation_id)
    return jsonify(QuotationDetailResponseSchema().dump(result)), 200


# ── PUT /<id> ────────────────────────────────────────────────────────────


@quotations_bp.route("/<uuid:quotation_id>", methods=["PUT"])
@jwt_required
@audit_action(
    "quotations.update",
    resource_type="quotation",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("quotation_id")),
)
@require_permission(Permissions.QUOTATIONS_MANAGE)
def update_quotation(quotation_id):
    schema = UpdateQuotationSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = QuotationService.update_quotation(quotation_id, data)
    return jsonify(QuotationDetailResponseSchema().dump(result)), 200


# ── PUT /<id>/status ─────────────────────────────────────────────────────


@quotations_bp.route("/<uuid:quotation_id>/status", methods=["PUT"])
@jwt_required
@audit_action(
    "quotations.status_update",
    resource_type="quotation",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("quotation_id")),
)
@require_permission(Permissions.QUOTATIONS_MANAGE)
def update_quotation_status(quotation_id):
    schema = UpdateQuotationStatusSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = QuotationService.update_status(quotation_id, data["status"])
    return jsonify(QuotationDetailResponseSchema().dump(result)), 200


# ── POST /<id>/convert-to-invoice ────────────────────────────────────────


@quotations_bp.route("/<uuid:quotation_id>/convert-to-invoice", methods=["POST"])
@jwt_required
@audit_action(
    "quotations.convert",
    resource_type="quotation",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("quotation_id")),
)
@require_permission(Permissions.QUOTATIONS_MANAGE)
def convert_to_invoice(quotation_id):
    result = QuotationService.convert_to_invoice(quotation_id)
    return jsonify(result), 201
