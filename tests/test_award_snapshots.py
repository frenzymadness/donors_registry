"""Tests for award eligibility snapshot feature."""

from datetime import datetime, timedelta

import pytest
from flask import url_for

from registry.donor.models import (
    AwardEligibilitySnapshot,
    Batch,
    DonorsOverview,
    Record,
)
from registry.extensions import db
from registry.list.models import DonationCenter, Medals

from .helpers import login


class TestAwardEligibilitySnapshot:
    """Tests for the award eligibility snapshot functionality."""

    @pytest.mark.parametrize("medal_slug", ["br", "st", "zl"])
    def test_snapshot_not_created_for_lower_medals(self, user, testapp, medal_slug):
        """Bronze, silver, and gold medals should not use snapshots (year-round processing)."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == medal_slug).first()
        current_year = datetime.now().year

        # Visit award prep page
        testapp.get(url_for("donor.award_prep", medal_slug=medal_slug))

        # No snapshot should be created
        snapshot_count = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).count()
        assert snapshot_count == 0

    @pytest.mark.parametrize("medal_slug", ["kr3", "kr2", "kr1", "plk"])
    def test_snapshot_not_auto_created_for_higher_medals(
        self, user, testapp, medal_slug
    ):
        """Higher medals should show warning when snapshot doesn't exist, not auto-create."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == medal_slug).first()
        current_year = datetime.now().year

        # Ensure no snapshot exists yet
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        page = testapp.get(url_for("donor.award_prep", medal_slug=medal_slug))

        # Should show warning, not auto-create
        assert "Snapshot pro rok" in page
        assert "nebyl dosud vytvořen" in page
        assert "Vytvořit snapshot" in page  # Button text

        # Should not have created snapshot
        snapshot_count = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).count()
        assert snapshot_count == 0

    @pytest.mark.parametrize("medal_slug", ["kr3", "kr2"])
    def test_manual_snapshot_creation(self, user, testapp, medal_slug):
        """Snapshots should be created manually via button."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == medal_slug).first()
        current_year = datetime.now().year

        # Ensure no snapshot exists
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Create snapshot via POST
        page = testapp.post(
            url_for("donor.create_snapshot", medal_slug=medal_slug)
        ).follow()

        # Should show success message
        assert "Vytvořen snapshot" in page

        # Snapshot should exist
        snapshot_count = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).count()
        assert snapshot_count > 0

        # Second attempt should fail
        page2 = testapp.post(
            url_for("donor.create_snapshot", medal_slug=medal_slug)
        ).follow()
        assert "již existuje" in page2

    @pytest.mark.parametrize("medal_slug", ["br", "st", "zl"])
    def test_create_snapshot_for_non_snapshot_medal(self, user, testapp, medal_slug):
        """Creating snapshot for bronze/silver/gold should fail with error message."""
        login(user, testapp)

        # Try to create snapshot for a medal that doesn't use snapshots
        page = testapp.post(
            url_for("donor.create_snapshot", medal_slug=medal_slug)
        ).follow()

        assert "nevyužívá snapshoty" in page

    def test_snapshot_excludes_donors_who_donated_after_cutoff(self, db):
        """Snapshot should only include donors eligible as of snapshot creation time."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()  # kr3 = 80 donations
        current_year = datetime.now().year

        # Create a donor with 79 donations in the past
        rodne_cislo = "9001010001"
        dc = DonationCenter.query.first()

        # Batch from a week ago with 79 donations
        past_date = datetime.now() - timedelta(days=7)
        batch_past = Batch(
            donation_center_id=dc.id,
            imported_at=past_date,
        )
        db.session.add(batch_past)
        db.session.commit()

        record_past = Record(
            batch_id=batch_past.id,
            rodne_cislo=rodne_cislo,
            first_name="Test",
            last_name="Donor",
            address="Test St.",
            city="Test City",
            postal_code="12345",
            kod_pojistovny="111",
            donation_count=79,
        )
        db.session.add(record_past)
        db.session.commit()

        # Refresh overview and create snapshot NOW
        DonorsOverview.refresh_overview(rodne_cislo=rodne_cislo)
        AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        # Now add 80th donation AFTER snapshot was created
        future_date = datetime.now() + timedelta(days=1)
        batch_future = Batch(
            donation_center_id=dc.id,
            imported_at=future_date,
        )
        db.session.add(batch_future)
        db.session.commit()

        record_future = Record(
            batch_id=batch_future.id,
            rodne_cislo=rodne_cislo,
            first_name="Test",
            last_name="Donor",
            address="Test St.",
            city="Test City",
            postal_code="12345",
            kod_pojistovny="111",
            donation_count=80,
        )
        db.session.add(record_future)
        db.session.commit()

        # Donor should NOT be in snapshot (only had 79 at snapshot creation time)
        eligible = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year, rodne_cislo=rodne_cislo
        ).first()
        assert eligible is None

    def test_snapshot_includes_donors_eligible_at_cutoff(self, db):
        """Snapshot should include donors who met requirements by snapshot creation time."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()  # kr3 = 80 donations
        current_year = datetime.now().year

        # Create a donor with 80 donations before snapshot is created
        rodne_cislo = "9002020002"
        dc = DonationCenter.query.first()

        past_date = datetime.now() - timedelta(days=7)
        batch = Batch(
            donation_center_id=dc.id,
            imported_at=past_date,
        )
        db.session.add(batch)
        db.session.commit()

        record = Record(
            batch_id=batch.id,
            rodne_cislo=rodne_cislo,
            first_name="Eligible",
            last_name="Donor",
            address="Test St.",
            city="Test City",
            postal_code="12345",
            kod_pojistovny="111",
            donation_count=80,
        )
        db.session.add(record)
        db.session.commit()

        # Refresh overview and create snapshot
        DonorsOverview.refresh_overview(rodne_cislo=rodne_cislo)
        AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        # Donor SHOULD be in snapshot
        eligible = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year, rodne_cislo=rodne_cislo
        ).first()
        assert eligible is not None
        assert eligible.rodne_cislo == rodne_cislo

    def test_snapshot_excludes_already_awarded_donors(self, db):
        """Snapshot should not include donors who already have the medal."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Find a donor who already has kr3 medal
        do = DonorsOverview.query.filter(
            DonorsOverview.awarded_medal_kr3.is_(True)
        ).first()

        if do is None:
            pytest.skip("No donors with kr3 medal in test data")

        # Create snapshot
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()
        AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        # Already awarded donor should NOT be in snapshot
        eligible = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year, rodne_cislo=do.rodne_cislo
        ).first()
        assert eligible is None

    def test_snapshot_handles_multiple_donation_centers(self, db):
        """Snapshot should correctly sum donations from multiple centers."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()  # kr3 = 80 donations
        current_year = datetime.now().year

        # Create donor with donations from multiple centers totaling 80
        rodne_cislo = "9003030003"
        dcs = DonationCenter.query.limit(2).all()

        past_date = datetime.now() - timedelta(days=14)

        # 50 donations from first center
        batch1 = Batch(
            donation_center_id=dcs[0].id,
            imported_at=past_date,
        )
        db.session.add(batch1)
        db.session.commit()

        record1 = Record(
            batch_id=batch1.id,
            rodne_cislo=rodne_cislo,
            first_name="Multi",
            last_name="Center",
            address="Test St.",
            city="Test City",
            postal_code="12345",
            kod_pojistovny="111",
            donation_count=50,
        )
        db.session.add(record1)

        # 30 donations from second center
        batch2 = Batch(
            donation_center_id=dcs[1].id,
            imported_at=past_date + timedelta(days=7),
        )
        db.session.add(batch2)
        db.session.commit()

        record2 = Record(
            batch_id=batch2.id,
            rodne_cislo=rodne_cislo,
            first_name="Multi",
            last_name="Center",
            address="Test St.",
            city="Test City",
            postal_code="12345",
            kod_pojistovny="111",
            donation_count=30,
        )
        db.session.add(record2)
        db.session.commit()

        # Refresh overview and create snapshot
        DonorsOverview.refresh_overview(rodne_cislo=rodne_cislo)
        AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        # Donor should be in snapshot (50 + 30 = 80)
        eligible = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year, rodne_cislo=rodne_cislo
        ).first()
        assert eligible is not None

    def test_get_eligible_rodne_cisla_returns_none_when_no_snapshot(self, db):
        """get_eligible_rodne_cisla should return None if snapshot doesn't exist."""
        medal = Medals.query.filter(Medals.slug == "kr1").first()
        current_year = datetime.now().year

        # Ensure no snapshot exists
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Should return None
        result = AwardEligibilitySnapshot.get_eligible_rodne_cisla(
            medal.id, current_year
        )
        assert result is None

    def test_get_eligible_rodne_cisla_returns_list(self, db):
        """get_eligible_rodne_cisla should return list when snapshot exists."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Create snapshot if it doesn't exist
        AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        # Should return list
        result = AwardEligibilitySnapshot.get_eligible_rodne_cisla(
            medal.id, current_year
        )
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0

    def test_snapshot_created_at_timestamp(self, db):
        """Snapshots should have created_at timestamp set."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        before_create = datetime.now()
        AwardEligibilitySnapshot.create_snapshot(medal, current_year)
        after_create = datetime.now()

        snapshots = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).all()

        for snapshot in snapshots:
            assert snapshot.created_at is not None
            assert before_create <= snapshot.created_at <= after_create

    @pytest.mark.parametrize("medal_slug", ["kr3", "kr2"])
    def test_awarding_medal_removes_from_award_prep_list(
        self, user, testapp, medal_slug
    ):
        """After awarding a medal, donor should not appear in award prep (snapshot-based)."""
        login(user, testapp)

        # Visit award prep page
        page = testapp.get(url_for("donor.award_prep", medal_slug=medal_slug))
        form = page.forms.get("awardMedalForm")

        if form is None or "rodne_cislo" not in form.fields:
            pytest.skip(f"No donors eligible for {medal_slug}")

        # Get first eligible donor
        first_rc = form.fields["rodne_cislo"][0].value

        # Award the medal to just this donor
        form.fields["rodne_cislo"][0].checked = True
        # Uncheck others
        for i in range(1, len(form.fields["rodne_cislo"])):
            form.fields["rodne_cislo"][i].checked = False

        page = form.submit().follow()

        # Check the donor is no longer in the list
        form = page.forms["awardMedalForm"]
        remaining_rcs = [f.value for f in form.fields["rodne_cislo"]]
        assert first_rc not in remaining_rcs

    def test_snapshot_count_matches_eligible_donors(self, db):
        """Number of snapshot entries should match eligible, non-awarded donors."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Create snapshot
        count = AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        # Count snapshot entries
        snapshot_count = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).count()

        assert snapshot_count == count

    def test_download_table_with_no_snapshot(self, user, testapp):
        """Download table without snapshot should redirect with error."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Ensure no snapshot exists
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Try to download - should redirect with error
        response = testapp.get(
            url_for("donor.award_prep_download_table", medal_slug="kr3")
        ).follow()

        assert "nebyl dosud vytvořen snapshot" in response
        assert response.status_code == 200

    def test_download_table_with_empty_snapshot(self, user, testapp, db):
        """Download table with empty snapshot should redirect with warning."""
        login(user, testapp)
        medal = Medals.query.filter(
            Medals.slug == "plk"
        ).first()  # plk = 250, likely empty
        current_year = datetime.now().year

        # Create empty snapshot
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Create snapshot (likely empty in test data)
        count = AwardEligibilitySnapshot.create_snapshot(medal, current_year)

        if count > 0:
            # If there are eligible donors, skip this test
            import pytest

            pytest.skip("Test data has eligible plk donors")

        # Try to download - should redirect with warning
        response = testapp.get(
            url_for("donor.award_prep_download_table", medal_slug="plk")
        ).follow()

        assert "neobsahuje žádné oprávněné dárce" in response
        assert response.status_code == 200

    def test_award_documents_respect_snapshot(self, user, testapp):
        """Award documents endpoint should respect snapshots."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Ensure no snapshot exists
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Try to access documents - should redirect with error
        response = testapp.get(
            url_for("donor.render_award_documents_for_award_prep", medal_slug="kr3")
        ).follow()

        assert "nebyl dosud vytvořen snapshot" in response

    def test_envelope_labels_respect_snapshot(self, user, testapp):
        """Envelope labels endpoint should respect snapshots."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Ensure no snapshot exists
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Try to access envelope labels - should redirect with error
        response = testapp.post(
            url_for("donor.render_envelope_labels"),
            {"medal_id": medal.id, "skip": 0},
        ).follow()

        assert "nebyl dosud vytvořen snapshot" in response

    def test_envelope_respect_snapshot(self, user, testapp):
        """Envelope endpoint should respect snapshots."""
        login(user, testapp)
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Ensure no snapshot exists
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # Try to access envelopes - should redirect with error
        response = testapp.post(
            url_for("donor.render_envelope"),
            {"medal_id": medal.id},
        ).follow()

        assert "nebyl dosud vytvořen snapshot" in response

    def test_create_snapshot_twice_returns_same_count(self, db):
        """Calling create_snapshot twice should return the same count without duplicates."""
        medal = Medals.query.filter(Medals.slug == "kr3").first()
        current_year = datetime.now().year

        # Delete any existing snapshot
        AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).delete()
        db.session.commit()

        # First call
        count1 = AwardEligibilitySnapshot.create_snapshot(medal, current_year)
        snapshot_count1 = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).count()

        # Second call (should detect existing and return same count)
        count2 = AwardEligibilitySnapshot.create_snapshot(medal, current_year)
        snapshot_count2 = AwardEligibilitySnapshot.query.filter_by(
            medal_id=medal.id, year=current_year
        ).count()

        # Counts should be identical
        assert count1 == count2
        assert snapshot_count1 == snapshot_count2
