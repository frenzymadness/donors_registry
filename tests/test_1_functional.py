# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
from random import randint

import pytest
from flask import url_for
from sqlalchemy.exc import IntegrityError

from registry.donor.models import Batch, DonorsOverview, Record
from registry.list.models import DonationCenter

from .fixtures import sample_of_rc
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
        res = testapp.get(url_for(case["endpoint"], **case["kwargs"]), status=404)

        assert res.status_code == 404
        assert "404 Stránka nenalezena" in res.text

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
        testapp.get(url_for(endpoint, **kwargs), status=401)


class TestLoggingIn:
    """Login."""

    def test_log_in(self, user, testapp):
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


class TestHomePage:
    def test_home_page(self, user, testapp):
        login(user, testapp)
        res = testapp.get("/")
        # Make sure there are no missing numbers on the homepage
        assert "<b></b>" not in res
        assert "<td></td>" not in res


class TestDonorsOverview:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(100))
    def test_refresh_overview(self, rodne_cislo, test_data_df):
        # Check of the total amount of donations
        donor_overview = DonorsOverview.query.filter_by(rodne_cislo=rodne_cislo).first()
        last_imports = (
            test_data_df[test_data_df.RC == rodne_cislo]
            .sort_values(by="DATUM_IMPORTU")
            .drop_duplicates(["MISTO_ODBERU"], keep="last")
        )
        total_donations = last_imports.POCET_ODBERU.sum()

        assert donor_overview.donation_count_total == total_donations

        # Check of the partial amounts of donations for each donation center
        donation_centers = DonationCenter.query.all()

        for donation_center_slug in [dc.slug for dc in donation_centers] + ["manual"]:
            try:
                dc_last_count = last_imports.loc[
                    last_imports.MISTO_ODBERU == donation_center_slug, "POCET_ODBERU"
                ].values[0]
            except IndexError:
                dc_last_count = 0
            do_last_count = getattr(
                donor_overview, f"donation_count_{donation_center_slug}"
            )
            assert dc_last_count == do_last_count

        # Check of all other attributes
        last_import = last_imports.tail(1)

        for csv_column, attr in (
            ("JMENO", "first_name"),
            ("PRIJMENI", "last_name"),
            ("ULICE", "address"),
            ("MESTO", "city"),
            ("PSC", "postal_code"),
            ("POJISTOVNA", "kod_pojistovny"),
        ):
            assert last_import[csv_column].values[0] == getattr(donor_overview, attr)


class TestIgnore:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_ignore(self, user, testapp, rodne_cislo):
        login(user, testapp)
        res = testapp.get(url_for("donor.show_ignored"))
        random_reason = str(randint(11111111, 99999999))

        form = res.forms[0]
        form.fields["rodne_cislo"][0].value = rodne_cislo
        form.fields["reason"][0].value = random_reason

        res = form.submit().follow()

        assert rodne_cislo in res.text
        assert random_reason in res.text
        assert "Dárce ignorován." in res.text

        do = testapp.get(url_for("donor.detail", rc=rodne_cislo), status=302)
        assert do.status_code == 302

        res = do.follow()
        assert res.status_code == 200
        assert "Dárce je ignorován" in res.text

        for _, form in res.forms.items():
            if form.fields["rodne_cislo"][0].value == rodne_cislo:
                unignore_form = form
        res = unignore_form.submit().follow()

        assert rodne_cislo not in res.text
        assert random_reason not in res.text
        assert "Dárce již není ignorován." in res.text

        do = testapp.get(url_for("donor.detail", rc=rodne_cislo), status=200)
        assert do.status_code == 200


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
