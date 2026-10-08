"""Permission constants and default role definitions for the RBAC system.

Permissions follow the naming convention: resource.action
These are code-defined and seeded into the database via the bootstrap flow.

Domain-specific permissions can be added in their own blueprint constants
or appended to ALL_PERMISSIONS later.

Usage::

    from app.core.constants import Permissions

    @require_permission(Permissions.USERS_CREATE)
    def create_user():
        ...
"""


class Permissions:
    """Permission constants, organised by resource domain."""

    # ── User Management ──────────────────────────────────────────────
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DELETE = "users.delete"
    USERS_MANAGE_ROLES = "users.manage_roles"

    # ── Role & Permission Management ─────────────────────────────────
    ROLES_VIEW = "roles.view"
    ROLES_CREATE = "roles.create"
    ROLES_EDIT = "roles.edit"
    ROLES_DELETE = "roles.delete"
    PERMISSIONS_VIEW = "permissions.view"

    # ── Settings & Configuration ─────────────────────────────────────
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"

    # ── Reports & Analytics ──────────────────────────────────────────
    REPORTS_VIEW = "reports.view"
    REPORTS_EXPORT = "reports.export"
    ANALYTICS_VIEW = "analytics.view"

    # ── Audit Logging ────────────────────────────────────────────────
    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"

    # ── Notifications ────────────────────────────────────────────────
    NOTIFICATIONS_VIEW = "notifications.view"
    NOTIFICATIONS_MANAGE = "notifications.manage"

    # ── File Storage ─────────────────────────────────────────────────
    FILES_VIEW = "files.view"
    FILES_UPLOAD = "files.upload"
    FILES_DOWNLOAD = "files.download"
    FILES_DELETE = "files.delete"

    # ── Customers ────────────────────────────────────────────────────
    CUSTOMERS_VIEW = "customers.view"
    CUSTOMERS_MANAGE = "customers.manage"

    # ── Bookings ─────────────────────────────────────────────────────
    BOOKINGS_VIEW = "bookings.view"
    BOOKINGS_MANAGE = "bookings.manage"

    # ── Tours ────────────────────────────────────────────────────────
    TOURS_VIEW = "tours.view"
    TOURS_MANAGE = "tours.manage"

    # ── Inquiries ────────────────────────────────────────────────────
    INQUIRIES_VIEW = "inquiries.view"
    INQUIRIES_MANAGE = "inquiries.manage"

    # ── Invoices ─────────────────────────────────────────────────────
    INVOICES_VIEW = "invoices.view"
    INVOICES_MANAGE = "invoices.manage"

    # ── Quotations ───────────────────────────────────────────────────
    QUOTATIONS_VIEW = "quotations.view"
    QUOTATIONS_MANAGE = "quotations.manage"


# ── Full permission list (for seeding) ──────────────────────────────────

ALL_PERMISSIONS = [
    # Users
    {"name": Permissions.USERS_VIEW, "resource": "users", "action": "view", "description": "View user list and details"},
    {"name": Permissions.USERS_CREATE, "resource": "users", "action": "create", "description": "Invite or create new users"},
    {"name": Permissions.USERS_EDIT, "resource": "users", "action": "edit", "description": "Edit user details and profile"},
    {"name": Permissions.USERS_DELETE, "resource": "users", "action": "delete", "description": "Deactivate or remove users"},
    {"name": Permissions.USERS_MANAGE_ROLES, "resource": "users", "action": "manage_roles", "description": "Assign or revoke user roles"},
    # Roles
    {"name": Permissions.ROLES_VIEW, "resource": "roles", "action": "view", "description": "View roles and permissions"},
    {"name": Permissions.ROLES_CREATE, "resource": "roles", "action": "create", "description": "Create custom roles"},
    {"name": Permissions.ROLES_EDIT, "resource": "roles", "action": "edit", "description": "Edit role details and permissions"},
    {"name": Permissions.ROLES_DELETE, "resource": "roles", "action": "delete", "description": "Delete custom roles"},
    {"name": Permissions.PERMISSIONS_VIEW, "resource": "permissions", "action": "view", "description": "View available permissions"},
    # Settings
    {"name": Permissions.SETTINGS_VIEW, "resource": "settings", "action": "view", "description": "View system settings"},
    {"name": Permissions.SETTINGS_EDIT, "resource": "settings", "action": "edit", "description": "Edit system settings"},
    # Reports
    {"name": Permissions.REPORTS_VIEW, "resource": "reports", "action": "view", "description": "View business reports"},
    {"name": Permissions.REPORTS_EXPORT, "resource": "reports", "action": "export", "description": "Export report data"},
    {"name": Permissions.ANALYTICS_VIEW, "resource": "analytics", "action": "view", "description": "View analytics dashboards"},
    # Audit
    {"name": Permissions.AUDIT_VIEW, "resource": "audit", "action": "view", "description": "View audit logs"},
    {"name": Permissions.AUDIT_EXPORT, "resource": "audit", "action": "export", "description": "Export audit logs"},
    # Notifications
    {"name": Permissions.NOTIFICATIONS_VIEW, "resource": "notifications", "action": "view", "description": "View notifications"},
    {"name": Permissions.NOTIFICATIONS_MANAGE, "resource": "notifications", "action": "manage", "description": "Manage notification preferences"},
    # Files
    {"name": Permissions.FILES_VIEW, "resource": "files", "action": "view", "description": "View file list and metadata"},
    {"name": Permissions.FILES_UPLOAD, "resource": "files", "action": "upload", "description": "Upload files"},
    {"name": Permissions.FILES_DOWNLOAD, "resource": "files", "action": "download", "description": "Download files"},
    {"name": Permissions.FILES_DELETE, "resource": "files", "action": "delete", "description": "Delete files"},
    # Customers
    {"name": Permissions.CUSTOMERS_VIEW, "resource": "customers", "action": "view", "description": "View customer list and details"},
    {"name": Permissions.CUSTOMERS_MANAGE, "resource": "customers", "action": "manage", "description": "Create, edit, and delete customers"},
    # Bookings
    {"name": Permissions.BOOKINGS_VIEW, "resource": "bookings", "action": "view", "description": "View booking list and details"},
    {"name": Permissions.BOOKINGS_MANAGE, "resource": "bookings", "action": "manage", "description": "Create, edit, and manage bookings"},
    # Tours
    {"name": Permissions.TOURS_VIEW, "resource": "tours", "action": "view", "description": "View tours, categories, destinations, dates, and gallery"},
    {"name": Permissions.TOURS_MANAGE, "resource": "tours", "action": "manage", "description": "Create, edit, and delete tours and related resources"},
    # Inquiries
    {"name": Permissions.INQUIRIES_VIEW, "resource": "inquiries", "action": "view", "description": "View inquiries"},
    {"name": Permissions.INQUIRIES_MANAGE, "resource": "inquiries", "action": "manage", "description": "Create, edit, and convert inquiries"},
    # Invoices
    {"name": Permissions.INVOICES_VIEW, "resource": "invoices", "action": "view", "description": "View invoices and payments"},
    {"name": Permissions.INVOICES_MANAGE, "resource": "invoices", "action": "manage", "description": "Create, edit, and manage invoices and payments"},
    # Quotations
    {"name": Permissions.QUOTATIONS_VIEW, "resource": "quotations", "action": "view", "description": "View quotations"},
    {"name": Permissions.QUOTATIONS_MANAGE, "resource": "quotations", "action": "manage", "description": "Create, edit, and manage quotations"},
]


# ── Default roles (seeded on bootstrap) ────────────────────────────────

DEFAULT_ROLES = {
    "Owner": {
        "description": "Full access to all resources. Cannot be deleted.",
        "is_system_role": True,
        "permissions": [p["name"] for p in ALL_PERMISSIONS],
    },
    "Admin": {
        "description": "Administrative access — users, roles, settings, reports, audit.",
        "is_system_role": True,
        "permissions": [
            Permissions.USERS_VIEW,
            Permissions.USERS_CREATE,
            Permissions.USERS_EDIT,
            Permissions.USERS_DELETE,
            Permissions.USERS_MANAGE_ROLES,
            Permissions.ROLES_VIEW,
            Permissions.ROLES_CREATE,
            Permissions.ROLES_EDIT,
            Permissions.ROLES_DELETE,
            Permissions.PERMISSIONS_VIEW,
            Permissions.SETTINGS_VIEW,
            Permissions.SETTINGS_EDIT,
            Permissions.REPORTS_VIEW,
            Permissions.REPORTS_EXPORT,
            Permissions.ANALYTICS_VIEW,
            Permissions.AUDIT_VIEW,
            Permissions.AUDIT_EXPORT,
            Permissions.NOTIFICATIONS_VIEW,
            Permissions.NOTIFICATIONS_MANAGE,
            Permissions.FILES_VIEW,
            Permissions.FILES_UPLOAD,
            Permissions.FILES_DOWNLOAD,
            Permissions.FILES_DELETE,
            Permissions.CUSTOMERS_VIEW,
            Permissions.CUSTOMERS_MANAGE,
            Permissions.BOOKINGS_VIEW,
            Permissions.BOOKINGS_MANAGE,
            Permissions.TOURS_VIEW,
            Permissions.TOURS_MANAGE,
            Permissions.INQUIRIES_VIEW,
            Permissions.INQUIRIES_MANAGE,
            Permissions.INVOICES_VIEW,
            Permissions.INVOICES_MANAGE,
            Permissions.QUOTATIONS_VIEW,
            Permissions.QUOTATIONS_MANAGE,
        ],
    },
    "Member": {
        "description": "Standard team member with operational access.",
        "is_system_role": True,
        "permissions": [
            Permissions.USERS_VIEW,
            Permissions.ROLES_VIEW,
            Permissions.SETTINGS_VIEW,
            Permissions.REPORTS_VIEW,
            Permissions.NOTIFICATIONS_VIEW,
            Permissions.FILES_VIEW,
            Permissions.FILES_UPLOAD,
            Permissions.FILES_DOWNLOAD,
            Permissions.CUSTOMERS_VIEW,
            Permissions.CUSTOMERS_MANAGE,
            Permissions.BOOKINGS_VIEW,
            Permissions.BOOKINGS_MANAGE,
            Permissions.TOURS_VIEW,
            Permissions.TOURS_MANAGE,
            Permissions.INQUIRIES_VIEW,
            Permissions.INQUIRIES_MANAGE,
            Permissions.INVOICES_VIEW,
            Permissions.INVOICES_MANAGE,
            Permissions.QUOTATIONS_VIEW,
            Permissions.QUOTATIONS_MANAGE,
        ],
    },
    "Viewer": {
        "description": "Read-only access to view data without modification.",
        "is_system_role": True,
        "permissions": [
            Permissions.USERS_VIEW,
            Permissions.ROLES_VIEW,
            Permissions.REPORTS_VIEW,
            Permissions.FILES_VIEW,
            Permissions.FILES_DOWNLOAD,
            Permissions.CUSTOMERS_VIEW,
            Permissions.BOOKINGS_VIEW,
            Permissions.TOURS_VIEW,
            Permissions.INQUIRIES_VIEW,
            Permissions.INVOICES_VIEW,
            Permissions.QUOTATIONS_VIEW,
        ],
    },
}
