"""CLI commands for management.

Available command groups::

    flask init setup                    # Initialise system (run first)
    flask seed permissions              # Seed all permissions
    flask seed roles                    # Seed default roles
    flask seed roles-sync              # Sync role permissions
    flask db-commands create            # Create tables via migrations
    flask db-commands drop              # Drop all tables
    flask db-commands reset             # Drop all tables, re-run migrations
"""


def init_cli(app):
    """Register all CLI command groups."""
    from app.cli.init_commands import register_init_commands
    from app.cli.reset_commands import register_db_commands
    from app.cli.seed_commands import register_seed_commands

    register_init_commands(app)
    register_db_commands(app)
    register_seed_commands(app)
