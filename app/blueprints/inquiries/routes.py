"""Inquiry management routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.inquiries.schemas import (
    ConvertInquirySchema,
    CreateInquirySchema,
    InquiryDetailResponseSchema,
    InquiryListQuerySchema,
    InquiryListResponseSchema,
    UpdateInquirySchema,
)
from app.blueprints.inquiries.services import InquiryService
from app.core.constants import Permissions
from app.core.decorators import audit_action, require_permission
from app.core.exceptions import ValidationError as AppValidationError

inquiries_bp = Blueprint("inquiries", __name__)


@inquiries_bp.route("/", methods=["GET"])
@require_permission(Permissions.INQUIRIES_VIEW)
def list_inquiries():
    schema = InquiryListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InquiryService.list_inquiries(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        status=params.get("status"),
        tour_id=params.get("tour_id"),
    )
    return jsonify(InquiryListResponseSchema().dump(result)), 200


@inquiries_bp.route("/", methods=["POST"])
@audit_action("inquiries.create", resource_type="inquiry")
@require_permission(Permissions.INQUIRIES_MANAGE)
def create_inquiry():
    schema = CreateInquirySchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InquiryService.create_inquiry(data)
    return jsonify(result), 201


@inquiries_bp.route("/<uuid:inquiry_id>", methods=["GET"])
@require_permission(Permissions.INQUIRIES_VIEW)
def get_inquiry(inquiry_id):
    result = InquiryService.get_inquiry(inquiry_id)
    return jsonify(InquiryDetailResponseSchema().dump(result)), 200


@inquiries_bp.route("/<uuid:inquiry_id>", methods=["PUT"])
@audit_action("inquiries.update", resource_type="inquiry",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("inquiry_id")))
@require_permission(Permissions.INQUIRIES_MANAGE)
def update_inquiry(inquiry_id):
    schema = UpdateInquirySchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InquiryService.update_inquiry(inquiry_id, data)
    return jsonify(result), 200


@inquiries_bp.route("/<uuid:inquiry_id>/convert", methods=["POST"])
@audit_action("inquiries.convert", resource_type="inquiry",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("inquiry_id")))
@require_permission(Permissions.INQUIRIES_MANAGE)
def convert_to_booking(inquiry_id):
    schema = ConvertInquirySchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = InquiryService.convert_to_booking(inquiry_id, data)
    return jsonify(result), 201
