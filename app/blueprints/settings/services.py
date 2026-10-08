"""SettingsService: business logic for application settings and dashboard."""

from flask import g
from sqlalchemy import func

from app.blueprints.settings.models import AppSettings
from app.extensions import db


class SettingsService:
    """Service for application settings."""

    @staticmethod
    def get_settings() -> AppSettings:
        """Get or create default app settings (singleton)."""
        settings = db.session.query(AppSettings).first()

        if not settings:
            settings = AppSettings()
            db.session.add(settings)
            db.session.commit()

        return settings

    @staticmethod
    def update_settings(data: dict) -> AppSettings:
        """Partial update of app settings."""
        settings = SettingsService.get_settings()

        updatable_fields = [
            "app_name",
            "timezone", "currency", "locale",
            "date_format", "time_format",
            "business_name", "business_address", "business_phone", "business_email",
        ]

        for field in updatable_fields:
            if field in data:
                setattr(settings, field, data[field])

        db.session.commit()
        return settings

    @staticmethod
    def get_dashboard() -> dict:
        """Get dashboard stats."""
        from app.blueprints.audit.models import AuditLog
        from app.blueprints.notifications.models import Notification
        from app.blueprints.users.models import User

        user_count = db.session.query(func.count(User.id)).filter(
            User.is_active.is_(True),
        ).scalar()

        unread_notifications = db.session.query(func.count(Notification.id)).filter(
            Notification.user_id == g.user.id,
            Notification.read_at.is_(None),
        ).scalar()

        recent_activity = db.session.query(AuditLog).order_by(
            AuditLog.created_at.desc(),
        ).limit(5).all()

        recent_activity_list = [
            {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "user_email": log.user.email if log.user else None,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in recent_activity
        ]

        return {
            "user_count": user_count,
            "unread_notifications": unread_notifications,
            "recent_activity": recent_activity_list,
        }
