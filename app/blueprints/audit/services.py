"""Audit Service for logging actions and retrieving audit logs."""

import csv
import json
import logging
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional
from uuid import UUID

from flask import g, request

from app.blueprints.audit.models import AuditLog
from app.core.exceptions import NotFoundError
from app.extensions import db

logger = logging.getLogger(__name__)


class AuditLogNotFoundError(NotFoundError):
    """Raised when audit log entry is not found."""

    error_code = "audit_log_not_found"

    def __init__(self, message: str = "Audit log entry not found"):
        super().__init__(message)


class AuditService:
    """Service for audit logging operations."""

    @staticmethod
    def log_action(
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log an audit event."""
        # Get values from context or parameters
        if user_id is None and hasattr(g, "user") and g.user:
            user_id = g.user.id

        # Get request context if available
        if ip_address is None:
            try:
                ip_address = request.remote_addr
            except RuntimeError:
                pass

        if user_agent is None:
            try:
                user_agent = request.headers.get("User-Agent")
            except RuntimeError:
                pass

        # Validate required fields
        if not user_id:
            raise ValueError("user_id is required for audit logging")

        # Sanitize values for JSON storage
        if old_values:
            old_values = AuditService._sanitize_for_json(old_values)
        if new_values:
            new_values = AuditService._sanitize_for_json(new_values)
        if extra_data:
            extra_data = AuditService._sanitize_for_json(extra_data)

        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            extra_data=extra_data,
        )

        db.session.add(audit_log)
        db.session.commit()

        return audit_log

    @staticmethod
    def _sanitize_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert non-JSON-serializable types to strings."""
        if data is None:
            return {}

        result = {}
        for key, value in data.items():
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = AuditService._sanitize_for_json(value)
            elif isinstance(value, list):
                result[key] = [
                    AuditService._sanitize_for_json(v) if isinstance(v, dict) else
                    str(v) if isinstance(v, (UUID, datetime)) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    @staticmethod
    def list_logs(
        page: int = 1,
        per_page: int = 50,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """List audit logs with filtering."""
        query = db.session.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        total = query.count()

        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        logs = query.all()
        pages = (total + per_page - 1) // per_page if total > 0 else 1

        return {
            "logs": logs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    @staticmethod
    def get_log(log_id: UUID) -> AuditLog:
        """Get a specific audit log entry."""
        log = db.session.query(AuditLog).filter(
            AuditLog.id == log_id,
        ).first()

        if not log:
            raise AuditLogNotFoundError()

        return log

    @staticmethod
    def export_logs(
        format: str = "json",
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10000,
    ) -> tuple:
        """Export audit logs in CSV or JSON format."""
        query = db.session.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        query = query.order_by(AuditLog.created_at.desc()).limit(limit)
        logs = query.all()

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if format == "csv":
            return AuditService._export_csv(logs), "text/csv", f"audit_logs_{timestamp}.csv"
        else:
            return AuditService._export_json(logs), "application/json", f"audit_logs_{timestamp}.json"

    @staticmethod
    def _export_csv(logs: List[AuditLog]) -> str:
        """Convert logs to CSV string."""
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "id", "created_at", "action", "resource_type", "resource_id",
            "user_id", "ip_address", "description",
        ])

        for log in logs:
            writer.writerow([
                str(log.id),
                log.created_at.isoformat() if log.created_at else "",
                log.action,
                log.resource_type,
                str(log.resource_id) if log.resource_id else "",
                str(log.user_id),
                log.ip_address or "",
                log.description or "",
            ])

        return output.getvalue()

    @staticmethod
    def _export_json(logs: List[AuditLog]) -> str:
        """Convert logs to JSON string."""
        data = []
        for log in logs:
            data.append({
                "id": str(log.id),
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "user_id": str(log.user_id),
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "description": log.description,
                "extra_data": log.extra_data,
            })
        return json.dumps(data, indent=2)
