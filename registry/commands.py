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
    with open("tests/data/imports.csv") as csv_file:
        reader = csv.DictReader(csv_file)
        donation_centers = {}
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

            if donation_center not in donation_centers:
                title = donation_center.replace("_", " ")
                slug = donation_center.lower()
                donation_centers[donation_center] = DonationCenter(
                    title=title, slug=slug
                )
                db.session.add(donation_centers[donation_center])
                db.session.commit()
                db.session.flush()
                print(donation_centers[donation_center])

            if import_date not in batches:
                batches[import_date] = Batch(
                    donation_center=str(donation_centers[donation_center].id),
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
