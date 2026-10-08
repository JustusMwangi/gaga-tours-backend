"""User management routes."""

from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError

from app.blueprints.users.schemas import (
    AdminUpdateUserSchema,
    InvitationResponseSchema,
    InviteUserSchema,
    UpdateProfileSchema,
    UserDetailResponseSchema,
    UserListQuerySchema,
    UserListResponseSchema,
)
from app.blueprints.users.services import UserService
from app.core.constants import Permissions
from app.core.decorators import audit_action, jwt_required, require_permission
from app.core.exceptions import ValidationError as AppValidationError

users_bp = Blueprint("users", __name__)


# ── Self-service endpoints ─────────────────────────────────────────────


@users_bp.route("/me", methods=["GET"])
@jwt_required
def get_me():
    result = UserService.get_current_user(user_id=g.user.id)
    return jsonify(UserDetailResponseSchema().dump(result)), 200


@users_bp.route("/me", methods=["PUT"])
@jwt_required
def update_me():
    schema = UpdateProfileSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.update_profile(user_id=g.user.id, data=data)
    return jsonify(UserDetailResponseSchema().dump(result)), 200


# ── Admin endpoints ────────────────────────────────────────────────────


@users_bp.route("/", methods=["GET"])
@require_permission(Permissions.USERS_VIEW)
def list_users():
    schema = UserListQuerySchema()
    try:
        params = schema.load(request.args)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.list_users(
        page=params["page"],
        per_page=params["per_page"],
        search=params.get("search"),
        is_active=params.get("is_active"),
    )
    return jsonify(UserListResponseSchema().dump(result)), 200


@users_bp.route("/<uuid:user_id>", methods=["GET"])
@require_permission(Permissions.USERS_VIEW)
def get_user(user_id):
    result = UserService.get_user_detail(user_id=user_id)
    return jsonify(UserDetailResponseSchema().dump(result)), 200


@users_bp.route("/invite", methods=["POST"])
@audit_action("users.invite", resource_type="user")
@require_permission(Permissions.USERS_CREATE)
def invite_user():
    schema = InviteUserSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.invite_user(
        invited_by=g.user.id,
        data=data,
    )
    return jsonify(InvitationResponseSchema().dump(result)), 201


@users_bp.route("/<uuid:user_id>", methods=["PUT"])
@audit_action("users.update", resource_type="user",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("user_id")))
@require_permission(Permissions.USERS_EDIT)
def admin_update_user(user_id):
    schema = AdminUpdateUserSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = UserService.admin_update_user(
        user_id=user_id,
        admin_user_id=g.user.id,
        data=data,
    )
    return jsonify(UserDetailResponseSchema().dump(result)), 200


@users_bp.route("/<uuid:user_id>", methods=["DELETE"])
@audit_action("users.deactivate", resource_type="user",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("user_id")))
@require_permission(Permissions.USERS_DELETE)
def deactivate_user(user_id):
    result = UserService.deactivate_user(
        user_id=user_id,
        admin_user_id=g.user.id,
    )
    return jsonify(result), 200
