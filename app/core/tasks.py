"""Celery tasks for background processing.

Generic tasks: email sending, token cleanup.
Domain-specific tasks will live in their own blueprint task files.
"""

from app.core.celery import celery_app


# ── Email tasks ─────────────────────────────────────────────────────────


@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, to: str, subject: str, body: str, html: str = None):
    """Send email asynchronously with retry."""
    try:
        from app.core.email import send_email
        send_email(to=to, subject=subject, body=body, html=html)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_email_task(self, to: str, reset_url: str):
    """Send password reset email asynchronously."""
    try:
        from app.core.email import send_password_reset_email
        send_password_reset_email(to=to, reset_url=reset_url)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def send_verification_email_task(self, to: str, verify_url: str):
    """Send email verification email asynchronously."""
    try:
        from app.core.email import send_email_verification
        send_email_verification(to=to, verify_url=verify_url)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def send_invitation_email_task(self, to: str, inviter_name: str, tenant_name: str, invite_url: str):
    """Send user invitation email asynchronously."""
    try:
        from app.core.email import send_user_invitation
        send_user_invitation(
            to=to,
            inviter_name=inviter_name,
            tenant_name=tenant_name,
            invite_url=invite_url,
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


# ── Cleanup tasks ───────────────────────────────────────────────────────


@celery_app.task
def cleanup_expired_tokens():
    """Clean up all expired auth tokens (run hourly via Beat)."""
    from app.blueprints.auth.repositories import (
        BlacklistedTokenRepository,
        InvitationRepository,
        PasswordResetTokenRepository,
        VerificationTokenRepository,
    )
    from app.extensions import db

    blacklist_repo = BlacklistedTokenRepository(db.session)
    reset_repo = PasswordResetTokenRepository(db.session)
    verification_repo = VerificationTokenRepository(db.session)
    invitation_repo = InvitationRepository(db.session)

    counts = {
        "blacklisted_tokens": blacklist_repo.cleanup_expired(),
        "password_reset_tokens": reset_repo.cleanup_expired(),
        "email_verification_tokens": verification_repo.cleanup_expired(),
        "invitations": invitation_repo.cleanup_expired(),
    }
    db.session.commit()

    return counts
