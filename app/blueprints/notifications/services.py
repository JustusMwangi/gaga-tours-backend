"""Notification Service for creating, managing, and delivering notifications."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from flask import g

from app.blueprints.notifications.models import (
    DEFAULT_NOTIFICATION_PREFERENCES,
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationPreference,
    NotificationType,
)
from app.blueprints.rbac.models import Permission, Role, RolePermission, UserRole
from app.core.exceptions import NotFoundError
from app.extensions import db


class NotificationNotFoundError(NotFoundError):
    """Raised when notification is not found."""

    error_code = "notification_not_found"

    def __init__(self, message: str = "Notification not found"):
        super().__init__(message)


class NotificationService:
    """Service for notification operations."""

    # ── Creating Notifications ───────────────────────────────────────

    @staticmethod
    def create_notification(
        user_id: UUID,
        title: str,
        message: str,
        category: str = NotificationCategory.SYSTEM.value,
        type: str = NotificationType.INFO.value,
        channel: str = NotificationChannel.IN_APP.value,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create a notification for a user."""
        # Accept both enum and string values
        if hasattr(category, "value"):
            category = category.value
        if hasattr(type, "value"):
            type = type.value
        if hasattr(channel, "value"):
            channel = channel.value

        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            type=type,
            channel=channel,
            data=data,
            sent_at=datetime.now(timezone.utc),
        )

        db.session.add(notification)
        db.session.commit()

        return notification

    @staticmethod
    def notify_user(
        user_id: UUID,
        title: str,
        message: str,
        category: str = "system",
        type: str = "info",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Notification:
        """Convenience method to notify a user with string parameters."""
        return NotificationService.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            type=type,
            data=data,
        )

    # ── Listing & Retrieving ─────────────────────────────────────────

    @staticmethod
    def list_notifications(
        page: int = 1,
        per_page: int = 20,
        is_read: Optional[bool] = None,
        category: Optional[str] = None,
        type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List notifications for the current user."""
        user_id = g.user.id

        query = db.session.query(Notification).filter(
            Notification.user_id == user_id,
        )

        if is_read is not None:
            if is_read:
                query = query.filter(Notification.read_at.isnot(None))
            else:
                query = query.filter(Notification.read_at.is_(None))

        if category:
            query = query.filter(Notification.category == category)

        if type:
            query = query.filter(Notification.type == type)

        total = query.count()

        unread_count = db.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        ).count()

        query = query.order_by(Notification.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        notifications = query.all()
        pages = (total + per_page - 1) // per_page if total > 0 else 1

        return {
            "notifications": notifications,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "unread_count": unread_count,
        }

    @staticmethod
    def get_unread_count() -> int:
        """Get count of unread notifications for current user."""
        user_id = g.user.id

        return db.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        ).count()

    @staticmethod
    def get_notification(notification_id: UUID) -> Notification:
        """Get a specific notification."""
        user_id = g.user.id

        notification = db.session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ).first()

        if not notification:
            raise NotificationNotFoundError()

        return notification

    # ── Marking as Read ──────────────────────────────────────────────

    @staticmethod
    def mark_as_read(notification_id: UUID) -> Notification:
        """Mark a notification as read."""
        notification = NotificationService.get_notification(notification_id)

        if not notification.read_at:
            notification.read_at = datetime.now(timezone.utc)
            db.session.commit()

        return notification

    @staticmethod
    def mark_all_as_read() -> int:
        """Mark all notifications as read for current user."""
        user_id = g.user.id

        count = db.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        ).update({Notification.read_at: datetime.now(timezone.utc)})

        db.session.commit()

        return count

    # ── Deleting ─────────────────────────────────────────────────────

    @staticmethod
    def delete_notification(notification_id: UUID) -> None:
        """Delete a notification."""
        notification = NotificationService.get_notification(notification_id)
        db.session.delete(notification)
        db.session.commit()

    # ── Preferences ──────────────────────────────────────────────────

    @staticmethod
    def get_preferences() -> List[NotificationPreference]:
        """Get all notification preferences for current user."""
        user_id = g.user.id

        preferences = db.session.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).all()

        if not preferences:
            preferences = NotificationService._create_default_preferences(user_id)

        return preferences

    @staticmethod
    def _create_default_preferences(user_id: UUID) -> List[NotificationPreference]:
        """Create default preferences for a user."""
        preferences = []

        for category, defaults in DEFAULT_NOTIFICATION_PREFERENCES.items():
            pref = NotificationPreference(
                user_id=user_id,
                category=category.value,
                email_enabled=defaults["email"],
                in_app_enabled=defaults["in_app"],
                push_enabled=defaults["push"],
            )
            db.session.add(pref)
            preferences.append(pref)

        db.session.commit()
        return preferences

    @staticmethod
    def update_preferences(
        preferences_data: List[Dict[str, Any]],
    ) -> List[NotificationPreference]:
        """Update notification preferences for current user."""
        user_id = g.user.id

        existing = {
            p.category: p for p in db.session.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).all()
        }

        if not existing:
            for pref in NotificationService._create_default_preferences(user_id):
                existing[pref.category] = pref

        for pref_data in preferences_data:
            category = pref_data["category"]

            if category in existing:
                pref = existing[category]
            else:
                pref = NotificationPreference(
                    user_id=user_id,
                    category=category,
                )
                db.session.add(pref)
                existing[category] = pref

            if pref_data.get("email_enabled") is not None:
                pref.email_enabled = pref_data["email_enabled"]
            if pref_data.get("in_app_enabled") is not None:
                pref.in_app_enabled = pref_data["in_app_enabled"]
            if pref_data.get("push_enabled") is not None:
                pref.push_enabled = pref_data["push_enabled"]

        db.session.commit()

        return list(existing.values())

    # ── Helper Methods for Common Notifications ──────────────────────

    @staticmethod
    def notify_password_changed(user_id: UUID) -> Notification:
        """Send notification when user changes their password."""
        return NotificationService.create_notification(
            user_id=user_id,
            title="Password Changed",
            message="Your password was successfully changed. If you didn't make this change, please contact support immediately.",
            category=NotificationCategory.SECURITY.value,
            type=NotificationType.WARNING.value,
        )

    # ── Role-Based Recipient Lookup ──────────────────────────────────

    @staticmethod
    def get_users_with_permission(permission: str) -> List[UUID]:
        """Get all user IDs that have a specific permission."""
        user_ids = db.session.query(UserRole.user_id).distinct().join(
            Role, UserRole.role_id == Role.id
        ).join(
            RolePermission, RolePermission.role_id == Role.id
        ).join(
            Permission, RolePermission.permission_id == Permission.id
        ).filter(
            Permission.name == permission,
        ).all()

        return [uid[0] for uid in user_ids]

    @staticmethod
    def notify_users_with_permission(
        permission: str,
        title: str,
        message: str,
        category: str = NotificationCategory.ACTIVITY.value,
        type: str = NotificationType.INFO.value,
        data: Optional[Dict[str, Any]] = None,
        exclude_user_id: Optional[UUID] = None,
        **kwargs,
    ) -> List[Notification]:
        """Send notification to all users with a specific permission."""
        user_ids = NotificationService.get_users_with_permission(permission)

        if exclude_user_id:
            user_ids = [uid for uid in user_ids if uid != exclude_user_id]

        notifications = []
        for user_id in user_ids:
            notification = NotificationService.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                type=type,
                data=data,
            )
            notifications.append(notification)

        return notifications
