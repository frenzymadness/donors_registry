import re
from datetime import datetime

import pytest
from flask import url_for

from registry.donor.models import AwardedMedals, DonorsOverview, Medals

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

        awarded_medals = AwardedMedals.query.order_by(
            AwardedMedals.awarded_at.desc()
        ).limit(checkboxes - uncheck)
        for awarded_medal in awarded_medals:
            assert awarded_medal.awarded_at.date() == datetime.now().date()

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
        DonorsOverview.refresh_overview()
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
