"""Application settings routes."""

from flask import Blueprint, jsonify, request
from marshmallow import ValidationError

from app.blueprints.settings.schemas import (
    AppSettingsResponseSchema,
    UpdateAppSettingsSchema,
)
from app.blueprints.settings.services import SettingsService
from app.core.constants import Permissions
from app.core.decorators import audit_action, jwt_required, require_permission
from app.core.exceptions import ValidationError as AppValidationError

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("", methods=["GET"])
@require_permission(Permissions.SETTINGS_VIEW)
def get_settings():
    """Get application settings."""
    settings = SettingsService.get_settings()

    schema = AppSettingsResponseSchema()
    return jsonify(schema.dump(settings)), 200


@settings_bp.route("", methods=["PUT"])
@audit_action("settings.update", resource_type="settings")
@require_permission(Permissions.SETTINGS_EDIT)
def update_settings():
    """Update application settings."""
    schema = UpdateAppSettingsSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    settings = SettingsService.update_settings(data)

    response_schema = AppSettingsResponseSchema()
    return jsonify(response_schema.dump(settings)), 200


@settings_bp.route("/dashboard", methods=["GET"])
@jwt_required
def get_dashboard():
    """Get dashboard stats."""
    data = SettingsService.get_dashboard()
    return jsonify(data), 200
