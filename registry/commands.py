"""Commands for CLI"""
import csv
from datetime import datetime

import click
from flask import Flask

from registry.donor.models import Batch, DonationCenter, Record
from registry.extensions import db
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


@app.cli.command("install-test-data")
def install_test_data():
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
                donation_count=int(float(donation_count)) if donation_count else 0,
            )
            db.session.add(record)

    db.session.commit()
