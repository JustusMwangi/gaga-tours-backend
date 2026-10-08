"""File schemas for request/response validation."""

from marshmallow import Schema, fields, validate


class FileResponseSchema(Schema):
    """Schema for file data in responses."""

    id = fields.UUID()
    filename = fields.String()
    original_filename = fields.String()
    size = fields.Integer()
    mime_type = fields.String()
    description = fields.String(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    created_by = fields.UUID(allow_none=True)


class FileListResponseSchema(Schema):
    """Schema for paginated file list response."""

    files = fields.List(fields.Nested(FileResponseSchema))
    total = fields.Integer()
    page = fields.Integer()
    per_page = fields.Integer()
    pages = fields.Integer()


class FileListQuerySchema(Schema):
    """Schema for file list query parameters."""

    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))
    search = fields.String(load_default=None)
    mime_type = fields.String(load_default=None)


class FileDownloadResponseSchema(Schema):
    """Schema for file download response (presigned URL)."""

    download_url = fields.String()
    filename = fields.String()
    mime_type = fields.String()
    expires_in = fields.Integer()


class FileUpdateSchema(Schema):
    """Schema for updating file metadata."""

    description = fields.String(
        validate=validate.Length(max=1000),
        allow_none=True,
    )
