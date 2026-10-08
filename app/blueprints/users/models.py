"""User model definition."""

from sqlalchemy import Boolean, Column, DateTime, String
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.models import BaseModel
from app.extensions import db


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_superadmin = Column(Boolean, nullable=False, default=False, server_default="0")
    email_verified = Column(Boolean, nullable=False, default=False, server_default="0")
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships (string refs to avoid circular imports)
    user_roles = db.relationship(
        "UserRole", back_populates="user", lazy="dynamic",
        foreign_keys="UserRole.user_id",
    )
    password_reset_tokens = db.relationship(
        "PasswordResetToken", back_populates="user", lazy="dynamic"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"
