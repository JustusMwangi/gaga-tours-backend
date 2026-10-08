"""Email tasks for subscription lifecycle notifications.

These wrap synchronous ``send_email`` with Celery retry logic so callers
can fire-and-forget.
"""

from app.core.celery import celery_app


@celery_app.task(bind=True, max_retries=3)
def send_trial_expiry_warning_email(self, to: str, tenant_name: str, days_remaining: int):
    """Warn a tenant owner that their trial is about to expire."""
    try:
        from app.core.email import send_email

        send_email(
            to=to,
            subject=f"Trial Expiring in {days_remaining} Day(s) - {tenant_name}",
            body=(
                f"Your trial for {tenant_name} expires in {days_remaining} day(s).\n\n"
                "Add a payment method to keep uninterrupted access to all features.\n\n"
                "If you have any questions, please contact support."
            ),
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def send_payment_due_email(self, to: str, tenant_name: str, plan_name: str, due_date: str):
    """Remind a tenant owner that payment is due soon."""
    try:
        from app.core.email import send_email

        send_email(
            to=to,
            subject=f"Payment Due Soon - {tenant_name}",
            body=(
                f"Your billing period for {tenant_name} ({plan_name} plan) "
                f"ends on {due_date}.\n\n"
                "Please ensure your payment method is up to date to avoid "
                "service interruption.\n\n"
                "If you have any questions, please contact support."
            ),
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=3)
def send_subscription_status_email(self, to: str, tenant_name: str, new_status: str, message: str):
    """Inform a tenant owner about a subscription status change."""
    try:
        from app.core.email import send_email

        send_email(
            to=to,
            subject=f"Subscription Update - {tenant_name}",
            body=(
                f"Your subscription for {tenant_name} is now: {new_status}.\n\n"
                f"{message}\n\n"
                "If you have any questions, please contact support."
            ),
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
