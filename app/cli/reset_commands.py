"""Database management commands.

Usage::

    flask db-commands create    # Create tables via migrations
    flask db-commands drop      # Drop all tables
    flask db-commands reset     # Drop all tables, re-run migrations
"""

import click

from app.extensions import db


def register_db_commands(app):
    """Register ``flask db-commands`` command group."""

    @app.cli.group("db-commands")
    def db_commands():
        """Database management commands."""

    @db_commands.command("create")
    def create_db():
        """Create database tables via migrations."""
        from flask_migrate import upgrade

        upgrade()
        click.echo("Database tables created.")

    @db_commands.command("drop")
    def drop_db():
        """Drop all database tables."""
        db.drop_all()
        db.session.execute(db.text("DROP TABLE IF EXISTS alembic_version"))
        db.session.commit()
        click.echo("Database tables dropped.")

    @db_commands.command("reset")
    def reset_db():
        """Reset the database by dropping and re-creating tables.

        After reset, visit the app to bootstrap via the setup page.
        Bootstrap auto-seeds: permissions, plans, roles, and subscription.
        """
        db.drop_all()
        db.session.execute(db.text("DROP TABLE IF EXISTS alembic_version"))
        db.session.commit()
        click.echo("Tables dropped.")

        from flask_migrate import upgrade

        upgrade()
        click.echo("Database has been reset.")
