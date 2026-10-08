"""MinIO/S3 storage client for file operations.

Provides:
- MinIO client initialization (lazy, with timeouts and retries)
- Upload, download, delete operations
- Presigned URL generation
- Path helpers for file storage

Design notes:
- The MinIO client is built with explicit connect/read timeouts so a slow
  or unreachable storage backend cannot hang a worker until gunicorn
  SIGKILLs it. Transport-level failures surface as StorageUnavailableError
  (HTTP 503) instead of leaking 500 tracebacks to clients.
- Init failures at boot do not permanently disable storage: the same
  client is reused on the next request and will retry against the backend.
"""

from datetime import timedelta
from io import BytesIO
from typing import BinaryIO, Optional
from uuid import UUID

import urllib3
from flask import current_app
from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import HTTPError as Urllib3HTTPError

from app.core.exceptions import APIError


class StorageUnavailableError(APIError):
    """Object storage backend is unreachable or timed out."""

    status_code = 503
    error_code = "storage_unavailable"

    def __init__(self, message: str = "File storage is temporarily unavailable"):
        super().__init__(message)


# Fail fast on a hung backend so gunicorn doesn't SIGKILL the worker.
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 30.0

_storage_client: Optional[Minio] = None


def _build_http_client() -> urllib3.PoolManager:
    return urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT),
        retries=urllib3.Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
        ),
        cert_reqs="CERT_REQUIRED",
    )


def get_storage_client() -> Minio:
    """Return the shared MinIO client, building it on first use."""
    global _storage_client
    if _storage_client is None:
        _storage_client = Minio(
            endpoint=current_app.config["MINIO_ENDPOINT"],
            access_key=current_app.config["MINIO_ACCESS_KEY"],
            secret_key=current_app.config["MINIO_SECRET_KEY"],
            secure=current_app.config["MINIO_SECURE"],
            http_client=_build_http_client(),
        )
    return _storage_client


def reset_storage_client():
    """Drop the cached client so the next call rebuilds it."""
    global _storage_client
    _storage_client = None


def init_storage(app):
    """Best-effort bucket check at boot. Failure here does not disable storage."""
    if app.config.get("TESTING"):
        return

    with app.app_context():
        try:
            client = get_storage_client()
            bucket = app.config["MINIO_BUCKET"]

            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                app.logger.info(f"Created MinIO bucket: {bucket}")
            else:
                app.logger.info(f"MinIO bucket already exists: {bucket}")
        except (Urllib3HTTPError, S3Error, OSError) as e:
            app.logger.warning(
                f"MinIO bucket check failed at boot ({e}); "
                "storage will retry on first request"
            )


def _call(fn, *args, **kwargs):
    """Run a storage call, mapping transport failures to StorageUnavailableError.

    S3Error propagates so callers can distinguish app-level outcomes
    (e.g. NoSuchKey) from a backend that's down.
    """
    try:
        return fn(*args, **kwargs)
    except S3Error:
        raise
    except (Urllib3HTTPError, OSError) as e:
        current_app.logger.warning(f"Storage backend unreachable: {e}")
        raise StorageUnavailableError() from e


def build_file_path(file_id: UUID, filename: str) -> str:
    """Build the object path for a file.

    Structure: files/file-uuid/original_filename
    """
    return f"files/{file_id}/{filename}"


def upload_file(
    file_data: BinaryIO,
    file_path: str,
    content_type: str,
    size: int,
) -> bool:
    """Upload file to MinIO.

    Raises:
        S3Error: On upload failure reported by the backend
        StorageUnavailableError: On transport failure (timeout, network)
    """
    client = get_storage_client()
    bucket = current_app.config["MINIO_BUCKET"]
    _call(
        client.put_object,
        bucket_name=bucket,
        object_name=file_path,
        data=file_data,
        length=size,
        content_type=content_type,
    )
    return True


def download_file(file_path: str) -> BytesIO:
    """Download file from MinIO.

    Raises:
        S3Error: On download failure reported by the backend
        StorageUnavailableError: On transport failure (timeout, network)
    """
    client = get_storage_client()
    bucket = current_app.config["MINIO_BUCKET"]

    response = _call(client.get_object, bucket, file_path)
    try:
        return BytesIO(response.read())
    finally:
        response.close()
        response.release_conn()


def delete_file(file_path: str) -> bool:
    """Delete file from MinIO.

    Raises:
        S3Error: On deletion failure reported by the backend
        StorageUnavailableError: On transport failure (timeout, network)
    """
    client = get_storage_client()
    bucket = current_app.config["MINIO_BUCKET"]
    _call(client.remove_object, bucket, file_path)
    return True


def generate_presigned_url(file_path: str, expiry_seconds: Optional[int] = None) -> str:
    """Generate presigned URL for direct file access."""
    client = get_storage_client()
    bucket = current_app.config["MINIO_BUCKET"]

    if expiry_seconds is None:
        expiry_seconds = current_app.config.get("MINIO_PRESIGNED_URL_EXPIRY", 3600)

    return _call(
        client.presigned_get_object,
        bucket,
        file_path,
        expires=timedelta(seconds=expiry_seconds),
    )


def file_exists(file_path: str) -> bool:
    """Check if file exists in MinIO."""
    client = get_storage_client()
    bucket = current_app.config["MINIO_BUCKET"]

    try:
        _call(client.stat_object, bucket, file_path)
        return True
    except S3Error:
        return False
