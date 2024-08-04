# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import logging
from itertools import cycle
from pathlib import Path
from random import sample, shuffle
from shutil import copy
from tempfile import NamedTemporaryFile

from flask_migrate import Migrate, upgrade
from pytest import fixture, skip
from sqlalchemy.exc import IntegrityError
from webtest import TestApp

from registry.app import create_app
from registry.donor.models import DonorsOverview, IgnoredDonors
from registry.extensions import db as _db
from registry.user.models import User

from .utils import (
    get_test_data_df,
    test_data_ignored,
    test_data_medals,
    test_data_overrides,
    test_data_records,
)

TEST_RECORDS = 1000  # Number of test imports to use in test database
BACKUP_DB_PATH = Path("instance") / "backup.sqlite"
TEST_DB_PATH = Path("instance") / "test.sqlite"


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


@fixture(scope="function", autouse=True)
def db(app):
    """Create database for the tests."""
    _db.app = app

    # If the backup db exists, use it
    # if not, create it from scratch and save it for other tests
    if BACKUP_DB_PATH.is_file():
        copy(BACKUP_DB_PATH, TEST_DB_PATH)
    else:
        with app.app_context():
            migrate = Migrate()
            migrate.init_app(app, _db)
            upgrade()

        test_data_records(_db, limit=TEST_RECORDS)
        test_data_medals(_db)
        test_data_overrides(_db)
        test_data_ignored(_db, limit=3)

        DonorsOverview.refresh_overview()

        copy(TEST_DB_PATH, BACKUP_DB_PATH)

    yield _db

    # Explicitly close DB connection
    _db.session.close()


@fixture(scope="function")
def user(db):
    """Create user for the tests."""
    user = User("test@example.com", "test123")
    user.test_password = "test123"
    user.active = True
    db.session.add(user)
    # The user might already exists in the db and we cannot
    # combine session-scoped and function-scoped fixtures
    # so we have to be ready for that situation.
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    return user


@fixture(scope="session")
def test_data_df():
    """The same data we have in test database but in form of Pandas DataFrame"""
    return get_test_data_df(TEST_RECORDS)


def sample_of_rc(amount=100):
    """Yields random sample of RC from test data"""
    test_data = get_test_data_df(TEST_RECORDS)
    dcs = test_data.MISTO_ODBERU.unique()
    shuffle(dcs)
    dcs = cycle(dcs)

    for _ in range(amount):
        dc = next(dcs)
        yield sample(list(test_data[test_data.MISTO_ODBERU == dc].RC.unique()), 1)[0]


def skip_if_ignored(rodne_cislo):
    if _db.session.get(IgnoredDonors, rodne_cislo):
        skip("Donor is ignored")


@fixture(scope="session", autouse=True)
def empty_stamp_png():
    with NamedTemporaryFile(
        dir="registry/static/stamps", suffix=".png"
    ), NamedTemporaryFile(dir="registry/static/signatures", suffix=".png"):
        yield
