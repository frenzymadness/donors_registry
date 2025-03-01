"""Commands for CLI"""

import csv
import re
from collections import Counter

import click
from flask import current_app
from flask.cli import with_appcontext

from registry.donor.models import DonorsOverview, Note
from registry.extensions import db
from registry.user.models import User
from registry.utils import EMAIL_RE
from tests.utils import (
    test_data_ignored,
    test_data_medals,
    test_data_overrides,
    test_data_records,
)


@click.command()
@click.argument("email")
@click.argument("password")
@with_appcontext
def create_user(email, password):
    """Create Flask user for given email and password."""
    user = User(email, password)
    user.active = True
    db.session.add(user)
    db.session.commit()


@click.command()
@click.option("--limit", default=None)
@with_appcontext
def install_test_data(limit):
    """Install test data from files to database."""
    # Turn off SQLAlchemy logging (produces thousands of SQL queries)
    current_app.config["SQLALCHEMY_ECHO"] = False

    test_data_records(db, limit=int(limit) if limit else None)
    test_data_medals(db)
    test_data_ignored(db)
    test_data_overrides(db)
    DonorsOverview.refresh_overview()


@click.command("refresh-overview")
@with_appcontext
def refresh_overview():
    """Refresh DonorsOverview table."""
    DonorsOverview.refresh_overview()


@click.command("import-emails")
@click.argument("csv_file")
@with_appcontext
def import_emails(csv_file):
    """Import e-mails from CVS file to donors' notes"""
    current_app.config["SQLALCHEMY_ECHO"] = False
    counter = Counter()

    with open(csv_file, encoding="utf-8") as file:
        reader = csv.reader(file)

        for row in reader:
            name, surname, rodne_cislo, email = row

            if not email:
                continue

            # Fix most common typos in e-mails
            if " " in email or "," in email:
                email = email.replace(" ", "")
                email = email.replace(",", ".")

            if not re.match(EMAIL_RE, email):
                print("Invalid e-mail:", email)
                counter["invalid emails"] += 1
                continue

            donor = DonorsOverview.query.get(rodne_cislo)

            if not donor:
                continue

            note = Note.query.get(rodne_cislo)

            if note:
                if email in note.note:
                    print("E-mail:", email, "already in the note for", rodne_cislo)
                    counter["already in the db"] += 1
                else:
                    note.note += "\n" + email
                    db.session.add(note)
                    print("E-mail:", email, "added for", rodne_cislo)
                    counter["added to existing notes"] += 1
            else:
                note = Note(rodne_cislo=rodne_cislo, note=email)
                db.session.add(note)
                print("New note for", rodne_cislo, "created with", email)
                counter["new notes created"] += 1

    db.session.commit()

    print(counter)
