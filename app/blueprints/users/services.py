"""UserService: CRUD operations for users."""

import logging
import math
from datetime import datetime, timezone
from uuid import UUID

from flask import current_app, g

from app.blueprints.auth.models import UserInvitation
from app.blueprints.auth.repositories import InvitationRepository
from app.blueprints.rbac.models import UserRole
from app.blueprints.rbac.repositories import (
    RoleRepository,
    UserRoleRepository,
)
from app.blueprints.users.repositories import UserRepository
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UserNotFoundError,
    ValidationError,
)
from app.extensions import db

logger = logging.getLogger(__name__)


class UserService:
    """Static methods for all user management operations."""

    # ── GET /me ─────────────────────────────────────────────────────

    @staticmethod
    def get_current_user(user_id: UUID) -> dict:
        """Return the current user's profile with roles."""
        user_repo = UserRepository(db.session)
        user_role_repo = UserRoleRepository(db.session)

        user = user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        user_roles = user_role_repo.find_by_user(user_id)
        role_repo = RoleRepository(db.session)
        roles = []
        for ur in user_roles:
            role = role_repo.find_by_id(ur.role_id)
            if role:
                permissions = role_repo.get_permission_names(role.id)
                roles.append({
                    "id": role.id,
                    "name": role.name,
                    "permissions": permissions,
                })

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": roles,
        }

    # ── PUT /me ─────────────────────────────────────────────────────

    @staticmethod
    def update_profile(user_id: UUID, data: dict) -> dict:
        """Update the current user's own profile."""
        user_repo = UserRepository(db.session)
        user = user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        password_changed = False
        if data.get("new_password"):
            if not data.get("current_password"):
                raise ValidationError(
                    "Current password is required to set a new password",
                    errors={"current_password": ["This field is required"]},
                )
            if not user.check_password(data["current_password"]):
                raise ValidationError(
                    "Current password is incorrect",
                    errors={"current_password": ["Incorrect password"]},
                )
            user.set_password(data["new_password"])
            password_changed = True

        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "phone" in data:
            user.phone = data["phone"]

        db.session.commit()

        if password_changed:
            from app.blueprints.notifications.services import NotificationService
            NotificationService.notify_password_changed(user_id=user_id)

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    # ── GET / ───────────────────────────────────────────────────────

    @staticmethod
    def list_users(page: int = 1, per_page: int = 20,
                   search: str = None, is_active: bool = None) -> dict:
        """List paginated users."""
        user_repo = UserRepository(db.session)

        users, total = user_repo.list_users(
            page=page,
            per_page=per_page,
            search=search,
            is_active=is_active,
        )

        return {
            "users": users,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    # ── GET /<id> ───────────────────────────────────────────────────

    @staticmethod
    def get_user_detail(user_id: UUID) -> dict:
        """Return a user's detail with roles."""
        user_repo = UserRepository(db.session)

        user = user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        user_role_repo = UserRoleRepository(db.session)
        role_repo = RoleRepository(db.session)

        user_roles = user_role_repo.find_by_user(user_id)
        roles = []
        for ur in user_roles:
            role = role_repo.find_by_id(ur.role_id)
            if role:
                roles.append({
                    "id": role.id,
                    "name": role.name,
                })

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": roles,
        }

    # ── POST /invite ────────────────────────────────────────────────

    @staticmethod
    def invite_user(invited_by: UUID, data: dict) -> dict:
        """Create an invitation to join the application."""
        email = data["email"].lower()
        role_id = data.get("role_id")

        invitation_repo = InvitationRepository(db.session)
        user_repo = UserRepository(db.session)

        # Check if user already exists and is active
        existing_user = user_repo.find_by_email(email)
        if existing_user and existing_user.is_active:
            raise ConflictError("User is already a member")

        # Check for pending invitation
        pending = invitation_repo.find_pending(email)
        if pending:
            raise ConflictError("A pending invitation already exists for this email")

        # Validate role exists
        if role_id:
            role_repo = RoleRepository(db.session)
            role = role_repo.find_by_id(role_id)
            if not role:
                raise ValidationError(
                    "Invalid role",
                    errors={"role_id": ["Role not found"]},
                )

        invitation = UserInvitation.make(
            email=email,
            invited_by=invited_by,
            role_id=role_id,
        )
        invitation_repo.create(invitation)
        db.session.commit()

        # Build invite URL
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
        invite_url = f"{frontend_url}/accept-invite?token={invitation.token}"

        # Send invitation email
        try:
            from app.core.tasks import send_invitation_email_task

            inviter = user_repo.find_by_id(invited_by)
            inviter_name = f"{inviter.first_name} {inviter.last_name}" if inviter else "Someone"

            from app.blueprints.settings.models import AppSettings
            settings = db.session.query(AppSettings).first()
            app_name = settings.app_name if settings else "our application"

            send_invitation_email_task.delay(
                to=email,
                inviter_name=inviter_name,
                tenant_name=app_name,
                invite_url=invite_url,
            )
        except Exception:
            logger.info("Invitation link for %s: %s", email, invite_url)

        # Notify users with user management permission
        from app.blueprints.notifications.services import NotificationService
        NotificationService.notify_users_with_permission(
            permission="users.manage",
            title="User Invited",
            message=f"{email} has been invited to join the team.",
            category="team", type="info",
            data={"action": "view_users"},
            exclude_user_id=invited_by,
        )

        return {
            "id": invitation.id,
            "email": invitation.email,
            "token": invitation.token,
            "role_id": invitation.role_id,
            "expires_at": invitation.expires_at,
            "invite_url": invite_url,
        }

    # ── PUT /<id> ───────────────────────────────────────────────────

    @staticmethod
    def admin_update_user(user_id: UUID, admin_user_id: UUID, data: dict) -> dict:
        """Admin update of a user's profile and roles."""
        user_repo = UserRepository(db.session)

        user = user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        # Prevent deactivating yourself
        if user_id == admin_user_id and data.get("is_active") is False:
            raise BadRequestError("You cannot deactivate your own account")

        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "phone" in data:
            user.phone = data["phone"]
        if "is_active" in data:
            user.is_active = data["is_active"]

        # Update roles if provided
        if "role_ids" in data:
            user_role_repo = UserRoleRepository(db.session)
            role_repo = RoleRepository(db.session)

            user_role_repo.delete_all_for_user(user_id)

            for rid in data["role_ids"]:
                role = role_repo.find_by_id(rid)
                if not role:
                    continue
                user_role_repo.create(UserRole(
                    user_id=user_id,
                    role_id=rid,
                    assigned_at=datetime.now(timezone.utc),
                    assigned_by=admin_user_id,
                ))

        db.session.commit()

        return UserService.get_user_detail(user_id)

    # ── DELETE /<id> ────────────────────────────────────────────────

    @staticmethod
    def deactivate_user(user_id: UUID, admin_user_id: UUID) -> dict:
        """Deactivate a user."""
        user_repo = UserRepository(db.session)

        user = user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if user_id == admin_user_id:
            raise BadRequestError("You cannot deactivate your own account")

        # Remove roles
        user_role_repo = UserRoleRepository(db.session)
        user_role_repo.delete_all_for_user(user_id)

        user.is_active = False
        db.session.commit()

        return {"message": "User has been deactivated"}
