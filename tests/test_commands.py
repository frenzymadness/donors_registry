from registry.commands import (
    create_user,
    import_emails,
    install_test_data,
    refresh_overview,
)
from registry.donor.models import (
    AwardedMedals,
    DonorsOverride,
    DonorsOverview,
    IgnoredDonors,
    Note,
    Record,
)
from registry.extensions import db
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

    def test_import_emails(self, app):
        runner = app.test_cli_runner()

        # Existing empty note
        note = Note(rodne_cislo="391105000", note="")
        db.session.add(note)

        # Existing note with e-mail already there
        note = Note(rodne_cislo="0457098862", note="foo@example.com")
        db.session.add(note)

        # Existing note with some other content
        note = Note(rodne_cislo="151008110", note="Note\ncontent")
        db.session.add(note)
        db.session.commit()

        result = runner.invoke(import_emails, ["tests/data/emails_import.csv"])
        assert result.exit_code == 0

        assert Note.query.get("391105000").note == "\nfoo@example.com"
        assert Note.query.get("0457098862").note == "foo@example.com"
        assert Note.query.get("9701037137").note == "foo@example.com"
        assert Note.query.get("151008110").note == "Note\ncontent\nfoo@example.com"
        assert Note.query.get("130811802") is None
        assert Note.query.get("0552277759") is None
