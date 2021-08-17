from random import randint

import pytest
from flask import url_for

from registry.donor.models import (
    DonationCenter,
    DonorsOverride,
    DonorsOverview,
)

from .fixtures import sample_of_rc, skip_if_ignored
from .helpers import login


class TestDonorsOverview:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(100))
    def test_refresh_overview(self, rodne_cislo, test_data_df):
        skip_if_ignored(rodne_cislo)
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

        override = DonorsOverride.query.get(rodne_cislo)

        for csv_column, attr in (
            ("JMENO", "first_name"),
            ("PRIJMENI", "last_name"),
            ("ULICE", "address"),
            ("MESTO", "city"),
            ("PSC", "postal_code"),
            ("POJISTOVNA", "kod_pojistovny"),
        ):
            if override and getattr(override, attr):
                assert getattr(donor_overview, attr) == getattr(override, attr)
            else:
                assert last_import[csv_column].values[0] == getattr(
                    donor_overview, attr
                )


class TestIgnore:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_ignore(self, user, testapp, rodne_cislo):
        skip_if_ignored(rodne_cislo)
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


class TestOverride:
    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(5))
    def test_override(self, user, testapp, rodne_cislo):
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))

        old_data = DonorsOverview.query.get(rodne_cislo)

        # Test save
        form = res.forms["donorsOverrideForm"]
        form["first_name"] = "--First--"
        form["last_name"] = "--Last--"
        res = form.submit("save_btn").follow()

        assert "Výjimka uložena" in res
        assert "Jméno: --First--" in res
        assert "Příjmení: --Last--" in res

        # Test repeated save
        form = res.forms["donorsOverrideForm"]
        res = form.submit("save_btn").follow()

        assert "Výjimka uložena" in res
        assert "Jméno: --First--" in res
        assert "Příjmení: --Last--" in res

        # Test removing one field's value but keeping the other
        form = res.forms["donorsOverrideForm"]
        form["first_name"] = ""
        res = form.submit("save_btn").follow()

        assert "Výjimka uložena" in res
        assert ("Jméno: " + str(old_data.first_name)) in res
        assert "Příjmení: --Last--" in res

        # Test deleting the override
        form = res.forms["donorsOverrideForm"]
        res = form.submit("delete_btn").follow()

        assert "Výjimka smazána" in res
        assert ("Jméno: " + str(old_data.first_name)) in res
        assert ("Příjmení: " + str(old_data.last_name)) in res
