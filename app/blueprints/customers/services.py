"""CustomerService: CRUD operations for customers."""

import math
from uuid import UUID

from app.blueprints.customers.models import Customer
from app.blueprints.customers.repositories import CustomerRepository
from app.core.exceptions import ConflictError, NotFoundError
from app.extensions import db


class CustomerService:
    """Static methods for all customer management operations."""

    # ── Find or create ──────────────────────────────────────────────────

    @staticmethod
    def find_or_create_by_email(email: str, first_name: str = None,
                                last_name: str = None, phone: str = None,
                                source: str = "direct") -> dict:
        """Return existing customer by email, or create a new one."""
        repo = CustomerRepository(db.session)

        existing = repo.find_by_email(email) if email else None
        if existing and existing.deleted_at is None:
            return existing.to_dict()

        customer = Customer(
            first_name=first_name or "",
            last_name=last_name or "",
            email=email.lower() if email else None,
            phone=phone,
            source=source,
        )
        repo.create(customer)
        db.session.commit()

        return customer.to_dict()

    # ── POST / ─────────────────────────────────────────────────────────

    @staticmethod
    def create_customer(data: dict) -> dict:
        """Create a new customer, checking for duplicate email."""
        repo = CustomerRepository(db.session)

        email = data.get("email")
        if email:
            existing = repo.find_by_email(email)
            if existing and existing.deleted_at is None:
                raise ConflictError("A customer with this email already exists")

        customer = Customer(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=email.lower() if email else None,
            phone=data.get("phone"),
            nationality=data.get("nationality"),
            passport_number=data.get("passport_number"),
            address=data.get("address"),
            notes=data.get("notes"),
            source=data.get("source", "direct"),
        )
        repo.create(customer)
        db.session.commit()

        return customer.to_dict()

    # ── GET / ──────────────────────────────────────────────────────────

    @staticmethod
    def list_customers(page: int = 1, per_page: int = 20,
                       search: str = None, source: str = None,
                       is_active: bool = None) -> dict:
        """List paginated customers."""
        repo = CustomerRepository(db.session)

        customers, total = repo.list_all(
            page=page,
            per_page=per_page,
            search=search,
            source=source,
            is_active=is_active,
        )

        return {
            "customers": [c.to_dict() for c in customers],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if per_page else 0,
        }

    # ── GET /<id> ──────────────────────────────────────────────────────

    @staticmethod
    def get_customer(customer_id: UUID) -> dict:
        """Return a single customer's details."""
        repo = CustomerRepository(db.session)

        customer = repo.find_by_id(customer_id)
        if not customer or customer.deleted_at is not None:
            raise NotFoundError("Customer not found")

        return customer.to_dict()

    # ── PUT /<id> ──────────────────────────────────────────────────────

    @staticmethod
    def update_customer(customer_id: UUID, data: dict) -> dict:
        """Update customer fields, checking email uniqueness if changed."""
        repo = CustomerRepository(db.session)

        customer = repo.find_by_id(customer_id)
        if not customer or customer.deleted_at is not None:
            raise NotFoundError("Customer not found")

        # Check email uniqueness if email is being changed
        new_email = data.get("email")
        if new_email is not None:
            new_email_lower = new_email.lower() if new_email else None
            if new_email_lower and new_email_lower != (customer.email or "").lower():
                existing = repo.find_by_email(new_email_lower)
                if existing and existing.id != customer.id and existing.deleted_at is None:
                    raise ConflictError("A customer with this email already exists")
            data["email"] = new_email_lower

        updatable_fields = [
            "first_name", "last_name", "email", "phone", "nationality",
            "passport_number", "address", "notes", "source", "is_active",
        ]
        for field in updatable_fields:
            if field in data:
                setattr(customer, field, data[field])

        db.session.commit()

        return customer.to_dict()

    # ── DELETE /<id> ───────────────────────────────────────────────────

    @staticmethod
    def delete_customer(customer_id: UUID) -> dict:
        """Soft-delete a customer."""
        repo = CustomerRepository(db.session)

        customer = repo.find_by_id(customer_id)
        if not customer or customer.deleted_at is not None:
            raise NotFoundError("Customer not found")

        customer.soft_delete()
        db.session.commit()

        return {"message": "Customer has been deleted"}
