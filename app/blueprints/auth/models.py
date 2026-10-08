"""Auth models: token lifecycle (blacklist, revocation, reset, invitation, email verification).

Data access (queries, persistence, cleanup) lives in auth/repositories.py.
Models only define schema, properties, instance methods, and factory classmethods.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Index, String

from app.core.models import BaseModel, TimestampMixin, _uuid_column, _uuid_fk
from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


def _ensure_aware(dt):
    """Ensure a datetime is timezone-aware (SQLite returns naive datetimes)."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── BlacklistedToken ─────────────────────────────────────────────────────


class BlacklistedToken(db.Model):
    """Per-token blacklist for individual logout.

    Tokens are stored by JTI (JWT ID) for efficient lookup.
    Expired entries can be periodically cleaned up.
    """

    __tablename__ = "blacklisted_tokens"

    id = _uuid_column()
    jti = Column(String(36), nullable=False, unique=True, index=True)
    user_id = _uuid_fk("users.id")
    token_type = Column(String(20), nullable=False)  # 'access' or 'refresh'
    expires_at = Column(DateTime(timezone=True), nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reason = Column(String(50), nullable=True)  # 'logout', 'logout_all', 'security'

    __table_args__ = (
        Index("ix_blacklisted_tokens_expires_at", "expires_at"),
        Index("ix_blacklisted_tokens_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<BlacklistedToken {self.jti}>"


# ── UserTokenRevocation ──────────────────────────────────────────────────


class UserTokenRevocation(TimestampMixin, db.Model):
    """Per-user revocation timestamp for logout-all.

    Any token with iat < revoked_at is considered invalid.
    One row per user (upserted on each logout-all).
    """

    __tablename__ = "user_token_revocations"

    id = _uuid_column()
    user_id = _uuid_fk("users.id")
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", name="uq_user_token_revocation_user"),
    )

    def __repr__(self):
        return f"<UserTokenRevocation user={self.user_id}>"


# ── PasswordResetToken ───────────────────────────────────────────────────


class PasswordResetToken(db.Model):
    """Single-use password reset token. Expires after 1 hour."""

    __tablename__ = "password_reset_tokens"

    id = _uuid_column()
    token = Column(String(64), nullable=False, unique=True, index=True)
    user_id = _uuid_fk("users.id")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_expires_at", "expires_at"),
    )

    user = db.relationship("User", back_populates="password_reset_tokens")

    @property
    def is_expired(self):
        return _utcnow() > _ensure_aware(self.expires_at)

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used

    def mark_used(self):
        self.used_at = _utcnow()

    @classmethod
    def make(cls, user_id, expires_in_hours=1):
        """Factory: create an unsaved instance with generated token."""
        return cls(
            token=secrets.token_urlsafe(48),
            user_id=user_id,
            expires_at=_utcnow() + timedelta(hours=expires_in_hours),
        )

    def __repr__(self):
        return f"<PasswordResetToken user={self.user_id}>"


# ── UserInvitation ───────────────────────────────────────────────────────


class UserInvitation(db.Model):
    """Invitation to join the application. Expires after 7 days, single-use."""

    __tablename__ = "user_invitations"

    id = _uuid_column()
    token = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    role_id = _uuid_fk("roles.id", nullable=True)
    invited_by = _uuid_fk("users.id")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_user_invitations_email", "email"),
        Index("ix_user_invitations_expires_at", "expires_at"),
    )

    @property
    def is_expired(self):
        return _utcnow() > _ensure_aware(self.expires_at)

    @property
    def is_accepted(self):
        return self.accepted_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_accepted

    def mark_accepted(self):
        self.accepted_at = _utcnow()

    @classmethod
    def make(cls, email, invited_by, role_id=None, expires_in_days=7):
        """Factory: create an unsaved invitation with generated token."""
        return cls(
            token=secrets.token_urlsafe(48),
            email=email.lower(),
            role_id=role_id,
            invited_by=invited_by,
            expires_at=_utcnow() + timedelta(days=expires_in_days),
        )

    def __repr__(self):
        return f"<UserInvitation email={self.email}>"


# ── EmailVerificationToken ───────────────────────────────────────────────


class EmailVerificationToken(db.Model):
    """Single-use email verification token. Expires after 24 hours."""

    __tablename__ = "email_verification_tokens"

    id = _uuid_column()
    token = Column(String(64), nullable=False, unique=True, index=True)
    user_id = _uuid_fk("users.id")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_email_verification_tokens_user_id", "user_id"),
        Index("ix_email_verification_tokens_expires_at", "expires_at"),
    )

    @property
    def is_expired(self):
        return _utcnow() > _ensure_aware(self.expires_at)

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_valid(self):
        return not self.is_expired and not self.is_used

    def mark_used(self):
        self.used_at = _utcnow()

    @classmethod
    def make(cls, user_id, expires_in_hours=24):
        """Factory: create an unsaved instance with generated token."""
        return cls(
            token=secrets.token_urlsafe(48),
            user_id=user_id,
            expires_at=_utcnow() + timedelta(hours=expires_in_hours),
        )

    def __repr__(self):
        return f"<EmailVerificationToken user={self.user_id}>"
