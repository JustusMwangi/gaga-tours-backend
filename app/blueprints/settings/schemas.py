"""Settings schemas for request/response validation."""

from marshmallow import Schema, fields, validate


class AppSettingsResponseSchema(Schema):
    """Schema for app settings in responses."""

    id = fields.UUID()
    app_name = fields.String()

    # Regional
    timezone = fields.String()
    currency = fields.String()
    locale = fields.String()

    # Display formats
    date_format = fields.String()
    time_format = fields.String()

    # Business info
    business_name = fields.String(allow_none=True)
    business_address = fields.String(allow_none=True)
    business_phone = fields.String(allow_none=True)
    business_email = fields.String(allow_none=True)


class UpdateAppSettingsSchema(Schema):
    """Schema for updating app settings — all fields optional."""

    app_name = fields.String(validate=validate.Length(min=1, max=255))
    timezone = fields.String(validate=validate.Length(max=50))
    currency = fields.String(validate=validate.Length(max=3))
    locale = fields.String(validate=validate.Length(max=10))
    date_format = fields.String(validate=validate.Length(max=20))
    time_format = fields.String(validate=validate.Length(max=10))
    business_name = fields.String(allow_none=True, validate=validate.Length(max=255))
    business_address = fields.String(allow_none=True, validate=validate.Length(max=500))
    business_phone = fields.String(allow_none=True, validate=validate.Length(max=50))
    business_email = fields.String(allow_none=True, validate=validate.Length(max=255))
