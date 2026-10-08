"""Seed commands for populating the database with initial data.

Usage::

    flask seed permissions              # Seed all permissions
    flask seed roles                    # Seed default roles
    flask seed roles-sync              # Sync role permissions
    flask seed all                      # Run all seed commands
"""

import click

from app.core.constants import ALL_PERMISSIONS, DEFAULT_ROLES
from app.extensions import db


def register_seed_commands(app):
    """Register ``flask seed`` command group."""

    @app.cli.group()
    def seed():
        """Seed database with initial data."""

    @seed.command("permissions")
    def seed_permissions():
        """Seed all permissions into the database (idempotent)."""
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
        click.echo(f"Permissions seeded: {created} created, {skipped} already exist")

    @seed.command("roles")
    def seed_roles():
        """Seed default roles (idempotent)."""
        from app.blueprints.rbac.models import Permission, Role, RolePermission

        created_roles = skipped_roles = 0

        for role_name, role_data in DEFAULT_ROLES.items():
            existing = db.session.query(Role).filter_by(name=role_name).first()
            if existing:
                skipped_roles += 1
                click.echo(f"  Skipped: {role_name} (already exists)")
                continue

            role = Role(
                name=role_name,
                description=role_data["description"],
                is_system_role=role_data["is_system_role"],
            )
            db.session.add(role)
            db.session.flush()

            perm_count = 0
            for perm_name in role_data["permissions"]:
                permission = db.session.query(Permission).filter_by(name=perm_name).first()
                if permission:
                    db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                    perm_count += 1

            created_roles += 1
            click.echo(f"  Created: {role_name} ({perm_count} permissions)")

        db.session.commit()
        click.echo(f"\nRoles seeded: {created_roles} created, {skipped_roles} skipped")

    @seed.command("roles-sync")
    @click.option("--dry-run", is_flag=True, help="Preview changes without applying")
    def seed_roles_sync(dry_run):
        """Sync existing roles with latest DEFAULT_ROLES permissions."""
        from app.blueprints.rbac.models import Permission, Role, RolePermission

        total_added = 0

        for role_name, role_data in DEFAULT_ROLES.items():
            role = db.session.query(Role).filter_by(name=role_name).first()
            if not role:
                click.echo(f"  {role_name}: Not found (run 'flask seed roles' first)")
                continue

            current_perms = {
                rp.permission.name
                for rp in db.session.query(RolePermission).filter_by(role_id=role.id).all()
                if rp.permission
            }
            expected_perms = set(role_data["permissions"])
            missing = expected_perms - current_perms

            if not missing:
                click.echo(f"  {role_name}: Up to date ({len(current_perms)} permissions)")
                continue

            click.echo(f"  {role_name}: Adding {len(missing)} missing permissions:")
            for perm_name in sorted(missing):
                click.echo(f"    + {perm_name}")
                if not dry_run:
                    permission = db.session.query(Permission).filter_by(name=perm_name).first()
                    if permission:
                        db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                        total_added += 1

        if not dry_run:
            db.session.commit()
            click.echo(f"\nSync complete: {total_added} permissions added")
        else:
            click.echo("\n[DRY RUN] Run without --dry-run to apply changes.")

    @seed.command("all")
    def seed_all():
        """Run all seed commands."""
        from app.blueprints.rbac.models import Permission, Role, RolePermission

        # 1. Permissions
        click.echo("=" * 50)
        click.echo("1. Seeding permissions...")
        click.echo("=" * 50)
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
        click.echo(f"  Permissions: {created} created, {skipped} already exist\n")

        # 2. Roles
        click.echo("=" * 50)
        click.echo("2. Seeding roles...")
        click.echo("=" * 50)
        for role_name, role_data in DEFAULT_ROLES.items():
            existing = db.session.query(Role).filter_by(name=role_name).first()
            if existing:
                continue
            role = Role(
                name=role_name,
                description=role_data["description"],
                is_system_role=role_data["is_system_role"],
            )
            db.session.add(role)
            db.session.flush()
            perm_count = 0
            for perm_name in role_data["permissions"]:
                permission = db.session.query(Permission).filter_by(name=perm_name).first()
                if permission:
                    db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                    perm_count += 1
            click.echo(f"    Created: {role_name} ({perm_count} permissions)")
        db.session.commit()
        click.echo()

        # 3. Sync role permissions
        click.echo("=" * 50)
        click.echo("3. Syncing role permissions...")
        click.echo("=" * 50)
        total_added = 0
        for role_name, role_data in DEFAULT_ROLES.items():
            role = db.session.query(Role).filter_by(name=role_name).first()
            if not role:
                continue
            current_perms = {
                rp.permission.name
                for rp in db.session.query(RolePermission).filter_by(role_id=role.id).all()
                if rp.permission
            }
            missing = set(role_data["permissions"]) - current_perms
            for perm_name in missing:
                permission = db.session.query(Permission).filter_by(name=perm_name).first()
                if permission:
                    db.session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                    total_added += 1
        db.session.commit()
        click.echo(f"  Permissions synced: {total_added} added\n")

        click.echo("=" * 50)
        click.echo("All seeds complete!")
        click.echo("=" * 50)
