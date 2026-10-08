"""Repository for consent records."""

from app.blueprints.consent.models import ConsentRecord
from app.extensions import db


class ConsentRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def create(self, record: ConsentRecord) -> ConsentRecord:
        self.session.add(record)
        self.session.flush()
        return record

    def find_by_email(self, email: str) -> list[ConsentRecord]:
        return (
            self.session.query(ConsentRecord)
            .filter_by(email=email.lower())
            .order_by(ConsentRecord.created_at.desc())
            .all()
        )

    def find_latest_by_email_and_purpose(
        self, email: str, purpose: str
    ) -> ConsentRecord | None:
        return (
            self.session.query(ConsentRecord)
            .filter_by(email=email.lower(), purpose=purpose)
            .order_by(ConsentRecord.created_at.desc())
            .first()
        )
