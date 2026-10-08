"""Inquiry repository -- data access for the Inquiry model."""

from sqlalchemy import func, or_

from app.blueprints.inquiries.models import Inquiry


class InquiryRepository:
    """Data access for the Inquiry model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, inquiry_id):
        return self.session.get(Inquiry, inquiry_id)

    def list_all(self, page=1, per_page=20, search=None, status=None, tour_id=None):
        """Return paginated inquiries.

        Returns (inquiries, total) tuple.
        """
        query = self.session.query(Inquiry).filter(
            Inquiry.deleted_at.is_(None),
        )

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Inquiry.first_name.ilike(pattern),
                    Inquiry.last_name.ilike(pattern),
                    Inquiry.email.ilike(pattern),
                    Inquiry.reference.ilike(pattern),
                )
            )

        if status is not None:
            query = query.filter(Inquiry.status == status)

        if tour_id is not None:
            query = query.filter(Inquiry.tour_id == tour_id)

        total = query.count()
        inquiries = (
            query
            .order_by(Inquiry.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return inquiries, total

    def create(self, inquiry):
        self.session.add(inquiry)
        self.session.flush()
        return inquiry

    def get_next_reference(self):
        """Return the next sequential INQ-XXXX reference."""
        last = (
            self.session.query(func.max(Inquiry.reference))
            .filter(Inquiry.reference.like("INQ-%"))
            .scalar()
        )
        if last:
            try:
                num = int(last.split("-")[1]) + 1
            except (IndexError, ValueError):
                num = 1
        else:
            num = 1
        return f"INQ-{num:04d}"

    def count(self):
        return self.session.query(Inquiry).filter(
            Inquiry.deleted_at.is_(None),
        ).count()
