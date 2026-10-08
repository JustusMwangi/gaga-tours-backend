"""RBAC models: Role, Permission, UserRole, RolePermission."""

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, UniqueConstraint

from app.core.models import AuditableModel, BaseModel, _uuid_fk
from app.extensions import db


# ── RBAC entities ────────────────────────────────────────────────────────


class Permission(BaseModel):
    """Global permission in resource.action format (e.g. 'users.create')."""

    __tablename__ = "permissions"

    name = Column(String(120), unique=True, nullable=False, index=True)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_permission_resource_action", "resource", "action"),
    )

    role_links = db.relationship(
        "RolePermission", back_populates="permission", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Permission {self.name}>"


class Role(AuditableModel):
    """Application-wide role."""

    __tablename__ = "roles"

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, nullable=False, default=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("name", name="uq_role_name"),
    )

    permission_links = db.relationship(
        "RolePermission", back_populates="role", lazy="dynamic"
    )
    user_roles = db.relationship("UserRole", back_populates="role", lazy="dynamic")

    def __repr__(self):
        return f"<Role {self.name}>"


class RolePermission(BaseModel):
    """Links a role to a permission. Surrogate UUID PK + unique constraint."""

    __tablename__ = "role_permissions"

    role_id = _uuid_fk("roles.id")
    permission_id = _uuid_fk("permissions.id")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role = db.relationship("Role", back_populates="permission_links")
    permission = db.relationship("Permission", back_populates="role_links")

    def __repr__(self):
        return f"<RolePermission role={self.role_id} perm={self.permission_id}>"


class UserRole(BaseModel):
    """User-role assignment."""

    __tablename__ = "user_roles"

    user_id = _uuid_fk("users.id")
    role_id = _uuid_fk("roles.id")
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    assigned_by = _uuid_fk("users.id", nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role_assignment"),
        Index("ix_user_role_user", "user_id"),
    )

    user = db.relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = db.relationship("Role", back_populates="user_roles")
    assigner = db.relationship("User", foreign_keys=[assigned_by])

    def __repr__(self):
        return f"<UserRole user={self.user_id} role={self.role_id}>"
