"""Authentication routes."""

from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError

from app.blueprints.auth.schemas import (
    AcceptInviteSchema,
    AuthResponseSchema,
    BootstrapSchema,
    ForgotPasswordSchema,
    LoginSchema,
    MessageResponseSchema,
    RefreshTokenSchema,
    ResetPasswordSchema,
    TokenResponseSchema,
    VerifyEmailSchema,
)
from app.blueprints.auth.services import AuthService
from app.core.decorators import audit_action, jwt_required
from app.core.exceptions import ValidationError as AppValidationError
from app.core.middleware import get_token_from_header
from app.extensions import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Login ──────────────────────────────────────────────────────────────


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    schema = LoginSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.login(
        email=data["email"],
        password=data["password"],
    )

    return jsonify(AuthResponseSchema().dump(result)), 200


# ── Bootstrap ──────────────────────────────────────────────────────────


@auth_bp.route("/bootstrap", methods=["GET"])
def check_bootstrap():
    needs_bootstrap = AuthService.needs_bootstrap()
    return jsonify({"needs_bootstrap": needs_bootstrap}), 200


@auth_bp.route("/bootstrap", methods=["POST"])
def bootstrap():
    schema = BootstrapSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.bootstrap(
        email=data["email"],
        password=data["password"],
        first_name=data["first_name"],
        last_name=data["last_name"],
    )

    return jsonify(AuthResponseSchema().dump(result)), 201


# ── Token refresh ───────────────────────────────────────────────────────


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    schema = RefreshTokenSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.refresh_token(refresh_token=data["refresh_token"])
    return jsonify(TokenResponseSchema().dump(result)), 200


# ── Logout ──────────────────────────────────────────────────────────────


@auth_bp.route("/logout", methods=["POST"])
@jwt_required
@audit_action("auth.logout", resource_type="session")
def logout():
    token = get_token_from_header()
    result = AuthService.logout(token=token)
    return jsonify(MessageResponseSchema().dump(result)), 200


@auth_bp.route("/logout-all", methods=["POST"])
@jwt_required
@audit_action("auth.logout_all", resource_type="session")
def logout_all():
    result = AuthService.logout_all(user_id=g.user.id)
    return jsonify(MessageResponseSchema().dump(result)), 200


# ── Password reset ──────────────────────────────────────────────────────


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per minute")
def forgot_password():
    schema = ForgotPasswordSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.forgot_password(email=data["email"])
    return jsonify(MessageResponseSchema().dump(result)), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    schema = ResetPasswordSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.reset_password(
        token=data["token"],
        new_password=data["password"],
    )
    return jsonify(MessageResponseSchema().dump(result)), 200


# ── Email verification ──────────────────────────────────────────────────


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    schema = VerifyEmailSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.verify_email(token=data["token"])
    return jsonify(MessageResponseSchema().dump(result)), 200


@auth_bp.route("/resend-verification", methods=["POST"])
@jwt_required
def resend_verification():
    result = AuthService.resend_verification(user_id=g.user.id)
    return jsonify(MessageResponseSchema().dump(result)), 200


# ── Invitations ─────────────────────────────────────────────────────────


@auth_bp.route("/accept-invite", methods=["POST"])
def accept_invite():
    schema = AcceptInviteSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuthService.accept_invite(
        token=data["token"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        password=data["password"],
    )

    return jsonify(AuthResponseSchema().dump(result)), 201
