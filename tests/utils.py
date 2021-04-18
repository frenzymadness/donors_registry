import csv
from datetime import datetime
from functools import lru_cache
from random import uniform

import pandas

from registry.donor.models import AwardedMedals, Batch, Record
from registry.list.models import DonationCenter, Medals

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(iterable, **kwargs):
        return iterable


def test_data_records(db, limit=None):
    with open("tests/data/imports.csv", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        donation_centers = {}
        for item in DonationCenter.query.all():
            donation_centers[item.slug] = item
        batches = {}
        for index, row in tqdm(enumerate(reader), desc="Records"):
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

            if limit is not None and index > limit:
                break

            if donation_center != "manual" and donation_center not in donation_centers:
                # This should not happen, all donation centers should
                # already be in the database
                raise RuntimeError(
                    "Donation center from test data is not present in DB."
                )
            elif donation_center == "manual":
                donation_center_id = None
            else:
                donation_center_id = str(donation_centers[donation_center].id)

            if import_date not in batches:
                batches[import_date] = Batch(
                    donation_center_id=donation_center_id,
                    imported_at=datetime.strptime(import_date, "%Y-%m-%d %H:%M:%S"),
                )
                db.session.add(batches[import_date])
                db.session.commit()

            record = Record(
                batch_id=batches[import_date].id,
                rodne_cislo=rodne_cislo,
                first_name=first_name,
                last_name=last_name,
                address=address,
                city=city,
                postal_code=postal_code,
                kod_pojistovny=kod_pojistovny,
                donation_count=int(float(donation_count)),
            )
            db.session.add(record)

    db.session.commit()

    records_count = Record.query.count()
    batches_count = Batch.query.count()

    print(f"Imported {records_count} records in {batches_count} batches")


def award_medal(db, rodne_cislo, medal_id):
    awarded_medal = AwardedMedals(rodne_cislo=rodne_cislo, medal_id=medal_id)
    db.session.add(awarded_medal)


def award_medal_if(db, rodne_cislo, medal_id, limit, random_number):
    """Helper function for awarding medals"""
    if random_number < limit:
        award_medal(db, rodne_cislo, medal_id)


def test_data_medals(db):
    # Get all medals from DB
    medals = {}
    for medal in Medals.query.all():
        medals[medal.slug] = medal

    # Add test data for Awarded medals
    for index, record in tqdm(
        enumerate(Record.query.with_entities(Record.rodne_cislo).distinct()),
        desc="Medals for records",
    ):
        rodne_cislo = record[0]

        # Make sure we have at least one person with all medals awarded
        if index == 0:
            for medal in medals.values():
                award_medal(db, rodne_cislo, medal.id)
            continue

        random_number = uniform(0, 1)

        # Bronze medal has ~50 % of donors
        award_medal_if(db, rodne_cislo, medals["br"].id, 0.5, random_number)
        # Silver medal has ~33 % of donors
        award_medal_if(db, rodne_cislo, medals["st"].id, 0.33, random_number)
        # Gold medal has ~19 % of donors
        award_medal_if(db, rodne_cislo, medals["zl"].id, 0.19, random_number)
        # Cross level 3 has ~7 % of donors
        award_medal_if(db, rodne_cislo, medals["kr3"].id, 0.07, random_number)
        # Cross level 2 has ~3 % of donors
        award_medal_if(db, rodne_cislo, medals["kr2"].id, 0.03, random_number)
        # Cross level 1 has ~1 % of donors
        award_medal_if(db, rodne_cislo, medals["kr1"].id, 0.01, random_number)
        # Cross level 1 has ~0,5 % of donors
        award_medal_if(db, rodne_cislo, medals["plk"].id, 0.005, random_number)

    db.session.commit()


@lru_cache()
def get_test_data_df(lines):
    """Returns test data from imports.csv as Pandas DataFrame"""
    return pandas.read_csv(
        "tests/data/imports.csv", dtype={"RC": str, "PSC": str, "POJISTOVNA": str}
    ).head(lines)
