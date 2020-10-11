# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import logging
import os
from pathlib import Path

import pytest
from flask_migrate import Migrate, upgrade
from webtest import TestApp

from registry.app import create_app
from registry.extensions import db as _db
from registry.user.models import User

from .utils import test_data_medals, test_data_records


@pytest.fixture(scope="session")
def app():
    """Create application for the tests."""
    _app = create_app("tests.settings")
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def testapp(app):
    """Create Webtest app."""
    return TestApp(app)


@pytest.fixture(scope="session")
def db(app):
    """Create database for the tests."""
    _db.app = app
    with app.app_context():
        migrate = Migrate()
        migrate.init_app(app, _db)
        upgrade()

    test_data_records(_db, limit=100)
    test_data_medals(_db)

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    # Remove test DB file
    os.unlink(Path("registry/test.sqlite"))


@pytest.fixture(scope="session")
def user(db):
    """Create user for the tests."""
    user = User("test@example.com", "test123")
    user.test_password = "test123"
    user.active = True
    db.session.add(user)
    db.session.commit()
    return user


def login(user, testapp):
    res = testapp.post(
        "/", params={"email": user.email, "password": user.test_password}
    ).follow()
    assert "Přihlášení proběhlo úspěšně" in res
