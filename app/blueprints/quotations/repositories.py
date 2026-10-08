"""Quotation repositories — data access for Quotation and QuotationItem."""

from sqlalchemy import func

from app.blueprints.quotations.models import Quotation, QuotationItem


class QuotationRepository:
    """Data access for the Quotation model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, quotation_id):
        return self.session.get(Quotation, quotation_id)

    def get_next_reference(self):
        """Generate next sequential reference like QT-0001."""
        total = self.session.query(func.count(Quotation.id)).scalar() or 0
        return f"QT-{total + 1:04d}"

    def list_all(
        self,
        page=1,
        per_page=20,
        search=None,
        status=None,
        customer_id=None,
        booking_id=None,
    ):
        """Return paginated quotations.

        Returns (items, total) tuple.
        """
        query = self.session.query(Quotation).filter(
            Quotation.deleted_at.is_(None),
        )

        if search:
            pattern = f"%{search}%"
            query = query.filter(Quotation.reference.ilike(pattern))

        if status:
            query = query.filter(Quotation.status == status)

        if customer_id:
            query = query.filter(Quotation.customer_id == customer_id)

        if booking_id:
            query = query.filter(Quotation.booking_id == booking_id)

        total = query.count()
        items = (
            query
            .order_by(Quotation.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def create(self, quotation):
        self.session.add(quotation)
        self.session.flush()
        return quotation

    def count(self):
        return (
            self.session.query(func.count(Quotation.id))
            .filter(Quotation.deleted_at.is_(None))
            .scalar()
        )


class QuotationItemRepository:
    """Data access for the QuotationItem model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, item_id):
        return self.session.get(QuotationItem, item_id)

    def list_by_quotation(self, quotation_id):
        return (
            self.session.query(QuotationItem)
            .filter(
                QuotationItem.quotation_id == quotation_id,
                QuotationItem.deleted_at.is_(None),
            )
            .order_by(QuotationItem.sort_order.asc())
            .all()
        )

    def create(self, item):
        self.session.add(item)
        self.session.flush()
        return item

    def delete_all_for_quotation(self, quotation_id):
        """Hard-delete all items for a quotation (replaced on update)."""
        self.session.query(QuotationItem).filter(
            QuotationItem.quotation_id == quotation_id,
        ).delete(synchronize_session="fetch")
