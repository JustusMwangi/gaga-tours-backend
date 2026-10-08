"""Public-facing API blueprint (unauthenticated, read-only + inquiry submission)."""

from app.blueprints.public.routes import public_bp

__all__ = ["public_bp"]
