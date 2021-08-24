import csv
from datetime import datetime
from functools import lru_cache
from itertools import cycle
from random import choice, uniform
from string import ascii_letters, digits

from registry.donor.models import (
    AwardedMedals,
    Batch,
    DonorsOverride,
    DonorsOverview,
    IgnoredDonors,
    Record,
)
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


def award_medal(db, rodne_cislo, medal_id, date):
    awarded_medal = AwardedMedals(
        rodne_cislo=rodne_cislo, medal_id=medal_id, awarded_at=date
    )
    db.session.add(awarded_medal)


def award_medal_if(db, rodne_cislo, medal_id, limit, random_number, date):
    """Helper function for awarding medals"""
    if random_number < limit:
        award_medal(db, rodne_cislo, medal_id, date)


def test_data_medals(db):
    # Get all medals from DB
    medals = {}
    for medal in Medals.query.all():
        medals[medal.slug] = medal

    records = Record.query.with_entities(Record.rodne_cislo).distinct()

    # To simulate the production database, half of the test data has
    # NULL in awarded_at column because medals imported from the old system
    # don't have that information.
    records_count = records.count()
    null_date_count = records_count // 2

    # Add test data for Awarded medals
    for index, record in tqdm(
        enumerate(records),
        desc="Medals for records",
    ):
        rodne_cislo = record[0]

        if index < null_date_count:
            date = None
        else:
            date = datetime.now()

        # Make sure we have at least one person with all medals awarded
        if index == 0:
            for medal in medals.values():
                award_medal(db, rodne_cislo, medal.id, date)
            continue

        # Also, make sure that we have at least one person with no medals awarded
        if index == records_count + 1:
            continue

        random_number = uniform(0, 1)

        # Bronze medal has ~50 % of donors
        award_medal_if(db, rodne_cislo, medals["br"].id, 0.5, random_number, date)
        # Silver medal has ~33 % of donors
        award_medal_if(db, rodne_cislo, medals["st"].id, 0.33, random_number, date)
        # Gold medal has ~19 % of donors
        award_medal_if(db, rodne_cislo, medals["zl"].id, 0.19, random_number, date)
        # Cross level 3 has ~7 % of donors
        award_medal_if(db, rodne_cislo, medals["kr3"].id, 0.07, random_number, date)
        # Cross level 2 has ~3 % of donors
        award_medal_if(db, rodne_cislo, medals["kr2"].id, 0.03, random_number, date)
        # Cross level 1 has ~1 % of donors
        award_medal_if(db, rodne_cislo, medals["kr1"].id, 0.01, random_number, date)
        # Cross level 1 has ~0,5 % of donors
        award_medal_if(db, rodne_cislo, medals["plk"].id, 0.005, random_number, date)

    db.session.commit()


@lru_cache()
def get_test_data_df(lines):
    """Returns test data from imports.csv as Pandas DataFrame"""
    import pandas  # noqa

    return pandas.read_csv(
        "tests/data/imports.csv", dtype={"RC": str, "PSC": str, "POJISTOVNA": str}
    ).head(lines)


def test_data_ignored(db, limit=25):
    duvody = ["Vysoký věk", "Nemoc", "Test"]

    for index, rodne_cislo in tqdm(
        enumerate(Record.query.with_entities(Record.rodne_cislo).distinct()),
        desc="Ignored donors",
    ):
        if index > limit:
            break
        ignored = IgnoredDonors(
            rodne_cislo=rodne_cislo[0],
            reason=choice(duvody),
            ignored_since=datetime.now(),
        )
        db.session.add(ignored)
    db.session.commit()


def random_string(allowed_chars, size):
    return "".join(choice(allowed_chars) for x in range(size))


def random_postal_code():
    return random_string(digits, 5)


def random_kod_pojistovny():
    return random_string(digits, 3)


def test_data_overrides(db, limit=25):
    fields = cycle(DonorsOverview.basic_fields)

    for index, record in tqdm(
        enumerate(Record.query.all()),
        desc="Overrides for donors",
    ):
        if index > limit:
            break
        field = next(fields)

        if field == "postal_code":
            random_value = random_postal_code()
        elif field == "kod_pojistovny":
            random_value = random_kod_pojistovny()
        else:
            random_value = random_string(ascii_letters, len(getattr(record, field)))
        override = DonorsOverride(rodne_cislo=record.rodne_cislo)
        setattr(override, field, random_value)

        db.session.add(override)
    db.session.commit()
