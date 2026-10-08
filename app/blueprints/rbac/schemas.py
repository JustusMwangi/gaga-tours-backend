"""RBAC schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# -- Response schemas -------------------------------------------------------


class PermissionResponseSchema(Schema):
    """Single permission."""
    id = fields.UUID()
    name = fields.String()
    resource = fields.String()
    action = fields.String()
    description = fields.String()


class RoleResponseSchema(Schema):
    """Basic role info for list views."""
    id = fields.UUID()
    name = fields.String()
    description = fields.String()
    is_system_role = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class RoleDetailResponseSchema(RoleResponseSchema):
    """Role detail with permissions and user count."""
    permissions = fields.List(fields.Nested(PermissionResponseSchema))
    user_count = fields.Integer()


class RoleListResponseSchema(Schema):
    """Paginated role list response."""
    roles = fields.List(fields.Nested(RoleResponseSchema))
    total = fields.Integer()


class PermissionListResponseSchema(Schema):
    """Permission list response."""
    permissions = fields.List(fields.Nested(PermissionResponseSchema))
    total = fields.Integer()


class UserRoleResponseSchema(Schema):
    """Single user-role assignment."""
    id = fields.UUID()
    role_id = fields.UUID()
    role_name = fields.String(attribute="role.name")
    assigned_at = fields.DateTime()


class UserRolesResponseSchema(Schema):
    """All roles for a user."""
    user_id = fields.UUID()
    roles = fields.List(fields.Nested(UserRoleResponseSchema))


# -- Request schemas --------------------------------------------------------


class CreateRoleSchema(Schema):
    """POST /roles request body."""
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(load_default=None)
    permission_ids = fields.List(fields.UUID(), load_default=[])


class UpdateRoleSchema(Schema):
    """PUT /roles/<id> request body."""
    name = fields.String(validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    permission_ids = fields.List(fields.UUID())


class AssignRoleSchema(Schema):
    """POST /users/<user_id>/roles request body."""
    role_id = fields.UUID(required=True)
