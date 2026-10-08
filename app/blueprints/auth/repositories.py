"""Auth token repositories — data access for token lifecycle models."""

from datetime import datetime, timezone

from app.blueprints.auth.models import (
    BlacklistedToken,
    EmailVerificationToken,
    PasswordResetToken,
    UserInvitation,
    UserTokenRevocation,
)


def _utcnow():
    return datetime.now(timezone.utc)


class BlacklistedTokenRepository:
    """Data access for the BlacklistedToken model."""

    def __init__(self, session):
        self.session = session

    def is_blacklisted(self, jti):
        return self.session.query(
            self.session.query(BlacklistedToken).filter(
                BlacklistedToken.jti == jti,
            ).exists()
        ).scalar()

    def create(self, record):
        self.session.add(record)
        return record

    def cleanup_expired(self):
        return self.session.query(BlacklistedToken).filter(
            BlacklistedToken.expires_at < _utcnow(),
        ).delete()


class RevocationRepository:
    """Data access for the UserTokenRevocation model."""

    def __init__(self, session):
        self.session = session

    def get_revocation_time(self, user_id):
        record = self.session.query(UserTokenRevocation).filter(
            UserTokenRevocation.user_id == user_id,
        ).first()
        return record.revoked_at if record else None

    def revoke_all(self, user_id):
        record = self.session.query(UserTokenRevocation).filter(
            UserTokenRevocation.user_id == user_id,
        ).first()
        if record:
            record.revoked_at = _utcnow()
        else:
            record = UserTokenRevocation(user_id=user_id)
            self.session.add(record)
        return record


class PasswordResetTokenRepository:
    """Data access for the PasswordResetToken model."""

    def __init__(self, session):
        self.session = session

    def create(self, record):
        self.session.add(record)
        return record

    def find_valid(self, token):
        record = self.session.query(PasswordResetToken).filter(
            PasswordResetToken.token == token,
        ).first()
        return record if record and record.is_valid else None

    def invalidate_user_tokens(self, user_id):
        return (
            self.session.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .update({"used_at": _utcnow()})
        )

    def cleanup_expired(self):
        return self.session.query(PasswordResetToken).filter(
            PasswordResetToken.expires_at < _utcnow(),
        ).delete()


class VerificationTokenRepository:
    """Data access for the EmailVerificationToken model."""

    def __init__(self, session):
        self.session = session

    def create(self, record):
        self.session.add(record)
        return record

    def find_by_token(self, token):
        return self.session.query(EmailVerificationToken).filter(
            EmailVerificationToken.token == token,
        ).first()

    def find_latest_unused(self, user_id):
        return (
            self.session.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .order_by(EmailVerificationToken.created_at.desc())
            .first()
        )

    def invalidate_user_tokens(self, user_id):
        return (
            self.session.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .update({"used_at": _utcnow()})
        )

    def cleanup_expired(self):
        return self.session.query(EmailVerificationToken).filter(
            EmailVerificationToken.expires_at < _utcnow(),
        ).delete()


class InvitationRepository:
    """Data access for the UserInvitation model."""

    def __init__(self, session):
        self.session = session

    def create(self, record):
        self.session.add(record)
        return record

    def find_valid(self, token):
        invitation = self.session.query(UserInvitation).filter(
            UserInvitation.token == token,
        ).first()
        return invitation if invitation and invitation.is_valid else None

    def find_pending(self, email):
        return (
            self.session.query(UserInvitation)
            .filter(
                UserInvitation.email == email.lower(),
                UserInvitation.accepted_at.is_(None),
                UserInvitation.expires_at > _utcnow(),
            )
            .first()
        )

    def delete_by_email(self, email):
        return self.session.query(UserInvitation).filter(
            UserInvitation.email == email,
        ).delete()

    def cleanup_expired(self):
        return self.session.query(UserInvitation).filter(
            UserInvitation.expires_at < _utcnow(),
        ).delete()
