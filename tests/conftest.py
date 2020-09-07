# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import logging

import pytest
from webtest import TestApp

from registry.app import create_app
from registry.donor.models import DonationCenter
from registry.extensions import db as _db
from registry.user.models import User


@pytest.fixture
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


@pytest.fixture
def db(app):
    """Create database for the tests."""
    _db.app = app
    with app.app_context():
        _db.create_all()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    _db.drop_all()


@pytest.fixture
def test_data(db):
    objects = [
        DonationCenter(title="FM", slug="fm"),
        DonationCenter(title="Trinex", slug="trinec"),
    ]
    db.session.add_all(objects)
    db.session.commit()


@pytest.fixture
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
