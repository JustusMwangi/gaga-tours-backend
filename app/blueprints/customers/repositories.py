"""Customer repository — data access for the Customer model."""

from sqlalchemy import or_

from app.blueprints.customers.models import Customer


class CustomerRepository:
    """Data access for the Customer model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, customer_id):
        return self.session.get(Customer, customer_id)

    def find_by_email(self, email):
        return self.session.query(Customer).filter(
            Customer.email == email.lower(),
        ).first()

    def list_all(self, page=1, per_page=20, search=None, source=None, is_active=None):
        """Return paginated customers.

        Returns (customers, total) tuple.
        """
        query = self.session.query(Customer).filter(
            Customer.deleted_at.is_(None),
        )

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Customer.first_name.ilike(pattern),
                    Customer.last_name.ilike(pattern),
                    Customer.email.ilike(pattern),
                )
            )

        if source is not None:
            query = query.filter(Customer.source == source)

        if is_active is not None:
            query = query.filter(Customer.is_active.is_(is_active))

        total = query.count()
        customers = (
            query
            .order_by(Customer.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return customers, total

    def create(self, customer):
        self.session.add(customer)
        self.session.flush()
        return customer

    def count(self):
        return self.session.query(Customer).filter(
            Customer.deleted_at.is_(None),
        ).count()
