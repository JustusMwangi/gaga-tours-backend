"""Smoke tests for Phase 3A: Users CRUD.

Tests all 7 endpoints and verifies repository extensions, blueprint
registration, and route wiring.
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
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# -- 0. Imports and blueprint registration ----------------------------------


def test_imports(app):
    """All repos, schemas, service, routes import correctly."""
    from app.blueprints.rbac.repositories import (
        RoleRepository,
        UserRoleRepository,
    )
    from app.blueprints.users.repositories import UserRepository
    from app.blueprints.users.schemas import (
        AdminUpdateUserSchema,
        InviteUserSchema,
        UpdateProfileSchema,
        UserDetailResponseSchema,
        UserListQuerySchema,
        UserListResponseSchema,
    )
    from app.blueprints.users.services import UserService
    from app.blueprints.users.routes import users_bp


def test_blueprint_registered(app):
    """users blueprint is registered at /api/v1/users."""
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/v1/users/me" in rules
    assert "/api/v1/users/" in rules
    assert "/api/v1/users/invite" in rules


def test_route_count(app):
    """Blueprint has the expected number of routes."""
    rules = [r for r in app.url_map.iter_rules() if r.rule.startswith("/api/v1/users")]
    # /me (GET,PUT), / (GET), /<id> (GET,PUT,DELETE), /invite (POST)
    # = 7 route+method combos
    methods = set()
    for r in rules:
        for m in r.methods:
            if m not in ("OPTIONS", "HEAD"):
                methods.add((r.rule, m))
    assert len(methods) == 7, f"Expected 7 route+method combos, got {len(methods)}: {methods}"


# -- 1. GET /me -------------------------------------------------------------


def test_get_me(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/users/me", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email"] == "owner@test.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "Owner"
    assert "roles" in data
    # Owner should have at least the "Owner" role
    role_names = [r["name"] for r in data["roles"]]
    assert "Owner" in role_names


def test_get_me_unauthenticated(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


# -- 2. PUT /me -------------------------------------------------------------


def test_update_me_name(client):
    token, user = bootstrap(client)

    resp = client.put("/api/v1/users/me", headers=auth_headers(token), json={
        "first_name": "Updated",
        "last_name": "Name",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"


def test_update_me_password(client):
    token, user = bootstrap(client)

    resp = client.put("/api/v1/users/me", headers=auth_headers(token), json={
        "current_password": "Password123",
        "new_password": "NewPassword456",
    })
    assert resp.status_code == 200

    # Verify new password works by logging in
    resp = client.post("/api/v1/auth/login", json={
        "email": "owner@test.com",
        "password": "NewPassword456",
    })
    assert resp.status_code == 200


def test_update_me_wrong_current_password(client):
    token, user = bootstrap(client)

    resp = client.put("/api/v1/users/me", headers=auth_headers(token), json={
        "current_password": "WrongPassword",
        "new_password": "NewPassword456",
    })
    assert resp.status_code == 400


# -- 3. POST /invite --------------------------------------------------------


def test_invite_user(client):
    token, user = bootstrap(client)

    resp = client.post("/api/v1/users/invite", headers=auth_headers(token), json={
        "email": "newuser@test.com",
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["email"] == "newuser@test.com"
    assert "token" in data
    assert "invite_url" in data


def test_invite_duplicate(client):
    token, user = bootstrap(client)

    client.post("/api/v1/users/invite", headers=auth_headers(token), json={
        "email": "dup@test.com",
    })
    resp = client.post("/api/v1/users/invite", headers=auth_headers(token), json={
        "email": "dup@test.com",
    })
    assert resp.status_code == 409


def test_invite_existing_member(client):
    token, user = bootstrap(client)

    resp = client.post("/api/v1/users/invite", headers=auth_headers(token), json={
        "email": "owner@test.com",
    })
    assert resp.status_code == 409


# -- 4. GET /users ----------------------------------------------------------


def test_list_users(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/users/", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["page"] == 1
    assert "pages" in data


def test_list_users_search(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/users/?search=owner", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] >= 1


def test_list_users_no_results(client):
    token, user = bootstrap(client)

    resp = client.get("/api/v1/users/?search=nonexistent", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 0


# -- 5. GET /users/<id> -----------------------------------------------------


def test_get_user_detail(client):
    token, user = bootstrap(client)

    resp = client.get(f"/api/v1/users/{user['id']}", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["email"] == "owner@test.com"
    assert "roles" in data


def test_get_user_not_found(client):
    token, user = bootstrap(client)

    resp = client.get(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# -- 6. PUT /users/<id> -----------------------------------------------------


def test_admin_update_user(client):
    token, user = bootstrap(client)

    # Invite and accept a second user to update
    resp = client.post("/api/v1/users/invite", headers=auth_headers(token), json={
        "email": "member@test.com",
    })
    invite_token = resp.get_json()["token"]

    resp = client.post("/api/v1/auth/accept-invite", json={
        "token": invite_token,
        "first_name": "Member",
        "last_name": "User",
        "password": "Password123",
    })
    assert resp.status_code == 201
    member_id = resp.get_json()["user"]["id"]

    # Admin updates the member's name
    resp = client.put(
        f"/api/v1/users/{member_id}",
        headers=auth_headers(token),
        json={"first_name": "Updated", "last_name": "Member"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["first_name"] == "Updated"


def test_admin_cannot_deactivate_self_via_update(client):
    token, user = bootstrap(client)

    resp = client.put(
        f"/api/v1/users/{user['id']}",
        headers=auth_headers(token),
        json={"is_active": False},
    )
    assert resp.status_code == 400


# -- 7. DELETE /users/<id> --------------------------------------------------


def test_deactivate_user(client):
    token, user = bootstrap(client)

    # Invite + accept a user to deactivate
    resp = client.post("/api/v1/users/invite", headers=auth_headers(token), json={
        "email": "deactivate@test.com",
    })
    invite_token = resp.get_json()["token"]

    resp = client.post("/api/v1/auth/accept-invite", json={
        "token": invite_token,
        "first_name": "Deactivate",
        "last_name": "Me",
        "password": "Password123",
    })
    assert resp.status_code == 201
    target_id = resp.get_json()["user"]["id"]

    # Deactivate the user
    resp = client.delete(
        f"/api/v1/users/{target_id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert "deactivated" in resp.get_json()["message"].lower()

    # Verify user no longer appears in active list
    resp = client.get("/api/v1/users/?is_active=true", headers=auth_headers(token))
    user_ids = [u["id"] for u in resp.get_json()["users"]]
    assert target_id not in user_ids


def test_cannot_deactivate_self(client):
    token, user = bootstrap(client)

    resp = client.delete(
        f"/api/v1/users/{user['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
