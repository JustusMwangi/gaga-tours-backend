"""Tour domain routes — categories, destinations, tours, dates, gallery."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.tours.schemas import (
    CategoryListQuerySchema,
    CategoryListResponseSchema,
    CategoryResponseSchema,
    CreateCategorySchema,
    CreateDestinationSchema,
    CreateGalleryItemSchema,
    CreateTourDateSchema,
    CreateTourSchema,
    DestinationListQuerySchema,
    DestinationListResponseSchema,
    DestinationResponseSchema,
    GalleryItemResponseSchema,
    TourDateResponseSchema,
    TourDetailResponseSchema,
    TourListQuerySchema,
    TourListResponseSchema,
    TourResponseSchema,
    UpdateCategorySchema,
    UpdateDestinationSchema,
    UpdateGalleryItemSchema,
    UpdateTourDateSchema,
    UpdateTourSchema,
)
from app.blueprints.tours.services import (
    DestinationService,
    TourCategoryService,
    TourDateService,
    TourGalleryService,
    TourService,
)
from app.core.constants import Permissions
from app.core.decorators import audit_action, require_permission
from app.core.exceptions import ValidationError as AppValidationError

tours_bp = Blueprint("tours", __name__)


# ── Categories ────────────────────────────────────────────────────────────


@tours_bp.route("/categories/", methods=["GET"])
@require_permission(Permissions.TOURS_VIEW)
def list_categories():
    schema = CategoryListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourCategoryService.list_categories(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        is_active=params.get("is_active"),
    )
    return jsonify(CategoryListResponseSchema().dump(result)), 200


@tours_bp.route("/categories/", methods=["POST"])
@audit_action("tours.create_category", resource_type="tour_category")
@require_permission(Permissions.TOURS_MANAGE)
def create_category():
    schema = CreateCategorySchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourCategoryService.create_category(data)
    return jsonify(CategoryResponseSchema().dump(result)), 201


@tours_bp.route("/categories/<uuid:category_id>", methods=["PUT"])
@audit_action("tours.update_category", resource_type="tour_category",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("category_id")))
@require_permission(Permissions.TOURS_MANAGE)
def update_category(category_id):
    schema = UpdateCategorySchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourCategoryService.update_category(category_id, data)
    return jsonify(CategoryResponseSchema().dump(result)), 200


@tours_bp.route("/categories/<uuid:category_id>", methods=["DELETE"])
@audit_action("tours.delete_category", resource_type="tour_category",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("category_id")))
@require_permission(Permissions.TOURS_MANAGE)
def delete_category(category_id):
    result = TourCategoryService.delete_category(category_id)
    return jsonify(result), 200


# ── Destinations ──────────────────────────────────────────────────────────


@tours_bp.route("/destinations/", methods=["GET"])
@require_permission(Permissions.TOURS_VIEW)
def list_destinations():
    schema = DestinationListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = DestinationService.list_destinations(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        is_active=params.get("is_active"),
    )
    return jsonify(DestinationListResponseSchema().dump(result)), 200


@tours_bp.route("/destinations/", methods=["POST"])
@audit_action("tours.create_destination", resource_type="destination")
@require_permission(Permissions.TOURS_MANAGE)
def create_destination():
    schema = CreateDestinationSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = DestinationService.create_destination(data)
    return jsonify(DestinationResponseSchema().dump(result)), 201


@tours_bp.route("/destinations/<uuid:destination_id>", methods=["PUT"])
@audit_action("tours.update_destination", resource_type="destination",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("destination_id")))
@require_permission(Permissions.TOURS_MANAGE)
def update_destination(destination_id):
    schema = UpdateDestinationSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = DestinationService.update_destination(destination_id, data)
    return jsonify(DestinationResponseSchema().dump(result)), 200


@tours_bp.route("/destinations/<uuid:destination_id>", methods=["DELETE"])
@audit_action("tours.delete_destination", resource_type="destination",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("destination_id")))
@require_permission(Permissions.TOURS_MANAGE)
def delete_destination(destination_id):
    result = DestinationService.delete_destination(destination_id)
    return jsonify(result), 200


# ── Tours ─────────────────────────────────────────────────────────────────


@tours_bp.route("/", methods=["GET"])
@require_permission(Permissions.TOURS_VIEW)
def list_tours():
    schema = TourListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourService.list_tours(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        status=params.get("status"),
        category_id=params.get("category_id"),
        destination_id=params.get("destination_id"),
        featured=params.get("featured"),
    )
    return jsonify(TourListResponseSchema().dump(result)), 200


@tours_bp.route("/", methods=["POST"])
@audit_action("tours.create", resource_type="tour")
@require_permission(Permissions.TOURS_MANAGE)
def create_tour():
    schema = CreateTourSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourService.create_tour(data)
    return jsonify(TourResponseSchema().dump(result)), 201


@tours_bp.route("/<uuid:tour_id>", methods=["GET"])
@require_permission(Permissions.TOURS_VIEW)
def get_tour(tour_id):
    result = TourService.get_tour(tour_id)
    return jsonify(TourDetailResponseSchema().dump(result)), 200


@tours_bp.route("/<uuid:tour_id>", methods=["PUT"])
@audit_action("tours.update", resource_type="tour",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("tour_id")))
@require_permission(Permissions.TOURS_MANAGE)
def update_tour(tour_id):
    schema = UpdateTourSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourService.update_tour(tour_id, data)
    return jsonify(TourDetailResponseSchema().dump(result)), 200


@tours_bp.route("/<uuid:tour_id>", methods=["DELETE"])
@audit_action("tours.delete", resource_type="tour",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("tour_id")))
@require_permission(Permissions.TOURS_MANAGE)
def delete_tour(tour_id):
    result = TourService.delete_tour(tour_id)
    return jsonify(result), 200


# ── Tour Dates ────────────────────────────────────────────────────────────


@tours_bp.route("/<uuid:tour_id>/dates/", methods=["GET"])
@require_permission(Permissions.TOURS_VIEW)
def list_dates(tour_id):
    result = TourDateService.list_dates(tour_id)
    return jsonify(TourDateResponseSchema(many=True).dump(result)), 200


@tours_bp.route("/<uuid:tour_id>/dates/", methods=["POST"])
@audit_action("tours.create_date", resource_type="tour_date")
@require_permission(Permissions.TOURS_MANAGE)
def create_date(tour_id):
    schema = CreateTourDateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourDateService.create_date(tour_id, data)
    return jsonify(TourDateResponseSchema().dump(result)), 201


@tours_bp.route("/<uuid:tour_id>/dates/<uuid:date_id>", methods=["PUT"])
@audit_action("tours.update_date", resource_type="tour_date",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("date_id")))
@require_permission(Permissions.TOURS_MANAGE)
def update_date(tour_id, date_id):
    schema = UpdateTourDateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourDateService.update_date(date_id, data)
    return jsonify(TourDateResponseSchema().dump(result)), 200


@tours_bp.route("/<uuid:tour_id>/dates/<uuid:date_id>", methods=["DELETE"])
@audit_action("tours.delete_date", resource_type="tour_date",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("date_id")))
@require_permission(Permissions.TOURS_MANAGE)
def delete_date(tour_id, date_id):
    result = TourDateService.delete_date(date_id)
    return jsonify(result), 200


# ── Gallery ───────────────────────────────────────────────────────────────


@tours_bp.route("/<uuid:tour_id>/gallery/", methods=["GET"])
@require_permission(Permissions.TOURS_VIEW)
def list_images(tour_id):
    result = TourGalleryService.list_images(tour_id)
    return jsonify(GalleryItemResponseSchema(many=True).dump(result)), 200


@tours_bp.route("/<uuid:tour_id>/gallery/", methods=["POST"])
@audit_action("tours.add_image", resource_type="tour_gallery")
@require_permission(Permissions.TOURS_MANAGE)
def add_image(tour_id):
    schema = CreateGalleryItemSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourGalleryService.add_image(tour_id, data)
    return jsonify(GalleryItemResponseSchema().dump(result)), 201


@tours_bp.route("/<uuid:tour_id>/gallery/<uuid:image_id>", methods=["PUT"])
@audit_action("tours.update_image", resource_type="tour_gallery",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("image_id")))
@require_permission(Permissions.TOURS_MANAGE)
def update_image(tour_id, image_id):
    schema = UpdateGalleryItemSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = TourGalleryService.update_image(image_id, data)
    return jsonify(GalleryItemResponseSchema().dump(result)), 200


@tours_bp.route("/<uuid:tour_id>/gallery/<uuid:image_id>", methods=["DELETE"])
@audit_action("tours.delete_image", resource_type="tour_gallery",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("image_id")))
@require_permission(Permissions.TOURS_MANAGE)
def delete_image(tour_id, image_id):
    result = TourGalleryService.delete_image(image_id)
    return jsonify(result), 200
