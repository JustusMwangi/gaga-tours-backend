"""RBACService: role and permission management."""

from datetime import datetime, timezone
from uuid import UUID

from flask import g
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.blueprints.rbac.models import Permission, Role, RolePermission, UserRole
from app.blueprints.rbac.repositories import RoleRepository
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RoleNotFoundError,
)
from app.extensions import db


class RBACService:
    """Static methods for RBAC management operations."""

    # -- Roles --------------------------------------------------------------

    @staticmethod
    def list_roles() -> dict:
        """List all non-deleted roles."""
        roles = (
            db.session.query(Role)
            .filter(Role.deleted_at.is_(None))
            .order_by(Role.is_system_role.desc(), Role.name)
            .all()
        )
        return {"roles": roles, "total": len(roles)}

    @staticmethod
    def get_role(role_id: UUID) -> dict:
        """Get a single role with permissions and user count."""
        repo = RoleRepository(db.session)
        role = repo.find_by_id(role_id)

        if not role or role.deleted_at is not None:
            raise RoleNotFoundError()

        permissions = (
            db.session.query(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(RolePermission.role_id == role_id)
            .all()
        )

        user_count = (
            db.session.query(func.count(UserRole.id))
            .filter(UserRole.role_id == role_id)
            .scalar()
        )

        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "permissions": permissions,
            "user_count": user_count,
        }

    @staticmethod
    def create_role(name: str, description: str = None,
                    permission_ids: list = None) -> dict:
        """Create a custom role with optional permissions."""
        user_id = g.user.id
        repo = RoleRepository(db.session)

        existing = repo.find_by_name(name)
        if existing and existing.deleted_at is None:
            raise ConflictError("A role with this name already exists")

        role = Role(
            name=name,
            description=description,
            is_system_role=False,
            created_by=user_id,
        )
        db.session.add(role)
        db.session.flush()

        if permission_ids:
            for pid in permission_ids:
                perm = db.session.get(Permission, pid)
                if perm:
                    repo.add_permission(role.id, pid)

        db.session.commit()

        return RBACService.get_role(role.id)

    @staticmethod
    def update_role(role_id: UUID, name: str = None, description: str = None,
                    permission_ids: list = None) -> dict:
        """Update a role's name, description, and/or permissions."""
        user_id = g.user.id
        repo = RoleRepository(db.session)
        role = repo.find_by_id(role_id)

        if not role or role.deleted_at is not None:
            raise RoleNotFoundError()

        if name and role.is_system_role and name != role.name:
            raise ForbiddenError("Cannot rename a system role")

        if name:
            existing = repo.find_by_name(name)
            if existing and existing.id != role_id and existing.deleted_at is None:
                raise ConflictError("A role with this name already exists")
            role.name = name

        if description is not None:
            role.description = description

        role.updated_by = user_id

        if permission_ids is not None:
            db.session.query(RolePermission).filter(
                RolePermission.role_id == role_id
            ).delete()
            for pid in permission_ids:
                perm = db.session.get(Permission, pid)
                if perm:
                    repo.add_permission(role.id, pid)

        db.session.commit()

        return RBACService.get_role(role.id)

    @staticmethod
    def delete_role(role_id: UUID) -> dict:
        """Soft-delete a custom role."""
        repo = RoleRepository(db.session)
        role = repo.find_by_id(role_id)

        if not role or role.deleted_at is not None:
            raise RoleNotFoundError()

        if role.is_system_role:
            raise ForbiddenError("Cannot delete a system role")

        db.session.query(UserRole).filter(UserRole.role_id == role_id).delete()

        role.soft_delete()
        db.session.commit()

        return {"message": "Role has been deleted"}

    # -- Permissions --------------------------------------------------------

    @staticmethod
    def list_permissions(resource: str = None) -> dict:
        """List all permissions, optionally filtered by resource."""
        query = db.session.query(Permission)
        if resource:
            query = query.filter(Permission.resource == resource)
        query = query.order_by(Permission.resource, Permission.action)
        permissions = query.all()
        return {"permissions": permissions, "total": len(permissions)}

    # -- User roles ---------------------------------------------------------

    @staticmethod
    def get_user_roles(user_id: UUID) -> dict:
        """Get all role assignments for a user."""
        from app.blueprints.users.repositories import UserRepository

        user_repo = UserRepository(db.session)
        user = user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        assignments = (
            db.session.query(UserRole)
            .options(joinedload(UserRole.role))
            .filter(UserRole.user_id == user_id)
            .all()
        )

        return {"user_id": user_id, "roles": assignments}

    @staticmethod
    def assign_role_to_user(user_id: UUID, role_id: UUID) -> dict:
        """Assign a role to a user."""
        assigner_id = g.user.id

        role = db.session.get(Role, role_id)
        if not role or role.deleted_at is not None:
            raise RoleNotFoundError()

        existing = db.session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        ).first()
        if existing:
            raise ConflictError("User already has this role assignment")

        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_at=datetime.now(timezone.utc),
            assigned_by=assigner_id,
        )
        db.session.add(assignment)
        db.session.commit()

        if user_id != assigner_id:
            from app.blueprints.notifications.services import NotificationService
            NotificationService.notify_user(
                user_id=user_id,
                title="Role Assigned",
                message=f"You have been assigned the \"{role.name}\" role.",
                category="team", type="info",
                data={"action": "view_roles"},
            )

        db.session.refresh(assignment)
        return RBACService.get_user_roles(user_id)

    @staticmethod
    def revoke_role_from_user(user_id: UUID, role_id: UUID) -> dict:
        """Remove a role assignment from a user."""
        assignment = db.session.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        ).first()
        if not assignment:
            raise NotFoundError("Role assignment not found")

        role = db.session.get(Role, role_id)
        if role and role.name == "Owner":
            if user_id == g.user.id:
                raise BadRequestError(
                    "Cannot remove the Owner role from yourself. "
                    "Another Owner must remove it."
                )
            owner_count = db.session.query(UserRole).filter(
                UserRole.role_id == role_id,
            ).count()
            if owner_count <= 1:
                raise BadRequestError(
                    "Cannot remove the last Owner. "
                    "Assign the Owner role to another user first."
                )

        db.session.delete(assignment)
        db.session.commit()

        if user_id != g.user.id:
            from app.blueprints.notifications.services import NotificationService
            NotificationService.notify_user(
                user_id=user_id,
                title="Role Removed",
                message=f"The \"{role.name}\" role has been removed from your account.",
                category="team", type="info",
                data={"action": "view_roles"},
            )

        return {"message": "Role assignment revoked"}
