"""User management schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Nested response helpers ────────────────────────────────────────────


class RoleInfoSchema(Schema):
    id = fields.UUID()
    name = fields.String()
    permissions = fields.List(fields.String())


# ── Request schemas ────────────────────────────────────────────────────


class UpdateProfileSchema(Schema):
    """Self-update: name, phone, password."""
    first_name = fields.String(validate=validate.Length(min=1, max=100))
    last_name = fields.String(validate=validate.Length(min=1, max=100))
    phone = fields.String(validate=validate.Length(max=30), allow_none=True)
    current_password = fields.String(load_only=True)
    new_password = fields.String(
        load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters"),
    )


class UserListQuerySchema(Schema):
    """Query params for GET /users."""
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    is_active = fields.Boolean(load_default=None)


class InviteUserSchema(Schema):
    """Invite a user to the application."""
    email = fields.Email(required=True)
    role_id = fields.UUID(load_default=None)


class AdminUpdateUserSchema(Schema):
    """Admin update: roles, is_active."""
    first_name = fields.String(validate=validate.Length(min=1, max=100))
    last_name = fields.String(validate=validate.Length(min=1, max=100))
    phone = fields.String(validate=validate.Length(max=30), allow_none=True)
    is_active = fields.Boolean()
    role_ids = fields.List(fields.UUID())


# ── Response schemas ───────────────────────────────────────────────────


class UserResponseSchema(Schema):
    """Basic user info for list views."""
    id = fields.UUID()
    email = fields.Email()
    first_name = fields.String()
    last_name = fields.String()
    phone = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()


class UserDetailResponseSchema(Schema):
    """User detail with roles."""
    id = fields.UUID()
    email = fields.Email()
    first_name = fields.String()
    last_name = fields.String()
    phone = fields.String()
    is_active = fields.Boolean()
    email_verified = fields.Boolean()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    roles = fields.List(fields.Nested(RoleInfoSchema))


class UserListResponseSchema(Schema):
    """Paginated user list response."""
    users = fields.List(fields.Nested(UserResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class InvitationResponseSchema(Schema):
    """Response after creating an invitation."""
    id = fields.UUID()
    email = fields.Email()
    token = fields.String()
    role_id = fields.UUID(allow_none=True)
    expires_at = fields.DateTime()
    invite_url = fields.String()


