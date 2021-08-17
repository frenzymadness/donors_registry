from registry.commands import create_user, install_test_data, refresh_overview
from registry.donor.models import (
    AwardedMedals,
    DonorsOverride,
    DonorsOverview,
    IgnoredDonors,
    Record,
)
from registry.user.models import User


class TestCommands:
    def test_add_user(self, app):
        email = "test_user_1@example.com"
        runner = app.test_cli_runner()
        runner.invoke(create_user, [email, "supersecretpass"])
        user = User.query.filter(User.email == email)
        assert user is not None

    def test_install_test_data_refresh_overview(self, app):
        limit = 10
        runner = app.test_cli_runner()

        # Clean the database.
        AwardedMedals.query.delete()
        Record.query.delete()
        DonorsOverview.query.delete()
        DonorsOverride.query.delete()

        result = runner.invoke(install_test_data, ["--limit", limit])
        assert result.exit_code == 0

        # Forget all ignored donors so we can check
        # the overview table.
        IgnoredDonors.query.delete()

        records = Record.query.count()
        assert records == limit

        result = runner.invoke(refresh_overview)
        assert result.exit_code == 0
        unique_do = DonorsOverview.query.count()
        unique_records = (
            Record.query.with_entities(Record.rodne_cislo).distinct().count()
        )
        assert unique_do == unique_records
