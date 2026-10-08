"""Security middleware for access control.

AuthMiddleware — validates JWT and sets user context (g.user).
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from flask import g, request

logger = logging.getLogger(__name__)

from app.core.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    TokenRevokedError,
    UnauthorizedError,
    UserInactiveError,
    UserNotFoundError,
)
from app.core.utils import (
    InvalidTokenError as JWTInvalidTokenError,
    TokenExpiredError as JWTTokenExpiredError,
    decode_token,
)
from app.extensions import db


# ── Helpers ──────────────────────────────────────────────────────────────


def get_token_from_header():
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def load_user(user_id):
    """Load user from DB. Returns user."""
    from app.blueprints.users.repositories import UserRepository

    user_repo = UserRepository(db.session)

    user = user_repo.find_by_id(UUID(user_id))
    if not user:
        raise UserNotFoundError()
    if not user.is_active:
        raise UserInactiveError()

    return user


# ── AuthMiddleware ───────────────────────────────────────────────────────


class AuthMiddleware:
    """Validates JWT and establishes user context.

    Sets g.user on every authenticated request.
    """

    EXEMPT_PATHS = [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/bootstrap",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/accept-invite",
        "/health",
        "/health/db",
    ]

    EXEMPT_PREFIXES = [
        "/static/",
        "/api/v1/public/",
    ]

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)

    def is_exempt(self, path):
        if path in self.EXEMPT_PATHS:
            return True
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def before_request(self):
        if request.method == "OPTIONS":
            return None

        # Initialize context
        g.user = None

        if self.is_exempt(request.path):
            return None

        # Extract and validate token
        token = get_token_from_header()
        if not token:
            raise UnauthorizedError("Missing authorization header")

        try:
            payload = decode_token(token)
        except JWTTokenExpiredError:
            raise TokenExpiredError()
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(str(e))

        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")

        user_id = payload.get("user_id")
        jti = payload.get("jti")
        iat = payload.get("iat")

        if not user_id:
            raise InvalidTokenError("Token missing required claims")

        # Check single-token blacklist
        if jti:
            from app.blueprints.auth.repositories import BlacklistedTokenRepository
            blacklist_repo = BlacklistedTokenRepository(db.session)
            if blacklist_repo.is_blacklisted(jti):
                raise TokenRevokedError()

        # Check user-wide revocation (logout-all)
        if iat:
            from app.blueprints.auth.repositories import RevocationRepository
            revocation_repo = RevocationRepository(db.session)
            revocation_time = revocation_repo.get_revocation_time(UUID(user_id))
            if revocation_time:
                if isinstance(iat, (int, float)):
                    token_issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
                else:
                    token_issued_at = iat
                if revocation_time.tzinfo is None:
                    revocation_time = revocation_time.replace(tzinfo=timezone.utc)
                if token_issued_at < revocation_time:
                    raise TokenRevokedError("All sessions have been revoked")

        # Load user and set context
        g.user = load_user(user_id)
        return None


# ── Error handlers ───────────────────────────────────────────────────────


def register_error_handlers(app):
    from app.core.exceptions import APIError

    @app.errorhandler(APIError)
    def handle_api_error(error):
        from flask import jsonify
        if 400 <= error.status_code < 500:
            user_id = getattr(getattr(g, "user", None), "id", None)
            logger.warning(
                "APIError %s on %s %s (user=%s): %s | errors=%s",
                error.status_code,
                request.method,
                request.path,
                user_id,
                error.message,
                getattr(error, "errors", None),
            )
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        from flask import jsonify
        return jsonify({"error": "not_found", "message": "The requested resource was not found"}), 404

    @app.errorhandler(500)
    def handle_internal_error(error):
        from flask import jsonify
        return jsonify({"error": "internal_error", "message": "An internal server error occurred"}), 500


# ── Initialization ───────────────────────────────────────────────────────


def init_middleware(app):
    """Wire into create_app() after model imports."""
    register_error_handlers(app)
    AuthMiddleware(app)
