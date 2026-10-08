"""Smoke tests for Phase 4C: Notifications.

Tests imports, blueprint registration, route wiring, notification CRUD,
mark read, unread count, preferences.
"""

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


def create_notification(app, user_id, title="Test Notification"):
    """Create a notification via the service."""
    from uuid import UUID
    from app.blueprints.notifications.services import NotificationService

    with app.test_request_context():
        return NotificationService.create_notification(
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            title=title,
            message="This is a test notification",
        )


# -- 0. Imports, blueprint registration -----------------------------------


def test_imports(app):
    from app.blueprints.notifications.models import (
        Notification,
        NotificationCategory,
        NotificationChannel,
        NotificationPreference,
        NotificationType,
    )
    from app.blueprints.notifications.schemas import (
        NotificationListQuerySchema,
        NotificationListResponseSchema,
        NotificationResponseSchema,
        UpdatePreferencesSchema,
    )
    from app.blueprints.notifications.services import NotificationService
    from app.blueprints.notifications.routes import notifications_bp


def test_blueprint_registered(app):
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/v1/notifications/" in rules


def test_route_count(app):
    rules = [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/v1/notifications")]
    methods = set()
    for r in rules:
        for m in r.methods:
            if m not in ("OPTIONS", "HEAD"):
                methods.add((r.rule, m))
    assert len(methods) == 8, f"Expected 8 route+method combos, got {len(methods)}: {methods}"


# -- 1. Create notification via service, list it --------------------------


def test_create_and_list_notification(client):
    token, user = bootstrap(client)

    create_notification(client.application, user["id"])

    resp = client.get("/api/v1/notifications/", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1
    assert len(data["notifications"]) >= 1
    assert data["notifications"][0]["title"] == "Test Notification"


def test_list_notifications_empty(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/notifications/", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 0


# -- 2. Get single notification -------------------------------------------


def test_get_notification(client):
    token, user = bootstrap(client)

    notif = create_notification(client.application, user["id"])

    resp = client.get(
        f"/api/v1/notifications/{notif.id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Test Notification"
    assert data["is_read"] is False


def test_get_notification_not_found(client):
    token, user = bootstrap(client)

    resp = client.get(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# -- 3. Mark as read, mark all read, unread count -------------------------


def test_mark_as_read(client):
    token, user = bootstrap(client)

    notif = create_notification(client.application, user["id"])

    resp = client.put(
        f"/api/v1/notifications/{notif.id}/read",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["notification"]["is_read"] is True


def test_mark_all_as_read(client):
    token, user = bootstrap(client)

    create_notification(client.application, user["id"], "Notif 1")
    create_notification(client.application, user["id"], "Notif 2")

    resp = client.put("/api/v1/notifications/read-all", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 2


def test_unread_count(client):
    token, user = bootstrap(client)

    create_notification(client.application, user["id"], "Unread 1")
    create_notification(client.application, user["id"], "Unread 2")

    resp = client.get("/api/v1/notifications/unread-count", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["unread_count"] == 2


# -- 4. Delete notification -----------------------------------------------


def test_delete_notification(client):
    token, user = bootstrap(client)

    notif = create_notification(client.application, user["id"])

    resp = client.delete(
        f"/api/v1/notifications/{notif.id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200

    # Verify it's gone
    resp = client.get(
        f"/api/v1/notifications/{notif.id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# -- 5. Preferences -------------------------------------------------------


def test_get_preferences(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/notifications/preferences", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "preferences" in data
    # Default preferences are auto-created for all 4 categories
    assert len(data["preferences"]) == 4


def test_update_preferences(client):
    token, user = bootstrap(client)

    # First get defaults
    client.get("/api/v1/notifications/preferences", headers=auth_headers(token))

    # Update one category
    resp = client.put(
        "/api/v1/notifications/preferences",
        headers=auth_headers(token),
        json={
            "preferences": [
                {"category": "team", "email_enabled": False},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    team = next(p for p in data["preferences"] if p["category"] == "team")
    assert team["email_enabled"] is False


# -- 6. Unauthenticated access -------------------------------------------


def test_unauthenticated_list(client):
    resp = client.get("/api/v1/notifications/")
    assert resp.status_code == 401


def test_unauthenticated_preferences(client):
    resp = client.get("/api/v1/notifications/preferences")
    assert resp.status_code == 401
