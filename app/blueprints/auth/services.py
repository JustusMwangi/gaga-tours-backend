"""Authentication service — business logic for login, register, tokens, etc."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from flask import current_app

from app.blueprints.auth.models import (
    BlacklistedToken,
    EmailVerificationToken,
    PasswordResetToken,
)
from app.blueprints.auth.repositories import (
    BlacklistedTokenRepository,
    InvitationRepository,
    PasswordResetTokenRepository,
    RevocationRepository,
    VerificationTokenRepository,
)
from app.blueprints.rbac.models import (
    Permission,
    Role,
    UserRole,
)
from app.blueprints.rbac.repositories import (
    PermissionRepository,
    RoleRepository,
    UserRoleRepository,
)
from app.blueprints.settings.models import AppSettings
from app.blueprints.users.models import User
from app.blueprints.users.repositories import UserRepository
from app.core.constants import ALL_PERMISSIONS, DEFAULT_ROLES
from app.core.exceptions import (
    BadRequestError,
    DuplicateResourceError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from app.core.utils import (
    InvalidTokenError as JWTInvalidTokenError,
    TokenExpiredError as JWTTokenExpiredError,
    generate_token_pair,
    get_token_payload,
    verify_token_type,
)
from app.extensions import db

logger = logging.getLogger(__name__)


class AuthService:
    """Static methods for all authentication operations."""

    # ── Login ────────────────────────────────────────────────────────

    @staticmethod
    def login(email: str, password: str) -> dict:
        user_repo = UserRepository(db.session)

        user = user_repo.find_by_email(email)
        if not user or not user.check_password(password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError("Account is inactive")

        tokens = generate_token_pair(user.id)

        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "user": user,
        }

    # ── Register ─────────────────────────────────────────────────────

    @staticmethod
    def register(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> dict:
        user_repo = UserRepository(db.session)
        invitation_repo = InvitationRepository(db.session)
        verification_repo = VerificationTokenRepository(db.session)

        email = email.lower()
        existing_user = user_repo.find_by_email(email)

        if existing_user:
            if existing_user.is_active:
                raise DuplicateResourceError("Email already registered")

            # Clean up orphaned invitations
            invitation_repo.delete_by_email(email)

            # Reactivate existing user with new credentials
            existing_user.first_name = first_name
            existing_user.last_name = last_name
            existing_user.set_password(password)
            existing_user.is_active = True
            existing_user.email_verified = False
            existing_user.email_verified_at = None
            db.session.flush()

        if existing_user:
            user = existing_user
        else:
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash="temp",
            )
            user.set_password(password)
            user_repo.create(user)

        # Seed default roles + assign Owner
        AuthService._seed_roles(user)

        # Create app settings singleton if not exists
        if not db.session.query(AppSettings).first():
            db.session.add(AppSettings())

        # Email verification token
        verification_repo.create(EmailVerificationToken.make(user.id))

        db.session.commit()

        # Queue verification email
        AuthService._send_verification_email_async(user)

        tokens = generate_token_pair(user.id)
        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "user": user,
        }

    # ── Role seeding ─────────────────────────────────────────────────

    @staticmethod
    def _seed_roles(user: User):
        """Seed permissions + default roles, assign Owner to user."""
        perm_repo = PermissionRepository(db.session)
        role_repo = RoleRepository(db.session)
        user_role_repo = UserRoleRepository(db.session)

        AuthService._seed_permissions(perm_repo)

        all_permissions = perm_repo.find_all()
        permissions_map = {p.name: p for p in all_permissions}

        owner_role = None

        for role_name, role_def in DEFAULT_ROLES.items():
            # Skip if role already exists (idempotent)
            existing = role_repo.find_by_name(role_name)
            if existing:
                if role_name == "Owner":
                    owner_role = existing
                continue

            new_role = role_repo.create(Role(
                name=role_name,
                description=role_def["description"],
                is_system_role=role_def["is_system_role"],
            ))

            for perm_name in role_def["permissions"]:
                perm_obj = permissions_map.get(perm_name)
                if perm_obj:
                    role_repo.add_permission(new_role.id, perm_obj.id)

            if role_name == "Owner":
                owner_role = new_role

        if owner_role:
            user_role_repo.create(UserRole(
                user_id=user.id,
                role_id=owner_role.id,
                assigned_at=datetime.now(timezone.utc),
                assigned_by=user.id,
            ))

    @staticmethod
    def _seed_permissions(perm_repo: PermissionRepository = None):
        """Ensure all permissions from ALL_PERMISSIONS exist in DB (idempotent)."""
        if perm_repo is None:
            perm_repo = PermissionRepository(db.session)

        existing = perm_repo.get_existing_names()

        for perm_def in ALL_PERMISSIONS:
            if perm_def["name"] not in existing:
                perm_repo.create(Permission(
                    name=perm_def["name"],
                    resource=perm_def["resource"],
                    action=perm_def["action"],
                    description=perm_def.get("description"),
                ))

        perm_repo.flush()

    # ── Refresh ──────────────────────────────────────────────────────

    @staticmethod
    def refresh_token(refresh_token: str) -> dict:
        try:
            payload = verify_token_type(refresh_token, "refresh")
        except JWTTokenExpiredError:
            raise TokenExpiredError("Refresh token has expired")
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(str(e))

        user_id = payload.get("user_id")
        jti = payload.get("jti")

        if not user_id:
            raise InvalidTokenError("Token missing required claims")

        blacklist_repo = BlacklistedTokenRepository(db.session)
        if jti and blacklist_repo.is_blacklisted(jti):
            raise InvalidTokenError("Token has been revoked")

        user_repo = UserRepository(db.session)

        user = user_repo.find_by_id(UUID(user_id))
        if not user or not user.is_active:
            raise InvalidTokenError("User no longer valid")

        tokens = generate_token_pair(user.id)
        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
        }

    # ── Bootstrap ────────────────────────────────────────────────────

    @staticmethod
    def needs_bootstrap() -> bool:
        user_repo = UserRepository(db.session)
        return user_repo.count() == 0

    @staticmethod
    def bootstrap(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> dict:
        user_repo = UserRepository(db.session)
        if user_repo.count() > 0:
            raise BadRequestError("System already bootstrapped")

        result = AuthService.register(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Promote first user to superadmin
        result["user"].is_superadmin = True
        db.session.commit()

        return result

    # ── Logout ───────────────────────────────────────────────────────

    @staticmethod
    def logout(token: str) -> dict:
        try:
            payload = get_token_payload(token)
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(str(e))

        jti = payload.get("jti")
        user_id = payload.get("user_id")
        token_type = payload.get("type", "access")
        exp = payload.get("exp")

        if not jti:
            return {"message": "Logged out successfully"}

        if not user_id:
            raise InvalidTokenError("Token missing user_id claim")

        if isinstance(exp, (int, float)):
            expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
        else:
            expires_at = exp or datetime.now(timezone.utc)

        blacklist_repo = BlacklistedTokenRepository(db.session)
        blacklist_repo.create(BlacklistedToken(
            jti=jti,
            user_id=UUID(user_id),
            token_type=token_type,
            expires_at=expires_at,
            reason="logout",
        ))
        db.session.commit()

        return {"message": "Logged out successfully"}

    @staticmethod
    def logout_all(user_id: UUID) -> dict:
        revocation_repo = RevocationRepository(db.session)
        revocation_repo.revoke_all(user_id)
        db.session.commit()
        return {"message": "All sessions have been logged out"}

    # ── Password reset ───────────────────────────────────────────────

    @staticmethod
    def forgot_password(email: str) -> dict:
        user_repo = UserRepository(db.session)
        reset_repo = PasswordResetTokenRepository(db.session)

        email = email.lower()
        user = user_repo.find_by_email(email)

        if user and user.is_active:
            reset_repo.invalidate_user_tokens(user.id)
            reset_token = PasswordResetToken.make(user.id)
            reset_repo.create(reset_token)
            db.session.commit()

            frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
            reset_url = f"{frontend_url}/reset-password?token={reset_token.token}"

            try:
                from app.core.tasks import send_password_reset_email_task
                send_password_reset_email_task.delay(to=user.email, reset_url=reset_url)
            except Exception:
                logger.info("Password reset link for %s: %s", user.email, reset_url)

        return {
            "message": "If an account with that email exists, a password reset link has been sent."
        }

    @staticmethod
    def reset_password(token: str, new_password: str) -> dict:
        user_repo = UserRepository(db.session)
        reset_repo = PasswordResetTokenRepository(db.session)
        revocation_repo = RevocationRepository(db.session)

        reset_token = reset_repo.find_valid(token)
        if not reset_token:
            raise InvalidTokenError("Invalid or expired password reset token")

        user = user_repo.find_by_id(reset_token.user_id)
        if not user or not user.is_active:
            raise InvalidTokenError("Invalid or expired password reset token")

        user.set_password(new_password)
        reset_token.mark_used()

        # Revoke all sessions for security
        revocation_repo.revoke_all(user.id)

        db.session.commit()

        return {"message": "Password has been reset successfully"}

    # ── Email verification ───────────────────────────────────────────

    @staticmethod
    def send_verification_email(user_id: UUID) -> dict:
        user_repo = UserRepository(db.session)
        verification_repo = VerificationTokenRepository(db.session)

        user = user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError()
        if user.email_verified:
            raise BadRequestError("Email is already verified")

        verification_repo.invalidate_user_tokens(user.id)
        verification_token = EmailVerificationToken.make(user.id)
        verification_repo.create(verification_token)
        db.session.commit()

        AuthService._send_verification_email_async(user, verification_token)

        return {"message": "Verification email sent"}

    @staticmethod
    def verify_email(token: str) -> dict:
        user_repo = UserRepository(db.session)
        verification_repo = VerificationTokenRepository(db.session)

        verification_token = verification_repo.find_by_token(token)
        if not verification_token:
            raise InvalidTokenError("Invalid or expired verification token")

        user = user_repo.find_by_id(verification_token.user_id)
        if not user:
            raise InvalidTokenError("Invalid or expired verification token")

        # Idempotent: return success if already verified
        if user.email_verified:
            return {"message": "Email already verified"}

        if not verification_token.is_valid:
            raise InvalidTokenError("Invalid or expired verification token")

        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        verification_token.mark_used()
        db.session.commit()

        return {"message": "Email verified successfully"}

    @staticmethod
    def resend_verification(user_id: UUID) -> dict:
        return AuthService.send_verification_email(user_id)

    # ── Invitations ──────────────────────────────────────────────────

    @staticmethod
    def accept_invite(
        token: str, first_name: str, last_name: str, password: str,
    ) -> dict:
        user_repo = UserRepository(db.session)
        role_repo = RoleRepository(db.session)
        user_role_repo = UserRoleRepository(db.session)
        invitation_repo = InvitationRepository(db.session)

        invitation = invitation_repo.find_valid(token)
        if not invitation:
            raise InvalidTokenError("Invalid or expired invitation")

        email = invitation.email

        existing_user = user_repo.find_by_email(email)

        if existing_user:
            if existing_user.is_active:
                raise DuplicateResourceError("This email is already registered")

            user = existing_user
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.set_password(password)
            user.is_active = True
            if not user.email_verified:
                user.email_verified = True
                user.email_verified_at = datetime.now(timezone.utc)
        else:
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash="temp",
                email_verified=True,
                email_verified_at=datetime.now(timezone.utc),
            )
            user.set_password(password)
            user_repo.create(user)

        # Assign role if specified
        if invitation.role_id:
            role = role_repo.find_by_id(invitation.role_id)
            if role:
                user_role_repo.create(UserRole(
                    user_id=user.id,
                    role_id=invitation.role_id,
                    assigned_at=datetime.now(timezone.utc),
                    assigned_by=invitation.invited_by,
                ))

        invitation.mark_accepted()
        db.session.commit()

        tokens = generate_token_pair(user.id)
        return {
            **tokens,
            "expires_in": current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
            "user": user,
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _send_verification_email_async(user, verification_token=None):
        """Attempt async email; fall back to logging the URL."""
        if verification_token is None:
            verification_repo = VerificationTokenRepository(db.session)
            verification_token = verification_repo.find_latest_unused(user.id)

        if not verification_token:
            return

        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
        verify_url = f"{frontend_url}/verify-email?token={verification_token.token}"

        try:
            from app.core.tasks import send_verification_email_task
            send_verification_email_task.delay(to=user.email, verify_url=verify_url)
        except Exception:
            logger.info("Verification link for %s: %s", user.email, verify_url)
