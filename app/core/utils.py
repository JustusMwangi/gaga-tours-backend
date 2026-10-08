"""JWT utilities for token generation, decoding, and validation.

Uses PyJWT directly (not Flask-JWT-Extended) for full control over
token claims.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from flask import current_app


class JWTError(Exception):
    pass


class TokenExpiredError(JWTError):
    pass


class InvalidTokenError(JWTError):
    pass


EAT = timezone(timedelta(hours=3))
"""Africa/Nairobi (EAT, UTC+3) — used when frontend sends naive datetimes."""


def generate_access_token(user_id, extra_claims=None):
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(seconds=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"])
    payload = {
        "jti": str(uuid4()),
        "user_id": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
    )


def generate_refresh_token(user_id):
    now = datetime.now(timezone.utc)
    expires_delta = timedelta(seconds=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"])
    payload = {
        "jti": str(uuid4()),
        "user_id": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config.get("JWT_ALGORITHM", "HS256"),
    )


def generate_token_pair(user_id, extra_claims=None):
    return {
        "access_token": generate_access_token(user_id, extra_claims),
        "refresh_token": generate_refresh_token(user_id),
    }


def decode_token(token):
    """Decode and validate a JWT token. Raises TokenExpiredError or InvalidTokenError."""
    try:
        return jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config.get("JWT_ALGORITHM", "HS256")],
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {e}")


def get_token_payload(token):
    """Extract payload without verifying expiry (for logout from expired tokens)."""
    try:
        return jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config.get("JWT_ALGORITHM", "HS256")],
            options={"verify_exp": False},
        )
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {e}")


def verify_token_type(token, expected_type):
    """Decode token and verify it matches the expected type ('access' or 'refresh')."""
    payload = decode_token(token)
    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected {expected_type} token, got {payload.get('type')}")
    return payload
