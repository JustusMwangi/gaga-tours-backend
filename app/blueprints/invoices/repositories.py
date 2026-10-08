"""Invoice & Payment repositories -- data access layer."""

from sqlalchemy import func

from app.blueprints.invoices.models import Invoice, Payment


class InvoiceRepository:
    """Data access for the Invoice model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, invoice_id):
        return self.session.get(Invoice, invoice_id)

    def get_next_number(self):
        """Generate next sequential invoice number like INV-0001."""
        total = self.session.query(func.count(Invoice.id)).scalar() or 0
        return f"INV-{total + 1:04d}"

    def list_all(
        self,
        page=1,
        per_page=20,
        search=None,
        status=None,
        customer_id=None,
    ):
        """Return paginated invoices as (items, total)."""
        query = self.session.query(Invoice).filter(Invoice.deleted_at.is_(None))

        if search:
            pattern = f"%{search}%"
            query = query.filter(Invoice.invoice_number.ilike(pattern))

        if status:
            query = query.filter(Invoice.status == status)

        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)

        total = query.count()
        items = (
            query
            .order_by(Invoice.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return items, total

    def create(self, invoice):
        self.session.add(invoice)
        self.session.flush()
        return invoice

    def count(self):
        return (
            self.session.query(func.count(Invoice.id))
            .filter(Invoice.deleted_at.is_(None))
            .scalar()
        )


class PaymentRepository:
    """Data access for the Payment model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, payment_id):
        return self.session.get(Payment, payment_id)

    def list_by_invoice(self, invoice_id):
        return (
            self.session.query(Payment)
            .filter(
                Payment.invoice_id == invoice_id,
                Payment.deleted_at.is_(None),
            )
            .order_by(Payment.payment_date.desc())
            .all()
        )

    def create(self, payment):
        self.session.add(payment)
        self.session.flush()
        return payment
