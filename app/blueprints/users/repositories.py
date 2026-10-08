"""User repository — data access for the User model."""

from sqlalchemy import or_

from app.blueprints.users.models import User


class UserRepository:
    """Data access for the User model."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, user_id):
        return self.session.get(User, user_id)

    def find_by_email(self, email):
        return self.session.query(User).filter(
            User.email == email.lower(),
        ).first()

    def create(self, user):
        self.session.add(user)
        self.session.flush()
        return user

    def count(self):
        return self.session.query(User).count()

    def list_users(self, page=1, per_page=20, search=None, is_active=None):
        """Return paginated users.

        Returns (users, total) tuple.
        """
        query = self.session.query(User)

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                )
            )

        if is_active is not None:
            query = query.filter(User.is_active.is_(is_active))

        total = query.count()
        users = (
            query
            .order_by(User.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        return users, total
