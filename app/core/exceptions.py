"""Custom API exceptions with structured JSON error responses."""


class APIError(Exception):
    """Base exception for all API errors."""

    status_code = 500
    error_code = "internal_error"

    def __init__(self, message="Internal server error", status_code=None, error_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code

    def to_dict(self):
        return {"error": self.error_code, "message": self.message}


# ── 401 Authentication ───────────────────────────────────────────────────


class UnauthorizedError(APIError):
    status_code = 401
    error_code = "unauthorized"

    def __init__(self, message="Authentication required"):
        super().__init__(message)


class InvalidCredentialsError(APIError):
    status_code = 401
    error_code = "invalid_credentials"

    def __init__(self, message="Invalid email or password"):
        super().__init__(message)


class TokenExpiredError(APIError):
    status_code = 401
    error_code = "token_expired"

    def __init__(self, message="Token has expired"):
        super().__init__(message)


class InvalidTokenError(APIError):
    status_code = 401
    error_code = "invalid_token"

    def __init__(self, message="Invalid token"):
        super().__init__(message)


class TokenRevokedError(APIError):
    status_code = 401
    error_code = "token_revoked"

    def __init__(self, message="Token has been revoked"):
        super().__init__(message)


# ── 403 Authorization ────────────────────────────────────────────────────


class ForbiddenError(APIError):
    status_code = 403
    error_code = "forbidden"

    def __init__(self, message="You do not have permission to perform this action"):
        super().__init__(message)


class InsufficientPermissionsError(APIError):
    status_code = 403
    error_code = "insufficient_permissions"

    def __init__(self, message="Insufficient permissions", required_permission=None):
        if required_permission:
            message = f"Missing required permission: {required_permission}"
        super().__init__(message)
        self.required_permission = required_permission


class UserInactiveError(APIError):
    status_code = 403
    error_code = "user_inactive"

    def __init__(self, message="User account is inactive"):
        super().__init__(message)


# ── 404 Not Found ────────────────────────────────────────────────────────


class NotFoundError(APIError):
    status_code = 404
    error_code = "not_found"

    def __init__(self, message="Resource not found"):
        super().__init__(message)


class UserNotFoundError(NotFoundError):
    error_code = "user_not_found"

    def __init__(self, message="User not found"):
        super().__init__(message)


class RoleNotFoundError(NotFoundError):
    error_code = "role_not_found"

    def __init__(self, message="Role not found"):
        super().__init__(message)


# ── 400 Validation ───────────────────────────────────────────────────────


class ValidationError(APIError):
    status_code = 400
    error_code = "validation_error"

    def __init__(self, message="Validation failed", errors=None):
        super().__init__(message)
        self.errors = errors or {}

    def to_dict(self):
        result = super().to_dict()
        if self.errors:
            result["errors"] = self.errors
        return result


class BadRequestError(APIError):
    status_code = 400
    error_code = "bad_request"

    def __init__(self, message="Bad request"):
        super().__init__(message)


# ── 409 Conflict ─────────────────────────────────────────────────────────


class ConflictError(APIError):
    status_code = 409
    error_code = "conflict"

    def __init__(self, message="Resource conflict"):
        super().__init__(message)


class DuplicateResourceError(ConflictError):
    error_code = "duplicate_resource"

    def __init__(self, message="Resource already exists"):
        super().__init__(message)
