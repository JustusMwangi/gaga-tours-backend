"""File service with business logic for file management."""

import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.blueprints.files.models import File
from app.blueprints.files.repositories import FileRepository
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.storage import (
    build_file_path,
    delete_file as storage_delete,
    download_file as storage_download,
    generate_presigned_url,
    upload_file as storage_upload,
)
from app.extensions import db


class FileNotFoundError(NotFoundError):
    error_code = "file_not_found"

    def __init__(self, message: str = "File not found"):
        super().__init__(message)


class FileUploadError(BadRequestError):
    error_code = "file_upload_error"

    def __init__(self, message: str = "File upload failed"):
        super().__init__(message)


class FileService:
    """Service handling file storage operations."""

    MAX_FILE_SIZE = 10 * 1024 * 1024

    ALLOWED_MIME_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain", "text/csv",
        "application/zip", "application/x-zip-compressed",
    }

    @staticmethod
    def validate_file(file: FileStorage) -> tuple:
        if not file or not file.filename:
            raise FileUploadError("No file provided")

        mime_type = file.content_type or "application/octet-stream"
        if mime_type not in FileService.ALLOWED_MIME_TYPES:
            raise FileUploadError(f"File type '{mime_type}' not allowed")

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        if size > FileService.MAX_FILE_SIZE:
            max_mb = FileService.MAX_FILE_SIZE / (1024 * 1024)
            raise FileUploadError(f"File size exceeds maximum of {max_mb}MB")

        if size == 0:
            raise FileUploadError("File is empty")

        return size, mime_type

    @staticmethod
    def upload_file(
        user_id: UUID,
        file: FileStorage,
        description: Optional[str] = None,
    ) -> File:
        size, mime_type = FileService.validate_file(file)

        file_id = uuid4()

        file_path = build_file_path(
            file_id=file_id,
            filename=file.filename,
        )

        try:
            storage_upload(
                file_data=file.stream,
                file_path=file_path,
                content_type=mime_type,
                size=size,
            )
        except Exception as e:
            raise FileUploadError(f"Storage upload failed: {str(e)}")

        repo = FileRepository(db.session)
        file_record = File(
            id=file_id,
            filename=str(file_id),
            original_filename=file.filename,
            file_path=file_path,
            size=size,
            mime_type=mime_type,
            description=description,
            created_by=user_id,
            updated_by=user_id,
        )
        repo.create(file_record)
        db.session.commit()

        return file_record

    @staticmethod
    def list_files(
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> dict:
        repo = FileRepository(db.session)

        files, total = repo.list_files(
            page=page,
            per_page=per_page,
            search=search,
            mime_type=mime_type,
        )

        pages = math.ceil(total / per_page) if per_page else 0

        return {
            "files": files,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    @staticmethod
    def get_file(file_id: UUID) -> File:
        repo = FileRepository(db.session)
        file = repo.find_active_by_id(file_id)

        if not file:
            raise FileNotFoundError()

        return file

    @staticmethod
    def get_download_url(file_id: UUID, expiry_seconds: Optional[int] = None) -> dict:
        file = FileService.get_file(file_id)

        if expiry_seconds is None:
            expiry_seconds = current_app.config.get("MINIO_PRESIGNED_URL_EXPIRY", 3600)

        download_url = generate_presigned_url(file.file_path, expiry_seconds)

        return {
            "download_url": download_url,
            "filename": file.original_filename,
            "mime_type": file.mime_type,
            "expires_in": expiry_seconds,
        }

    @staticmethod
    def download_file(file_id: UUID) -> tuple:
        file = FileService.get_file(file_id)
        data = storage_download(file.file_path)
        return data, file.original_filename, file.mime_type

    @staticmethod
    def update_file(
        file_id: UUID,
        user_id: UUID,
        description: Optional[str] = None,
    ) -> File:
        file = FileService.get_file(file_id)

        if description is not None:
            file.description = description

        file.updated_at = datetime.now(timezone.utc)
        file.updated_by = user_id

        db.session.commit()

        return file

    @staticmethod
    def delete_file(file_id: UUID, user_id: UUID) -> File:
        file = FileService.get_file(file_id)

        file.deleted_at = datetime.now(timezone.utc)
        file.updated_by = user_id

        db.session.commit()

        return file

    @staticmethod
    def hard_delete_file(file_id: UUID) -> bool:
        repo = FileRepository(db.session)
        file = repo.find_by_id(file_id)

        if not file:
            return False

        try:
            storage_delete(file.file_path)
        except Exception:
            pass

        repo.hard_delete(file)
        db.session.commit()

        return True
