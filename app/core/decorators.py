"""Route decorators for authentication and authorization.

Decorators:
- @jwt_required: Ensures valid JWT token (explicit complement to AuthMiddleware)
- @require_permission: Checks user has specific permission(s)
- @audit_action: Auto-logs audit events after successful requests

Utility functions:
- get_user_permissions(): Collects permission names for a user
- has_permission() / has_any_permission(): Check permissions in business logic
"""

import logging
from functools import wraps
from typing import Callable, List, Optional, Union

from flask import g

from app.core.exceptions import (
    ForbiddenError,
    InsufficientPermissionsError,
    UnauthorizedError,
)
from app.extensions import db

logger = logging.getLogger(__name__)


# ── Authentication decorators ────────────────────────────────────────────


def jwt_required(f):
    """Ensure the request has a valid JWT token.

    AuthMiddleware already handles JWT validation and sets g.user,
    so this decorator mainly serves as explicit documentation that
    an endpoint requires authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, "user") or g.user is None:
            raise UnauthorizedError()
        return f(*args, **kwargs)
    return decorated_function


# ── Permission helpers ───────────────────────────────────────────────────


def get_user_permissions(user_id) -> set:
    """Get all permission names for a user.

    Returns:
        Set of permission name strings (e.g. {"users.create", "roles.view"}).
    """
    from app.blueprints.rbac.repositories import UserRoleRepository

    repo = UserRoleRepository(db.session)
    return repo.get_user_permissions(user_id)


def has_permission(permission: str) -> bool:
    """Check if current user has a specific permission.

    Utility for checking permissions inside business logic (not as a decorator).
    """
    if not hasattr(g, "user") or g.user is None:
        return False

    user_permissions = get_user_permissions(user_id=g.user.id)
    return permission in user_permissions


def has_any_permission(permissions: List[str]) -> bool:
    """Check if current user has any of the specified permissions."""
    if not hasattr(g, "user") or g.user is None:
        return False

    user_permissions = get_user_permissions(user_id=g.user.id)
    return any(p in user_permissions for p in permissions)


# ── Permission decorator ────────────────────────────────────────────────


def require_permission(permission: Union[str, List[str]], require_all: bool = False):
    """Ensure user has required permission(s).

    Args:
        permission: Permission name (e.g. "users.create") or list of names.
        require_all: If True, user must have ALL permissions. If False (default),
                     user needs at least ONE.

    Usage::

        @require_permission("users.create")
        def create_user(): ...

        @require_permission(["users.create", "users.edit"])
        def manage_user(): ...

        @require_permission(["admin.access", "users.delete"], require_all=True)
        def admin_delete(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "user") or g.user is None:
                raise UnauthorizedError()

            # Superadmins bypass permission checks
            if g.user.is_superadmin:
                return f(*args, **kwargs)

            permissions = [permission] if isinstance(permission, str) else permission

            user_permissions = get_user_permissions(user_id=g.user.id)

            if require_all:
                missing = [p for p in permissions if p not in user_permissions]
                if missing:
                    raise InsufficientPermissionsError(
                        f"Missing required permissions: {', '.join(missing)}"
                    )
            else:
                if not any(p in user_permissions for p in permissions):
                    raise InsufficientPermissionsError(
                        required_permission=permissions[0] if len(permissions) == 1 else None
                    )

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ── Audit decorator ─────────────────────────────────────────────────────


def audit_action(
    action: str,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[Callable] = None,
    get_old_values: Optional[Callable] = None,
    get_new_values: Optional[Callable] = None,
    description: Optional[Union[str, Callable]] = None,
):
    """Auto-log an audit event after a successful endpoint response.

    Captures request context (IP, User-Agent) and extracts relevant data
    from the response. Audit failures are logged but never fail the request.

    Args:
        action: Action identifier (e.g. "users.create", "roles.update").
        resource_type: Defaults to first part of action (e.g. "users").
        get_resource_id: ``(kwargs, response_data) -> id``
        get_old_values: ``(kwargs, response_data) -> dict``
        get_new_values: ``(kwargs, response_data) -> dict``
        description: Static string or ``(kwargs, response_data) -> str``.

    Usage::

        @audit_action("users.create", resource_type="user")
        @require_permission("users.create")
        def create_user(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)

            try:
                if not hasattr(g, "user") or g.user is None:
                    return result

                # Parse response
                response_data = None
                status_code = 200

                if isinstance(result, tuple):
                    response_obj = result[0]
                    status_code = result[1] if len(result) > 1 else 200
                else:
                    response_obj = result

                if status_code >= 400:
                    return result

                if hasattr(response_obj, "get_json"):
                    try:
                        response_data = response_obj.get_json()
                    except Exception:
                        response_data = None

                # Extract resource_id
                res_id = None
                if get_resource_id:
                    try:
                        res_id = get_resource_id(kwargs, response_data)
                    except Exception:
                        pass
                elif response_data and isinstance(response_data, dict):
                    res_id = response_data.get("id")

                if res_id and isinstance(res_id, str):
                    from uuid import UUID as UUID_type
                    try:
                        res_id = UUID_type(res_id)
                    except ValueError:
                        res_id = None

                # Extract old/new values
                old_vals = None
                new_vals = None

                if get_old_values:
                    try:
                        old_vals = get_old_values(kwargs, response_data)
                    except Exception:
                        pass

                if get_new_values:
                    try:
                        new_vals = get_new_values(kwargs, response_data)
                    except Exception:
                        pass
                elif response_data and isinstance(response_data, dict):
                    sensitive = {"password", "password_hash", "token", "access_token"}
                    new_vals = {k: v for k, v in response_data.items() if k not in sensitive}

                res_type = resource_type or action.split(".")[0]

                desc = description
                if callable(desc):
                    try:
                        desc = desc(kwargs, response_data)
                    except Exception:
                        desc = None

                from app.blueprints.audit.services import AuditService

                AuditService.log_action(
                    action=action,
                    resource_type=res_type,
                    resource_id=res_id,
                    old_values=old_vals,
                    new_values=new_vals,
                    description=desc,
                )

            except Exception as e:
                logger.error("Audit logging failed for action '%s': %s", action, e)

            return result
        return decorated_function
    return decorator
