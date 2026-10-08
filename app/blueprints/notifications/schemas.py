"""Notification schemas for request/response validation."""

from marshmallow import Schema, fields, validate


class NotificationResponseSchema(Schema):
    """Schema for notification in responses."""

    id = fields.UUID()
    user_id = fields.UUID()
    type = fields.String()
    category = fields.String()
    title = fields.String()
    message = fields.String()
    data = fields.Dict(allow_none=True)
    channel = fields.String()
    is_read = fields.Boolean()
    read_at = fields.DateTime(allow_none=True)
    sent_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime()


class NotificationListResponseSchema(Schema):
    """Schema for paginated notification list."""

    notifications = fields.List(fields.Nested(NotificationResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()
    unread_count = fields.Integer()


class NotificationListQuerySchema(Schema):
    """Schema for notification list query parameters."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    is_read = fields.Boolean(load_default=None)
    category = fields.String(
        load_default=None,
        validate=validate.OneOf(["system", "security", "team", "activity"]),
    )
    type = fields.String(
        load_default=None,
        validate=validate.OneOf(["info", "success", "warning", "error"]),
    )


class UnreadCountResponseSchema(Schema):
    """Schema for unread count response."""

    unread_count = fields.Integer()


class MarkAllReadResponseSchema(Schema):
    """Schema for mark all as read response."""

    message = fields.String()
    count = fields.Integer()


class DeleteNotificationResponseSchema(Schema):
    """Schema for delete notification response."""

    message = fields.String()


class NotificationPreferenceSchema(Schema):
    """Schema for a single notification preference."""

    category = fields.String()
    email_enabled = fields.Boolean()
    in_app_enabled = fields.Boolean()
    push_enabled = fields.Boolean()


class UpdatePreferenceSchema(Schema):
    """Schema for updating a single preference."""

    category = fields.String(
        required=True,
        validate=validate.OneOf(["system", "security", "team", "activity"]),
    )
    email_enabled = fields.Boolean(load_default=None)
    in_app_enabled = fields.Boolean(load_default=None)
    push_enabled = fields.Boolean(load_default=None)


class UpdatePreferencesSchema(Schema):
    """Schema for updating multiple preferences at once."""

    preferences = fields.List(
        fields.Nested(UpdatePreferenceSchema),
        required=True,
        validate=validate.Length(min=1, max=10),
    )
