"""Celery tasks for GDPR data export and deletion."""

import json
import logging
from datetime import datetime, timezone

from app.core.celery import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2)
def process_data_export(self, email: str):
    """Gather all personal data for an email and send it as a JSON attachment."""
    try:
        from app.blueprints.consent.models import ConsentRecord
        from app.blueprints.customers.models import Customer
        from app.blueprints.inquiries.models import Inquiry
        from app.blueprints.bookings.models import Booking
        from app.blueprints.public.models import Subscriber
        from app.core.email import send_email
        from app.extensions import db

        email_lower = email.lower()
        export = {"exported_at": datetime.now(timezone.utc).isoformat(), "email": email_lower}

        # Subscriber data
        sub = db.session.query(Subscriber).filter_by(email=email_lower).first()
        if sub:
            export["newsletter_subscription"] = {
                "email": sub.email,
                "name": sub.name,
                "is_active": sub.is_active,
                "subscribed_at": sub.created_at.isoformat() if sub.created_at else None,
            }

        # Inquiries
        inquiries = db.session.query(Inquiry).filter(
            Inquiry.email == email_lower,
            Inquiry.deleted_at.is_(None),
        ).all()
        if inquiries:
            export["inquiries"] = [
                {
                    "reference": i.reference,
                    "first_name": i.first_name,
                    "last_name": i.last_name,
                    "email": i.email,
                    "phone": i.phone,
                    "message": i.message,
                    "travel_date": i.travel_date.isoformat() if i.travel_date else None,
                    "group_size_adults": i.group_size_adults,
                    "group_size_children": i.group_size_children,
                    "status": i.status,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in inquiries
            ]

        # Customer + bookings
        customer = db.session.query(Customer).filter(
            Customer.email == email_lower,
            Customer.deleted_at.is_(None),
        ).first()
        if customer:
            export["customer_profile"] = {
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "email": customer.email,
                "phone": customer.phone,
                "nationality": customer.nationality,
                "address": customer.address,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
            }
            bookings = db.session.query(Booking).filter(
                Booking.customer_id == customer.id,
                Booking.deleted_at.is_(None),
            ).all()
            if bookings:
                export["bookings"] = [
                    {
                        "reference": b.reference,
                        "booking_date": b.booking_date.isoformat() if b.booking_date else None,
                        "number_of_adults": b.number_of_adults,
                        "number_of_children": b.number_of_children,
                        "special_requests": b.special_requests,
                        "total_amount": str(b.total_amount) if b.total_amount else None,
                        "currency": b.currency,
                        "status": b.status,
                        "created_at": b.created_at.isoformat() if b.created_at else None,
                    }
                    for b in bookings
                ]

        # Consent records
        consents = db.session.query(ConsentRecord).filter_by(email=email_lower).all()
        if consents:
            export["consent_records"] = [
                {
                    "purpose": c.purpose,
                    "consent_given": c.consent_given,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in consents
            ]

        # Check if we found any data at all
        if len(export) <= 2:  # only exported_at and email
            logger.info("No data found for export request: %s", email_lower)
            return

        json_data = json.dumps(export, indent=2, ensure_ascii=False).encode("utf-8")

        send_email(
            to=email_lower,
            subject="Your Data Export — Book With Sheilla",
            body=(
                "Please find attached a copy of all personal data we hold "
                "about you, as requested under GDPR.\n\n"
                "If you have any questions, contact us at hello@bookwithsheilla.com."
            ),
            attachments=[("data_export.json", "application/json", json_data)],
        )

        # Log fulfilment
        record = ConsentRecord(
            email=email_lower,
            purpose="data_export_fulfilled",
            consent_given=True,
            source="system",
        )
        db.session.add(record)
        db.session.commit()

        logger.info("Data export sent to %s", email_lower)

    except Exception as exc:
        logger.error("Data export failed for %s: %s", email, exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=2)
def process_data_deletion(self, email: str):
    """Anonymize all personal data for an email address."""
    try:
        from app.blueprints.consent.models import ConsentRecord
        from app.blueprints.customers.models import Customer
        from app.blueprints.inquiries.models import Inquiry
        from app.blueprints.public.models import Subscriber
        from app.core.email import send_email
        from app.extensions import db

        email_lower = email.lower()

        # Send confirmation BEFORE anonymizing (we still need the real email)
        send_email(
            to=email_lower,
            subject="Data Deletion Confirmed — Book With Sheilla",
            body=(
                "Your request to delete your personal data has been processed.\n\n"
                "All personal information we held about you has been anonymized "
                "or removed from our systems.\n\n"
                "Financial records may be retained in anonymized form as required "
                "by Belgian accounting law (7 years).\n\n"
                "If you have any questions, contact us at hello@bookwithsheilla.com."
            ),
        )

        # Anonymize subscriber
        sub = db.session.query(Subscriber).filter_by(email=email_lower).first()
        if sub:
            sub.is_active = False
            sub.email = f"deleted-{sub.id}@anonymized.local"
            sub.name = None
            sub.unsubscribed_at = datetime.now(timezone.utc)

        # Anonymize inquiries
        inquiries = db.session.query(Inquiry).filter(
            Inquiry.email == email_lower,
            Inquiry.deleted_at.is_(None),
        ).all()
        for inq in inquiries:
            inq.first_name = "Deleted"
            inq.last_name = "User"
            inq.email = "anonymized@deleted.local"
            inq.phone = None
            inq.message = None
            inq.internal_notes = None
            inq.soft_delete()

        # Anonymize customer (bookings/invoices keep references but PII is gone)
        customer = db.session.query(Customer).filter(
            Customer.email == email_lower,
            Customer.deleted_at.is_(None),
        ).first()
        if customer:
            customer.first_name = "Deleted"
            customer.last_name = "User"
            customer.email = f"deleted-{customer.id}@anonymized.local"
            customer.phone = None
            customer.passport_number = None
            customer.nationality = None
            customer.address = None
            customer.notes = None
            customer.soft_delete()

        # Log fulfilment
        record = ConsentRecord(
            email=email_lower,
            purpose="data_deletion_fulfilled",
            consent_given=True,
            source="system",
        )
        db.session.add(record)
        db.session.commit()

        logger.info("Data deletion processed for %s", email_lower)

    except Exception as exc:
        logger.error("Data deletion failed for %s: %s", email, exc)
        raise self.retry(exc=exc, countdown=60)
