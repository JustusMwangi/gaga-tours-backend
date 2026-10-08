"""Smoke tests for Phase 5A: RBAC Schemas + Service + Routes.

Tests all 9 endpoints: role CRUD, permission listing, user-role management.
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


# -- 0. Imports, blueprint registration, route count ------------------------


def test_imports(app):
    """All schemas, service, routes import correctly."""
    from app.blueprints.rbac.schemas import (
        AssignRoleSchema,
        CreateRoleSchema,
        PermissionListResponseSchema,
        PermissionResponseSchema,
        RoleDetailResponseSchema,
        RoleListResponseSchema,
        RoleResponseSchema,
        UpdateRoleSchema,
        UserRoleResponseSchema,
        UserRolesResponseSchema,
    )
    from app.blueprints.rbac.services import RBACService
    from app.blueprints.rbac.routes import rbac_bp


def test_blueprint_registered(app):
    """RBAC blueprint is registered at /api/v1/rbac."""
    rules = [r.rule for r in app.url_map.iter_rules()]
    assert "/api/v1/rbac/roles" in rules


def test_route_count(app):
    """Blueprint has 9 route+method combos."""
    rules = [r for r in app.url_map.iter_rules()
             if r.rule.startswith("/api/v1/rbac")]
    methods = set()
    for r in rules:
        for m in r.methods:
            if m not in ("OPTIONS", "HEAD"):
                methods.add((r.rule, m))
    assert len(methods) == 9, f"Expected 9 route+method combos, got {len(methods)}: {methods}"


# -- 1. GET /roles (list system roles from bootstrap) ----------------------


def test_list_roles(client):
    """Should list the 4 system roles created by bootstrap."""
    token, user = bootstrap(client)

    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "roles" in data
    assert data["total"] == 4
    role_names = [r["name"] for r in data["roles"]]
    assert "Owner" in role_names
    assert "Admin" in role_names
    assert "Member" in role_names
    assert "Viewer" in role_names


# -- 2. GET /roles/<id> (detail with permissions) --------------------------


def test_get_role_detail(client):
    """Should return role with permissions and user_count."""
    token, user = bootstrap(client)

    # Get the Owner role
    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    owner_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Owner")

    resp = client.get(
        f"/api/v1/rbac/roles/{owner_role['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Owner"
    assert data["is_system_role"] is True
    assert "permissions" in data
    assert len(data["permissions"]) > 0
    assert "user_count" in data
    assert data["user_count"] >= 1  # At least the bootstrap user


def test_get_role_not_found(client):
    """Should return 404 for non-existent role."""
    token, user = bootstrap(client)

    resp = client.get(
        "/api/v1/rbac/roles/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


# -- 3. POST /roles (create custom role) -----------------------------------


def test_create_role(client):
    """Should create a custom role with permissions."""
    token, user = bootstrap(client)

    # Get some permission IDs
    resp = client.get("/api/v1/rbac/permissions", headers=auth_headers(token))
    perms = resp.get_json()["permissions"]
    perm_ids = [p["id"] for p in perms[:3]]

    resp = client.post("/api/v1/rbac/roles", headers=auth_headers(token), json={
        "name": "Custom Role",
        "description": "A test custom role",
        "permission_ids": perm_ids,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Custom Role"
    assert data["description"] == "A test custom role"
    assert data["is_system_role"] is False
    assert len(data["permissions"]) == 3


def test_create_role_duplicate_name(client):
    """Should reject duplicate role names."""
    token, user = bootstrap(client)

    client.post("/api/v1/rbac/roles", headers=auth_headers(token), json={
        "name": "Duplicate Role",
    })
    resp = client.post("/api/v1/rbac/roles", headers=auth_headers(token), json={
        "name": "Duplicate Role",
    })
    assert resp.status_code == 409


# -- 4. PUT /roles/<id> (update role) --------------------------------------


def test_update_role(client):
    """Should update role name and permissions."""
    token, user = bootstrap(client)

    # Create a custom role
    resp = client.post("/api/v1/rbac/roles", headers=auth_headers(token), json={
        "name": "Updatable Role",
    })
    role_id = resp.get_json()["id"]

    # Get some permissions
    resp = client.get("/api/v1/rbac/permissions", headers=auth_headers(token))
    perm_ids = [p["id"] for p in resp.get_json()["permissions"][:2]]

    resp = client.put(
        f"/api/v1/rbac/roles/{role_id}",
        headers=auth_headers(token),
        json={"name": "Updated Role", "permission_ids": perm_ids},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "Updated Role"
    assert len(data["permissions"]) == 2


def test_cannot_rename_system_role(client):
    """Should reject renaming a system role."""
    token, user = bootstrap(client)

    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    owner_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Owner")

    resp = client.put(
        f"/api/v1/rbac/roles/{owner_role['id']}",
        headers=auth_headers(token),
        json={"name": "Renamed Owner"},
    )
    assert resp.status_code == 403


# -- 5. DELETE /roles/<id> (soft delete) ------------------------------------


def test_cannot_delete_system_role(client):
    """Should reject deleting a system role."""
    token, user = bootstrap(client)

    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    owner_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Owner")

    resp = client.delete(
        f"/api/v1/rbac/roles/{owner_role['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_delete_custom_role(client):
    """Should soft-delete a custom role."""
    token, user = bootstrap(client)

    resp = client.post("/api/v1/rbac/roles", headers=auth_headers(token), json={
        "name": "Deletable Role",
    })
    role_id = resp.get_json()["id"]

    resp = client.delete(
        f"/api/v1/rbac/roles/{role_id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert "deleted" in resp.get_json()["message"].lower()

    # Should no longer appear in list
    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    role_ids = [r["id"] for r in resp.get_json()["roles"]]
    assert role_id not in role_ids


# -- 6. GET /permissions ---------------------------------------------------


def test_list_permissions(client):
    """Should list all seeded permissions."""
    token, user = bootstrap(client)

    resp = client.get("/api/v1/rbac/permissions", headers=auth_headers(token))
    assert resp.status_code == 200
    data = resp.get_json()
    assert "permissions" in data
    assert data["total"] > 0
    # Check structure
    perm = data["permissions"][0]
    assert "id" in perm
    assert "name" in perm
    assert "resource" in perm
    assert "action" in perm


def test_list_permissions_filter_by_resource(client):
    """Should filter permissions by resource."""
    token, user = bootstrap(client)

    resp = client.get(
        "/api/v1/rbac/permissions?resource=users",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] > 0
    for perm in data["permissions"]:
        assert perm["resource"] == "users"


# -- 7. GET /users/<id>/roles ---------------------------------------------


def test_get_user_roles(client):
    """Should return the bootstrap user's role assignments."""
    token, user = bootstrap(client)

    resp = client.get(
        f"/api/v1/rbac/users/{user['id']}/roles",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["user_id"] == user["id"]
    assert "roles" in data
    assert len(data["roles"]) >= 1  # Owner role assigned at bootstrap


# -- 8. POST /users/<id>/roles (assign role) -------------------------------


def test_assign_role_to_user(client):
    """Should assign a role to a user."""
    token, user = bootstrap(client)

    # Get the Viewer role
    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    viewer_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Viewer")

    resp = client.post(
        f"/api/v1/rbac/users/{user['id']}/roles",
        headers=auth_headers(token),
        json={"role_id": viewer_role["id"]},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    role_ids = [r["role_id"] for r in data["roles"]]
    assert viewer_role["id"] in role_ids


def test_assign_role_duplicate(client):
    """Should reject duplicate role assignment."""
    token, user = bootstrap(client)

    # Get the Viewer role
    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    viewer_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Viewer")

    # Assign once
    client.post(
        f"/api/v1/rbac/users/{user['id']}/roles",
        headers=auth_headers(token),
        json={"role_id": viewer_role["id"]},
    )
    # Assign again --- should conflict
    resp = client.post(
        f"/api/v1/rbac/users/{user['id']}/roles",
        headers=auth_headers(token),
        json={"role_id": viewer_role["id"]},
    )
    assert resp.status_code == 409


# -- 9. DELETE /users/<id>/roles/<role_id> (revoke role) -------------------


def test_revoke_role_from_user(client):
    """Should revoke a role from a user."""
    token, user = bootstrap(client)

    # Get the Viewer role and assign it
    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    viewer_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Viewer")

    client.post(
        f"/api/v1/rbac/users/{user['id']}/roles",
        headers=auth_headers(token),
        json={"role_id": viewer_role["id"]},
    )

    # Revoke
    resp = client.delete(
        f"/api/v1/rbac/users/{user['id']}/roles/{viewer_role['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert "revoked" in resp.get_json()["message"].lower()


# -- 9b. Cannot revoke last Owner ------------------------------------------


def test_cannot_revoke_own_owner_role(client):
    """Should reject removing the Owner role from yourself."""
    token, user = bootstrap(client)

    # Get the Owner role
    resp = client.get("/api/v1/rbac/roles", headers=auth_headers(token))
    owner_role = next(r for r in resp.get_json()["roles"] if r["name"] == "Owner")

    # Try to revoke own Owner role --- should fail with 400
    resp = client.delete(
        f"/api/v1/rbac/users/{user['id']}/roles/{owner_role['id']}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 400
    assert "yourself" in resp.get_json()["message"]


# -- 10. Unauthenticated access --------------------------------------------


def test_unauthenticated_roles(client):
    """Should return 401 for unauthenticated access."""
    resp = client.get("/api/v1/rbac/roles")
    assert resp.status_code == 401


def test_unauthenticated_permissions(client):
    """Should return 401 for unauthenticated access."""
    resp = client.get("/api/v1/rbac/permissions")
    assert resp.status_code == 401
