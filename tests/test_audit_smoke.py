"""Smoke tests for Phase 4A: Audit Logging.

Tests imports, blueprint registration, route wiring, service operations,
and API endpoint behaviour.
"""

import json

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
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_audit_log(app, user_id, action="users.create", resource_type="user"):
    """Create an audit log entry via the service."""
    from uuid import UUID
    from app.blueprints.audit.services import AuditService

    with app.test_request_context():
        return AuditService.log_action(
            action=action,
            resource_type=resource_type,
            description="Test audit log",
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
        )


# -- 0. Imports, blueprint registration, permissions -----------------------


def test_imports(app):
    from app.blueprints.audit.models import AuditLog
    from app.blueprints.audit.schemas import (
        AuditLogExportQuerySchema,
        AuditLogListQuerySchema,
        AuditLogListResponseSchema,
        AuditLogResponseSchema,
    )
    from app.blueprints.audit.services import AuditService
    from app.blueprints.audit.routes import audit_bp


def test_blueprint_registered(app):
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/v1/audit/" in rules


def test_route_count(app):
    rules = [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/v1/audit")]
    methods = set()
    for r in rules:
        for m in r.methods:
            if m not in ("OPTIONS", "HEAD"):
                methods.add((r.rule, m))
    assert len(methods) == 3, f"Expected 3 route+method combos, got {len(methods)}: {methods}"


def test_permissions_defined(app):
    from app.core.constants import Permissions, ALL_PERMISSIONS

    assert Permissions.AUDIT_VIEW == "audit.view"
    assert Permissions.AUDIT_EXPORT == "audit.export"

    perm_names = [p["name"] for p in ALL_PERMISSIONS]
    assert "audit.view" in perm_names
    assert "audit.export" in perm_names


# -- 1. Service: log_action ------------------------------------------------


def test_log_action_via_service(app):
    token, user = None, None
    with app.test_client() as client:
        token, user = bootstrap(client)

    log = create_audit_log(app, user["id"])

    assert log is not None
    assert log.action == "users.create"
    assert log.resource_type == "user"
    assert log.description == "Test audit log"


def test_log_action_appears_in_list(client):
    token, user = bootstrap(client)

    create_audit_log(client.application, user["id"])

    resp = client.get("/api/v1/audit/", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert len(data["logs"]) >= 1
    assert data["logs"][0]["action"] == "users.create"


# -- 2. GET /audit/ --- list with filters -----------------------------------


def test_list_audit_logs_filter_by_action(client):
    token, user = bootstrap(client)

    create_audit_log(client.application, user["id"], action="users.create")
    create_audit_log(client.application, user["id"], action="roles.update")

    resp = client.get("/api/v1/audit/?action=users.create", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["logs"][0]["action"] == "users.create"


def test_list_audit_logs_filter_by_resource_type(client):
    token, user = bootstrap(client)

    create_audit_log(client.application, user["id"], resource_type="user")
    create_audit_log(client.application, user["id"], resource_type="role")

    resp = client.get("/api/v1/audit/?resource_type=role", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1


def test_list_audit_logs_pagination(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/audit/?page=1&per_page=5", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert "total" in data


# -- 3. GET /audit/<log_id> --- single log detail ---------------------------


def test_get_audit_log_detail(client):
    token, user = bootstrap(client)

    log = create_audit_log(client.application, user["id"])

    resp = client.get(f"/api/v1/audit/{log.id}", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["action"] == "users.create"
    assert data["resource_type"] == "user"
    assert "user_email" in data
    assert "user_name" in data


def test_get_audit_log_not_found(client):
    token, user = bootstrap(client)

    resp = client.get(
        "/api/v1/audit/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# -- 4. GET /audit/export -------------------------------------------------


def test_export_json(client):
    token, user = bootstrap(client)

    create_audit_log(client.application, user["id"])

    resp = client.get("/api/v1/audit/export?format=json", headers=auth_headers(token))
    assert resp.status_code == 200
    assert "application/json" in resp.content_type
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert len(data) >= 1


def test_export_csv(client):
    token, user = bootstrap(client)

    create_audit_log(client.application, user["id"])

    resp = client.get("/api/v1/audit/export?format=csv", headers=auth_headers(token))
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    content = resp.data.decode("utf-8")
    assert "id" in content
    assert "action" in content


# -- 5. Unauthenticated access --------------------------------------------


def test_unauthenticated_list(client):
    resp = client.get("/api/v1/audit/")
    assert resp.status_code == 401


def test_unauthenticated_export(client):
    resp = client.get("/api/v1/audit/export")
    assert resp.status_code == 401
