"""Authentication schemas for request/response validation."""

from marshmallow import Schema, fields, validate


# ── Request schemas ─────────────────────────────────────────────────────


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)


class BootstrapSchema(Schema):
    """Bootstrap first user."""
    email = fields.Email(required=True)
    password = fields.String(
        required=True, load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters"),
    )
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=100))


class RefreshTokenSchema(Schema):
    refresh_token = fields.String(required=True, load_only=True)


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.String(required=True)
    password = fields.String(
        required=True, load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters"),
    )


class VerifyEmailSchema(Schema):
    token = fields.String(required=True)


class AcceptInviteSchema(Schema):
    token = fields.String(required=True)
    first_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    password = fields.String(
        required=True, load_only=True,
        validate=validate.Length(min=8, error="Password must be at least 8 characters"),
    )


# ── Response schemas ────────────────────────────────────────────────────


class TokenResponseSchema(Schema):
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(dump_default="Bearer")
    expires_in = fields.Integer()


class UserResponseSchema(Schema):
    id = fields.UUID()
    email = fields.Email()
    first_name = fields.String()
    last_name = fields.String()
    is_active = fields.Boolean()
    created_at = fields.DateTime()


class AuthResponseSchema(Schema):
    """Full auth response: tokens + user."""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(dump_default="Bearer")
    expires_in = fields.Integer()
    user = fields.Nested(UserResponseSchema)


class MessageResponseSchema(Schema):
    message = fields.String(required=True)


