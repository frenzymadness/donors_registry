# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
import pytest
from flask import url_for
from sqlalchemy.exc import IntegrityError

from registry.donor.models import Batch, Record

from .helpers import login


class TestPublicInterface:
    """Test the stuff visible for annonymous users."""

    def test_home_page(self, testapp, db):
        """Login form appears on home page."""
        # Goes to homepage
        res = testapp.get("/")
        # Check content and status code
        assert "Evidence dárců ČČK Frýdek-Místek" in res
        assert res.status_code == 200

    def test_home_page_status_code(self, testapp, db):
        """Login form appears on home page."""
        # Goes to homepage
        res = testapp.get("/418", status=418)
        # Check content and status code
        assert "Evidence dárců ČČK Frýdek-Místek" in res
        assert res.status_code == 418


class TestErrorInterface:
    """Test 404 and 401 pages"""

    values_404 = [
        5005165649,
        5055172826,
        0,
        "hello",
        "aa",
    ]

    endpoints_keys_404 = (
        ("donor.detail", "rc"),
        ("donor.award_prep", "medal_slug"),
        ("batch.batch_detail", "id"),
    )

    testcases_404 = {}
    for endpoint, key in endpoints_keys_404:
        for value in values_404:
            testname = f"{endpoint}-{value}"
            testcases_404[testname] = {
                "endpoint": endpoint,
                "kwargs": {key: value},
            }

    @pytest.mark.parametrize("case_name", testcases_404)
    def test_dynamic_urls_404(self, user, testapp, case_name):
        login(user, testapp)
        case = self.testcases_404[case_name]
        res = testapp.get(url_for(case["endpoint"], **case["kwargs"])).follow(
            status=404
        )

        assert res.status_code == 404
        assert "404 - Stránka, kterou hledáte, neexistuje." in res.text

    testcases_401 = [
        ("batch.import_data", {}),
        ("batch.batch_list", {}),
        ("batch.batch_detail", {"id": 1}),
        ("batch.download_batch", {"id": 1}),
        ("donor.overview", {}),
        ("donor.award_prep", {"medal_slug": "br"}),
    ]

    @pytest.mark.parametrize(("endpoint, kwargs"), testcases_401)
    def test_pages_401(self, testapp, endpoint, kwargs):
        """Test pages which requires login."""
        res = testapp.get(url_for(endpoint, **kwargs)).follow(status=401)

        assert res.status_code == 401
        assert (
            "401 - Nejste přihlášeni. Pro pokračování se prosím přihlaste." in res.text
        )


class TestLoggingIn:
    """Login."""

    def test_log_in_log_out(self, user, testapp):
        """Login successful."""
        # Goes to homepage
        res = testapp.get("/")
        # Fills out login form
        form = res.form
        form["email"] = user.email
        form["password"] = user.test_password
        # Submits
        res = form.submit().follow()
        assert "Přihlášení proběhlo úspěšně" in res
        res.status_code == 200
        res = res.click(description="Odhlásit se").follow()
        assert "Odhlášení bylo úspěšné." in res
        res.status_code == 200

    def test_invalid_user(self, user, testapp):
        res = testapp.get("/")
        form = res.form
        form["email"] = "foobarbaz"
        form["password"] = "foobarbaz"
        res = form.submit()
        assert "Neznámý uživatel" in res

    def test_invalid_pass(self, user, testapp):
        res = testapp.get("/")
        form = res.form
        form["email"] = user.email
        form["password"] = "foobarbaz"
        res = form.submit()
        assert "Nesprávné heslo" in res

    def test_empty_input(self, user, testapp):
        res = testapp.get("/")
        form = res.form
        form["email"] = None
        form["password"] = None
        res = form.submit()
        assert "E-mail - Toto pole je povinné!" in res

    def test_inactive_user(self, user, testapp, db):
        res = testapp.get("/")
        user.active = False
        db.session.add(user)
        db.session.commit()
        form = res.form
        form["email"] = user.email
        form["password"] = user.test_password
        res = form.submit()
        assert "Neaktivní uživatel" in res
        user.active = True
        db.session.add(user)
        db.session.commit()


class TestHomePage:
    def test_home_page(self, user, testapp):
        login(user, testapp)
        res = testapp.get("/")
        # Make sure there are no missing numbers on the homepage
        assert "<b></b>" not in res
        assert "<td></td>" not in res


class TestDatabase:
    def test_foreign_key_check(self, db):
        """
        Test that foreign keys works as expected.
        This is mainly needed for SQLite where foreing keys are not checked by default
        """
        record = Record.query.get(1)
        batch = Batch.query.get(record.batch_id)
        # Deleting a batch with associated record should not be possible
        db.session.delete(batch)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
