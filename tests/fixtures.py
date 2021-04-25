# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import logging
import os
from pathlib import Path
from random import sample

from flask_migrate import Migrate, upgrade
from pytest import fixture
from webtest import TestApp

from registry.app import create_app
from registry.donor.models import DonorsOverview
from registry.extensions import db as _db
from registry.user.models import User

from .utils import get_test_data_df, test_data_medals, test_data_records

TEST_RECORDS = 1000  # Number of test imports to use in test database


@fixture(scope="session")
def app():
    """Create application for the tests."""
    _app = create_app("tests.settings")
    _app.logger.setLevel(logging.CRITICAL)
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@fixture
def testapp(app):
    """Create Webtest app."""
    return TestApp(app)


@fixture(scope="session")
def db(app):
    """Create database for the tests."""
    # If a test fails, it might leave the test database there.
    # Make sure we create a fresh one everytime.
    if Path("registry/test.sqlite").exists():
        os.unlink(Path("registry/test.sqlite"))

    _db.app = app
    with app.app_context():
        migrate = Migrate()
        migrate.init_app(app, _db)
        upgrade()

    test_data_records(_db, limit=TEST_RECORDS)
    test_data_medals(_db)

    DonorsOverview.refresh_overview()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    # Remove test DB file
    os.unlink(Path("registry/test.sqlite"))


@fixture(scope="session")
def user(db):
    """Create user for the tests."""
    user = User("test@example.com", "test123")
    user.test_password = "test123"
    user.active = True
    db.session.add(user)
    db.session.commit()
    return user


@fixture(scope="session")
def test_data_df():
    """The same data we have in test database but in form of Pandas DataFrame"""
    return get_test_data_df(TEST_RECORDS)


def sample_of_rc(amount=100):
    """Yields random sample of RC from test data"""
    for rc in sample(list(get_test_data_df(TEST_RECORDS).RC.unique()), amount):
        yield rc
