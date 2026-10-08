"""File management routes."""

from flask import Blueprint, g, jsonify, request, send_file
from marshmallow import ValidationError

from app.blueprints.files.schemas import (
    FileDownloadResponseSchema,
    FileListQuerySchema,
    FileListResponseSchema,
    FileResponseSchema,
    FileUpdateSchema,
)
from app.blueprints.files.services import FileService
from app.core.constants import Permissions
from app.core.decorators import audit_action, require_permission
from app.core.exceptions import ValidationError as AppValidationError

files_bp = Blueprint("files", __name__)


@files_bp.route("", methods=["POST"])
@require_permission(Permissions.FILES_UPLOAD)
@audit_action("files.upload", resource_type="file")
def upload_file():
    """Upload a new file (multipart/form-data)."""
    if "file" not in request.files:
        raise AppValidationError("No file provided", errors={"file": ["File is required"]})

    file = request.files["file"]
    description = request.form.get("description")

    file_record = FileService.upload_file(
        user_id=g.user.id,
        file=file,
        description=description,
    )

    return jsonify(FileResponseSchema().dump(file_record)), 201


@files_bp.route("", methods=["GET"])
@require_permission(Permissions.FILES_VIEW)
def list_files():
    """List files (paginated)."""
    query_schema = FileListQuerySchema()

    try:
        query_params = {
            "page": request.args.get("page", type=int),
            "per_page": request.args.get("per_page", type=int),
            "search": request.args.get("search"),
            "mime_type": request.args.get("mime_type"),
        }
        query_params = {k: v for k, v in query_params.items() if v is not None}
        data = query_schema.load(query_params)
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    result = FileService.list_files(
        page=data["page"],
        per_page=data["per_page"],
        search=data.get("search"),
        mime_type=data.get("mime_type"),
    )

    return jsonify(FileListResponseSchema().dump(result)), 200


@files_bp.route("/<uuid:file_id>", methods=["GET"])
@require_permission(Permissions.FILES_VIEW)
def get_file(file_id):
    """Get a specific file's metadata."""
    file = FileService.get_file(file_id=file_id)
    return jsonify(FileResponseSchema().dump(file)), 200


@files_bp.route("/<uuid:file_id>", methods=["PATCH"])
@require_permission(Permissions.FILES_UPLOAD)
@audit_action(
    "files.update",
    resource_type="file",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("file_id")),
)
def update_file(file_id):
    """Update file metadata (description)."""
    schema = FileUpdateSchema()

    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as e:
        raise AppValidationError("Validation failed", errors=e.messages)

    file = FileService.update_file(
        file_id=file_id,
        user_id=g.user.id,
        description=data.get("description"),
    )

    return jsonify(FileResponseSchema().dump(file)), 200


@files_bp.route("/<uuid:file_id>/download", methods=["GET"])
@require_permission(Permissions.FILES_DOWNLOAD)
def download_file_url(file_id):
    """Get presigned download URL for a file."""
    result = FileService.get_download_url(file_id=file_id)
    return jsonify(FileDownloadResponseSchema().dump(result)), 200


@files_bp.route("/<uuid:file_id>/content", methods=["GET"])
@require_permission(Permissions.FILES_DOWNLOAD)
def download_file_content(file_id):
    """Download file content directly (proxy download)."""
    data, filename, mime_type = FileService.download_file(file_id=file_id)
    return send_file(
        data,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
    )


@files_bp.route("/<uuid:file_id>", methods=["DELETE"])
@require_permission(Permissions.FILES_DELETE)
@audit_action(
    "files.delete",
    resource_type="file",
    get_resource_id=lambda kwargs, resp: str(kwargs.get("file_id")),
)
def delete_file(file_id):
    """Soft delete a file."""
    file = FileService.delete_file(
        file_id=file_id,
        user_id=g.user.id,
    )
    return jsonify({"message": "File deleted successfully", "id": str(file.id)}), 200
