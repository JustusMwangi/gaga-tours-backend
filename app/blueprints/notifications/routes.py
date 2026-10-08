"""Notification management routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.notifications.schemas import (
    DeleteNotificationResponseSchema,
    MarkAllReadResponseSchema,
    NotificationListQuerySchema,
    NotificationListResponseSchema,
    NotificationPreferenceSchema,
    NotificationResponseSchema,
    UnreadCountResponseSchema,
    UpdatePreferencesSchema,
)
from app.blueprints.notifications.services import NotificationService
from app.core.decorators import jwt_required
from app.core.exceptions import ValidationError as AppValidationError

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/", methods=["GET"])
@jwt_required
def list_notifications():
    """List notifications for the current user."""
    query_schema = NotificationListQuerySchema()

    try:
        query_params = {
            "page": request.args.get("page", type=int),
            "per_page": request.args.get("per_page", type=int),
            "is_read": request.args.get("is_read"),
            "category": request.args.get("category"),
            "type": request.args.get("type"),
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}

        # Handle boolean conversion for is_read
        if "is_read" in query_params:
            query_params["is_read"] = query_params["is_read"].lower() in ("true", "1", "yes")

        data = query_schema.load(query_params)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = NotificationService.list_notifications(
        page=data.get("page", 1),
        per_page=data.get("per_page", 20),
        is_read=data.get("is_read"),
        category=data.get("category"),
        type=data.get("type"),
    )

    response_schema = NotificationListResponseSchema()
    return jsonify(response_schema.dump(result)), 200


@notifications_bp.route("/unread-count", methods=["GET"])
@jwt_required
def get_unread_count():
    """Get count of unread notifications."""
    count = NotificationService.get_unread_count()
    response_schema = UnreadCountResponseSchema()
    return jsonify(response_schema.dump({"unread_count": count})), 200


@notifications_bp.route("/<uuid:notification_id>", methods=["GET"])
@jwt_required
def get_notification(notification_id):
    """Get a specific notification."""
    notification = NotificationService.get_notification(notification_id)
    response_schema = NotificationResponseSchema()
    return jsonify(response_schema.dump(notification)), 200


@notifications_bp.route("/<uuid:notification_id>/read", methods=["PUT"])
@jwt_required
def mark_as_read(notification_id):
    """Mark a notification as read."""
    notification = NotificationService.mark_as_read(notification_id)
    notification_schema = NotificationResponseSchema()

    return jsonify({
        "message": "Notification marked as read",
        "notification": notification_schema.dump(notification),
    }), 200


@notifications_bp.route("/read-all", methods=["PUT"])
@jwt_required
def mark_all_as_read():
    """Mark all notifications as read."""
    count = NotificationService.mark_all_as_read()
    response_schema = MarkAllReadResponseSchema()
    return jsonify(response_schema.dump({
        "message": f"Marked {count} notifications as read",
        "count": count,
    })), 200


@notifications_bp.route("/<uuid:notification_id>", methods=["DELETE"])
@jwt_required
def delete_notification(notification_id):
    """Delete a notification."""
    NotificationService.delete_notification(notification_id)
    response_schema = DeleteNotificationResponseSchema()
    return jsonify(response_schema.dump({"message": "Notification deleted"})), 200


@notifications_bp.route("/preferences", methods=["GET"])
@jwt_required
def get_preferences():
    """Get notification preferences for the current user."""
    preferences = NotificationService.get_preferences()
    preference_schema = NotificationPreferenceSchema(many=True)
    return jsonify({"preferences": preference_schema.dump(preferences)}), 200


@notifications_bp.route("/preferences", methods=["PUT"])
@jwt_required
def update_preferences():
    """Update notification preferences."""
    schema = UpdatePreferencesSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    preferences = NotificationService.update_preferences(data["preferences"])
    preference_schema = NotificationPreferenceSchema(many=True)
    return jsonify({"preferences": preference_schema.dump(preferences)}), 200
