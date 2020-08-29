# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""


class TestPublicInterface:
    """Test the stuff visible for annonymous users."""

    def test_home_page(self, testapp):
        """Login form appears on home page."""
        # Goes to homepage
        res = testapp.get("/")
        # Check content and status code
        assert "Evidence dárců ČČK Frýdek-Místek" in res
        assert res.status_code == 200


class TestLoggingIn:
    """Login."""

    def test_log_in(self, user, testapp):
        """Login successful."""
        # Goes to homepage
        res = testapp.get("/")
        # Fills out login form in navbar
        form = res.forms["loginForm"]
        form["email"] = user.email
        form["password"] = "test123"
        # Submits
        res = form.submit()
        assert res.status_code == 200
