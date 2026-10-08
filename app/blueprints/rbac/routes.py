"""RBAC routes: role management, permission listing, user-role assignments."""

from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError

from app.blueprints.rbac.schemas import (
    AssignRoleSchema,
    CreateRoleSchema,
    PermissionListResponseSchema,
    RoleDetailResponseSchema,
    RoleListResponseSchema,
    UpdateRoleSchema,
    UserRolesResponseSchema,
)
from app.blueprints.rbac.services import RBACService
from app.core.constants import Permissions
from app.core.decorators import audit_action, require_permission
from app.core.exceptions import ValidationError as AppValidationError

rbac_bp = Blueprint("rbac", __name__)


# ── Role endpoints ────────────────────────────────────────────────────────


@rbac_bp.route("/roles", methods=["GET"])
@require_permission(Permissions.ROLES_VIEW)
def list_roles():
    result = RBACService.list_roles()
    return jsonify(RoleListResponseSchema().dump(result)), 200


@rbac_bp.route("/roles/<uuid:role_id>", methods=["GET"])
@require_permission(Permissions.ROLES_VIEW)
def get_role(role_id):
    result = RBACService.get_role(role_id)
    return jsonify(RoleDetailResponseSchema().dump(result)), 200


@rbac_bp.route("/roles", methods=["POST"])
@audit_action("roles.create", resource_type="role")
@require_permission(Permissions.ROLES_CREATE)
def create_role():
    schema = CreateRoleSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = RBACService.create_role(
        name=data["name"],
        description=data.get("description"),
        permission_ids=data.get("permission_ids", []),
    )
    return jsonify(RoleDetailResponseSchema().dump(result)), 201


@rbac_bp.route("/roles/<uuid:role_id>", methods=["PUT"])
@audit_action("roles.update", resource_type="role",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("role_id")))
@require_permission(Permissions.ROLES_EDIT)
def update_role(role_id):
    schema = UpdateRoleSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = RBACService.update_role(
        role_id=role_id,
        name=data.get("name"),
        description=data.get("description"),
        permission_ids=data.get("permission_ids"),
    )
    return jsonify(RoleDetailResponseSchema().dump(result)), 200


@rbac_bp.route("/roles/<uuid:role_id>", methods=["DELETE"])
@audit_action("roles.delete", resource_type="role",
              get_resource_id=lambda kwargs, resp: str(kwargs.get("role_id")))
@require_permission(Permissions.ROLES_DELETE)
def delete_role(role_id):
    result = RBACService.delete_role(role_id)
    return jsonify(result), 200


# ── Permission endpoints ──────────────────────────────────────────────────


@rbac_bp.route("/permissions", methods=["GET"])
@require_permission(Permissions.PERMISSIONS_VIEW)
def list_permissions():
    resource = request.args.get("resource")
    result = RBACService.list_permissions(resource=resource)
    return jsonify(PermissionListResponseSchema().dump(result)), 200


# ── User role endpoints ──────────────────────────────────────────────────


@rbac_bp.route("/users/<uuid:user_id>/roles", methods=["GET"])
@require_permission(Permissions.USERS_VIEW)
def get_user_roles(user_id):
    result = RBACService.get_user_roles(user_id)
    return jsonify(UserRolesResponseSchema().dump(result)), 200


@rbac_bp.route("/users/<uuid:user_id>/roles", methods=["POST"])
@audit_action("roles.assign", resource_type="user_role")
@require_permission(Permissions.USERS_MANAGE_ROLES)
def assign_role(user_id):
    schema = AssignRoleSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = RBACService.assign_role_to_user(
        user_id=user_id,
        role_id=data["role_id"],
    )
    return jsonify(UserRolesResponseSchema().dump(result)), 201


@rbac_bp.route("/users/<uuid:user_id>/roles/<uuid:role_id>", methods=["DELETE"])
@audit_action("roles.revoke", resource_type="user_role")
@require_permission(Permissions.USERS_MANAGE_ROLES)
def revoke_role(user_id, role_id):
    result = RBACService.revoke_role_from_user(
        user_id=user_id,
        role_id=role_id,
    )
    return jsonify(result), 200
