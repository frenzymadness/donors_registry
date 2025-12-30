import locale
from functools import cmp_to_key
from operator import ge, le

import pytest
from flask import url_for
from sqlalchemy import and_, extract
from sqlalchemy.sql import text

from registry.donor.models import (
    AwardedMedals,
    DonorsOverview,
    IgnoredDonors,
    Note,
)
from registry.extensions import db
from registry.list.models import Medals
from tests.fixtures import delete_note_if_exists, sample_of_rc, skip_if_ignored

from .helpers import login


class TestDataTablesBackend:
    @pytest.mark.parametrize("limit", (5, 10, 20, 50))
    def test_json_backend_limit(self, user, testapp, limit):
        # This is very limited subset of what datatables frontend
        # sends to the backend but it's enough for the simple test.
        params = {
            "draw": "1",
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "start": "0",
            "length": str(limit),
            "search[value]": "",
            "search[regex]": "false",
        }
        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == limit

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_json_backend_search(self, user, testapp, rodne_cislo):
        skip_if_ignored(rodne_cislo)
        params = {
            "draw": "1",
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "start": "0",
            "length": "10",
            "search[value]": rodne_cislo,
            "search[regex]": "false",
        }
        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 1
        assert res.json["data"][0]["rodne_cislo"] == rodne_cislo

    def test_json_backend_search_by_note(self, user, testapp):
        note_text = "FooBarBaz note special text"
        while True:
            first_rodne_cislo, second_rodne_cislo = sample_of_rc(2)
            if not (
                db.session.get(IgnoredDonors, first_rodne_cislo)
                or db.session.get(IgnoredDonors, second_rodne_cislo)
            ):
                break

        note = Note(rodne_cislo=first_rodne_cislo, note=note_text)
        db.session.add(note)
        db.session.commit()

        params = {
            "draw": "1",
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "start": "0",
            "length": "10",
            "search[value]": "FooBarBaz",
            "search[regex]": "false",
        }
        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 1
        # Note is now structured data
        assert res.json["data"][0]["note"]["raw"] == note_text
        assert res.json["data"][0]["note"]["other"] == note_text
        assert res.json["data"][0]["note"]["emails"] == []
        assert res.json["data"][0]["note"]["phones"] == []

        note = Note(rodne_cislo=second_rodne_cislo, note=note_text)
        db.session.add(note)
        db.session.commit()

        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 2
        # Note is now structured data
        assert res.json["data"][1]["note"]["raw"] == note_text
        assert res.json["data"][1]["note"]["other"] == note_text
        assert res.json["data"][1]["note"]["emails"] == []
        assert res.json["data"][1]["note"]["phones"] == []

    def test_json_backend_note_structure(self, user, testapp):
        """Test that note data is properly structured with emails, phones, and other text."""
        rodne_cislo = next(sample_of_rc(1))
        skip_if_ignored(rodne_cislo)
        delete_note_if_exists(rodne_cislo)

        # Create note with mixed content
        note_text = "Please contact: jan.novak@seznam.cz or call 602123456\nImportant: Check blood type!"
        note = Note(rodne_cislo=rodne_cislo, note=note_text)
        db.session.add(note)
        db.session.commit()

        params = {
            "draw": "1",
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "start": "0",
            "length": "100",
            "search[value]": rodne_cislo,
            "search[regex]": "false",
        }

        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 1

        note_data = res.json["data"][0]["note"]

        # Check structured data
        assert note_data["raw"] == note_text
        assert "jan.novak@seznam.cz" in note_data["emails"]
        assert "602123456" in note_data["phones"]
        assert "Check blood type!" in note_data["other"]
        # Emails and phones should be removed from "other"
        assert "jan.novak@seznam.cz" not in note_data["other"]
        assert "602123456" not in note_data["other"]

    @pytest.mark.parametrize("direction", ("asc", "desc"))
    def test_json_backend_order_by_rodne_cislo(self, user, testapp, direction):
        params = {
            "draw": "1",
            "order[0][column]": list(DonorsOverview.frontend_column_names.keys()).index(
                "rodne_cislo"
            ),
            "order[0][dir]": direction,
            "start": "0",
            "length": "10",
            "search[value]": "",
            "search[regex]": "false",
        }
        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 10

        do = DonorsOverview.query.order_by(
            getattr(DonorsOverview.rodne_cislo, direction)()
        ).limit(10)

        for index, donor in enumerate(do):
            assert res.json["data"][index]["rodne_cislo"] == donor.rodne_cislo

    @pytest.mark.parametrize("direction", ("asc", "desc"))
    def test_json_backend_order_by_donations(self, user, testapp, direction):
        params = {
            "draw": "1",
            "order[0][column]": list(DonorsOverview.frontend_column_names.keys()).index(
                "donations"
            ),
            "order[0][dir]": direction,
            "start": "0",
            "length": "10",
            "search[value]": "",
            "search[regex]": "false",
        }
        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 10

        if direction == "asc":
            compare_function = le
        else:
            compare_function = ge

        for previous, current in zip(res.json["data"], res.json["data"][1:]):
            assert compare_function(
                previous["donations"]["total"], current["donations"]["total"]
            )

    @pytest.mark.parametrize("direction", ("asc", "desc"))
    def test_json_backend_order_by_medals(self, user, testapp, direction):
        params = {
            "draw": "1",
            "order[0][column]": list(DonorsOverview.frontend_column_names.keys()).index(
                "last_award"
            ),
            "order[0][dir]": direction,
            "start": "0",
            "length": "10",
            "search[value]": "",
            "search[regex]": "false",
        }
        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 10

        if direction == "asc":
            expected_first_medal = "Žádné"
        else:
            # Find the highest medal at least one donor has
            for medal in Medals.query.order_by(Medals.minimum_donations.desc()).all():
                if (
                    AwardedMedals.query.filter(
                        AwardedMedals.medal_id == medal.id,
                        AwardedMedals.rodne_cislo.notin_(
                            IgnoredDonors.query.with_entities(IgnoredDonors.rodne_cislo)
                        ),
                    ).count()
                    > 0
                ):
                    expected_first_medal = medal.title
                    break

        assert res.json["data"][0]["last_award"] == expected_first_medal

    @pytest.mark.parametrize("medal_id", range(1, 8))
    def test_json_backend_for_awarded_medals(self, user, testapp, db, medal_id):
        params = {
            "draw": "1",
            "order[0][column]": "0",
            "order[0][dir]": "asc",
            "start": "0",
            "length": "100000",
            "search[value]": "",
            "search[regex]": "false",
        }

        login(user, testapp)
        medal = db.session.get(Medals, medal_id)
        # Set some random awarded_at to some awarded medals
        db.session.execute(
            text(
                "UPDATE awarded_medals SET awarded_at = :awarded_at "
                "WHERE rodne_cislo LIKE :rc_start;"
            ),
            params={"awarded_at": "2000-12-12 13:13:13", "rc_start": "8%"},
        )
        db.session.execute(
            text(
                "UPDATE awarded_medals SET awarded_at = :awarded_at "
                "WHERE rodne_cislo LIKE :rc_start;"
            ),
            params={"awarded_at": "2020-12-12 13:13:13", "rc_start": "9%"},
        )
        db.session.commit()

        for year in 0, 2000, 2020:
            res = testapp.get(
                url_for("donor.overview_data", year=year, medal_slug=medal.slug),
                params=params,
            )
            assert res.status_code == 200
            awarded_medals = AwardedMedals.query.filter(
                and_(
                    extract("year", AwardedMedals.awarded_at) == (year or None),
                    AwardedMedals.medal_id == medal.id,
                )
            ).all()

            count = DonorsOverview.query.filter(
                DonorsOverview.rodne_cislo.in_(
                    [am.rodne_cislo for am in awarded_medals]
                )
            ).count()

            assert len(res.json["data"]) == count

    @pytest.mark.parametrize("direction", ("asc", "desc"))
    def test_json_backend_order_by_utf_8(self, user, testapp, direction):
        params = {
            "draw": "1",
            "order[0][column]": list(DonorsOverview.frontend_column_names.keys()).index(
                "last_name"
            ),
            "order[0][dir]": direction,
            "start": "0",
            "length": "100",
            "search[value]": "",
            "search[regex]": "false",
        }

        login(user, testapp)
        res = testapp.get(url_for("donor.overview_data"), params=params)
        assert res.status_code == 200
        assert len(res.json["data"]) == 100

        last_names = [d["last_name"] for d in res.json["data"]]

        if direction == "asc":
            reverse = False
        else:
            reverse = True

        assert (
            sorted(last_names, key=cmp_to_key(locale.strcoll), reverse=reverse)
            == last_names
        )

    @pytest.mark.parametrize(
        ("last_names", "count"),
        (
            (("Čermáková", "čermáková", "ČERMÁKOVÁ", "ČeRmÁkOvÁ", "čErMáKoVÁ"), 9),
            (("Blažek", "blažek", "BLAŽEK", "BlAžEk", "bLaŽeK"), 13),
            (("Bláha", "bláha", "BLÁHA", "BlÁhA", "bLáHa"), 6),
            (("Bláhová", "bláhová", "BLÁHOVÁ", "BlÁhOvÁ", "bLáHoVá"), 15),
        ),
    )
    def test_json_backend_search_by_utf_8(self, user, testapp, last_names, count):
        params = {
            "draw": "1",
            "order[0][column]": 0,
            "order[0][dir]": "asc",
            "start": "0",
            "length": "100",
            "search[value]": "",
            "search[regex]": "false",
        }

        login(user, testapp)
        for last_name in last_names:
            params["search[value]"] = last_name
            res = testapp.get(url_for("donor.overview_data"), params=params)
            assert res.status_code == 200
            assert len(res.json["data"]) == count
