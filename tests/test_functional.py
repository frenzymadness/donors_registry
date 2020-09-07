# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
from pathlib import Path

from conftest import login

from registry.donor.models import Batch, Record


class TestPublicInterface:
    """Test the stuff visible for annonymous users."""

    def test_home_page(self, testapp):
        """Login form appears on home page."""
        # Goes to homepage
        res = testapp.get("/")
        # Check content and status code
        assert "Evidence dárců ČČK Frýdek-Místek" in res
        assert res.status_code == 200

    def test_import_page_401(self, testapp):
        testapp.get("/import/", status=401)


class TestLoggingIn:
    """Login."""

    def test_log_in(self, user, testapp):
        """Login successful."""
        # Goes to homepage
        res = testapp.get("/")
        # Fills out login form
        form = res.forms["loginForm"]
        form["email"] = user.email
        form["password"] = user.test_password
        # Submits
        res = form.submit().follow()
        assert "Přihlášení proběhlo úspěšně" in res
        res.status_code == 200


class TestImport:
    """Test of imports"""

    def test_valid_input(self, user, testapp, test_data):
        input_data = Path("tests/data/valid_import.txt").read_text()
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get("/import/")
        form = res.forms["importForm"]
        form["input_data"] = input_data
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200

        assert Record.query.count() == existing_records + new_records
        assert Batch.query.count() == existing_batches + 1
