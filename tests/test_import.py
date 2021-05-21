from pathlib import Path

import pytest
from flask import url_for

from registry.donor.models import Batch, DonorsOverview, Record

from .helpers import login


class TestImport:
    """Test of imports"""

    def test_valid_input(self, user, testapp):
        input_data = Path("tests/data/valid_import.txt").read_text(encoding="utf-8")
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
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
        input_data = Path("tests/data/repairable_import.txt").read_text(
            encoding="utf-8"
        )
        new_records = 12  # 15 lines in file - 2 empty lines - 1 without free donations
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
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
        input_data = Path("tests/data/invalid_import.txt").read_text(encoding="utf-8")
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()
        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
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
            assert len(form["invalid_lines"].value.splitlines()) == 7
            # We have to have as many lines of errors as invalid lines
            assert len(form["invalid_lines_errors"].value.splitlines()) == len(
                form["invalid_lines"].value.splitlines()
            )
            assert "Import proběhl úspěšně" not in res
        assert Record.query.count() == existing_records
        assert Batch.query.count() == existing_batches

    def test_invalid_input_invalid_rcs(self, user, testapp):
        input_data = Path("tests/data/invalid_rc.txt").read_text(encoding="utf-8")
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()
        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = input_data
        res = form.submit()
        assert res.status_code == 200
        form = res.form
        assert len(form["valid_lines"].value.splitlines()) == 0
        assert len(form["invalid_lines"].value.splitlines()) == 5
        assert len(form["invalid_lines_errors"].value.splitlines()) == len(
            form["invalid_lines"].value.splitlines()
        )
        assert "příliš dlouhé" in form["invalid_lines_errors"].value
        assert "příliš krátké" in form["invalid_lines_errors"].value
        assert "chybí" in form["invalid_lines_errors"].value
        assert "není číselné" in form["invalid_lines_errors"].value
        assert "Import proběhl úspěšně" not in res
        assert Record.query.count() == existing_records
        assert Batch.query.count() == existing_batches

    def test_valid_manual_input(self, user, testapp):
        input_data = Path("tests/data/valid_import.txt").read_text(encoding="utf-8")
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.filter(
            Batch.donation_center_id.is_(None)
        ).count()

        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
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
        res = testapp.get(url_for("batch.import_data"))
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
        input_data = Path(input_file).read_text(encoding="utf-8")
        new_records = len(input_data.strip().splitlines())
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = input_data
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200

        assert Record.query.count() == existing_records + new_records
        assert Batch.query.count() == existing_batches + 1

        DonorsOverview.query.get("205225299").donation_count_total == 70
        DonorsOverview.query.get("1860231599").donation_count_total == 6

    def test_zero_donations(self, user, testapp):
        # three lines in the input file end with zero and should
        # be automatically ommited from the import
        ends_with_zero = 3
        input_data = Path("tests/data/valid_import_zeroes.txt").read_text(
            encoding="utf-8"
        )
        new_records = len(input_data.strip().splitlines()) - ends_with_zero
        existing_records = Record.query.count()
        existing_batches = Batch.query.count()

        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = input_data
        res = form.submit().follow()
        assert "Import proběhl úspěšně" in res
        assert res.status_code == 200

        assert Record.query.count() == existing_records + new_records
        assert Batch.query.count() == existing_batches + 1

    def test_empty_input(self, user, testapp):
        """Regression test for issue #118"""
        existing_batches = Batch.query.count()

        # Test regular empty input
        login(user, testapp)
        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = ""
        res = form.submit()

        assert res.status_code == 200
        assert "Vstupní data z odběrného místa - Chybí vstupní data" in res
        assert Batch.query.count() == existing_batches

        # Test empty input for data repair form
        existing_batches = Batch.query.count()
        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = "invalid"
        res = form.submit()

        form = res.form
        form["invalid_lines"] = ""
        res = form.submit()

        assert res.status_code == 200
        assert "Vstupní data z odběrného místa - Chybí vstupní data" in res
        assert Batch.query.count() == existing_batches

    def test_all_zero_donations(self, user, testapp):
        """
        Tests if the system displays a warning for an input with all of the
        donations set to 0
        """
        login(user, testapp)
        expected_msg = (
            "Vstupní data z odběrného místa - Ze vstupních dat není po filtraci"
            + " co importovat"
        )

        # Test a correct but empty input
        existing_batches = Batch.query.count()

        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = "1;a;b;c;d;00000;000;\n2;a;b;c;d;00000;000;0"
        res = form.submit()

        assert res.status_code == 200
        assert expected_msg in res
        assert Batch.query.count() == existing_batches
        # We don't want the data repair form to show up
        assert "Řádky s chybami" not in res

        # Test an input with an invalid line which is then set to 0
        existing_batches = Batch.query.count()

        res = testapp.get(url_for("batch.import_data"))
        form = res.form
        form["input_data"] = "1;a;b;c;d;00000;000;\ninvalid"
        res = form.submit()

        form = res.form
        form["invalid_lines"] = "1;a;b;c;d;00000;000;"
        res = form.submit()

        assert res.status_code == 200
        assert expected_msg in res
        assert Batch.query.count() == existing_batches
        # We don't want the data repair form to show up
        assert "Řádky s chybami" not in res
