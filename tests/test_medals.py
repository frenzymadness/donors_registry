import re
from datetime import datetime, timedelta

import pytest
from flask import url_for

from registry.donor.models import (
    AwardedMedals,
    Batch,
    DonorsOverview,
    IgnoredDonors,
    Medals,
    Record,
)

from .fixtures import sample_of_rc, skip_if_ignored
from .helpers import login


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
        form = page.forms["awardMedalForm"]
        try:
            checkboxes = len(form.fields["rodne_cislo"])
        except KeyError:
            pytest.skip("No medals to award.")
        uncheck = checkboxes // 4
        # Uncheck some checkboxes
        for i in range(uncheck):
            form.fields["rodne_cislo"][i].checked = False
        # Award first batch of medals
        page = form.submit().follow()
        awarded_new = AwardedMedals.query.count()
        awarded_do_new = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).count()
        assert (
            checkboxes - uncheck == awarded_new - awarded == awarded_do_new - awarded_do
        )

        awarded_medals = AwardedMedals.query.order_by(
            AwardedMedals.awarded_at.desc()
        ).limit(checkboxes - uncheck)
        for awarded_medal in awarded_medals:
            assert awarded_medal.awarded_at.date() == datetime.now().date()

        form = page.forms["awardMedalForm"]

        try:
            assert len(form.fields["rodne_cislo"]) == uncheck
        except KeyError:
            return  # No more checkboxes, no reason to continue
        # Award the remaining medals
        page = form.submit().follow()
        form = page.forms["awardMedalForm"]
        # No checkboxes left
        assert form.fields.get("rodne_cislo", None) is None
        awarded_new = AwardedMedals.query.count()
        awarded_do_new = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).count()
        assert checkboxes == awarded_new - awarded == awarded_do_new - awarded_do

        awarded_medals = AwardedMedals.query.order_by(
            AwardedMedals.awarded_at.desc()
        ).limit(checkboxes - uncheck)
        for awarded_medal in awarded_medals:
            assert awarded_medal.awarded_at.date() == datetime.now().date()

    # TODO: Find a better way to parametrize this
    @pytest.mark.parametrize("medal_id", range(1, 8))
    def test_remove_medal(self, user, testapp, medal_id):
        medal = Medals.query.get(medal_id)
        do = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 1
        ).first()
        if do is None:
            pytest.skip(f"No donors with medal id {medal_id}")
        login(user, testapp)
        detail = testapp.get(url_for("donor.detail", rc=do.rodne_cislo))
        # Medal is there
        assert detail.status_code == 200
        # Find the right form to remove it
        for index, form in detail.forms.items():
            if form.id == "awardMedalForm":
                continue
            if form.fields["medal_id"][0].value == str(medal.id):
                break
        else:
            assert False, "Cannot find the right form for the medal"
        detail = form.submit().follow()
        # Medal is not there anymore
        assert detail.status_code == 200
        assert "Medaile byla úspěšně odebrána" in detail
        do = DonorsOverview.query.get(do.rodne_cislo)
        assert getattr(do, "awarded_medal_" + medal.slug) is False
        assert AwardedMedals.query.get((do.rodne_cislo, medal.id)) is None

    # TODO: Find a better way to parametrize this
    @pytest.mark.parametrize("medal_id", range(1, 8))
    def test_award_one_medal(self, user, testapp, medal_id):
        medal = Medals.query.get(medal_id)
        do = DonorsOverview.query.filter(
            getattr(DonorsOverview, "awarded_medal_" + medal.slug) == 0
        ).first()
        login(user, testapp)
        detail = testapp.get(url_for("donor.detail", rc=do.rodne_cislo))
        # Medal is there
        assert detail.status_code == 200
        # Find the right form to award it
        for index, form in detail.forms.items():
            if form.id == "removeMedalForm":
                continue
            if form.fields["medal_id"][0].value == str(medal.id):
                break
        else:
            assert False, "Cannot find the right form for the medal"
        detail = form.submit().follow()
        # Medal is awarded
        assert detail.status_code == 200
        assert "Medaile udělena." in detail
        do = DonorsOverview.query.get(do.rodne_cislo)
        assert getattr(do, "awarded_medal_" + medal.slug) is True
        awarded_medal = AwardedMedals.query.get((do.rodne_cislo, medal.id))
        assert awarded_medal is not None
        assert awarded_medal.awarded_at.date() == datetime.now().date()

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_medal_amount(self, user, testapp, rodne_cislo):
        skip_if_ignored(rodne_cislo)
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        medal_amount = AwardedMedals.query.filter(
            AwardedMedals.rodne_cislo == rodne_cislo
        ).count()

        assert medal_amount == len(re.findall('title="Odebrat medaili"', res.text))

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_medal_eligibility(self, user, testapp, db, rodne_cislo):
        skip_if_ignored(rodne_cislo)
        do = DonorsOverview.query.get(rodne_cislo)
        medals = Medals.query.all()
        AwardedMedals.query.filter(AwardedMedals.rodne_cislo == rodne_cislo).delete()
        db.session.commit()
        DonorsOverview.refresh_overview(rodne_cislo=do.rodne_cislo)
        login(user, testapp)
        res = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        el_medal_amount = 0
        unel_medal_amount = 0
        for medal in medals:
            if do.donation_count_total >= medal.minimum_donations:
                el_medal_amount += 1
            else:
                unel_medal_amount += 1
        assert el_medal_amount == len(re.findall('title="Udělit medaili"', res.text))
        assert unel_medal_amount == len(re.findall("(Nemá nárok)", res.text))

    def test_award_nonexisting_medal(self, user, testapp):
        awarded = AwardedMedals.query.count()
        login(user, testapp)
        page = testapp.get(url_for("donor.award_prep", medal_slug="br"))
        page.forms["awardMedalForm"].fields["medal_id"][0].value = "foo"
        page = page.forms["awardMedalForm"].submit().follow()
        assert "Odeslána nevalidní data" in page
        assert awarded == AwardedMedals.query.count()

    def test_award_invalid_rc(self, user, testapp):
        awarded = AwardedMedals.query.count()
        login(user, testapp)
        page = testapp.get(url_for("donor.award_prep", medal_slug="br"))
        page.forms["awardMedalForm"].fields["rodne_cislo"][0].force_value("foobarbaz")
        page = page.forms["awardMedalForm"].submit().follow()
        assert "Odeslána nevalidní data" in page
        assert awarded == AwardedMedals.query.count()

    def test_remove_nonexisting_medal(self, user, testapp):
        awarded = AwardedMedals.query.count()
        login(user, testapp)
        # First rodne cislo with some medal and not ignored
        rodne_cislo = (
            AwardedMedals.query.filter(
                AwardedMedals.rodne_cislo.notin_(
                    IgnoredDonors.query.with_entities(IgnoredDonors.rodne_cislo)
                )
            )
            .first()
            .rodne_cislo
        )
        detail = testapp.get(url_for("donor.detail", rc=rodne_cislo))
        # Find the right form to remove it
        for index, form in detail.forms.items():
            if form.id == "removeMedalForm":
                break
        form.fields["medal_id"][0].value = "999"
        detail = form.submit().follow()
        assert "Při odebrání medaile došlo k chybě." in detail
        assert awarded == AwardedMedals.query.count()

    # TODO: Find a better way to parametrize this
    @pytest.mark.parametrize("medal_id", range(4, 8))
    def test_award_prep_medals_yearly(self, db, user, testapp, medal_id):
        medal = Medals.query.get(medal_id)
        rodne_cislo = "9999999999"
        urls = [
            url_for("donor.award_prep", medal_slug=medal.slug),
            url_for("donor.render_envelope_labels", medal_slug=medal.slug),
            url_for(
                "donor.render_award_documents_for_award_prep", medal_slug=medal.slug
            ),
        ]
        # When a donors gets an eligibility for one of the 4 highest medals
        # this year, it will be actually eligible next year.
        # So a fresh import with enough donations does not make
        # the donor eligible.
        batch = Batch(imported_at=datetime.now())
        db.session.add(batch)
        db.session.commit()
        record_params = [
            batch.id,
            rodne_cislo,
            "Charles Philip Arthur George",
            "Mountbatten-Windsor",
            "Buckingham Palace",
            "London",
            "99888",
            "111",
            medal.minimum_donations + 5,
        ]
        # Properties of donor we can find on all tested pages
        search_params = record_params[2:4]
        record = Record.from_list(record_params)
        db.session.add(record)
        db.session.commit()
        DonorsOverview.refresh_overview(rodne_cislo=rodne_cislo)

        login(user, testapp)

        for url in urls:
            page = testapp.get(url)
            assert page.status_code == 200
            for param in search_params:
                assert param not in page

        # But when we move the latest batch to the previous year,
        # the donor is eligible this year.
        batch.imported_at = batch.imported_at - timedelta(days=365)
        db.session.add(batch)
        db.session.commit()

        for url in urls:
            page = testapp.get(url)
            assert page.status_code == 200
            for param in search_params:
                assert param in page
