"""Pytest fixtures: test client, database, and user setup."""

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    """Create a Flask test app with a fresh database."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()
