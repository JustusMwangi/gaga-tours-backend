"""Booking management routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.bookings.schemas import (
    BookingDetailResponseSchema,
    BookingListQuerySchema,
    BookingListResponseSchema,
    CreateBookingSchema,
    UpdateBookingSchema,
    UpdateBookingStatusSchema,
)
from app.blueprints.bookings.services import BookingService
from app.core.constants import Permissions
from app.core.decorators import audit_action, jwt_required, require_permission
from app.core.exceptions import ValidationError as AppValidationError

bookings_bp = Blueprint("bookings", __name__)


# ── GET / ────────────────────────────────────────────────────────────────


@bookings_bp.route("/", methods=["GET"])
@jwt_required
@require_permission(Permissions.BOOKINGS_VIEW)
def list_bookings():
    schema = BookingListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = BookingService.list_bookings(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        status=params.get("status"),
        customer_id=params.get("customer_id"),
        tour_id=params.get("tour_id"),
    )
    return jsonify(BookingListResponseSchema().dump(result)), 200


# ── POST / ───────────────────────────────────────────────────────────────


@bookings_bp.route("/", methods=["POST"])
@jwt_required
@audit_action("bookings.create", resource_type="booking")
@require_permission(Permissions.BOOKINGS_MANAGE)
def create_booking():
    schema = CreateBookingSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = BookingService.create_booking(data)
    return jsonify(BookingDetailResponseSchema().dump(result)), 201


# ── GET /<id> ────────────────────────────────────────────────────────────


@bookings_bp.route("/<uuid:booking_id>", methods=["GET"])
@jwt_required
@require_permission(Permissions.BOOKINGS_VIEW)
def get_booking(booking_id):
    result = BookingService.get_booking(booking_id)
    return jsonify(BookingDetailResponseSchema().dump(result)), 200


# ── PUT /<id> ────────────────────────────────────────────────────────────


@bookings_bp.route("/<uuid:booking_id>", methods=["PUT"])
@jwt_required
@audit_action(
    "bookings.update",
    resource_type="booking",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("booking_id")),
)
@require_permission(Permissions.BOOKINGS_MANAGE)
def update_booking(booking_id):
    schema = UpdateBookingSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = BookingService.update_booking(booking_id, data)
    return jsonify(BookingDetailResponseSchema().dump(result)), 200


# ── PUT /<id>/status ─────────────────────────────────────────────────────


@bookings_bp.route("/<uuid:booking_id>/status", methods=["PUT"])
@jwt_required
@audit_action(
    "bookings.status_update",
    resource_type="booking",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("booking_id")),
)
@require_permission(Permissions.BOOKINGS_MANAGE)
def update_booking_status(booking_id):
    schema = UpdateBookingStatusSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = BookingService.update_status(booking_id, data["status"])
    return jsonify(BookingDetailResponseSchema().dump(result)), 200


# ── POST /<id>/quotation ─────────────────────────────────────────────────


@bookings_bp.route("/<uuid:booking_id>/quotation", methods=["POST"])
@jwt_required
@require_permission(Permissions.BOOKINGS_MANAGE)
def create_quotation_from_booking(booking_id):
    result = BookingService.create_quotation_from_booking(booking_id)
    return jsonify(result), 201


# ── POST /<id>/invoice ───────────────────────────────────────────────────


@bookings_bp.route("/<uuid:booking_id>/invoice", methods=["POST"])
@jwt_required
@require_permission(Permissions.BOOKINGS_MANAGE)
def create_invoice_from_booking(booking_id):
    result = BookingService.create_invoice_from_booking(booking_id)
    return jsonify(result), 201
