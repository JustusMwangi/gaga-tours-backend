"""Application factory with all blueprint registrations."""

import os

from flask import Flask

from app.config import config_by_name
from app.extensions import cors, db, limiter, mail, migrate


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # ── Extensions ──────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    limiter.init_app(app)

    # CORS — read allowed origins from config, wildcard in dev only
    cors_origins = app.config.get("CORS_ORIGINS", "")
    if cors_origins:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    elif app.debug:
        origins = "*"
    else:
        origins = []
    cors.init_app(
        app,
        resources={r"/*": {"origins": origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    )

    # ── Celery ──────────────────────────────────────────────────────
    from app.core.celery import init_celery
    init_celery(app)

    # ── File storage (MinIO) ─────────────────────────────────────
    from app.core.storage import init_storage
    init_storage(app)

    # ── Models (for Alembic autogenerate) ───────────────────────────
    with app.app_context():
        from app.blueprints.audit import models as audit_models  # noqa: F401
        from app.blueprints.auth import models as auth_models  # noqa: F401
        from app.blueprints.notifications import models as notif_models  # noqa: F401
        from app.blueprints.rbac import models as rbac_models  # noqa: F401
        from app.blueprints.settings import models as settings_models  # noqa: F401
        from app.blueprints.users import models as user_models  # noqa: F401
        from app.blueprints.files import models as file_models  # noqa: F401
        from app.blueprints.customers import models as customer_models  # noqa: F401
        from app.blueprints.bookings import models as booking_models  # noqa: F401
        from app.blueprints.inquiries import models as inquiry_models  # noqa: F401
        from app.blueprints.tours import models as tour_models  # noqa: F401
        from app.blueprints.invoices import models as invoice_models  # noqa: F401
        from app.blueprints.quotations import models as quotation_models  # noqa: F401
        from app.blueprints.public import models as public_models  # noqa: F401
        from app.blueprints.consent import models as consent_models  # noqa: F401
        from app.core import models as core_models  # noqa: F401

    # ── Blueprints ──────────────────────────────────────────────────
    from app.blueprints.audit import audit_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.health import health_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.rbac import rbac_bp
    from app.blueprints.settings import settings_bp
    from app.blueprints.users import users_bp
    from app.blueprints.files import files_bp
    from app.blueprints.customers import customers_bp
    from app.blueprints.bookings import bookings_bp
    from app.blueprints.inquiries import inquiries_bp
    from app.blueprints.tours import tours_bp
    from app.blueprints.invoices import invoices_bp
    from app.blueprints.quotations import quotations_bp
    from app.blueprints.public import public_bp

    app.register_blueprint(audit_bp, url_prefix="/api/v1/audit")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(rbac_bp, url_prefix="/api/v1/rbac")
    app.register_blueprint(users_bp, url_prefix="/api/v1/users")
    app.register_blueprint(notifications_bp, url_prefix="/api/v1/notifications")
    app.register_blueprint(settings_bp, url_prefix="/api/v1/settings")
    app.register_blueprint(files_bp, url_prefix="/api/v1/files")
    app.register_blueprint(customers_bp, url_prefix="/api/v1/customers")
    app.register_blueprint(bookings_bp, url_prefix="/api/v1/bookings")
    app.register_blueprint(inquiries_bp, url_prefix="/api/v1/inquiries")
    app.register_blueprint(tours_bp, url_prefix="/api/v1/tours")
    app.register_blueprint(invoices_bp, url_prefix="/api/v1/invoices")
    app.register_blueprint(quotations_bp, url_prefix="/api/v1/quotations")
    app.register_blueprint(public_bp, url_prefix="/api/v1/public")
    app.register_blueprint(health_bp)  # mounted at /health (no /api/v1 prefix)

    # ── Middleware & error handlers ─────────────────────────────────
    from app.core.middleware import init_middleware
    init_middleware(app)

    # ── CLI commands ────────────────────────────────────────────────
    from app.cli import init_cli
    init_cli(app)

    return app
