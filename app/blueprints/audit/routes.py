"""Audit log API routes."""

from flask import Blueprint, Response, jsonify, request
from marshmallow import ValidationError

from app.blueprints.audit.schemas import (
    AuditLogExportQuerySchema,
    AuditLogListQuerySchema,
    AuditLogListResponseSchema,
    AuditLogResponseSchema,
)
from app.blueprints.audit.services import AuditService
from app.core.constants import Permissions
from app.core.decorators import require_permission
from app.core.exceptions import ValidationError as AppValidationError

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("/", methods=["GET"])
@require_permission(Permissions.AUDIT_VIEW)
def list_audit_logs():
    """List audit logs with filtering and pagination."""
    query_schema = AuditLogListQuerySchema()

    try:
        query_params = {
            "page": request.args.get("page", type=int),
            "per_page": request.args.get("per_page", type=int),
            "action": request.args.get("action"),
            "resource_type": request.args.get("resource_type"),
            "resource_id": request.args.get("resource_id"),
            "user_id": request.args.get("user_id"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        data = query_schema.load(query_params)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = AuditService.list_logs(
        page=data.get("page", 1),
        per_page=data.get("per_page", 50),
        action=data.get("action"),
        resource_type=data.get("resource_type"),
        resource_id=data.get("resource_id"),
        user_id=data.get("user_id"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
    )

    response_schema = AuditLogListResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@audit_bp.route("/<uuid:log_id>", methods=["GET"])
@require_permission(Permissions.AUDIT_VIEW)
def get_audit_log(log_id):
    """Get a specific audit log entry."""
    log = AuditService.get_log(log_id)

    response_schema = AuditLogResponseSchema()
    return jsonify(response_schema.dump(log)), 200


@audit_bp.route("/export", methods=["GET"])
@require_permission(Permissions.AUDIT_EXPORT)
def export_audit_logs():
    """Export audit logs in CSV or JSON format."""
    query_schema = AuditLogExportQuerySchema()

    try:
        query_params = {
            "format": request.args.get("format", "json"),
            "action": request.args.get("action"),
            "resource_type": request.args.get("resource_type"),
            "user_id": request.args.get("user_id"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date"),
            "limit": request.args.get("limit", type=int),
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        data = query_schema.load(query_params)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    content, content_type, filename = AuditService.export_logs(
        format=data.get("format", "json"),
        action=data.get("action"),
        resource_type=data.get("resource_type"),
        user_id=data.get("user_id"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        limit=data.get("limit", 10000),
    )

    return Response(
        content,
        mimetype=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
