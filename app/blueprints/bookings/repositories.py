"""Booking repository — data access for the Booking model."""

from sqlalchemy import func, or_

from app.blueprints.bookings.models import Booking


class BookingRepository:
    """Data access for the Booking model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, booking_id):
        return self.session.get(Booking, booking_id)

    def get_next_reference(self):
        """Generate next sequential reference like BK-0001."""
        total = self.session.query(func.count(Booking.id)).scalar() or 0
        return f"BK-{total + 1:04d}"

    def list_all(
        self,
        page=1,
        per_page=20,
        search=None,
        status=None,
        customer_id=None,
        tour_id=None,
    ):
        """Return paginated bookings.

        Returns (items, total) tuple.
        """
        query = self.session.query(Booking).filter(Booking.deleted_at.is_(None))

        if search:
            pattern = f"%{search}%"
            query = query.filter(Booking.reference.ilike(pattern))

        if status:
            query = query.filter(Booking.status == status)

        if customer_id:
            query = query.filter(Booking.customer_id == customer_id)

        if tour_id:
            query = query.filter(Booking.tour_id == tour_id)

        total = query.count()
        items = (
            query
            .order_by(Booking.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def create(self, booking):
        self.session.add(booking)
        self.session.flush()
        return booking

    def count(self):
        return (
            self.session.query(func.count(Booking.id))
            .filter(Booking.deleted_at.is_(None))
            .scalar()
        )
