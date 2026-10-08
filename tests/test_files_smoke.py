"""Smoke tests for Phase 8: File Storage Infrastructure.

Tests storage module, File model, FileRepository, FileService,
routes, permissions, and validation --- all with mocked MinIO.
"""

import io
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# -- Helpers ----------------------------------------------------------------


def bootstrap(client):
    """Bootstrap + login: returns (access_token, user)."""
    resp = client.post("/api/v1/auth/bootstrap", json={
        "email": "owner@test.com",
        "password": "Password123",
        "first_name": "Test",
        "last_name": "Owner",
    })
    assert resp.status_code == 201, resp.get_json()
    data = resp.get_json()
    return data["access_token"], data["user"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def make_test_file(filename="test.pdf", content=b"fake pdf content", mime="application/pdf"):
    """Create a file-like object for upload testing."""
    return (io.BytesIO(content), filename, mime)


def upload_file(client, token, filename="test.pdf", content=b"fake pdf content",
                mime="application/pdf", description=None):
    """Helper to upload a file via the API."""
    data = {"file": (io.BytesIO(content), filename, mime)}
    if description:
        data["description"] = description
    return client.post(
        "/api/v1/files",
        headers=auth_headers(token),
        data=data,
        content_type="multipart/form-data",
    )


# -- 0. Imports, blueprint registration, permissions -----------------------


def test_imports(app):
    """All modules import correctly."""
    from app.core.storage import (
        build_file_path,
        delete_file,
        download_file,
        file_exists,
        generate_presigned_url,
        get_storage_client,
        init_storage,
        reset_storage_client,
        upload_file,
    )
    from app.blueprints.files.models import File
    from app.blueprints.files.repositories import FileRepository
    from app.blueprints.files.services import FileService, FileNotFoundError, FileUploadError
    from app.blueprints.files.schemas import (
        FileResponseSchema,
        FileListResponseSchema,
        FileListQuerySchema,
        FileDownloadResponseSchema,
        FileUpdateSchema,
    )
    from app.blueprints.files.routes import files_bp


def test_blueprint_registered(app):
    """files blueprint is registered at /api/v1/files."""
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/v1/files" in rules


def test_route_count(app):
    """Blueprint has the expected number of routes (7 method+path combos)."""
    rules = [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/v1/files")]
    methods = set()
    for r in rules:
        for m in r.methods:
            if m not in ("OPTIONS", "HEAD"):
                methods.add((r.rule, m))
    assert len(methods) == 7, f"Expected 7 route+method combos, got {len(methods)}: {methods}"


def test_permissions_defined(app):
    """File permissions exist in constants."""
    from app.core.constants import Permissions, ALL_PERMISSIONS

    assert Permissions.FILES_VIEW == "files.view"
    assert Permissions.FILES_UPLOAD == "files.upload"
    assert Permissions.FILES_DOWNLOAD == "files.download"
    assert Permissions.FILES_DELETE == "files.delete"

    perm_names = [p["name"] for p in ALL_PERMISSIONS]
    assert "files.view" in perm_names
    assert "files.upload" in perm_names
    assert "files.download" in perm_names
    assert "files.delete" in perm_names


# -- 1. Storage module tests -----------------------------------------------


def test_build_file_path(app):
    """build_file_path returns correct format."""
    from app.core.storage import build_file_path

    file_id = uuid4()
    filename = "document.pdf"

    path = build_file_path(file_id, filename)
    assert path == f"files/{file_id}/{filename}"
    assert path.count("/") == 2


# -- 2. Model tests -------------------------------------------------------


def test_file_model_create(app):
    """Create a File record and verify to_dict()."""
    from app.blueprints.files.models import File
    from app.blueprints.users.models import User

    user = User(
        email="test@test.com",
        password_hash="fake",
        first_name="Test",
        last_name="User",
    )
    db.session.add(user)
    db.session.flush()

    file = File(
        filename="abc123",
        original_filename="report.pdf",
        file_path=f"files/abc123/report.pdf",
        size=1024,
        mime_type="application/pdf",
        description="Quarterly report",
        created_by=user.id,
        updated_by=user.id,
    )
    db.session.add(file)
    db.session.commit()

    d = file.to_dict()
    assert d["original_filename"] == "report.pdf"
    assert d["size"] == 1024
    assert d["mime_type"] == "application/pdf"
    assert d["description"] == "Quarterly report"
    assert d["created_by"] == str(user.id)
    assert "id" in d


def test_file_model_soft_delete(app):
    """Soft delete sets deleted_at and is_deleted."""
    from app.blueprints.files.models import File

    file = File(
        filename="x",
        original_filename="x.txt",
        file_path="path/x",
        size=10,
        mime_type="text/plain",
    )
    db.session.add(file)
    db.session.commit()

    assert file.is_deleted is False
    file.soft_delete()
    db.session.commit()
    assert file.is_deleted is True
    assert file.deleted_at is not None


# -- 3. Repository tests ---------------------------------------------------


def test_repo_create_and_find(app):
    """Repository creates and finds files."""
    from app.blueprints.files.models import File
    from app.blueprints.files.repositories import FileRepository

    repo = FileRepository(db.session)
    file = File(
        filename="f1",
        original_filename="doc.pdf",
        file_path="path/doc.pdf",
        size=100,
        mime_type="application/pdf",
    )
    repo.create(file)
    db.session.commit()

    found = repo.find_active_by_id(file.id)
    assert found is not None
    assert found.original_filename == "doc.pdf"


def test_repo_find_active_excludes_deleted(app):
    """find_active_by_id excludes soft-deleted files."""
    from app.blueprints.files.models import File
    from app.blueprints.files.repositories import FileRepository

    repo = FileRepository(db.session)
    file = File(
        filename="f2",
        original_filename="old.pdf",
        file_path="path/old.pdf",
        size=50,
        mime_type="application/pdf",
    )
    repo.create(file)
    db.session.commit()

    repo.soft_delete(file)
    db.session.commit()

    assert repo.find_active_by_id(file.id) is None


def test_repo_list_files_pagination(app):
    """list_files returns paginated results."""
    from app.blueprints.files.models import File
    from app.blueprints.files.repositories import FileRepository

    repo = FileRepository(db.session)
    for i in range(5):
        f = File(
            filename=f"f{i}",
            original_filename=f"file{i}.pdf",
            file_path=f"path/file{i}.pdf",
            size=100,
            mime_type="application/pdf",
        )
        repo.create(f)
    db.session.commit()

    files, total = repo.list_files(page=1, per_page=2)
    assert total == 5
    assert len(files) == 2

    files2, total2 = repo.list_files(page=3, per_page=2)
    assert total2 == 5
    assert len(files2) == 1


def test_repo_list_files_search(app):
    """list_files filters by search term."""
    from app.blueprints.files.models import File
    from app.blueprints.files.repositories import FileRepository

    repo = FileRepository(db.session)
    for name in ["lease_agreement.pdf", "receipt_jan.pdf", "lease_renewal.pdf"]:
        f = File(
            filename="x",
            original_filename=name,
            file_path=f"path/{name}",
            size=100,
            mime_type="application/pdf",
        )
        repo.create(f)
    db.session.commit()

    files, total = repo.list_files(search="lease")
    assert total == 2


def test_repo_list_files_mime_filter(app):
    """list_files filters by MIME type."""
    from app.blueprints.files.models import File
    from app.blueprints.files.repositories import FileRepository

    repo = FileRepository(db.session)
    for name, mime in [("a.pdf", "application/pdf"), ("b.png", "image/png"), ("c.pdf", "application/pdf")]:
        f = File(
            filename="x",
            original_filename=name,
            file_path=f"path/{name}",
            size=100,
            mime_type=mime,
        )
        repo.create(f)
    db.session.commit()

    files, total = repo.list_files(mime_type="image/png")
    assert total == 1
    assert files[0].original_filename == "b.png"


# -- 4. Service tests (mocked storage) ------------------------------------


@patch("app.blueprints.files.services.storage_upload")
def test_service_upload(mock_upload, app):
    """FileService.upload_file creates record with mocked storage."""
    mock_upload.return_value = True

    from app.blueprints.files.services import FileService
    from app.blueprints.users.models import User

    user = User(
        email="svc@test.com",
        password_hash="fake",
        first_name="Svc",
        last_name="User",
    )
    db.session.add(user)
    db.session.commit()

    from werkzeug.datastructures import FileStorage
    file = FileStorage(
        stream=io.BytesIO(b"test content"),
        filename="contract.pdf",
        content_type="application/pdf",
    )

    result = FileService.upload_file(
        user_id=user.id,
        file=file,
        description="Test upload",
    )

    assert result.original_filename == "contract.pdf"
    assert result.mime_type == "application/pdf"
    assert result.description == "Test upload"
    assert result.created_by == user.id
    mock_upload.assert_called_once()


@patch("app.blueprints.files.services.storage_upload")
def test_service_list(mock_upload, app):
    """FileService.list_files returns paginated results."""
    mock_upload.return_value = True

    from app.blueprints.files.services import FileService
    from app.blueprints.users.models import User
    from werkzeug.datastructures import FileStorage

    user = User(
        email="svc2@test.com",
        password_hash="fake",
        first_name="Svc",
        last_name="User",
    )
    db.session.add(user)
    db.session.commit()

    for i in range(3):
        f = FileStorage(
            stream=io.BytesIO(b"content"),
            filename=f"file{i}.pdf",
            content_type="application/pdf",
        )
        FileService.upload_file(user.id, f)

    result = FileService.list_files(page=1, per_page=2)
    assert result["total"] == 3
    assert len(result["files"]) == 2
    assert result["pages"] == 2


@patch("app.blueprints.files.services.storage_upload")
def test_service_get(mock_upload, app):
    """FileService.get_file returns file metadata."""
    mock_upload.return_value = True

    from app.blueprints.files.services import FileService
    from app.blueprints.users.models import User
    from werkzeug.datastructures import FileStorage

    user = User(
        email="svc3@test.com",
        password_hash="fake",
        first_name="Svc",
        last_name="User",
    )
    db.session.add(user)
    db.session.commit()

    f = FileStorage(
        stream=io.BytesIO(b"content"),
        filename="report.pdf",
        content_type="application/pdf",
    )
    uploaded = FileService.upload_file(user.id, f)

    result = FileService.get_file(uploaded.id)
    assert result.original_filename == "report.pdf"


@patch("app.blueprints.files.services.storage_upload")
def test_service_update_description(mock_upload, app):
    """FileService.update_file updates description."""
    mock_upload.return_value = True

    from app.blueprints.files.services import FileService
    from app.blueprints.users.models import User
    from werkzeug.datastructures import FileStorage

    user = User(
        email="svc4@test.com",
        password_hash="fake",
        first_name="Svc",
        last_name="User",
    )
    db.session.add(user)
    db.session.commit()

    f = FileStorage(
        stream=io.BytesIO(b"content"),
        filename="doc.pdf",
        content_type="application/pdf",
    )
    uploaded = FileService.upload_file(user.id, f)

    updated = FileService.update_file(uploaded.id, user.id, description="Updated desc")
    assert updated.description == "Updated desc"


@patch("app.blueprints.files.services.storage_upload")
def test_service_delete(mock_upload, app):
    """FileService.delete_file soft-deletes."""
    mock_upload.return_value = True

    from app.blueprints.files.services import FileService, FileNotFoundError
    from app.blueprints.users.models import User
    from werkzeug.datastructures import FileStorage

    user = User(
        email="svc5@test.com",
        password_hash="fake",
        first_name="Svc",
        last_name="User",
    )
    db.session.add(user)
    db.session.commit()

    f = FileStorage(
        stream=io.BytesIO(b"content"),
        filename="old.pdf",
        content_type="application/pdf",
    )
    uploaded = FileService.upload_file(user.id, f)

    deleted = FileService.delete_file(uploaded.id, user.id)
    assert deleted.is_deleted is True

    with pytest.raises(FileNotFoundError):
        FileService.get_file(uploaded.id)


@patch("app.blueprints.files.services.storage_delete")
@patch("app.blueprints.files.services.storage_upload")
def test_service_hard_delete(mock_upload, mock_delete, app):
    """FileService.hard_delete_file removes from DB."""
    mock_upload.return_value = True
    mock_delete.return_value = True

    from app.blueprints.files.services import FileService
    from app.blueprints.files.repositories import FileRepository
    from app.blueprints.users.models import User
    from werkzeug.datastructures import FileStorage

    user = User(
        email="svc6@test.com",
        password_hash="fake",
        first_name="Svc",
        last_name="User",
    )
    db.session.add(user)
    db.session.commit()

    f = FileStorage(
        stream=io.BytesIO(b"content"),
        filename="gone.pdf",
        content_type="application/pdf",
    )
    uploaded = FileService.upload_file(user.id, f)
    file_id = uploaded.id

    result = FileService.hard_delete_file(file_id)
    assert result is True
    mock_delete.assert_called_once()

    # Verify gone from DB
    repo = FileRepository(db.session)
    assert repo.find_by_id(file_id) is None


# -- 5. Route smoke tests -------------------------------------------------


@patch("app.blueprints.files.services.storage_upload")
def test_route_upload(mock_upload, client):
    """POST /api/v1/files uploads a file."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token, description="My lease")
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["original_filename"] == "test.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["description"] == "My lease"
    assert "id" in data


@patch("app.blueprints.files.services.storage_upload")
def test_route_list(mock_upload, client):
    """GET /api/v1/files lists uploaded files."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    upload_file(client, token, filename="a.pdf")
    upload_file(client, token, filename="b.pdf")

    resp = client.get("/api/v1/files", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 2
    assert len(data["files"]) == 2
    assert "page" in data
    assert "pages" in data


@patch("app.blueprints.files.services.storage_upload")
def test_route_get_metadata(mock_upload, client):
    """GET /api/v1/files/<id> returns file metadata."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token)
    file_id = resp.get_json()["id"]

    resp = client.get(f"/api/v1/files/{file_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == file_id
    assert data["original_filename"] == "test.pdf"


@patch("app.blueprints.files.services.storage_upload")
def test_route_update_description(mock_upload, client):
    """PATCH /api/v1/files/<id> updates description."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token)
    file_id = resp.get_json()["id"]

    resp = client.patch(
        f"/api/v1/files/{file_id}",
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"description": "Updated via API"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["description"] == "Updated via API"


@patch("app.blueprints.files.services.generate_presigned_url")
@patch("app.blueprints.files.services.storage_upload")
def test_route_download_url(mock_upload, mock_presigned, client):
    """GET /api/v1/files/<id>/download returns presigned URL."""
    mock_upload.return_value = True
    mock_presigned.return_value = "https://minio.local/presigned-url"

    token, user = bootstrap(client)

    resp = upload_file(client, token)
    file_id = resp.get_json()["id"]

    resp = client.get(f"/api/v1/files/{file_id}/download", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "download_url" in data
    assert data["filename"] == "test.pdf"
    assert data["mime_type"] == "application/pdf"
    assert "expires_in" in data


@patch("app.blueprints.files.services.storage_upload")
def test_route_delete(mock_upload, client):
    """DELETE /api/v1/files/<id> soft-deletes."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token)
    file_id = resp.get_json()["id"]

    resp = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers(token))
    assert resp.status_code == 200
    assert "deleted" in resp.get_json()["message"].lower()

    # Verify file no longer appears in list
    resp = client.get("/api/v1/files", headers=auth_headers(token))
    assert resp.get_json()["total"] == 0


# -- 6. Permission / auth tests -------------------------------------------


def test_upload_unauthenticated(client):
    """Upload without auth returns 401."""
    data = {"file": (io.BytesIO(b"content"), "test.pdf", "application/pdf")}
    resp = client.post("/api/v1/files", data=data, content_type="multipart/form-data")
    assert resp.status_code == 401


def test_list_unauthenticated(client):
    """List without auth returns 401."""
    resp = client.get("/api/v1/files")
    assert resp.status_code == 401


def test_get_not_found(client):
    """Get non-existent file returns 404."""
    token, user = bootstrap(client)
    resp = client.get(
        "/api/v1/files/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


@patch("app.blueprints.files.services.storage_upload")
def test_delete_not_found(mock_upload, client):
    """Delete non-existent file returns 404."""
    token, user = bootstrap(client)
    resp = client.delete(
        "/api/v1/files/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


@patch("app.blueprints.files.services.storage_upload")
def test_double_delete(mock_upload, client):
    """Deleting already-deleted file returns 404."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token)
    file_id = resp.get_json()["id"]

    client.delete(f"/api/v1/files/{file_id}", headers=auth_headers(token))
    resp = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers(token))
    assert resp.status_code == 404


# -- 7. Validation tests ---------------------------------------------------


def test_upload_no_file(client):
    """Upload with no file field returns 400."""
    token, user = bootstrap(client)
    resp = client.post(
        "/api/v1/files",
        headers=auth_headers(token),
        data={},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400


@patch("app.blueprints.files.services.storage_upload")
def test_upload_empty_file(mock_upload, client):
    """Upload empty file returns 400."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token, content=b"")
    assert resp.status_code == 400
    assert "empty" in resp.get_json()["message"].lower()


@patch("app.blueprints.files.services.storage_upload")
def test_upload_disallowed_mime(mock_upload, client):
    """Upload with disallowed MIME type returns 400."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    resp = upload_file(client, token, filename="script.exe", content=b"binary", mime="application/x-msdownload")
    assert resp.status_code == 400
    assert "not allowed" in resp.get_json()["message"].lower()


@patch("app.blueprints.files.services.storage_upload")
def test_upload_list_search(mock_upload, client):
    """Search files by name via query parameter."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    upload_file(client, token, filename="lease_agreement.pdf")
    upload_file(client, token, filename="receipt_jan.pdf")

    resp = client.get("/api/v1/files?search=lease", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["files"][0]["original_filename"] == "lease_agreement.pdf"


@patch("app.blueprints.files.services.storage_upload")
def test_upload_list_mime_filter(mock_upload, client):
    """Filter files by MIME type via query parameter."""
    mock_upload.return_value = True
    token, user = bootstrap(client)

    upload_file(client, token, filename="photo.png", content=b"png data", mime="image/png")
    upload_file(client, token, filename="doc.pdf", content=b"pdf data", mime="application/pdf")

    resp = client.get("/api/v1/files?mime_type=image/png", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["files"][0]["original_filename"] == "photo.png"
