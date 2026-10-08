"""Initialisation commands for setting up the system.

Usage::

    flask init setup                    # Initialise database + seed permissions
    flask init setup --with-demo        # Also create demo user (owner@demo.com / demo1234)
"""

import click
from datetime import datetime, timezone

from app.extensions import db
from app.core.constants import ALL_PERMISSIONS, DEFAULT_ROLES


def register_init_commands(app):
    """Register ``flask init`` command group."""

    @app.cli.group()
    def init():
        """Initialise the system."""

    @init.command("setup")
    @click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
    @click.option("--with-demo", is_flag=True, help="Create demo user (owner@demo.com / demo1234)")
    @click.option("--owner-email", default=None, help="Owner email")
    @click.option("--first-name", default=None, help="Owner first name")
    @click.option("--last-name", default=None, help="Owner last name")
    @click.option("--password", default=None, help="Owner password")
    def init_setup(confirm, with_demo, owner_email, first_name, last_name, password):
        """Initialise system: create tables, seed permissions, optionally create user."""
        custom_user = owner_email or first_name or last_name or password

        if custom_user:
            if not owner_email:
                owner_email = click.prompt("Owner email")
            if not first_name:
                first_name = click.prompt("First name")
            if not last_name:
                last_name = click.prompt("Last name")
            if not password:
                password = click.prompt("Password", hide_input=True, confirmation_prompt=True)

        total_steps = 2
        if with_demo or custom_user:
            total_steps += 1

        click.echo("=" * 60)
        click.echo("System Initialisation")
        click.echo("=" * 60)

        if not confirm:
            click.echo("\nThis will:")
            click.echo("  1. Create database tables (if needed)")
            click.echo("  2. Seed all permissions")
            if with_demo:
                click.echo("  3. Create demo user with roles (owner@demo.com / demo1234)")
            elif custom_user:
                click.echo(f"  3. Create user '{owner_email}' with roles")
            click.echo("")
            if not click.confirm("Continue with initialisation?"):
                click.echo("Initialisation cancelled.")
                return

        try:
            step = 0

            # Step 1: Create tables
            step += 1
            click.echo(f"\n[{step}/{total_steps}] Creating database tables...")
            db.create_all()
            click.echo("  Done")

            # Step 2: Seed permissions
            step += 1
            click.echo(f"\n[{step}/{total_steps}] Seeding permissions...")
            from app.blueprints.rbac.models import Permission

            created = skipped = 0
            for perm_data in ALL_PERMISSIONS:
                existing = db.session.query(Permission).filter_by(name=perm_data["name"]).first()
                if existing:
                    skipped += 1
                    continue
                db.session.add(Permission(
                    name=perm_data["name"],
                    resource=perm_data["resource"],
                    action=perm_data["action"],
                    description=perm_data["description"],
                ))
                created += 1
            db.session.commit()
            click.echo(f"  Permissions: {created} created, {skipped} skipped")

            # Step 3: Create user (optional)
            if with_demo or custom_user:
                step += 1
                click.echo(f"\n[{step}/{total_steps}] Creating user with roles...")
                from app.blueprints.users.models import User
                from app.blueprints.settings.models import AppSettings
                from app.blueprints.rbac.models import Role, RolePermission, UserRole

                if with_demo:
                    owner_email = "owner@demo.com"
                    first_name = "Demo"
                    last_name = "Owner"
                    password = "demo1234"

                existing_user = db.session.query(User).filter_by(email=owner_email).first()
                if existing_user:
                    click.echo(f"  User '{owner_email}' already exists. Skipping.")
                else:
                    owner = User(
                        email=owner_email,
                        first_name=first_name,
                        last_name=last_name,
                        password_hash="temp",
                        is_superadmin=True,
                    )
                    owner.set_password(password)
                    db.session.add(owner)
                    db.session.flush()

                    # Create app settings if not exists
                    if not db.session.query(AppSettings).first():
                        db.session.add(AppSettings())

                    # Seed roles
                    permissions_map = {p.name: p for p in db.session.query(Permission).all()}
                    roles = {}
                    for role_name, role_data in DEFAULT_ROLES.items():
                        existing_role = db.session.query(Role).filter_by(name=role_name).first()
                        if existing_role:
                            roles[role_name] = existing_role
                            continue

                        role = Role(
                            name=role_name,
                            description=role_data["description"],
                            is_system_role=role_data["is_system_role"],
                            created_by=owner.id,
                        )
                        db.session.add(role)
                        db.session.flush()
                        roles[role_name] = role

                        for perm_name in role_data["permissions"]:
                            perm_obj = permissions_map.get(perm_name)
                            if perm_obj:
                                db.session.add(RolePermission(
                                    role_id=role.id,
                                    permission_id=perm_obj.id,
                                ))

                    db.session.add(UserRole(
                        user_id=owner.id,
                        role_id=roles["Owner"].id,
                        assigned_at=datetime.now(timezone.utc),
                    ))

                    db.session.commit()

                    click.echo(f"  Owner:  {owner_email}")
                    click.echo(f"  Roles:  {', '.join(roles.keys())}")

            click.echo("\n" + "=" * 60)
            click.echo("System initialisation completed successfully!")
            click.echo("=" * 60)

            if with_demo:
                click.echo(f"\nDemo user created:")
                click.echo(f"  Email:    owner@demo.com")
                click.echo(f"  Password: demo1234")
            elif custom_user:
                click.echo(f"\nUser created:")
                click.echo(f"  Email:    {owner_email}")
            else:
                click.echo("\nNext steps:")
                click.echo("  1. Run with --with-demo to create a demo user")
                click.echo("  2. Or POST /api/v1/auth/bootstrap to create via API")

        except Exception as e:
            db.session.rollback()
            click.echo(f"\nInitialisation failed: {e}", err=True)
            raise SystemExit(1)
