"""Audit log schemas for request/response validation."""

from marshmallow import Schema, fields, validate


class AuditLogResponseSchema(Schema):
    """Schema for audit log in responses."""

    id = fields.UUID()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    user_id = fields.UUID()
    action = fields.String()
    resource_type = fields.String()
    resource_id = fields.UUID(allow_none=True)
    old_values = fields.Dict(allow_none=True)
    new_values = fields.Dict(allow_none=True)
    ip_address = fields.String(allow_none=True)
    user_agent = fields.String(allow_none=True)
    description = fields.String(allow_none=True)
    extra_data = fields.Dict(allow_none=True)

    # Nested user info (when relationship is loaded)
    user_email = fields.Method("get_user_email", allow_none=True)
    user_name = fields.Method("get_user_name", allow_none=True)

    def get_user_email(self, obj):
        if hasattr(obj, "user") and obj.user:
            return obj.user.email
        return None

    def get_user_name(self, obj):
        if hasattr(obj, "user") and obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return None


class AuditLogListResponseSchema(Schema):
    """Schema for paginated audit log list."""

    logs = fields.List(fields.Nested(AuditLogResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class AuditLogListQuerySchema(Schema):
    """Schema for audit log list query parameters."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=50, validate=validate.Range(min=1, max=100))
    action = fields.String(load_default=None)
    resource_type = fields.String(load_default=None)
    resource_id = fields.UUID(load_default=None)
    user_id = fields.UUID(load_default=None)
    start_date = fields.DateTime(load_default=None)
    end_date = fields.DateTime(load_default=None)


class AuditLogExportQuerySchema(Schema):
    """Schema for export query parameters."""

    format = fields.String(
        load_default="json",
        validate=validate.OneOf(["json", "csv"]),
    )
    action = fields.String(load_default=None)
    resource_type = fields.String(load_default=None)
    user_id = fields.UUID(load_default=None)
    start_date = fields.DateTime(load_default=None)
    end_date = fields.DateTime(load_default=None)
    limit = fields.Integer(load_default=10000, validate=validate.Range(min=1, max=100000))
