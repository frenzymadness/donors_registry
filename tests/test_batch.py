from random import choice

import pytest
from flask import url_for

from registry.donor.models import Batch, Record
from registry.extensions import db

from .helpers import login


class TestBatch:
    @pytest.mark.parametrize("batch_id", range(1, 11))
    def test_batch_list(self, user, testapp, batch_id):
        """Just a simple test that the detail page loads for some random donors"""
        login(user, testapp)
        res = testapp.get(url_for("batch.batch_list"))
        format_time = testapp.app.jinja_env.filters["format_time"]
        assert res.status_code == 200
        batch = db.session.get(Batch, batch_id)
        assert f">{batch.id}</a></td>" in res
        assert f">{format_time(batch.imported_at)}</td>" in res
        assert "<td></td>" not in res

    @pytest.mark.parametrize("unused", range(1, 6))
    def test_delete_batch(self, user, testapp, unused):
        login(user, testapp)
        res = testapp.get(url_for("batch.batch_list"))
        # Take and submit random form
        form = choice(list(res.forms.values()))
        batch_id = form.fields["batch_id"][0].value
        res = form.submit().follow()
        assert "Dávka smazána." in res
        assert db.session.get(Batch, batch_id) is None
        assert Record.query.filter(Record.batch_id == batch_id).count() == 0

    def test_delete_nonexisting_batch(self, user, testapp):
        login(user, testapp)
        res = testapp.get(url_for("batch.batch_list"))
        form = res.forms[0]
        # Modify the form content to point to batch that
        # does not exist.
        form.fields["batch_id"][0].value = 99999
        res = form.submit().follow()
        assert "Při odebrání dávky došlo k chybě." in res

    @pytest.mark.parametrize("unused", range(1, 11))
    def test_batch_detail(self, user, testapp, unused):
        login(user, testapp)
        batch_id = choice([b.id for b in Batch.query.all()])
        res = testapp.get(url_for("batch.batch_detail", id=batch_id))
        batch = db.session.get(Batch, batch_id)
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
        res = testapp.get(url_for("batch.batch_detail", id=batch_id))
        records_count = Record.query.filter(Record.batch_id == batch_id).count()
        batch_file = res.click(description="Stáhnout soubor s dávkou")
        assert records_count == len(batch_file.text.splitlines())
        assert ";;" not in batch_file.text
        assert ";\n" not in batch_file.text

    def test_download_batch_compare_file(self, user, testapp):
        login(user, testapp)
        res = testapp.get(url_for("batch.batch_detail", id=7))
        batch_file = res.click(description="Stáhnout soubor s dávkou")
        with open(
            "tests/data/batch7_downloaded.txt", encoding="utf-8", newline=""
        ) as f:
            content_to_compare = f.read()
        assert batch_file.text == content_to_compare
