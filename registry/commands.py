"""Commands for CLI"""
import csv
from datetime import datetime
from random import uniform

import click
from flask import Flask

from registry.donor.models import AwardedMedals, Batch, DonationCenter, Record
from registry.extensions import db
from registry.list.models import Medals
from registry.user.models import User

app = Flask(__name__)


@app.cli.command("create-user")
@click.argument("email")
@click.argument("password")
def create_user(email, password):
    user = User(email, password)
    user.active = True
    db.session.add(user)
    db.session.commit()


@app.cli.command("install-test-data")  # noqa: C901
def install_test_data():  # noqa: C901
    with open("tests/data/imports.csv", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        donation_centers = {}
        for item in DonationCenter.query.all():
            donation_centers[item.slug] = item
        batches = {}
        for row in reader:
            (
                id,
                rodne_cislo,
                first_name,
                last_name,
                address,
                city,
                postal_code,
                kod_pojistovny,
                donation_count,
                donation_center,
                import_date,
            ) = tuple(row.values())

            if donation_center != "jinde" and donation_center not in donation_centers:
                # This should not happen, all donation centers should
                # already be in the database
                raise RuntimeError(
                    "Donation center from test data is not present in DB."
                )
            elif donation_center == "jinde":
                donation_center_id = None
            else:
                donation_center_id = str(donation_centers[donation_center].id)

            if import_date not in batches:
                batches[import_date] = Batch(
                    donation_center=donation_center_id,
                    imported_at=datetime.strptime(import_date, "%Y-%m-%d %H:%M:%S"),
                )
                db.session.add(batches[import_date])
                db.session.commit()
                print(batches[import_date])

            record = Record(
                batch=batches[import_date].id,
                rodne_cislo=rodne_cislo,
                first_name=first_name,
                last_name=last_name,
                address=address,
                city=city,
                postal_code=postal_code,
                kod_pojistovny=kod_pojistovny,
                donation_count=donation_count,
            )
            db.session.add(record)

    db.session.commit()

    def award_medal(rodne_cislo, medal_id):
        """Helper function for awarding medals"""
        awarded_medal = AwardedMedals(rodne_cislo=rodne_cislo, medal=medal_id)
        db.session.add(awarded_medal)

    # Get all medals from DB
    medals = {}
    for medal in Medals.query.all():
        medals[medal.slug] = medal

    # Add test data for Awarded medals
    for index, record in enumerate(
        Record.query.with_entities(Record.rodne_cislo).distinct()
    ):
        rodne_cislo = record[0]

        # Make sure we have at least one person with all medals awarded
        if index == 0:
            for medal in medals.values():
                award_medal(rodne_cislo, medal.id)
            continue

        random_number = uniform(0, 1)

        # Bronze medal has ~50 % of donors
        if random_number < 0.5:
            award_medal(rodne_cislo, medals["br"].id)
        else:
            continue
        # Silver medal has ~33 % of donors
        if random_number < 0.33:
            award_medal(rodne_cislo, medals["st"].id)
        else:
            continue
        # Gold medal has ~19 % of donors
        if random_number < 0.19:
            award_medal(rodne_cislo, medals["zl"].id)
        else:
            continue
        # Cross level 3 has ~7 % of donors
        if random_number < 0.07:
            award_medal(rodne_cislo, medals["kr3"].id)
        else:
            continue
        # Cross level 2 has ~3 % of donors
        if random_number < 0.03:
            award_medal(rodne_cislo, medals["kr2"].id)
        else:
            continue
        # Cross level 1 has ~1 % of donors
        if random_number < 0.01:
            award_medal(rodne_cislo, medals["kr1"].id)
        else:
            continue

    db.session.commit()
