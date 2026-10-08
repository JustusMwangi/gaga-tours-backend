"""RBAC repositories — data access for Permission, Role, UserRole."""

from app.blueprints.rbac.models import (
    Permission,
    Role,
    RolePermission,
    UserRole,
)


class PermissionRepository:
    """Data access for the Permission model."""

    def __init__(self, session):
        self.session = session

    def find_all(self):
        return self.session.query(Permission).all()

    def find_by_name(self, name):
        return self.session.query(Permission).filter_by(name=name).first()

    def get_existing_names(self):
        """Return a set of all permission names in the database."""
        return {p.name for p in self.session.query(Permission.name).all()}

    def create(self, permission):
        self.session.add(permission)
        return permission

    def flush(self):
        self.session.flush()


class RoleRepository:
    """Data access for the Role and RolePermission models."""

    def __init__(self, session):
        self.session = session

    def find_by_id(self, role_id):
        return self.session.get(Role, role_id)

    def find_by_name(self, name):
        return self.session.query(Role).filter_by(name=name).first()

    def create(self, role):
        self.session.add(role)
        self.session.flush()
        return role

    def add_permission(self, role_id, permission_id):
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        self.session.add(rp)
        return rp

    def get_permission_names(self, role_id):
        """Return list of permission name strings for a role."""
        rows = (
            self.session.query(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == role_id)
            .all()
        )
        return [r[0] for r in rows]


class UserRoleRepository:
    """Data access for UserRole and permission queries."""

    def __init__(self, session):
        self.session = session

    def create(self, user_role):
        self.session.add(user_role)
        return user_role

    def get_user_permissions(self, user_id):
        """Collect all permission names for a user."""
        role_ids = [
            r[0] for r in self.session.query(UserRole.role_id).filter(
                UserRole.user_id == user_id,
            ).all()
        ]

        if not role_ids:
            return set()

        permissions = (
            self.session.query(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id.in_(role_ids))
            .all()
        )

        return {p[0] for p in permissions}

    def find_by_user(self, user_id):
        """Return all UserRole rows for a user."""
        return self.session.query(UserRole).filter(
            UserRole.user_id == user_id,
        ).all()

    def delete_all_for_user(self, user_id):
        """Delete all role assignments for a user."""
        return self.session.query(UserRole).filter(
            UserRole.user_id == user_id,
        ).delete()
