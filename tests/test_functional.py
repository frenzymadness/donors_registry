# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
import re
from pathlib import Path
from random import choice

import pytest
from flask import url_for
from sqlalchemy.exc import IntegrityError

from registry.donor.models import (
    AwardedMedals,
    Batch,
    DonorsOverview,
    Note,
    Record,
)
from registry.list.models import DonationCenter, Medals

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

    def test_pages_401(self, testapp, db):
        """Test pages which requires login."""
        testapp.get(url_for("donor.import_data"), status=401)
        testapp.get(url_for("donor.overview"), status=401)
        testapp.get(url_for("donor.award_prep", medal_slug="br"), status=401)
        testapp.get(url_for("donor.batch_list"), status=401)
        testapp.get(url_for("donor.batch_detail", id=1), status=401)
        testapp.get(url_for("donor.download_batch", id=1), status=401)


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


class TestImport:
    """Test of imports"""

    def test_valid_input(self, user, testapp):
        input_data = Path("tests/data/valid_import.txt").read_text()
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("donor.import_data"))
        form = res.form
        form["input_data"] = input_data
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200

        assert Record.query.count() == existing_records + new_records
        assert Batch.query.count() == existing_batches + 1

    def test_repairable_input(self, user, testapp):
        """Tests an input file the import machinery should be able
        repair automatically without any manual assistance from user"""
        input_data = Path("tests/data/repairable_import.txt").read_text()
        new_records = 12  # 15 lines in file - 2 empty lines - 1 without free donations
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("donor.import_data"))
        form = res.form
        form["input_data"] = input_data
        res = form.submit()
        assert res.status_code == 200
        form = res.form
        # There is one valid line
        assert len(form["valid_lines"].value.splitlines()) == 1
        # And the rest are invalid lines
        assert len(form["invalid_lines"].value.splitlines()) == new_records - 1
        # We have to have as many lines of errors as invalid lines
        assert len(form["invalid_lines_errors"].value.splitlines()) == len(
            form["invalid_lines"].value.splitlines()
        )
        # But everything should be fixed by the app so we should be
        # ready to just submit the form again and see a sucessful import
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200
        assert Record.query.count() == existing_records + new_records
        assert Batch.query.count() == existing_batches + 1

    def test_invalid_input(self, user, testapp):
        """Tests an invalid import the app cannot fix automaticaly"""
        input_data = Path("tests/data/invalid_import.txt").read_text()
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()
        login(user, testapp)
        res = testapp.get(url_for("donor.import_data"))
        form = res.form
        form["input_data"] = input_data
        # No matter how many times we submit the form because it contains
        # invalid records so they never be imported
        for _ in range(5):
            res = form.submit()
            assert res.status_code == 200
            form = res.form
            assert len(form["valid_lines"].value.splitlines()) == 0
            # And the rest are invalid lines
            assert len(form["invalid_lines"].value.splitlines()) == 5
            # We have to have as many lines of errors as invalid lines
            assert len(form["invalid_lines_errors"].value.splitlines()) == len(
                form["invalid_lines"].value.splitlines()
            )
            assert "Import proběhl úspěšně" not in res
        assert Record.query.count() == existing_records
        assert Batch.query.count() == existing_batches

    def test_valid_manual_input(self, user, testapp):
        input_data = Path("tests/data/valid_import.txt").read_text()
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.filter(
            Batch.donation_center_id.is_(None)
        ).count()

        login(user, testapp)
        res = testapp.get(url_for("donor.import_data"))
        form = res.form
        form["input_data"] = input_data
        form.fields["donation_center_id"][0].select(-1)
        assert (
            form.fields["donation_center_id"][0].selectedIndex
            == len(form.fields["donation_center_id"][0].options) - 1
        )
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200

        assert Record.query.count() == existing_records + new_records
        assert (
            Batch.query.filter(Batch.donation_center_id.is_(None)).count()
            == existing_batches + 1
        )

    def test_invalid_donation_center(self, user, testapp):
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("donor.import_data"))
        form = res.form
        form.fields["donation_center_id"][0].options.append(("666", False, "malicious"))
        form.fields["donation_center_id"][0].select(666)
        res = form.submit()
        assert "Odběrné místo - Not a valid choice" in res

        assert Record.query.count() == existing_records
        assert Batch.query.count() == existing_batches

    @pytest.mark.parametrize(
        "input_file",
        (
            "tests/data/valid_import_multiple_rc.txt",
            "tests/data/valid_import_multiple_rc_dups.txt",
        ),
    )
    def test_valid_import_with_multiple_rc(self, input_file, user, testapp):
        input_data = Path(input_file).read_text()
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("donor.import_data"))
        form = res.form
        form["input_data"] = input_data
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200

        assert Record.query.count() == existing_records + new_records
        assert Batch.query.count() == existing_batches + 1

        DonorsOverview.query.get("205225299").donation_count_total == 70
        DonorsOverview.query.get("1860231599").donation_count_total == 6


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


class TestMedals:
    # TODO: Find a better way to parametrize this
    @pytest.mark.parametrize("medal_id", range(1, 8))
    def test_award_medal(self, user, testapp, medal_id):
        medal = Medals.query.get(medal_id)
        awarded = AwardedMedals.query.count()
        awarded_do = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).count()
        login(user, testapp)
        page = testapp.get(url_for("donor.award_prep", medal_slug=medal.slug))
        try:
            checkboxes = len(page.form.fields["rodne_cislo"])
        except KeyError:
            pytest.skip("No medals to award.")
        uncheck = checkboxes // 4
        # Uncheck some checkboxes
        for i in range(uncheck):
            page.form.fields["rodne_cislo"][i].checked = False
        # Award first batch of medals
        page = page.form.submit().follow()
        awarded_new = AwardedMedals.query.count()
        awarded_do_new = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).count()
        assert (
            checkboxes - uncheck == awarded_new - awarded == awarded_do_new - awarded_do
        )
        try:
            assert len(page.form.fields["rodne_cislo"]) == uncheck
        except KeyError:
            return  # No more checkboxes, no reason to continue
        # Award the remaining medals
        page = page.form.submit().follow()
        # No checkboxes left
        assert page.form.fields.get("rodne_cislo", None) is None
        awarded_new = AwardedMedals.query.count()
        awarded_do_new = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).count()
        assert checkboxes == awarded_new - awarded == awarded_do_new - awarded_do

    # TODO: Find a better way to parametrize this
    @pytest.mark.parametrize("medal_id", range(1, 8))
    def test_remove_medal(self, user, testapp, medal_id):
        medal = Medals.query.get(medal_id)
        do = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).first()
        login(user, testapp)
        detail = testapp.get(url_for("donor.detail", rc=do.rodne_cislo))
        # Medal is there
        nav_end = detail.text.find("</nav>")  # to search text after navigation bar only
        assert detail.status_code == 200
        assert detail.text.find(medal.title, nav_end) != -1
        # Find the right form to remove it
        for index, form in detail.forms.items():
            if form.fields["medal_id"][0].value == str(medal.id):
                break
        else:
            assert False, "Cannot find the right form for the medal"
        detail = form.submit().follow()
        # Medal is not there anymore
        assert detail.status_code == 200
        assert "Medaile byla úspěšně odebrána" in detail
        assert detail.text.find(medal.title, nav_end) == -1
        do = DonorsOverview.query.get(do.rodne_cislo)
        assert getattr(do, "awarded_medal_" + medal.slug) is False
        assert AwardedMedals.query.get((do.rodne_cislo, medal.id)) is None


class TestDetail:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(50))
    def test_detail(self, user, testapp, rodne_cislo):
        """Just a simple test that the detail page loads for some random donors"""
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        assert res.status_code == 200
        assert "<td></td>" not in res
        # Check that the sum of the donations is eqal to the total count
        donations_list = re.search(r"<h2>Počty darování</h2>(.*?)</ul>", res.text, re.S)
        numbers = re.findall(r">.*?: (\d+)</", donations_list.group())
        numbers = list(map(int, numbers))
        assert sum(numbers[:-1]) == numbers[-1]

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(5))
    def test_save_update_note(self, user, testapp, rodne_cislo):
        existing_notes = Note.query.count()
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        # New note
        form = res.forms["noteForm"]
        assert form.fields["note"][0].value == ""
        form.fields["note"][0].value = "Lorem ipsum"
        res = form.submit().follow()
        assert res.status_code == 200
        assert "Poznámka uložena." in res
        assert "Lorem ipsum</textarea>" in res.text
        assert Note.query.count() == existing_notes + 1
        # Update existing
        form = res.forms["noteForm"]
        assert form.fields["note"][0].value == "Lorem ipsum"
        form.fields["note"][0].value += " dolor sit amet,"
        res = form.submit().follow()
        assert res.status_code == 200
        assert "Poznámka uložena." in res
        assert "Lorem ipsum dolor sit amet,</textarea>" in res.text
        assert Note.query.count() == existing_notes + 1


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


class TestBatch:
    @pytest.mark.parametrize("batch_id", range(1, 11))
    def test_batch_list(self, user, testapp, batch_id):
        """Just a simple test that the detail page loads for some random donors"""
        login(user, testapp)
        res = testapp.get(url_for("donor.batch_list"))
        assert res.status_code == 200
        batch = Batch.query.get(batch_id)
        assert f">{batch.id}</a></td>" in res
        assert f"<td>{batch.imported_at}</td>" in res
        assert "<td></td>" not in res

    @pytest.mark.parametrize("unused", range(1, 6))
    def test_delete_batch(self, user, testapp, unused):
        login(user, testapp)
        res = testapp.get(url_for("donor.batch_list"))
        # Take and submit random form
        form = choice(res.forms)
        batch_id = form.fields["batch_id"][0].value
        res = form.submit().follow()
        assert "Dávka smazána." in res
        assert Batch.query.get(batch_id) is None
        assert Record.query.filter(Record.batch_id == batch_id).count() == 0

    @pytest.mark.parametrize("unused", range(1, 11))
    def test_batch_detail(self, user, testapp, unused):
        login(user, testapp)
        batch_id = choice([b.id for b in Batch.query.all()])
        res = testapp.get(url_for("donor.batch_detail", id=batch_id))
        batch = Batch.query.get(batch_id)
        records_count = Record.query.filter(Record.batch_id == batch_id).count()
        if batch.donation_center:
            assert f"Dávka z {batch.donation_center.title}" in res
        else:
            assert "Manuální dávka importována" in res
        assert res.text.count("<td>") == records_count * res.text.count("<th>")

    @pytest.mark.parametrize("unused", range(1, 11))
    def test_download_batch(self, user, testapp, unused):
        login(user, testapp)
        batch_id = choice([b.id for b in Batch.query.all()])
        res = testapp.get(url_for("donor.batch_detail", id=batch_id))
        records_count = Record.query.filter(Record.batch_id == batch_id).count()
        batch_file = res.click(description="Stáhnout soubor s dávkou")
        assert records_count == len(batch_file.text.splitlines())
        assert ";;" not in batch_file.text
        assert ";\n" not in batch_file.text
